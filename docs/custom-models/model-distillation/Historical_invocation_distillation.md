---
tags:
    - Customization/ Model-Distillation
    - API-Usage-Example
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/custom-models/model_distillation/Historical_invocation_distillation.ipynb){:target="_blank"}"

<h3>Introduction</h3>
Model distillation in Amazon Bedrock allows you to create smaller, more efficient models while maintaining performance by learning from larger, more capable models. This guide demonstrates how to use the Amazon Bedrock APIs to implement model distillation using:
**historical model invocation logs**.

Through this API usage notebook, we'll explore the complete distillation workflow, from configuring teacher and student models to deploying the final distilled model. You'll learn how to set up distillation jobs, manage training data sources, handle model deployments, and implement production best practices using boto3 and the Bedrock SDK.

The guide covers essential API operations including:
- Creating and configuring distillation jobs
- Invoke model to generate invocation logs using ConverseAPI
- Working with historical invocation logs in your account to create distillation job
- Managing model provisioning and deployment
- Running inference with distilled models


While model distillation offers benefits like improved efficiency and reduced costs, this guide focuses on the practical implementation details and API usage patterns needed to successfully execute distillation workflows in Amazon Bedrock.

<h3>Best Practices and Considerations</h3>

When using model distillation:
1. Ensure your training data is diverse and representative of your use case
2. Monitor distillation metrics in the S3 output location
3. Evaluate the distilled model's performance against your requirements
4. Consider cost-performance tradeoffs when selecting model units for deployment

The distilled model should provide faster responses and lower costs while maintaining acceptable performance for your specific use case.


<h3>Setup and Prerequisites</h3>

Before starting with model distillation, ensure you have the following:

<h4>Required AWS Resources:</h4>
- An AWS account with appropriate permissions
- Amazon Bedrock access enabled in your preferred region
- An S3 bucket for storing invocation logs 
- An S3 bucket to store output metrics
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
                "arn:aws:s3:::YOUR_INVOCATION_LOG_BUCKET",
                "arn:aws:s3:::YOUR_INVOCATION_LOG_BUCKET/*"
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
As an example, in this notebook we will be using Uber10K dataset, which already contains a system prompt and the relevant contexts to the question in each prompt. 


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


```python
import json
import boto3
from datetime import datetime

# Create Bedrock client
bedrock_client = boto3.client(service_name="bedrock")

# Create runtime client for inference
bedrock_runtime = boto3.client(service_name='bedrock-runtime')

# Region and accountID
session = boto3.session.Session()
region = session.region_name
sts_client = session.client('sts')
account_id = sts_client.get_caller_identity()['Account']
```

<h3>Model selection</h3>
When selecting models for distillation, consider:
1. Performance targets
2. Latency requirements
3. Total Cost of Ownership


```python
# Setup teacher and student model pairs
teacher_model_id = "meta.llama3-1-70b-instruct-v1:0"
student_model = "meta.llama3-1-8b-instruct-v1:0:128k"
```

<h3>Step 1. Configure Model Invocation Logging using the API</h3>

In this example, we only store loggings to S3 bucket, but you can optionally enable logging in Cloudwatch as well. 


```python
# S3 bucket and prefix to store invocation logs
s3_bucket_for_log = "<YOUR S3 BUCKET TO STORE INVOCATION LOGS>"
prefix_for_log = "<PREFIX FOR LOG STORAGE>" # Optional
```


```python
def setup_s3_bucket_policy(bucket_name, prefix, account_id, region):
    s3_client = boto3.client('s3')
    
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AmazonBedrockLogsWrite",
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": [
                     f"arn:aws:s3:::{bucket_name}/{prefix}/AWSLogs/{account_id}/BedrockModelInvocationLogs/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }
    
    bucket_policy_string = json.dumps(bucket_policy)
    
    try:
        response = s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=bucket_policy_string
        )
        print("Successfully set bucket policy")
        return True
    except Exception as e:
        print(f"Error setting bucket policy: {str(e)}")
        return False
```


```python
# Setup bucket policy
setup_s3_bucket_policy(s3_bucket_for_log, prefix_for_log, account_id, region)

# Setup logging configuration
bedrock_client.put_model_invocation_logging_configuration(
    loggingConfig={
        's3Config': {
            'bucketName': s3_bucket_for_log,
            'keyPrefix': prefix_for_log
        },
        'textDataDeliveryEnabled': True,
        'imageDataDeliveryEnabled': True,
        'embeddingDataDeliveryEnabled': True
    }
)
```

<h3>Step 2. Invoke teacher model to generate logs</h3>

We're using [ConverseAPI](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html) in this example, but you can also use [InvokeModel API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html) in Bedrock.

We will invoke `Llama3.1 70b` to generate response on `Uber10K` dataset for each input prompt


```python
# Setup inference params
inference_config = {"maxTokens": 2048, "temperature": 0.1, "topP": 0.9}
request_metadata = {"job_type": "Uber10K",
                    "use_case": "RAG",
                    "invoke_model": "llama31-70b"}
```

<div class="alert alert-block alert-warning">
The following code sample takes about 30mins to complete, which invokes teacher model to generate invocation logs
</div>


```python
with open('SampleData/uber10K.jsonl', 'r', encoding='utf-8') as file:
    for line in file:
        data = json.loads(line)

        prompt = data['prompt']

        conversation = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]

        response = bedrock_runtime.converse(
            modelId=teacher_model_id,
            messages=conversation,
            inferenceConfig=inference_config,
            requestMetadata=request_metadata
        )

        response_text = response["output"]["message"]["content"][0]["text"]
```

<h3>Step 3. Configure and submit distillation job using historical invocation logs</h3>

Now we have enough logs in our S3 bucket, let's configure and submit our distillation job using historical invocation logs

<div class="alert alert-block alert-warning">
Please make sure to update <b>role_arn</b> and <b>output_path</b> in the following code sample
</div>


```python
# Generate unique names for the job and model
job_name = f"distillation-job-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
model_name = f"distilled-model-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"

# Set maximum response length
max_response_length = 1000

# Setup IAM role
role_arn = "arn:aws:iam::<YOUR_ACCOUNT_ID>:role/<YOUR_IAM_ROLE>" # Replace by your IAM role configured for distillation job (Update everything starting with < and ending with >)

# Invocation_logs_data
invocation_logs_data = f"s3://{s3_bucket_for_log}/{prefix_for_log}/AWSLogs"
output_path = "s3://<YOUR_BUCKET>/output/"
```


```python
# Configure training data using invocation logs
training_data_config = {
    'invocationLogsConfig': {
        'usePromptResponse': True, # By default it is set as "False"
        'invocationLogSource': {
            's3Uri': invocation_logs_data
        },
        'requestMetadataFilters': { # Replace by our filter
            'equals': {"job_type": "Uber10K"},
            'equals': {"use_case": "RAG"},
            'equals': {"invoke_model": "llama31-70b"},
        }
    }
}
```


```python
# Create distillation job with invocation logs
response = bedrock_client.create_model_customization_job(
    jobName=job_name,
    customModelName=model_name,
    roleArn=role_arn,
    baseModelIdentifier=student_model,
    customizationType="DISTILLATION",
    trainingDataConfig=training_data_config,
    outputDataConfig={
        "s3Uri": output_path
    },
    customizationConfig={
        "distillationConfig": {
            "teacherModelConfig": {
                "teacherModelIdentifier": teacher_model_id,
                "maxResponseLengthForInference": max_response_length
            }
        }
    }
)
```

<h3>Step 4. Monitoring distillation job status</h3>

After submitted your distillation job, you can run the following code to monitor the job status

<div class="alert alert-block alert-warning">
Please be aware that distillation job could run for up to 7 days
</div>


```python
# Record the distillation job arn
job_arn = response['jobArn']

# print job status
job_status = bedrock_client.get_model_customization_job(jobIdentifier=job_arn)["status"]
print(job_status)
```

<div class="alert alert-block alert-warning">
Proceed to following sections only when the status shows <b>Complete</b>
</div>

<h3>Step 5. Deploying the Distilled Model</h3>

After distillation is complete, you'll need to set up Provisioned Throughput to use the model.


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

Check the provisioned throughput status, proceed until it shows **InService**


```python
# print pt status
pt_status = bedrock_client.get_provisioned_model_throughput(provisionedModelId=provisioned_model_id)['status']
print(pt_status)
```

<h3>Step 6. Run inference with provisioned throughput units</h3>

In this example, we use ConverseAPI to invoke the distilled model, you can use both InvokeModel or ConverseAPI to generate response.


```python
# Example inference with the distilled model
input_prompt = "<Your input prompt here>"  # Replace by your input prompt
```


```python
conversation = [ 
    {
        "role": "user", 
        "content": [{"text": input_prompt}], 
    } 
]
inferenceConfig = {
    "maxTokens": 2048, 
    "temperature": 0.1, 
    "topP": 0.9
    }

# test the deloyed model
response = bedrock_runtime.converse(
    modelId=provisioned_model_id,
    messages=conversation,
    inferenceConfig=inferenceConfig,
)
response_text = response["output"]["message"]["content"][0]["text"]
print(response_text)
```

<h3>(Optional) Model Copy and Share</h3>

If you want to deploy the model to a `different AWS Region` or a `different AWS account`, you can use `Model Share` and `Model Copy` feature of Amazon Bedrock. Please check the following notebook for more information.

[Sample notebook](https://github.com/aws-samples/amazon-bedrock-samples/blob/main_archieve_10_06_2024/custom_models/model_copy/cross-region-copy.ipynb){:target="_blank"}

<h3>Step 7. Cleanup</h3>

After you're done with the experiment, please ensure to **delete** the provisioned throughput model unit to avoid unnecessary cost.


```python
response = bedrock_client.delete_provisioned_model_throughput(provisionedModelId=provisioned_model_id)
```

<h2>Conclusion</h2>

In this guide, we've walked through the entire process of model distillation using Amazon Bedrock with historical model invocation logs. We covered:

1. Setting up the environment and configuring necessary AWS resources
2. Configuring model invocation logging using the API
3. Invoking the teacher model to generate logs
4. Configuring and submitting a distillation job using historical invocation logs
5. Monitoring the distillation job's progress
6. Deploying the distilled model using Provisioned Throughput
7. Running inference with the distilled model
8. Optional model copy and share procedures
9. Cleaning up resources

Remember to always consider your specific use case requirements when selecting models, configuring the distillation process, and filtering invocation logs. The ability to use actual production data from your model invocations can lead to distilled models that are highly optimized for your particular applications.

With these tools and techniques at your disposal, you're well-equipped to leverage the power of model distillation to optimize your AI/ML workflows in Amazon Bedrock.

**Happy distilling!**
