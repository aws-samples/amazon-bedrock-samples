# Bedrock Managed Knowledge Base Samples

## Build production-ready RAG applications — fully managed by Amazon Bedrock

[Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-build-managed.html) ◆ [API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/) ◆ [Pricing](https://aws.amazon.com/bedrock/pricing/)

Welcome to the Bedrock Managed Knowledge Base Samples repository!

With a **Bedrock Managed Knowledge Base**, Amazon Bedrock manages the ingestion, storage, indexing, and retrieval infrastructure for you. You provide your data sources and Bedrock manages the data ingestion pipeline, datastore setup, and retrieval optimization — including embedding and reranking with service-managed models by default at no additional cost.

This collection provides examples and tutorials to help you understand, implement, and integrate Bedrock Managed Knowledge Bases into your applications.

## 📁 Repository Structure

### 🚀 [01-getting-started/](01-getting-started/)

**Your First Managed Knowledge Base**

Create a KB, ingest documents, and query with the Retrieve and AgenticRetrieveStream APIs.

- [01-create-bmkb-s3.ipynb](01-getting-started/01-create-bmkb-s3.ipynb) — Create a managed KB with S3 data source, ingest, and query

### 🧩 [02-feature-examples/](02-feature-examples/)

**Feature Deep Dives**

Focused examples for individual managed KB capabilities:

- [01-data-connectors/](02-feature-examples/01-data-connectors/) — Web Crawler,  <span style="color:red">[ Confluence, SharePoint, OneDrive, Google Drive, Custom - coming soon]</span>
- [02-chunking-and-parsing/](02-feature-examples/02-chunking-and-parsing/) — chunking strategies, Multi-modal RAG using Smart Parsing & advance indexing
- [03-retrieval-optimization/](02-feature-examples/03-retrieval-optimization/) — Hybrid search, metadata filtering, agentic retrieval deep dive
- [04-rag-evaluation/](02-feature-examples/04-rag-evaluation/) — Synthetic Q&A generation, Bedrock evaluation jobs <span style="color:red">[coming soon]</span>
- [05-observability/](02-feature-examples/05-observability/) — CloudWatch metrics, OTEL spans, vended logs <span style="color:red">[coming soon]</span>
- [06-responsible-ai/](02-feature-examples/06-responsible-ai/) — Bedrock Guardrails integration <span style="color:red">[coming soon]</span>

### 💡 [03-use-case-example/](03-use-case-example/)

**Complete Applications**

End-to-end patterns that combine multiple capabilities:

- [01-end-to-end-example-with-ac-gateway/](03-use-case-example/01-end-to-end-example-with-ac-gateway/) — KB + AgentCore Gateway + Strands Agent + full-stack observability

## Quick Start

### Step 1: Prerequisites

- An AWS account with credentials configured (`aws configure`)
- Python 3.10+
- Model access enabled in [Amazon Bedrock console](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html)
- AWS Permissions: `AmazonBedrockFullAccess` + IAM permissions for role/policy creation

### Step 2: Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Run your first notebook

```bash
jupyter notebook 01-getting-started/01-create-bmkb-s3.ipynb
```

## Key Capabilities

| Capability | Description | Cost |
|-----------|-------------|------|
| **Managed Embedding** | Built-in embedding model optimized for accuracy | Included (no extra cost) |
| **Managed Reranking** | Built-in semantic reranker | Included (no extra cost) |
| **Custom Embedding** | Choose any Bedrock embedding model (float32, 1024 dims) | Additional cost |
| **Custom Reranking** | Choose your reranker model at query time | Additional cost |
| **7 Native Connectors** | S3, SharePoint, Confluence, Web Crawler, Google Drive, OneDrive, Custom | — |
| **Smart Parsing** | Built-in multi-modal parser (PDF, images, audio, video) | — |
| **Agentic Retrieval** | Query decomposition + iterative retrieval + generation | — |
| **AgentCore Gateway** | MCP-based tool server for agent access | — |
| **Observability** | CloudWatch metrics, OTEL spans, vended logs | — |

## Supported Retrieval APIs

| API | What it does | `generate_response` |
|-----|-------------|---------------------|
| **Retrieve** | Returns raw chunks with relevance scores | N/A |
| **AgenticRetrieveStream** | Agentic sub-query decomposition + retrieval | `False` → chunks only |
| **AgenticRetrieveStream** | Agentic retrieval + synthesized answer with citations | `True` (default) |

> **Note:** `RetrieveAndGenerate` is not supported for Managed Knowledge Bases. Use `AgenticRetrieveStream` with `generate_response=True` instead.

## Embedding & Reranking Models

```python
from utils.managed_knowledge_base import ManagedKnowledgeBase

# Option 1: Use managed defaults (no extra cost)
kb = ManagedKnowledgeBase(
    kb_name="my-kb",
    bucket_name="my-bucket",
)

# Option 2: Specify custom embedding model (additional cost)
kb = ManagedKnowledgeBase(
    kb_name="my-kb",
    bucket_name="my-bucket",
    embedding_model="amazon.titan-embed-text-v2:0",
)

# At query time — managed reranker (default, no extra cost)
result = kb.agentic_retrieve_stream(query, model_arn)

# At query time — custom reranker (additional cost)
result = kb.agentic_retrieve_stream(
    query, model_arn,
    reranking_model_type='CUSTOM',
    reranking_model_arn='arn:aws:bedrock:us-west-2::foundation-model/cohere.rerank-v3-5:0'
)
```
## Chunking Strategies

Managed KBs support configurable chunking per data source:

```python
# Default chunking (~300 tokens, sentence-aware) — no config needed
kb = ManagedKnowledgeBase(kb_name="my-kb", bucket_name="my-bucket")

# Fixed-size chunking (custom token size + overlap)
kb = ManagedKnowledgeBase(
    kb_name="my-kb",
    data_sources=[{
        'type': 'S3',
        'bucket_name': 'my-bucket',
        'chunking_strategy': 'FIXED_SIZE',
        'max_tokens': 500,
        'overlap_percentage': 20,
    }],
)

# No chunking (each file = 1 chunk, for pre-split documents)
kb = ManagedKnowledgeBase(
    kb_name="my-kb",
    data_sources=[{
        'type': 'S3',
        'bucket_name': 'my-bucket',
        'chunking_strategy': 'NONE',
    }],
)
```

| Strategy | Description | When to use |
|----------|-------------|-------------|
| **Default** (recommended) | ~300 tokens, honors sentence boundaries | Most use cases |
| **Fixed-size** | Configurable token size + overlap % | Need more context or more precision |
| **No chunking** | 1 file = 1 chunk | Pre-processed/pre-split documents |

> **Note:** Semantic and Hierarchical chunking are only available for Customer-managed Knowledge Bases.

## Advanced Indexing

Extract visual, audio, and video content beyond text:

```python
# Enable image extraction (charts, diagrams from PDFs/DOCX/PPT)
kb = ManagedKnowledgeBase(
    kb_name="my-kb",
    data_sources=[{
        'type': 'S3',
        'bucket_name': 'my-bucket',
        'enable_image_extraction': True,
        'enable_audio_extraction': True,   # .mp3, .wav, .m4a, .flac, .ogg
        'enable_video_extraction': True,   # .mp4, .mov, .m4v
    }],
)
```

| Toggle | File types | What gets indexed |
|--------|-----------|-------------------|
| `enable_image_extraction` | PDF, DOCX, PPT, HTML | Descriptions of charts, diagrams, screenshots |
| `enable_audio_extraction` | MP3, WAV, M4A, FLAC, OGG | Audio transcriptions |
| `enable_video_extraction` | MP4, MOV, M4V | Video content descriptions |



## 🔗 Related Links

- [Build a managed knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-build-managed.html)
- [Create a managed knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-create.html)
- [Observability for managed knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-observability.html)
- [Connect through AgentCore Gateway](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-gateway-target.html)
- [AgentCore Samples](https://github.com/awslabs/agentcore-samples)
- [Supported regions](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-regions.html)
- [Service quotas](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-quotas.html)

## 🤝 Contributing

We welcome contributions! When adding samples:
- Follow the existing notebook structure (config → create → ingest → query → cleanup)
- Use the shared `utils/managed_knowledge_base.py` utility
- Include `enable_logging=True` for observability
- Use managed defaults (embedding + reranking) unless demonstrating custom models

## 📄 License

This project is licensed under the Apache License 2.0.
