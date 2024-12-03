---
tags:
    - Customization/ Model-Distillation
    - API-Usage-Example
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/custom-models/model_distillation/Distillation-via-S3-input.ipynb){:target="_blank"}"

<h3>Introduction</h3>

Model distillation in Amazon Bedrock allows you to create smaller, more efficient models while maintaining performance by learning from larger, more capable models. This guide demonstrates how to use the Amazon Bedrock APIs to implement model distillation using:
**JSONL training data available in Amazon S3 bucket**.

Through this API usage notebook, we'll explore the complete distillation workflow, from configuring teacher and student models to deploying the final distilled model. You'll learn how to:

- Set up and configure distillation jobs
- Prepare and format training data for distillation
- Upload and use training data from S3
- Manage model provisioning and deployment
- Run inference with distilled models

The guide covers essential API operations including:
- Creating and configuring distillation jobs
- Managing training data sources in S3
- Handling model deployments
- Implementing production best practices using boto3 and the Bedrock SDK

While model distillation offers benefits like improved efficiency and reduced costs, this guide focuses on the practical implementation details and API usage patterns needed to successfully execute distillation workflows in Amazon Bedrock.

<h3>Best Practices and Considerations</h3>

When using model distillation:
1. Ensure your training data is diverse and representative of your use case
2. Monitor distillation metrics in the S3 output location
3. Evaluate the distilled model's performance against your requirements
4. Consider cost-performance tradeoffs when selecting model units for deployment

The distilled model should provide faster responses and lower costs while maintaining acceptable performance for your specific use case.

<h3>Setup and Prerequisites</h3>

Before we begin, make sure you have the following:

- An active AWS account with appropriate permissions
- Amazon Bedrock access enabled in your preferred region
- An S3 bucket for storing training data and output
- Training data in JSONL format
- Sufficient service quota to use Provisioned Throughput in Bedrock
- An IAM role with the following permissions:

IAM Policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR_DISTILLATION_OUTPUT_BUCKET",
                "arn:aws:s3:::YOUR_DISTILLATION_OUTPUT_BUCKET/*",
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateModelCustomizationJob",
                "bedrock:GetModelCustomizationJob",
                "bedrock:ListModelCustomizationJobs",
                "bedrock:StopModelCustomizationJob"
            ],
            "Resource": "arn:aws:bedrock:YOUR_REGION:YOUR_ACCOUNT_ID:model-customization-job/*"
        }
    ]
}
```

Trust Relationship:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "bedrock.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "YOUR_ACCOUNT_ID"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:bedrock:YOUR_REGION:YOUR_ACCOUNT_ID:model-customization-job/*"
                }
            }
        }
    ]
}
```

<h3>Dataset</h3>
As an example, in this notebook we will be using the `Uber10K dataset`.

First, let's set up our environment and import required libraries.


```python
# upgrade boto3 
%pip install --upgrade pip --quiet
%pip install boto3 --upgrade --quiet
```


```python
# restart kernel
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```

<h2> Model Selection and Configuration</h2>

When selecting models for distillation, consider the following factors:

1. Performance targets
2. Latency requirements
3. Total Cost of Ownership (TCO)

Let's set up our configuration parameters for the distillation process.

(We're using Amazon Nova/Micro as the example teacher/student models in this code sample. Please change it based on your use case, and run code sample in **supporting region**)


```python
import json
import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from utils import create_s3_bucket, upload_training_data_to_s3, delete_s3_bucket_and_contents, \
create_model_distillation_role_and_permissions, delete_role_and_attached_policies, delete_distillation_buckets

# Create Bedrock client
bedrock_client = boto3.client(service_name="bedrock")

# Create runtime client for inference
bedrock_runtime = boto3.client(service_name='bedrock-runtime')

# Region and accountID
session = boto3.session.Session()
region = session.region_name
sts_client = session.client('sts')
account_id = sts_client.get_caller_identity()['Account']

# define bucket you want to create and upload the dataset to:
bucket_name='<YOUR-DISTILLATION-BUCKET-NAME>' # Replace by your bucket name
data_prefix = '<PREFIX>' # Replace by your defined prefix

# configure teacher nd student model
teacher_model = "amazon.nova-pro-v1:0"
student_model_micro = "amazon.nova-micro-v1:0:128k"
```

<h2>Prepare Dataset for Model Distillation</h2>

Before we start the distillation process, we need to prepare our dataset. We'll create a function to convert our input data into the format required by Amazon Bedrock.

<h3>Model Distillation Input Format</h3>

The training data must follow the Bedrock conversation schema in JSONL format. Each line should be a valid JSON object with this structure:

```json
{
    "schemaVersion": "bedrock-conversation-2024",
    "system": [
        {
            "text": <Your-System-Prompt>
        }
    ],
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": <Your-Prompt-And-OR-Context>
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "text": <Your-Ground-Truth-Response>
                }
            ]
        }
    ]
}
```

Key formatting requirements:
- Each line must be a complete JSON object
- The schemaVersion field must be specified as `bedrock-conversation-2024`
- System instructions should be included in the system array
- Messages (including any context) must include both user and assistant roles in the correct order
- All text content must be wrapped in the appropriate content structure


```python
def prepare_training_dataset(input_file, output_file, system_message):
    try:
        # Create the base conversation template
        conversation_template = {
            "schemaVersion": "bedrock-conversation-2024",
            "system": [{"text": system_message}],
            "messages": []
        }
        
        # Process input file and write output
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            # Read input file line by line
            for line in infile:
                if line.strip():  # Skip empty lines
                    # Parse the input JSON line
                    input_data = json.loads(line)
                    
                    # Create a new conversation for each line
                    conversation = conversation_template.copy()
                    
                    # Add user message
                    user_message = {
                        "role": "user",
                        "content": [{"text": input_data["prompt"]}]
                    }
                    
                    # Add assistant message
                    assistant_message = {
                        "role": "assistant",
                        "content": [{"text": input_data["completion"]}]
                    }
                    
                    # Add messages to conversation
                    conversation["messages"] = [user_message, assistant_message]
                    
                    # Write the conversation to output file
                    outfile.write(json.dumps(conversation) + '\n')
                
        print(f"Successfully converted {input_file} to Bedrock format and saved to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return False
```

<h3>Now that we have our data preparation function, let's use it to create our distillation dataset.</h3>


```python
system_message = """You are a specialized financial analyst assistant trained to analyze SEC filings, financial documents, and regulatory submissions. Your role is to:
- Extract and interpret key information from 10-K, 10-Q, and other SEC filings
- Provide accurate, factual responses based solely on the provided document context
- Focus on specific financial, legal, and corporate governance details
- Present information clearly and concisely without speculation
- Maintain accuracy in reporting numbers, dates, and regulatory details
When responding, only use information explicitly stated in the provided context."""

input_data_file = 'SampleData/uber10K.jsonl'
output_data_file = 'model_distillation_dataset.jsonl'

prepare_training_dataset(
    input_file=input_data_file,
    output_file=output_data_file,
    system_message=system_message
)
```


```python
# Generate unique names for the job and model
job_name = f"distillation-job-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
model_name = f"distilled-model-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"

# Configure models and IAM role
role_name, role_arn = create_model_distillation_role_and_permissions(bucket_name=bucket_name, account_id=account_id)

# creating training data bucket
create_s3_bucket(bucket_name=bucket_name)

# Specify S3 locations
training_data = upload_training_data_to_s3(bucket_name, output_data_file, prefix=data_prefix)
output_path = f"s3://{bucket_name}/output/"

# Set maximum response length
max_response_length = 1000
```

<h2>Starting the Distillation Job</h2>

With our dataset prepared, we can now start the distillation job. We'll use the `create_model_customization_job` API to do this.


```python
response = bedrock_client.create_model_customization_job(
    jobName=job_name,
    customModelName=model_name,
    roleArn=role_arn,
    baseModelIdentifier=student_model_micro,
    customizationType="DISTILLATION",
    trainingDataConfig={
        "s3Uri": training_data
    },
    outputDataConfig={
        "s3Uri": output_path
    },
    customizationConfig={
        "distillationConfig": {
            "teacherModelConfig": {
                "teacherModelIdentifier": teacher_model,
                "maxResponseLengthForInference": max_response_length 
            }
        }
    }
)
```

<h3>Monitoring the Distillation Job</h3>

After starting the distillation job, it's important to monitor its progress. We can use the `get_model_customization_job` API to check the status of our job.


```python
# Record the distillation job arn
job_arn = response['jobArn']

# print job status
job_status = bedrock_client.get_model_customization_job(jobIdentifier=job_arn)["status"]
print(job_status)
```

<h3>Deploying the Distilled Model</h3>

Once the distillation job is complete, we can deploy our distilled model. This involves creating a Provisioned Throughput model instance.


```python
# Deploy the distilled model
custom_model_id = bedrock_client.get_model_customization_job(jobIdentifier=job_arn)['outputModelArn']
distilled_model_name = f"distilled-model-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"

provisioned_model_id = bedrock_client.create_provisioned_model_throughput(
    modelUnits=1,
    provisionedModelName=distilled_model_name,
    modelId=custom_model_id 
)['provisionedModelArn']
```

<h2>Clean Up</h2>
Let's delete the resources that were created in this notebook. `Uncomment` the code below to delete the resources.


```python
# # delete bucket and dataset
# delete_distillation_buckets(bucket_name)

# delete role and its policy:
# delete_role_and_attached_policies(role_name=role_name)

# delete provisioned throughput:
# response = bedrock_client.delete_provisioned_model_throughput(provisionedModelId=provisioned_model_id)
```

<h2>Conclusion</h2>

In this guide, we've walked through the entire process of model distillation using Amazon Bedrock. We covered:

1. Setting up the environment
2. Preparing the dataset
3. Configuring and starting a distillation job
4. Monitoring the job's progress
5. Deploying the distilled model
6. Cleaning up resources

Model distillation is a powerful technique that can help you create more efficient models tailored to your specific use case. By following this guide, you should now be able to implement model distillation in your own projects using Amazon Bedrock.

Remember to always consider your specific use case requirements when selecting models and configuring the distillation process. 

**Happy distilling!**
