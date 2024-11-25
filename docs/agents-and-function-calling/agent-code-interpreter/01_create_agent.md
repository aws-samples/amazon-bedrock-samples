---
tags:
    - Agent/ Code-Interpreter
    - Agent/ Prompt-Engineering
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/agents-and-function-calling/agent-code-interpreter/01_create_agent.ipynb){:target="_blank"}

<h2>Bedrock Agent Creation Overview</h2>

This is the second notebook in the series to demonstrates how to set up and use an Amazon Bedrock Agent with Code Interpreter capabilities.

This involves creating an IAM role, setting up policies, and configuring the agent itself. We'll use Claude 3.5 Sonnet as our foundation model.


```python
import os
import boto3
import json
import logging
import requests
import pandas as pd
import uuid, string
import time, random 
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime, timedelta
```

<h2>Set the AWS Region</h2>

We're using the US East (N. Virginia) region for this demo. Feel free to change this to your preferred region, but make sure that a) the region supports Amazon Bedrock, b) Agents, c) the Claude Sonnet (3) model, and finally d) you have enabled access to the Sonnet (3) in this region. 


```python
region_name: str = 'us-east-1'
```


```python
# Read the S3 URI from the text file
with open('s3_uri.txt', 'r') as f:
    s3_uri = f.read().strip()

print(f"Loaded S3 URI: {s3_uri}") 
```


```python
# constants
CSV_DATA_FILE: str = 'nyc_taxi_subset.csv'
# Bucket and prefix name where this csv file will be uploaded and used as S3 source by code interpreter
S3_BUCKET_NAME: str = s3_uri.replace("s3://", "")
PREFIX: str = 'code-interpreter-demo-data'
# This is the size of the file that will be uploaded to s3 and used by the agent (in MB)
DATASET_FILE_SIZE: float = 99
```


```python
# Set up Bedrock Agent and IAM clients
bedrock_agent = boto3.client(service_name = 'bedrock-agent', region_name = region_name)
iam = boto3.client('iam')

agentName = 'ds-assistant-test-agent'

# Define the agent's personality and behavior
instruction = """You are a data analyst assistant capable of various tasks including writing and executing code for exploratory data analysis,
creating ML models, and providing natural language summaries of complex analysis. 

You have access to tools that allow you to write and run Python code. You have capabilities in code execution,
chart generation, and complex data analysis.
Your primary function is to assist users by solving problems and fulfilling requests through these capabilities.

Here are your key attributes and instructions:

Code Execution:

You have access to a Python environment where you can write and execute code in real-time.
When asked to perform calculations or data manipulations, always use this code execution capability to ensure accuracy.
After executing code, report the exact output and explain the results.
Record any code you used to the analysis in a standalone Python file so I can take a look at the steps you went through
and execute the code. Make sure to include installation of any dependencies that were needed by your code.


Data Analysis:

You excel at complex data analysis tasks. This includes statistical analysis, data visualization, and machine learning applications.
Approach data analysis tasks systematically: understand the problem, prepare the data, perform the analysis, and interpret the results.

Problem-Solving Approach:

When presented with a problem or request, break it down into steps.
Clearly communicate your thought process and the steps you're taking.
If a task requires multiple steps or tools, outline your approach before beginning.
If there are multiple parts to a question and they need to be done in a sequence then make sure the code handles that.


Transparency and Accuracy:

Always be clear about what you're doing. If you're running code, say so. If you're generating an image, explain that.
If you're unsure about something or if a task is beyond your capabilities, communicate this clearly.
Do not present hypothetical results as actual outcomes. Only report real results from your code execution or image generation.


Interaction Style:

Be concise in simple queries but provide detailed explanations for complex tasks.
Use technical language appropriately, but be prepared to explain concepts in simpler terms if asked.
Proactively offer relevant information or alternative approaches that might be helpful.


Continuous Improvement:

After completing a task, ask if the user needs any clarification or has follow-up questions.
Be receptive to feedback and adjust your approach accordingly.


Remember, your goal is to provide accurate, helpful, and insightful assistance by leveraging your unique capabilities in code execution, image generation, and data analysis.
Always strive to give the most practical and effective solution to the user's request."""

#Testing with Claude Sonnet 3.5
foundationModel = 'anthropic.claude-3-5-sonnet-20240620-v1:0'

# Generate a random suffix for unique naming
randomSuffix = "".join(
    random.choices(string.ascii_uppercase + string.digits, k=5)
)

print("Creating the IAM policy and role...")

# Define IAM trust policy
trustPolicy = {
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

# Define IAM policy for invoking the foundation model
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                f"arn:aws:bedrock:{region_name}::foundation-model/{foundationModel}"
            ]
        }
    ]
}

# Define S3 access policy
s3Policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                f"arn:aws:s3:::{S3_BUCKET_NAME}",
                f"arn:aws:s3:::{S3_BUCKET_NAME}/*"
            ]
        }
    ]
}

role_name = f"test-agent-{randomSuffix}"

# Create IAM role and attach policy
role = iam.create_role(
    RoleName=role_name,
    AssumeRolePolicyDocument = json.dumps(trustPolicy)
)
iam.put_role_policy(
    RoleName=role_name,
    PolicyName = f"policy-test-agent-{randomSuffix}",
    PolicyDocument = json.dumps(policy)
)


# Attach S3 policy
iam.put_role_policy(
    RoleName=role_name,
    PolicyName=f"policy-s3-access-{randomSuffix}",
    PolicyDocument=json.dumps(s3Policy)
)

roleArn = role['Role']['Arn']

print(f"IAM Role: {roleArn[:13]}{'*' * 12}{roleArn[25:]}")

print("Creating the agent...")

# Create the Bedrock Agent
response = bedrock_agent.create_agent(
    agentName=f"{agentName}-{randomSuffix}",
    foundationModel=foundationModel,
    instruction=instruction,
    agentResourceRoleArn=roleArn,
)

agentId = response['agent']['agentId']

print("Waiting for agent status of 'NOT_PREPARED'...")

# Wait for agent to reach 'NOT_PREPARED' status
agentStatus = ''
while agentStatus != 'NOT_PREPARED':
    response = bedrock_agent.get_agent(
        agentId=agentId
    )
    agentStatus = response['agent']['agentStatus']
    print(f"Agent status: {agentStatus}")
    time.sleep(2)

######################################### Configure code interpreter for the agent
response = bedrock_agent.create_agent_action_group(
    
    actionGroupName='CodeInterpreterAction',
    actionGroupState='ENABLED',
    agentId=agentId,
    agentVersion='DRAFT',

    parentActionGroupSignature='AMAZON.CodeInterpreter' # <-  To allow your agent to generate, 
                                                        #     run, and troubleshoot code when trying 
                                                        #     to complete a task, set this field to 
                                                        #     AMAZON.CodeInterpreter. 
                                                        #     You must leave the `description`, `apiSchema`, 
                                                        #     and `actionGroupExecutor` fields blank for 
                                                        #     this action group.
)

actionGroupId = response['agentActionGroup']['actionGroupId']

print("Waiting for action group status of 'ENABLED'...")

# Wait for action group to reach 'ENABLED' status
actionGroupStatus = ''
while actionGroupStatus != 'ENABLED':
    response = bedrock_agent.get_agent_action_group(
        agentId=agentId,
        actionGroupId=actionGroupId,
        agentVersion='DRAFT'
    )
    actionGroupStatus = response['agentActionGroup']['actionGroupState']
    print(f"Action Group status: {actionGroupStatus}")
    time.sleep(2)

print("Preparing the agent...")

# Prepare the agent for use
response = bedrock_agent.prepare_agent(
    agentId=agentId
)

print("Waiting for agent status of 'PREPARED'...")

# Wait for agent to reach 'PREPARED' status
agentStatus = ''
while agentStatus != 'PREPARED':
    response = bedrock_agent.get_agent(
        agentId=agentId
    )
    agentStatus = response['agent']['agentStatus']
    print(f"Agent status: {agentStatus}")
    time.sleep(2)

print("Creating an agent alias...")

# Create an alias for the agent
response = bedrock_agent.create_agent_alias(
    agentAliasName='test',
    agentId=agentId
)

agentAliasId = response['agentAlias']['agentAliasId']

# Wait for agent alias to be prepared
agentAliasStatus = ''
while agentAliasStatus != 'PREPARED':
    response = bedrock_agent.get_agent_alias(
        agentId=agentId,
        agentAliasId=agentAliasId
    )
    agentAliasStatus = response['agentAlias']['agentAliasStatus']
    print(f"Agent alias status: {agentAliasStatus}")
    time.sleep(2)
f"test-agent-{randomSuffix}"
print('Done.\n')

print(f"agentId: {agentId}, agentAliasId: {agentAliasId}")
```


```python
agent_info = {
    "agentId": agentId,
    "agentAliasId": agentAliasId,
    "agentAliasStatus": agentAliasStatus,
    "role_name" : role_name 
}

# Write the agent info to a JSON file
with open('agent_info.json', 'w') as f:
    json.dump(agent_info, f)

print("Agent information has been written to agent_info.json")
```


```python

```
