# Managed Knowledge Base — CDK Deployment

Deploy an end-to-end Bedrock Managed Knowledge Base using AWS CDK (Python).

## What it creates

| Resource | Description |
|----------|-------------|
| S3 Bucket | Document storage (auto-created or use existing) |
| IAM Role | KB execution role with S3, CloudWatch, FM policies |
| Managed KB | `Type: MANAGED` with embedding model |
| S3 Data Source | `MANAGED_KNOWLEDGE_BASE_CONNECTOR` with Smart Parsing |

## Comparison: Managed KB vs DIY KB CDK

| | Managed KB (this project) | DIY KB (e2e_rag_using_bedrock_kb_cdk) |
|---|---|---|
| Stacks | 1 (single stack) | 3 (role + vector store + KB) |
| Vector store | Not needed | OpenSearch Serverless / Aurora |
| Resources | ~5 | ~12+ |
| Config complexity | Simple | Complex (index mappings, collection policies) |

## Quick Start

### 1. Prerequisites

```bash
npm install -g aws-cdk
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

Edit `config.py`:
```python
class EnvSettings:
    ACCOUNT_ID = "123456789012"  # Your AWS account
    ACCOUNT_REGION = "us-west-2"  # Your region

class DsConfig:
    S3_BUCKET_NAME = ""  # Leave empty to auto-create
    S3_PREFIX = "documents/"
```

### 3. Deploy

```bash
cdk bootstrap  # First time only
cdk deploy
```

### 4. Upload documents and ingest

```bash
# Upload documents
aws s3 cp octank_financial_10K.pdf s3://<bucket-name>/documents/

# Start ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <kb-id> \
  --data-source-id <ds-id>
```

### 5. Query

```python
import boto3
client = boto3.client('bedrock-agent-runtime')
response = client.retrieve(
    knowledgeBaseId='<kb-id>',
    retrievalQuery={'text': 'What is the total revenue?'},
    retrievalConfiguration={'managedSearchConfiguration': {'numberOfResults': 5}}
)
```

## Configuration Options

| Config | Default | Options |
|--------|---------|---------|
| `EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Any supported Bedrock embedding model |
| `CHUNKING_STRATEGY` | `DEFAULT` | `DEFAULT`, `FIXED_SIZE`, `NONE` |
| `MAX_TOKENS` | 500 | Any int (for FIXED_SIZE) |
| `OVERLAP_PERCENTAGE` | 20 | 0-100 (for FIXED_SIZE) |
| `S3_BUCKET_NAME` | Auto-create | Existing bucket name |
| `S3_PREFIX` | `documents/` | Any S3 prefix |

## Key Implementation Note

The `connector_parameters` field in the data source is a **free-form JSON dict**. All keys inside must be **camelCase** (API format), not snake_case or PascalCase:

```python
connector_parameters={
    "type": "S3",              # camelCase
    "version": "1",
    "connectionConfiguration": {  # camelCase
        "bucketName": "...",      # camelCase
    },
}
```

## Cleanup

```bash
cdk destroy
# Then manually delete the S3 bucket (retained by default)
aws s3 rm s3://<bucket-name> --recursive
aws s3 rb s3://<bucket-name>
```

## Project Structure

```
managed_kb_cdk/
├── app.py              # CDK app entry point
├── config.py           # Configuration (edit this)
├── cdk.json            # CDK config
├── requirements.txt    # Python dependencies
├── stacks/
│   ├── __init__.py
│   └── managed_kb_stack.py  # Single stack: S3 + IAM + KB + DataSource
└── README.md
```
