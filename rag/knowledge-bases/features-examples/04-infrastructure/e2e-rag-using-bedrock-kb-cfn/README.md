# Deploy e2e RAG solution (using Knowledgebases for Amazon Bedrock) via CloudFormation


This is a complete setup for automatic deployment of end-to-end RAG workflow using Knowledge Bases for Amazon Bedrock. 
Following resources will get created and deployed:
- IAM role
- Open Search Serverless Collection and Index
- Set up Data Source (DS) and Knowledge Base (KB)

## Pre-requisite:
- You already have s3 bucket where your documents are stored
- The documents must be in one of the following supported formats- .txt,.md, .html, doc/.docx, .csv, xls/.xlsx, .pdf

## Solution Deployment:

### Step 1 : Prepare templates for deployment
`deploy.sh` script will create a S3 deployment bucket, upload the required artifacts it, and prepare the CloudFormation templates for deployment. 
         
         a.	If you run this script without [args], this will create a deployment bucket with default name - 'e2e-rag-deployment-${ACCOUNT_ID}-${AWS_REGION}'

         b.	If you run this script with [args], this will create a deployment bucket with the name provided in second args- '<BUCKET_NAME>-${ACCOUNT_ID}-${AWS_REGION}'

Run the included `deploy.sh` script as shown below:

    -  git clone https://github.com/aws-samples/amazon-bedrock-samples.git
    
    -  cd knowledge-bases/04-infrastructure/e2e-rag-deployment-using-bedrock-kb-cfn

    -  bash deploy.sh (For Windows users it may be different)

Once deploy.sh script run is finished, go to the deployment bucket created and copy the `main-template-out.yml` S3 URL for Step 2

### Step 2 : Deploy stacks

Using AWS Console:

    - 1. Go to AWS CloudFormation Console and choose 'Template source' as Amazon S3 URL

    - 2. Enter the 'Main CloudFormation template S3 URL' (noted in step 1) in Amazon S3 URL text box.

    - 3. Specify the RAG workflow details with the options fitting your use case

    - 4. In the Configure stack options section, add optional tags, permissions, and other advanced settings

    - 5. Click Submit

## Testing the RAG Workflow

Deployment may take 7-10 minutes.
After successful deployment, 

- Go to Amazon Bedrock Console and select the Knowledge Base which is created
- Click on the `sync` button to start the ingestion job
- Once data is sync, selected the Foundation Model of your choice and ask query

Done!!
