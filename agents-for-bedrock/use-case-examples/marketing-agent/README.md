
# Bedrock Agent for generating marketing content

## Introduction
Marketing effectiveness hinges heavily on creative content, with personalized material proving especially impactful. However, crafting such tailored content has long been a formidable obstacle for marketers, demanding significant time and resources. This challenge is particularly acute for small and medium-sized businesses (SMBs), where scaling personalized content creation can seem insurmountable. Enter generative AI: a game-changing technology that empowers marketers to produce personalized creative content efficiently and at scale, even with constrained resources. This innovation is democratizing personalized marketing, allowing businesses of all sizes to compete more effectively in the digital landscape.


## Prerequisites

Before installing the AWS CDK, ensure you have the following:

- Node.js (version 20.15.1 or later)
- npm (usually comes with Node.js)
- Python 3.9 or higher and pip and virtualenv
- Docker 27.0.3 or higher
- AWS CLI [installed](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
- [AWS CDK v2](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install) installed
- An AWS account with the following permissions:
  - Create and manage IAM roles and policies.
  - Create and invoke AWS Lambda functions.
  - Create, Read from, and Write to Amazon S3 buckets.
  - Access and manage Amazon Bedrock agents and models.
  - Create and manage Amazon DynamoDB.
  - Create and manage OpenSearch Serverless Collection.
  - Access to Amazon Bedrock foundation models (Anthropic’s Claude 3 haiku and sonnet model for this solution)

## Installation

1. Clone the repository to your local machine or AWS environment, set up a virtual environment and activate it and install required Python packages using below code:
```bash
git clone https://github.com/aws-samples/amazon-bedrock-samples.git
cd ./amazon-bedrock-samples/agents-for-bedrock/use-case-examples/marketing-agent
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

2. Deploymant
```bash
cdk deploy --context region=us-east-1
```

3. Cleaning Up
```bash
cdk destroy --context region=us-east-1
```

