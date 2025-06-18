# Structured Data Retrieval using Amazon Bedrock Knowledge Bases

This repository demonstrates how to implement Structured Data Retrieval using Amazon Bedrock Knowledge Bases with Amazon S3, AWS Glue, and Amazon Redshift. The demo shows how to query structured data using natural language and receive natural language responses summarizing the data.

Read more about how Amazon Bedrock Knowledge Bases allows you to connect to structured data stores [here](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-structured.html).

## Overview

The project consists of two main notebooks that demonstrate:
1. Data ingestion and setup (structured-rag-s3-glue-ingestion.ipynb)
2. Knowledge Base creation and querying (structured-rag-using-kb-and-glue.ipynb)

### Features

- Natural language querying of structured data
- SQL query generation from natural language
- Support for both Redshift Serverless and Provisioned clusters
- Integration with AWS Glue Data Catalog
- Data retrieval using Amazon Bedrock Knowledge Bases APIs

## Prerequisites

- AWS Account with appropriate permissions
- Python 3.x
- AWS CLI configured
- Required Python packages (installed via pip):
  - boto3
  - pandas
  - awswrangler
  - ipywidgets
  - tabulate

## Setup Instructions

### 1. Data Ingestion (structured-rag-s3-glue-ingestion.ipynb)

1. Downloads e-commerce dataset from Kaggle
2. Creates S3 bucket and uploads data
3. Sets up AWS Glue Crawler and creates catalog
4. Creates Redshift Serverless/Provisioned infrastructure
5. Validates data ingestion

### 2. Knowledge Base Creation (structured-rag-using-kb-and-glue.ipynb)

1. Creates Knowledge Base execution role
2. Configures Knowledge Base with structured database
3. Sets up data sources
4. Starts ingestion jobs
5. Demonstrates query capabilities using:
   - RetrieveAndGenerate API
   - Retrieve API
   - Generate Query API

## Usage

1. First run the `structured-rag-s3-glue-ingestion.ipynb` notebook to set up your data infrastructure
2. Then run the `structured-rag-using-kb-and-glue.ipynb` notebook to create and test the Knowledge Base
3. Follow the notebook instructions for cleaning up resources when finished

## Configuration

Key configuration parameters needed:

```python
# Redshift Serverless Configuration
workgroup_id = '<your-workgroup-id>'
redshiftDBName = '<your-database-name>'

# AWS Glue Configuration
bucketName = '<your-bucket-name>'
glueDatabaseName = '<your-database-name>'
glueTableName = '<your-table-name>'
```

## Cleanup
Both notebooks include cleanup sections to remove created resources:

1. S3 buckets
2. Glue databases and crawlers
3. Redshift clusters/workgroups
4. IAM roles and policies
5. Knowledge Bases

## Important Notes

1. Ensure proper IAM permissions are set up before running the notebooks
2. Follow the cleanup instructions to avoid unnecessary AWS charges
3. The demo uses an e-commerce dataset as an example, but can be adapted for other datasets
4. Support for both Redshift Serverless and Provisioned configurations

## Contributing
We welcome community contributions! Please ensure your sample aligns with [AWS best practices](_!https://aws.amazon.com/architecture/well-architected/_), and please update the Contents section of this README file with a link to your sample, along with a description.