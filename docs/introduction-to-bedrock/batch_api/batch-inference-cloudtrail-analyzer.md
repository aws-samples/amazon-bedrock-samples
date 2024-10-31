---
tags:
    - Batch-Inference
    - Security/CloudTrail
    - API-Usage-Example
---

<!-- <h1>Batch Inference for CloudTrail Analyzer</h1> -->

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/introduction-to-bedrock/batch_api/batch-inference-cloudtrail-analyzer.ipynb){:target="_blank"}"

<h2>Overview</h2>

This notebook demonstrates how to analyze CloudTrail logs using <b>Amazon Bedrock for batch inference</b> to identify potential security anomalies. 

<h2>Context</h2>

The key steps in this process are:

1. Data Collection: Retrieve the latest CloudTrail events (default: 20k events)
2. Batch Inference: Use Amazon Bedrock batch inference to analyze user activities in batches.
3. Summarization: Summarize the results to provide a concise overview of potential security concerns in your AWS environment.

The output can be sent to an SNS topic to receive the summary in email for eg.

- Amazon Bedrock batch inference works with jsonl files. Each completion to process is a json object with a modelInput and modelOutput.
- The minimum number of items in the jsonl file for the batch inference job is 1000.
- Observed time to summarize 2000 batch items of 10 cloudtrail events with given prompt is ~15 minutes.
- You can check the job status with get_model_invocation_job passing jobArn as parameter.
- Final summarisation is performed with Amazon Bedrock invoke_model API.

Model chosen for this example is <b>Claude 3 Haiku</b>. This provides a good balance between cost, quality and context size.<br>
Other models (Mistal for eg.) can be used as well to lower the cost but would require more requests to be processed due to the smaller context window.

Pricing:
- Est. Pricing - Input: 20K events est. <b>$3.3</b> with Claude 3 Haiku in us-east-1 as of september 2024
- Est. Pricing - Output: 2000 summarizations est. <b>$1.25</b> with Claude 3 Haiku in us-east-1 as of september 2024

Assuming:
- 20K events ~600 tokens per event
- 10 cloudtrail event per batch item
- 500 tokens for prompt size
- 15-20 final summarizations of 10k tokens
- Input tokens ~13M tokens / est. 
- 500 tokens per summarization
- 2000 summaries to generate in batch inference
- 15-20 final summarizations to generate
- Output ~1M tokens 

<h2>Prerequisites</h2>

- Make sure boto3 can access your AWS account
- Make sure you have acces to Claude 3 Haiku model in us-east-1
- Make sure your credentials allow creation of resources (S3 bucket, SNS topic, IAM role) and access to Bedrock

```python
%pip install boto3
```

```python
import json
import uuid
import os
import time
from datetime import datetime, timedelta
import boto3
import utils
import bedrock
from botocore.exceptions import ClientError

aws_region = "us-east-1"

s3 = boto3.client('s3')
cloudtrail = boto3.client('cloudtrail')
sns = boto3.client('sns')
iam = boto3.client('iam')
aws_account_number = boto3.client('sts').get_caller_identity().get('Account')
bedrock = boto3.client('bedrock')
bedrock_runtime = boto3.client("bedrock-runtime", region_name=aws_region)

batch_inference_input_file = "input.jsonl"
s3_bucket_name = f"cloudtrail-analysis-with-bedrock-{aws_account_number}"
bedrock_role_name = "CloudTrailAnalyser_BedrockS3AccessRole"
sns_topic_name = "cloudtrail-summary"

s3_input_uri = f"s3://{s3_bucket_name}/{batch_inference_input_file}"
s3_output_uri = f"s3://{s3_bucket_name}/batch_inference_output/"
```

```python
# Claude 3 Haiku for a balance between cost and quality
model_id = "anthropic.claude-3-haiku-20240307-v1:0"

# chars, not tokens. Adjust this to match your model's context length / performance requirements
max_context_length = 50000 
# chars, not tokens. Size of prompt to summarize the events
prompt_length = 500 
# minimum batch entries in jsonl file required for Amazon Bedrockbatch inference
min_batch_items_for_bedrock_batch_inference = 1000 
# mini batches to keep a balance between summarizing and not losing too much signal
events_per_batch_item = 10 
# max number of batch item entries in the jsonl file, this is a cost control safety measure
max_batch_items = 2000
# max tokens in summary to keep a balance between summarizing and not losing too much signal
max_tokens_in_summary = 500
```

<h2>Setup</h2>

<h3> Create S3 bucket, Role, SNS topic</h3>

- S3 bucket is needed to store intermediate data for the batch inference job.
- Role is needed to allow bedrock to access the S3 bucket.
- SNS topic is needed to receive the final summary.

```python
def create_or_get_bedrock_s3_access_role(bedrock_role_name: str, s3_bucket_name: str):

    try:
        response = iam.get_role(RoleName=bedrock_role_name)
        print(f"Role {bedrock_role_name} already exists.")
        return response['Role']['Arn']
    except iam.exceptions.NoSuchEntityException:
        # Role doesn't exist, create it
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            response = iam.create_role(
                RoleName=bedrock_role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy)
            )
            
            # Attach S3 access policy
            s3_policy = {
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
                            f"arn:aws:s3:::{s3_bucket_name}",
                            f"arn:aws:s3:::{s3_bucket_name}/*"
                        ]
                    }
                ]
            }
            
            iam.put_role_policy(
                RoleName=bedrock_role_name,
                PolicyName="S3AccessPolicy",
                PolicyDocument=json.dumps(s3_policy)
            )
            
            print(f"Role {bedrock_role_name} created successfully.")
            return response['Role']['Arn']
        except Exception as e:
            print(f"Error creating role: {str(e)}")
            return None

def create_s3_bucket_if_not_exists(bucket_name):

    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists.")
        return True
    except:
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"Bucket {bucket_name} created successfully.")
            return True
        except Exception as e:
            print(f"Error creating bucket {bucket_name}: {str(e)}")
            return False

def create_or_get_sns_topic(topic_name):
    
    try:
        # create only if it doesnt exist (function is idempotent)
        topic = sns.create_topic(Name=topic_name)
        print(f"SNS topic {topic_name} created successfully (arn: {topic['TopicArn']})")
        return topic['TopicArn']
    except Exception as e:
        print(f"Error creating SNS topic {topic_name}: {str(e)}")
        return False

if not create_s3_bucket_if_not_exists(s3_bucket_name):
    print("Failed to create or access the S3 bucket.")

role_arn = create_or_get_bedrock_s3_access_role(bedrock_role_name, s3_bucket_name)
if not role_arn:
    print("Failed to create or get the IAM role for Bedrock. Exiting.")

sns_topic_arn = create_or_get_sns_topic(sns_topic_name)
if not sns_topic_arn:
    print("Failed to create or get the SNS topic. Exiting.")

```

<h3> Create the batch inference input file</h3>

Every line of the input file is a json object with a `modelInput`.<br>
`modelInput` is the prompt sent to Claude and contains the list of events to summarize.

```python
def create_batch_entry_and_add_to_file(events_string, input_file):

    # putting words in claude's mouth    
    prompt = f"""Human: Please summarize the following list of AWS CloudTrail events for several users. 
    Focus on identifying patterns, unusual activities, and potential security concerns. 
    Here's the list of events:

    {events_string}

    Provide a concise summary of the user's activities, highlighting any noteworthy or suspicious actions.

    Assistant: Certainly! I'll analyze the CloudTrail events several users and provide a summary of their activities, focusing on patterns, unusual activities, and potential security concerns. Here's the summary:

    """

    if len(prompt) > max_context_length:
        print(f"Prompt too long: {len(prompt)} chars for max_context_length configured (chars). \
              Process will carry on anyway. You may encounter errors")

    bedrock_batch_json = {
        "modelInput": {
            "anthropic_version": "bedrock-2023-05-31", 
            "max_tokens": max_tokens_in_summary,
            "temperature": 0.5,
            "top_p": 0.9,
            "stop_sequences": [],
            "messages": [ 
                { 
                    "role": "user", 
                    "content": [
                        {
                            "type": "text", 
                            "text": prompt 
                        } 
                    ]
                }
            ]
        }
    }

    with open(input_file, 'a') as f:
        json.dump(bedrock_batch_json, f)
        f.write('\n')
```
<h3> Process CloudTrail events</h3>

Cloudtrail events can be retrieved with the `lookup_events` API. 

We paginate through all events in the account and create a jsonl file with a modelInput for each batch item.

Max RPS for `lookup_events` is 2. This can lead to throttling exceptions that are automatically retried by boto3.

```python
print("Starting CloudTrail event processing...")

if os.path.exists(batch_inference_input_file):
    os.remove(batch_inference_input_file)

event_count = 0
page_count = 0
completion_count = 0
event_buffer = []

paginator = cloudtrail.get_paginator('lookup_events')
page_iterator = paginator.paginate(
    PaginationConfig={
        'MaxItems': None,
        'PageSize': 50
    }
)

for page in page_iterator:
    
    page_count += 1
    print(f"\rProcessing page {page_count} -> batch entries created : {completion_count}/[{min_batch_items_for_bedrock_batch_inference}(min),{max_batch_items}(max)]", end="", flush=True)
    
    for event in page['Events']:

        event_count += 1
        ct_event = json.loads(event['CloudTrailEvent'])
        event_buffer.append(ct_event)

        if(len(event_buffer) >= events_per_batch_item):
            events_string = ' '.join(json.dumps(event, separators=(',', ':')) for event in event_buffer)

            create_batch_entry_and_add_to_file(events_string, batch_inference_input_file)
            
            event_buffer = []
            completion_count += 1
    
    # stop if we have enough batch items, this limits the cost of the test in case if you have many events
    if completion_count >= max_batch_items:
        break
    
    if 'NextToken' not in page:
        print("Reached the end of available events.")
        break
    
print(f"\nTotal pages processed: {page_count}")
print(f"Total events processed: {event_count}")
print(f"Total completion count (items in batch inference): {completion_count}")

if completion_count < min_batch_items_for_bedrock_batch_inference:
    print(f"Bedrock requires a minimum of {completion_count} entries for batch inference. You may not have enough cloudtrail events.")
```

<h3> Batch inference job</h3>

Batch inference input file is uploaded to S3 and passed as `inputDataConfig` eg. `input_file_name.jsonl`<br>

```python
job_name = f"cloudtrail-summary-{int(time.time())}"

s3.upload_file(batch_inference_input_file, s3_bucket_name, batch_inference_input_file)
print(f"Uploaded {batch_inference_input_file} to {s3_input_uri}")
        
response = bedrock.create_model_invocation_job(
    modelId=model_id,
    roleArn=role_arn,
    jobName=job_name,
    inputDataConfig=({
        "s3InputDataConfig": {
            "s3Uri": s3_input_uri
        }
    }),
    outputDataConfig=({
        "s3OutputDataConfig": {
            "s3Uri": s3_output_uri
        }
    })
)
        
job_arn = response.get('jobArn')
job_id = job_arn.split('/')[1]

print(f"Batch inference job launched successfully. Job ID: {job_id}")
print(f"Output will be available at: {s3_output_uri}")
```

```python
# wait for the job to complete, est. 10-20min
while True:
    time.sleep(10)
    print(f"Waiting for job {job_arn} to complete")
    response = bedrock.get_model_invocation_job(jobIdentifier=job_arn)
    if response['status'] == 'Completed':
        print(f"Done")
        break
    elif response['status'] == 'Failed':
        raise Exception(f"Batch inference job failed: {response['failureReason']}")
```

<h3> Batch inference output</h3>

Batch inference job output data configuration `outputDataConfig`is a folder where sub-folder `job-id` is created containing a `.out` file eg. `input_file_name.jsonl.out` with the completion results.<br>
Each item processed by the batch inference job is a json object containing `modelInput` and `modelOutput` 

NOTE: a `manifest.json.out` is also generated and includes statistics on the batch job. eg. input tokens, output tokens.

In this example, we download the `.out` file locally to process it.

```python
output_file = "output.jsonl"

print(f"Downloading batch output from {s3_bucket_name} for job {job_id}")
s3.download_file(s3_bucket_name, f'batch_inference_output/{job_id}/{batch_inference_input_file}.out', output_file)
print(f"Done.")
```

```python
with open(output_file, 'r') as f:
    lines = f.readlines()

summaries = []

print(f"Processing {len(lines)} lines to get the summaries")
for line in lines:
    data = json.loads(line)
    summary = data['modelOutput']["content"][0]["text"]
    summaries.append(summary)
```

<h3> Computing final summary</h3>

To compute the final summary we will group the summaries in prompt maxing out the configured context length.

Direct calls to bedrock are made to summarize the groups of summaries.

```python
# utility method to invoke bedrock and get result
def invoke_bedrock(prompt):

    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }

    # Convert the native request to JSON.
    request = json.dumps(native_request)

    try:
        # Invoke the model with the request.
        response = bedrock_runtime.invoke_model(modelId=model_id, body=request)

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)

    model_response = json.loads(response["body"].read())

    response_text = model_response["content"][0]["text"]

    return response_text
```

```python
# prompt sent to bedrockto summarize a block of summaries generated by batch inference
def summarize_block(to_summarize):

    final_prompt = f"""Human: Please summarize the following summaries of AWS CloudTrail events. 
        Focus on identifying patterns, unusual activities, and potential security concerns. 
        Here's the list of summaries:

        {to_summarize}

        Provide a concise summary of the user's activities, highlighting any noteworthy or suspicious actions.

        Assistant: Certainly! I'll analyze the summaries and provide a final summary of their activities, focusing on patterns, unusual activities, and potential security concerns. Here's the final summary:

        """

    summary = invoke_bedrock(final_prompt)

    print(f"Summarized {len(to_summarize)} chars with bedrock in {len(summary)} chars")

    return summary
```

```python
# processes the list of summaries to generate a final summary
def summarize_list(summaries):

    print(f"Summarizing {len(summaries)} summaries")

    context_length = 0
    summaries_of_summaries = []
    final_summary = ""
    to_summarize = ""
    count_summaries = 0

    for summary in summaries:     
        
        count_summaries += 1
        
        context_length += len(summary)
        to_summarize += "\n" + summary

        # we split summarization task by max_context_length given, 
        if context_length > max_context_length - prompt_length:
            print(f"Processing summaries {count_summaries} of {len(summaries)}")
            summaries_of_summaries.append(summarize_block(to_summarize))
            to_summarize = ""
            context_length = 0

    if len(to_summarize) > 0:
        summaries_of_summaries.append(summarize_block(to_summarize))       

    if len(summaries_of_summaries) > 1:
        final_summary = summarize_list(summaries_of_summaries)
    else:
        final_summary = summaries_of_summaries[0]

    return final_summary
```


```python
final_summary = summarize_list(summaries)
```

```python
print(final_summary)
```

<h3> Sample output 1</h3>

Based on the provided CloudTrail event summaries, the key observations regarding the user's activities are:

1. Repeated CloudTrail API Calls by User "vivien":
   - The IAM user "--redacted--" made multiple consecutive "LookupEvents" API calls to the CloudTrail service within a short timeframe, potentially indicating an attempt to retrieve a large amount of CloudTrail data.
   - This user accessed the CloudTrail service from a non-AWS IP address (x.x.x.x) and used consistent user agent information (Boto3/1.35.8), suggesting an automated or scripted activity.
   - The repeated API calls and resulting throttling exceptions raise concerns about the user's intentions and the potential risk of unauthorized access or data exfiltration.

2. Broad Role Permissions:
   - Some of the assumed roles, such as the "--redacted---" and the "--redacted---", have broad permissions (e.g., "Allow *" on all resources).
   - This level of broad access should be reviewed to ensure it is necessary and not overly permissive, as it could potentially lead to security risks if the roles are compromised.

3. Security Audit Activities:
   - The user with the assumed role "--redacted---" performed a DescribeRegions operation, which is likely part of a security audit or monitoring activity.
   - However, this user also attempted to retrieve the bucket policy for the "--redacted---" bucket, but received a "NoSuchBucketPolicy" error, indicating a potential permission issue.
   - Additionally, the user accessed a bucket named "--redacted---", which is an unusual and potentially suspicious bucket name. This bucket access should be investigated further.

In summary, the key concerns identified in the CloudTrail event summaries are the repeated CloudTrail API calls by the user "--redacted--", which could indicate unauthorized access or data exfiltration.

<h3> Sample output 2</h3>

Based on the analysis of the provided CloudTrail event summaries, the key findings are:

1. Routine CloudTrail Monitoring: The majority of the events are related to the CloudTrail service accessing S3 buckets to monitor and log API activities, which is a standard security practice.

2. Assumed Roles by AWS Services: Various AWS services, such as Kinesis Analytics, SageMaker, Lightsail, and Pipes, are assuming specific IAM roles to perform their operations. This is a common and expected behavior for AWS services.

3. Potential Security Concern: One event stands out where the SageMaker service assumed the "--redacted--" role, which grants broad permissions ("*" on all resources). While assuming roles is a normal practice, the broad permissions granted to this role could be a potential security concern and should be reviewed to ensure the role has the minimum required permissions.

4. Unusual IAM User Activity: The IAM user "--redacted--" is performing a high volume of "InvokeModel" API calls on the "anthropic.claude-3-haiku-20240307-v1:0" model within a short timeframe. This pattern of repeated model invocations from a single user account could indicate potential unauthorized or abusive use of the AI/ML service.

5. Potential Security Concern with Source IP: The source IP address "--redacted--" used by the "--redacted--" user is not a typical AWS IP range, which raises a potential security concern and warrants further investigation to ensure the legitimacy of the user's activities.

Overall, the CloudTrail event summaries do not indicate any clearly malicious or suspicious activities, aside from the unusual pattern of model invocations by the "--redacted--" user and the broad permissions granted to the SageMaker execution role. It is recommended to closely monitor the user's activities, review their permissions, investigate the source IP address, and ensure the principle of least privilege is followed for all IAM roles.

<h3> Publish to SNS topic</h3>

```python
# send to sns to receive the summary in email for eg.
sns.publish(TopicArn=sns_topic_arn, Message=final_summary)
```

<h2> Next steps</h2>

This sample is a baseline for anyone looking to enhance their security posture by analyzing CloudTrail logs using Amazon Bedrock. By following the steps outlined in the notebook, you can quickly set up and execute batch inference jobs that help you identify potential security threats in your AWS environment. Furthermore, the techniques demonstrated here can be applied to a wide range of other AWS services and use cases, making it a versatile addition to your cloud security toolkit.
We encourage you to explore its capabilities, adapt it to your specific needs, and share your experiences with the community.

Additionally, you can add the following features to enhance the solution:
- parralelize the final summary processing to reduce latency of last step
- filter out principals or services that are not believed to be interesting
- break down by user, service, region
- Integrate code in step function / lambda to to be able to trigger it on schedule
- use IaC to create the resources

For more examples and use cases, see:
- [Batch Inference for Call Center Transcripts](batch-inference-transcript-summarization.md)
- [Amazon Bedrock Batch Inference Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html){:target="_blank"}

<h2> Cleanup</h2>

Optionally, you can delete the resources created in the setup section through AWS console or CLI.

- Empty S3 bucket and delete the bucket
- Delete the SNS topic
- Delete the role

