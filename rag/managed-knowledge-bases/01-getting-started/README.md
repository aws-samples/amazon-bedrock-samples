# 01 — Getting Started

Create your first Bedrock Managed Knowledge Base, ingest documents, and query.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | [01-create-bmkb-s3.ipynb](01-create-bmkb-s3.ipynb) | Create a managed KB with S3, ingest, query with Retrieve & AgenticRetrieveStream |


## What you'll learn

- Create a managed KB with zero infrastructure (Bedrock manages the vector store)
- Use the managed default embedding model (no extra cost) or specify a custom one
- Ingest documents with Smart Parsing
- Query with `Retrieve` (raw chunks) and `AgenticRetrieveStream` (with optional generation)
- Enable CloudWatch log delivery for ingestion tracking
