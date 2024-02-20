# Text to SQL Bedrock Agent

This repository contains the necessary files to set up and test a Text to SQL conversion using the Bedrock Agent with AWS services.

## Authors:
Pedram Jahangiri @jpedram, Sawyer Hirt @sawyehir, Suyin Wang @suyinwa, Zeek Granston @zeekg 


## Prerequisites

Before you begin, ensure you have the following:
- An AWS account with the following permissions:
  - `IAMFullAccess`
  - `AWSLambda_FullAccess`
  - `AmazonS3FullAccess`
  - `AmazonBedrockFullAccess`
- For local setup, 
        - Python and Jupyter Notebooks installed
        - AWS CLI installed and configured
- For AWS SageMaker 
    - Make sure your domain has above permission 
    - use Data Science 3.0 kernel in SageMaker Studio

## Installation

Clone the repository to your local machine or AWS environment:

git clone git@ssh.gitlab.aws.dev:jpedram/text_2_sql_bedrock_agent.git


## Usage

1. Start by opening the `create_and_invoke_sql_agent.ipynb` Jupyter Notebook.
2. Run the notebook cells in order. The notebook will:
   - Import configurations from `config.py`.
   - Set your own 'AWS_PROFILE' if running locally, if using AWS sagemaker notebook just comment "os.environ['AWS_PROFILE']" 
   - Build the necessary infrastructure using `build_infrastructure.py`, which includes:
     - S3 buckets
     - Lambda functions
     - Bedrock agents
     - Glue databases and crawlers
     - Necessary IAM roles and policies
3. After the infrastructure is set up, you can execute sample queries within the notebook to test the agent.
4. To delete all resources created and avoid ongoing charges, run the clean.py script, in the notebook.

