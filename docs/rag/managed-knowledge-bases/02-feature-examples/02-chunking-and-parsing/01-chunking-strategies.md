---
tags:
    - RAG
    - Knowledge Bases
    - API-Usage-Example
---

[Open in GitHub](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/rag/managed-knowledge-bases/02-feature-examples/02-chunking-and-parsing/01-chunking-strategies.ipynb)

<h2>Chunking Strategies for Bedrock Managed Knowledge Bases</h2>

This notebook demonstrates the different text chunking strategies available for **Bedrock Managed Knowledge Bases**.

<h3>Supported chunking strategies</h3>

| Strategy | Description | When to use |
|----------|-------------|-------------|
| **Default** (recommended) | Splits text into chunks of ~300 tokens, honoring sentence boundaries | Most use cases — good balance of precision and context |
| **Fixed-size** | Splits text into your configured token size with overlap | When you need control over chunk size for specific retrieval patterns |
| **No chunking** | Each file is treated as a single chunk | Pre-processed documents already split into individual files |

> **Note:** Semantic chunking and Hierarchical chunking are only available for Customer-managed Knowledge Bases, not Bedrock Managed KBs.

<h3>How chunking works</h3>

```
Source Document
    │
    ▼
Managed Parser (extracts text from PDF, DOCX, etc.)
    │
    ▼
Chunking Strategy (splits text into retrievable pieces)
    │
    ├── Default: ~300 tokens per chunk
    ├── Fixed-size: N tokens + overlap %
    └── No chunking: 1 file = 1 chunk
    │
    ▼
Embedding → Vector Store → Retrieval
```

<h3>What this notebook does</h3>

1. Creates 3 Managed KBs with the same data but different chunking strategies
2. Ingests the same document into each
3. Queries each KB and compares chunk sizes, counts, and retrieval quality
4. Cleans up all resources

<h3>Prerequisites</h3>

- AWS credentials with Bedrock and IAM permissions
- S3 bucket with documents (or uses the shared synthetic dataset)
- Python 3.10+


```python
%pip install --upgrade pip --quiet
%pip install -r ../../requirements.txt --quiet
```


```python
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```


```python
import warnings
warnings.filterwarnings('ignore')
```

<h2>Step 1 — Configuration</h2>

Explicit chunking settings require a custom embedding model rather than the managed default.
Both KBs use Titan Text Embeddings V2 so the comparison changes only the chunking strategy.
Custom embeddings incur additional charges; ensure the model is available in your Region.


```python
import boto3
import sys
import time
import os
import json
import logging
import pprint

sys.path.insert(0, "../..")

s3_client = boto3.client('s3')
sts_client = boto3.client('sts')
session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()['Account']

logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

suffix = time.strftime('%Y%m%d%H%M%S', time.localtime())[-7:]

# ── Configuration ─────────────────────────────────────────────────────
bucket_name = f'bedrock-bmkb-chunking-{suffix}-{account_id}'

# Explicit chunking requires a custom embedding model (additional charges apply).
# Use the same model for both KBs to isolate the effect of chunking.
embedding_model = 'amazon.titan-embed-text-v2:0'

# Generation model for AgenticRetrieveStream
region_prefix_map = {'us-': 'us', 'eu-': 'eu', 'ap-': 'apac'}
cris_prefix = next((v for k, v in region_prefix_map.items() if region.startswith(k)), 'us')
generation_model_arn = f'arn:aws:bedrock:{region}:{account_id}:inference-profile/{cris_prefix}.anthropic.claude-haiku-4-5-20251001-v1:0'

pp = pprint.PrettyPrinter(indent=2)

print(f'Region:     {region}')
print(f'Account:    {account_id}')
print(f'Bucket:     {bucket_name}')
print(f'Embedding:  {embedding_model or "managed default (no extra cost)"}')
print(f'Generation: {generation_model_arn}')
```

<h2>Step 2 — Create S3 bucket and upload test document</h2>


```python
# Create bucket
try:
    s3_client.head_bucket(Bucket=bucket_name)
    print(f'Bucket {bucket_name} already exists')
except Exception:
    print(f'Creating bucket {bucket_name}')
    if region == 'us-east-1':
        s3_client.create_bucket(Bucket=bucket_name)
    else:
        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})

# Upload Octank Financial 10K
file_to_upload = '../../synthetic_dataset/octank_financial_10K.pdf'
print(f'Uploading {file_to_upload}')
s3_client.upload_file(file_to_upload, bucket_name, 'octank_financial_10K.pdf')
print('Done.')
```

<h2>Step 3 — Create KB with Default Chunking</h2>

Default chunking splits text into chunks of ~300 tokens, honoring sentence boundaries.
This is the recommended strategy for most use cases.


```python
from utils.managed_knowledge_base import ManagedKnowledgeBase

# Default chunking — no chunking config needed (service default)
kb_default = ManagedKnowledgeBase(
    kb_name=f'bmkb-chunk-default-{suffix}',
    bucket_name=bucket_name,
    embedding_model=embedding_model,
    enable_logging=True,
    region_name=region,
    suffix=f'default-{suffix}',
)

print(f'\nDefault Chunking KB: {kb_default.kb_id}')

# Ingest
time.sleep(15)
kb_default.start_ingestion_job()
```

<h2>Step 4 — Create KB with Fixed-Size Chunking</h2>

Fixed-size chunking lets you control the exact chunk size. Useful when you want:
- Larger chunks (more context per retrieval) — e.g., 500-1000 tokens
- Smaller chunks (more precise retrieval) — e.g., 100-200 tokens
- Overlap between chunks to avoid cutting context at boundaries

> **Note:** For Managed KBs, chunking is configured per data source via the `vectorIngestionConfiguration`.


```python
# Fixed-size chunking — 500 tokens with 20% overlap
kb_fixed = ManagedKnowledgeBase(
    kb_name=f'bmkb-chunk-fixed-{suffix}',
    data_sources=[{
        'type': 'S3',
        'bucket_name': bucket_name,
        'chunking_strategy': 'FIXED_SIZE',
        'max_tokens': 500,
        'overlap_percentage': 20,
    }],
    embedding_model=embedding_model,
    enable_logging=True,
    region_name=region,
    suffix=f'fixed-{suffix}',
)

print(f'\nFixed-Size Chunking KB: {kb_fixed.kb_id}')
print(f'  max_tokens=500, overlap=20%')

# Ingest
time.sleep(15)
kb_fixed.start_ingestion_job()
```

<h2>Step 5 — Query and Compare Chunk Characteristics</h2>

Compare retrieval results between chunking strategies.


```python
query = "What is Octank Financial's total revenue and key risk factors?"

# Default chunking results
print('=== Default Chunking (~300 tokens) ===')
response = kb_default.retrieve(query, num_results=5)
chunks = response.get('retrievalResults', [])
print(f'Chunks returned: {len(chunks)}')
for i, chunk in enumerate(chunks[:3], 1):
    text = chunk['content']['text']
    token_est = len(text.split())  # rough token estimate
    print(f'  {i}. score={chunk["score"]:.4f} | ~{token_est} tokens | {text[:100]}...')
avg_default = sum(len(c['content']['text'].split()) for c in chunks) / len(chunks) if chunks else 0
print(f'  Average chunk size: ~{avg_default:.0f} tokens')

# Fixed-size chunking results
print(f'\n=== Fixed-Size Chunking (500 tokens, 20% overlap) ===')
response = kb_fixed.retrieve(query, num_results=5)
chunks = response.get('retrievalResults', [])
print(f'Chunks returned: {len(chunks)}')
for i, chunk in enumerate(chunks[:3], 1):
    text = chunk['content']['text']
    token_est = len(text.split())
    print(f'  {i}. score={chunk["score"]:.4f} | ~{token_est} tokens | {text[:100]}...')
avg_fixed = sum(len(c['content']['text'].split()) for c in chunks) / len(chunks) if chunks else 0
print(f'  Average chunk size: ~{avg_fixed:.0f} tokens')

# Comparison
print(f'\n=== Comparison ===')
print(f'  Default: ~{avg_default:.0f} tokens/chunk')
print(f'  Fixed:   ~{avg_fixed:.0f} tokens/chunk')
print(f'  Fixed-size chunks are {avg_fixed/avg_default:.1f}x larger → more context per retrieval')
```

<h2>Step 6 — AgenticRetrieveStream with Default Chunking</h2>


```python
result = kb_default.agentic_retrieve_stream(
    query=query,
    model_arn=generation_model_arn,
    generate_response=True,
)

print('=== AgenticRetrieveStream (Default Chunking) ===')
if result.get('generated_response'):
    print(f"Answer:\n{result['generated_response']['answer']}")
    print(f"\nChunks used: {len(result['results'])}")
    print(f"Citations: {len(result['generated_response'].get('citations', []))}")
else:
    print(f"Chunks retrieved: {len(result['results'])}")
    for i, r in enumerate(result['results'][:3], 1):
        print(f"  {i}. {r['content']['text'][:120]}...")
```

<h2>Step 7 — Cleanup</h2>


```python
# Uncomment to delete all resources
# kb_default.delete_kb(delete_iam=True)
# kb_fixed.delete_kb(delete_iam=True, delete_s3_bucket=True)
```

<h2>Summary</h2>

<h3>Chunking strategies for Bedrock Managed KBs</h3>

| Strategy | Token size | Overlap | Best for |
|----------|-----------|---------|----------|
| **Default** | ~300 tokens | Sentence-aware | Most use cases |
| **Fixed-size** | Configurable | Configurable % | Specific retrieval needs |
| **No chunking** | Entire file | N/A | Pre-split documents |

<h3>Key takeaways</h3>

- **Default chunking** works well for most documents — start here
- **Fixed-size** gives control when you need larger context (500+ tokens) or more precision (100-200 tokens)
- **No chunking** is for pre-processed data where each file is already a single logical unit
- Chunking is configured per **data source**, not per KB — you can have different strategies for different connectors
- Parsing strategy for Managed KBs is always **Managed parser** (not configurable)

<h3>Not available for Managed KBs</h3>

- Semantic chunking (uses FM, additional cost — Customer-managed only)
- Hierarchical chunking (Customer-managed only)
- Custom Lambda transformation

<h3>Documentation</h3>

- [How content chunking works](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html)
- [ChunkingConfiguration API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_ChunkingConfiguration.html)
- [Create a managed knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-create.html)
