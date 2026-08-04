# Infrastructure as Code — Managed Knowledge Base

Deploy a complete Bedrock Managed Knowledge Base stack using CloudFormation or CDK.

## Templates

| Directory | Type | Description |
|-----------|------|-------------|
| `managed_kb_cfn/` | CloudFormation | Single YAML template — S3 + IAM + KB + data source |
| `managed_kb_cdk/` | CDK (Python) | Python CDK app with configurable options |

## What it creates

```
┌─────────────────────────────────────────────────────────┐
│ Stack Resources                                         │
│                                                         │
│  ┌─────────────┐    ┌──────────────────────────────┐   │
│  │ S3 Bucket   │───▶│  Managed Knowledge Base      │   │
│  │ (documents) │    │  + S3 Data Source             │   │
│  └─────────────┘    │  + Smart Parsing             │   │
│                     └──────────────────────────────┘   │
│  ┌─────────────┐                                       │
│  │ IAM Role    │  S3 + CloudWatch + FM (optional)      │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

## Quick Start — CloudFormation

```bash
# Deploy (uses managed default embedding — no extra cost)
aws cloudformation create-stack \
  --stack-name my-managed-kb \
  --template-body file://managed_kb_cfn/managed-kb-s3-cfn.yaml \
  --parameters ParameterKey=KnowledgeBaseName,ParameterValue=my-bmkb \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-west-2

# Wait
aws cloudformation wait stack-create-complete --stack-name my-managed-kb

# Get outputs
aws cloudformation describe-stacks --stack-name my-managed-kb \
  --query 'Stacks[0].Outputs' --output table

# Upload docs + ingest
aws s3 cp octank_financial_10K.pdf s3://<bucket>/documents/
aws bedrock-agent start-ingestion-job --knowledge-base-id <kb-id> --data-source-id <ds-id>
```

## Quick Start — CDK

```bash
cd managed_kb_cdk
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Edit config.py with your account/region
cdk bootstrap
cdk deploy
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `KnowledgeBaseName` | `bmkb-cfn-demo` | Name for the KB |
| `BucketName` | Auto-generated | S3 bucket (leave empty for auto) |
| `S3Prefix` | `documents/` | Prefix to scope ingestion |
| `EmbeddingModel` | `MANAGED` | `MANAGED` (free) or custom model ID |

## Key implementation note

`ConnectorParameters` inside `ManagedKnowledgeBaseConnectorConfiguration` is a **free-form JSON field**. All keys must be **camelCase** (API format), not PascalCase:

```yaml
# CFN — ConnectorParameters uses camelCase keys
ConnectorParameters:
  type: S3
  version: '1'
  connectionConfiguration:
    bucketName: my-bucket
    bucketOwnerAccountId: '123456789012'
```

```python
# CDK — same camelCase in the dict
connector_parameters={
    "type": "S3",
    "version": "1",
    "connectionConfiguration": {
        "bucketName": bucket_name,
        "bucketOwnerAccountId": account_id,
    },
}
```

## Cleanup

```bash
# CFN
aws s3 rm s3://<bucket> --recursive
aws cloudformation delete-stack --stack-name my-managed-kb

# CDK
cdk destroy
aws s3 rb s3://<bucket> --force  # bucket retained by default
```


## Documentation

- [AWS::Bedrock::KnowledgeBase](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrock-knowledgebase.html)
- [AWS::Bedrock::DataSource](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrock-datasource.html)
- [Connect a data source (Managed KB)](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-connect-ds.html)
- [Create a managed knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-create.html)
