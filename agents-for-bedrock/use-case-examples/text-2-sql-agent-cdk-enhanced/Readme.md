# Text to SQL Bedrock Agent CDK Enhanced

## Authors:
- **Pedram Jahangiri** [@iut62elec](https://github.com/iut62elec)

## Reviewer:
- **Maira Ladeira Tanke** [@mttanke](https://github.com/mttanke)

## Introduction
Harnessing the power of natural language processing, the "Text to SQL Bedrock Agent" facilitates the automatic transformation of natural language questions into executable SQL queries. This tool bridges the gap between complex database structures and intuitive human inquiries, enabling users to effortlessly extract insights from data using simple English prompts. It leverages AWS Bedrock's cutting-edge agent technology and exemplifies the synergy between AWS's robust infrastructure and advanced large language models offered in AWS Bedrock, making sophisticated data analysis accessible to a wider audience. This repository contains the necessary files to set up and test a Text to SQL conversion using the Bedrock Agent with AWS services.

## Use Case
The code here sets up an agent capable of crafting SQL queries from natural language questions. It then retrieves responses from the database, providing accurate answers to user inquiries. The diagram below outlines the high-level architecture of this solution.

The Agent is designed to:
- Retrieve database schemas
- Execute SQL queries

## Differences from [text-2-sql-agent](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-for-bedrock/use-case-examples/text-2-sql-agent)


This repository enhances the original Text to SQL Bedrock Agent with the following improvements:

- Uses AWS CDK to build the necessary infrastructure.
- Works with any dataset: simply create a folder with all your data in CSV files, create a zip file of this folder, place it in the "Data" directory, and the code will automatically extract and upload the files, generating the necessary instructions. Provide the zip file name at the time of deployment (cdk deploy --profile XXX --context zip_file_name=EV_WA.zip --context region=us-east-1).
- If the answer is large, it creates a file in S3 and points the user to the S3 location.




## Prerequisites
Before you begin, ensure you have the following:
- AWS CLI installed and configured with the necessary permissions
- Node.js and npm
- Python 3.9 or higher and pip
- Access to Amazon Bedrock foundation models (Before you can use a foundation model in Amazon Bedrock, you must request access to it. Use this Link for detail https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- An AWS account (AWS_PROFILE) with the following permissions:
  - Create and manage IAM roles and policies.
  - Create and invoke AWS Lambda functions.
  - Create, read from, and write to Amazon S3 buckets.
  - Access and manage Amazon Bedrock agents and models.
  - Create and manage Amazon Glue databases and crawlers.
  - Execute queries and manage workspaces in Amazon Athena.
  - Access to Amazon Bedrock foundation models (Anthropic’s Claude 3 Sonnet model for this solution)



## Installation
Clone the repository to your local machine or AWS environment, set up a virtual environment and activate it and install the AWS CDK and required Python packages using below code:

```bash
git clone https://github.com/aws-samples/amazon-bedrock-samples.git
cd ./amazon-bedrock-samples/agents-for-bedrock/use-case-examples/text-2-sql-agent-cdk-enhanced
export AWS_PROFILE=XXX
python3.9 -m venv .venv
source .venv/bin/activate
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
chmod +x setup.sh
./setup.sh
```

## Deployment 
Deploy the stack using the AWS CDK. 
If you want to run this with sample data, use the data provided as an example, which is "EV_WA.zip" in the "Data" directory. This is public data from [Electric Vehicle Population Data](https://catalog.data.gov/dataset/electric-vehicle-population-data). This dataset shows the Battery Electric Vehicles (BEVs) and Plug-in Hybrid Electric Vehicles (PHEVs) that are currently registered through the Washington State Department of Licensing (DOL). For the purpose of this repository, the data was split into 4 CSV files by the author. 

```bash
cdk bootstrap --profile XXX --context zip_file_name=EV_WA.zip
cdk deploy --profile XXX --context zip_file_name=EV_WA.zip --context region=us-east-1
```

Feel free to use this for your own data. If you want to deploy with your own data on your existing infrastructure, you can do that. Just make sure to stop your crawler schedule, then deploy with the new data, and then resume the schedule. However, if it is a fresh deployment with your data, you don't need to do anything extra.

## Usage
After deployment is finished, wait for 2 minute for the first crawling of database to complete. Then go to the AWS Bedrock console, navigate to the agent section, find your agent, and test your agent with a question, for example:

"What are the 5 model years and types of electric vehicles available in Thurston County?"

## Data
This project uses the Electric Vehicle Population Data, which is under the Open Data Commons Open Database License (ODbL) v1.0. You can find the dataset [here](https://catalog.data.gov/dataset/electric-vehicle-population-data) and the license details [here](https://opendatacommons.org/licenses/odbl/1-0/).

### Conditions for Use:
- You will cite the dataset in your documentation/scientific publication as appropriate.
- You will include a link to the source of the original dataset with the dataset.
- You will abide by the terms of the ODbL license for attribution and attachment of the license to data.
- You will prominently identify the data as being under the ODbL license. Our customers need to be made aware of the usage in a way that allows them to make reasoned decisions.


### Citation:
This dataset shows the Battery Electric Vehicles (BEVs) and Plug-in Hybrid Electric Vehicles (PHEVs) that are currently registered through the Washington State Department of Licensing (DOL). For the purpose of this repository, the data was split into 4 CSV files by the author. 


## Cleaning Up

To delete all resources created and avoid ongoing charges, run .

```bash
cdk destroy --profile XXX --context zip_file_name=EV_WA.zip --context region=us-east-1
```