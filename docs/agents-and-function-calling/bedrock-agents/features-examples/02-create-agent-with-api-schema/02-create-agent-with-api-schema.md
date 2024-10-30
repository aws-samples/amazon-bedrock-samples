---
tags:
    - Agents/ Function Definition
    - API-Usage-Example
    - Use cases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/02-create-agent-with-api-schema/02-create-agent-with-api-schema.ipynb){:target="_blank"}"

<h2>Create and Invoke Agent via Boto3 SDK</h2>

> *This notebook should work well with the **`Data Science 3.0`** kernel in SageMaker Studio*

<h2>Introduction</h2>

In this notebook we show you how to use the `bedrock-agent` and the `bedrock-agent-runtime` boto3 clients to:
- create an agent
- create an action group using an API Schema (vs using function definitions)
- associate the agent with the action group and prepare the agent
- create an agent alias
- invoke the agent

We will use Bedrock's Claude Sonnet using the Boto3 API. 

**Note:** *This notebook can be used in SageMaker Studio or run locally if you setup your AWS credentials.*

<h4>Prerequisites</h4>
This notebook requires permissions to: 
- create and delete Amazon IAM roles
- create, update and invoke AWS Lambda functions 
- create, update and delete Amazon S3 buckets 
- access Amazon Bedrock 

If you are running this notebook without an Admin role, make sure that your role include the following managed policies:
- IAMFullAccess
- AWSLambda_FullAccess
- AmazonS3FullAccess
- AmazonBedrockFullAccess


<h4>Context</h4>
We will demonstrate how to create and invoke an agent for Bedrock using the Boto3 SDK

<h4>Use case</h4>
For this notebook, our agent acts as an assistant for an insurance claims use case. The agent helps the insurance employee to check open claims, identify the details for a specific claim, get open documents for a claim and send reminders to a claim policyholder.

The Agent created can handle the follow tasks or combinations of these in a multi-step process:
- Get Open Claims
- Get Claim Details
- Get Claim Outstanding Documents
- Send Claim reminder

<h2>Notebook setup</h2>
Before starting, let's import the required packages and configure the support variables


```python
import logging
import boto3
import time
import zipfile
from io import BytesIO
import json
import uuid
import pprint
```


```python
<h2>setting logger</h2>
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
```


```python
<h2>get boto3 clients for required AWS services</h2>
sts_client = boto3.client('sts')
iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
```


```python
session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
region, account_id
```


```python
<h2>Generate random prefix for unique IAM roles, agent name and S3 Bucket and </h2>
<h2>assign variables</h2>
suffix = f"{region}-{account_id}"
agent_name = "insurance-claims-agent"
agent_alias_name = "workshop-alias"
bucket_name = f'{agent_name}-{suffix}'
bucket_key = f'{agent_name}-schema.json'
schema_name = 'insurance_claims_agent_openapi_schema.json'
schema_arn = f'arn:aws:s3:::{bucket_name}/{bucket_key}'
bedrock_agent_bedrock_allow_policy_name = f"{agent_name}-allow-{suffix}"
bedrock_agent_s3_allow_policy_name = f"{agent_name}-s3-allow-{suffix}"
lambda_role_name = f'{agent_name}-lambda-role-{suffix}'
agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{suffix}'
lambda_code_path = "lambda_function.py"
lambda_name = f'{agent_name}-{suffix}'
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
```

<h3>Create S3 bucket and upload API Schema</h3>

Agents require an API Schema stored on s3. Let's create an S3 bucket to store the file and upload the file to the newly created bucket


```python
<h2>Create S3 bucket for Open API schema</h2>
if region == "us-east-1":
    s3bucket = s3_client.create_bucket(
        Bucket=bucket_name
    )
else:
    s3bucket = s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={ 'LocationConstraint': region } 
    )
```


```python
<h2>Upload Open API schema to this s3 bucket</h2>
s3_client.upload_file(schema_name, bucket_name, bucket_key)
```

<h3>Create Lambda function for Action Group</h3>
Let's now create the lambda function required by the agent action group. We first need to create the lambda IAM role and it's policy. After that, we package the lambda function into a ZIP format to create the function


```python
<h2>Create IAM Role for the Lambda function</h2>
try:
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)

    lambda_iam_role = iam_client.create_role(
        RoleName=lambda_role_name,
        AssumeRolePolicyDocument=assume_role_policy_document_json
    )

    # Pause to make sure role is created
    time.sleep(10)
except:
    lambda_iam_role = iam_client.get_role(RoleName=lambda_role_name)

iam_client.attach_role_policy(
    RoleName=lambda_role_name,
    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
)
```

Take a look at the Lambda function code that will be used as an Action group for the agent


```python
!pygmentize lambda_function.py
```


```python
<h2>Package up the lambda function code</h2>
s = BytesIO()
z = zipfile.ZipFile(s, 'w')
z.write(lambda_code_path)
z.close()
zip_content = s.getvalue()

<h2>Create Lambda Function</h2>
lambda_function = lambda_client.create_function(
    FunctionName=lambda_name,
    Runtime='python3.12',
    Timeout=180,
    Role=lambda_iam_role['Role']['Arn'],
    Code={'ZipFile': zip_content},
    Handler='lambda_function.lambda_handler'
)
```

<h3>Create Agent</h3>
We will now create our agent. To do so, we first need to create the agent policies that allow bedrock model invocation  and s3 bucket access. 


```python
<h2>Create IAM policies for agent</h2>

bedrock_agent_bedrock_allow_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                f"arn:aws:bedrock:{region}::foundation-model/{model_id}"
            ]
        }
    ]
}

bedrock_policy_json = json.dumps(bedrock_agent_bedrock_allow_policy_statement)

agent_bedrock_policy = iam_client.create_policy(
    PolicyName=bedrock_agent_bedrock_allow_policy_name,
    PolicyDocument=bedrock_policy_json
)


```

Next, we will create a policy document that allows fetching of the Agent's OpenAPI schema from S3:


```python
bedrock_agent_s3_allow_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowAgentAccessOpenAPISchema",
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": [
                schema_arn
            ]
        }
    ]
}


bedrock_agent_s3_json = json.dumps(bedrock_agent_s3_allow_policy_statement)
agent_s3_schema_policy = iam_client.create_policy(
    PolicyName=bedrock_agent_s3_allow_policy_name,
    Description=f"Policy to allow invoke Lambda that was provisioned for it.",
    PolicyDocument=bedrock_agent_s3_json
)
```

Finally, create a role with the above two policies attached


```python
<h2>Create IAM Role for the agent and attach IAM policies</h2>
assume_role_policy_document = {
    "Version": "2012-10-17",
    "Statement": [{
          "Effect": "Allow",
          "Principal": {
            "Service": "bedrock.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
    }]
}

assume_role_policy_document_json = json.dumps(assume_role_policy_document)
agent_role = iam_client.create_role(
    RoleName=agent_role_name,
    AssumeRolePolicyDocument=assume_role_policy_document_json
)

<h2>Pause to make sure role is created</h2>
time.sleep(10)
    
iam_client.attach_role_policy(
    RoleName=agent_role_name,
    PolicyArn=agent_bedrock_policy['Policy']['Arn']
)

iam_client.attach_role_policy(
    RoleName=agent_role_name,
    PolicyArn=agent_s3_schema_policy['Policy']['Arn']
)
```

<h4>Creating Agent</h4>
Once the needed IAM role is created, we can use the bedrock agent client to create a new agent. To do so we use the `create_agent` function. It requires an agent name, underlying foundation model and instructions. You can also provide an agent description. Note that the agent created is not yet prepared. We will focus on preparing the agent and then using it to invoke actions and use other APIs


```python
<h2>Create Agent</h2>
agent_instruction = """
You are an agent that can handle various tasks related to insurance claims, including looking up claim 
details, finding what paperwork is outstanding, and sending reminders. Only send reminders if you have been 
explicitly requested to do so. If an user asks about your functionality, provide guidance in natural language 
and do not include function names on the output."""

response = bedrock_agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_role['Role']['Arn'],
    description="Agent for handling insurance claims.",
    idleSessionTTLInSeconds=1800,
    foundationModel=model_id,
    instruction=agent_instruction,
)
```

Looking at the created agent, we can see its status and agent id


```python
response
```

Let's now store the agent id in a local variable to use it on the next steps


```python
agent_id = response['agent']['agentId']
agent_id
```

<h3>Create Agent Action Group</h3>
We will now create and agent action group that uses the lambda function and API schema files created before.
The `create_agent_action_group` function provides this functionality. We will use `DRAFT` as the agent version since we haven't yet create an agent version or alias. To inform the agent about the action group functionalities, we will provide an action group description containing the functionalities of the action group.


```python
<h2>Pause to make sure agent is created</h2>
time.sleep(30)
<h2>Now, we can configure and create an action group here:</h2>
agent_action_group_response = bedrock_agent_client.create_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupExecutor={
        'lambda': lambda_function['FunctionArn']
    },
    actionGroupName='ClaimManagementActionGroup',
    apiSchema={
        's3': {
            's3BucketName': bucket_name,
            's3ObjectKey': bucket_key
        }
    },
    description='Actions for listing claims, identifying missing paperwork, sending reminders'
)
```


```python
agent_action_group_response
```

<h3>Allowing Agent to invoke Action Group Lambda</h3>
Before using our action group, we need to allow our agent to invoke the lambda function associated to the action group. This is done via resource-based policy. Let's add the resource-based policy to the lambda function created


```python
<h2>Create allow invoke permission on lambda</h2>
response = lambda_client.add_permission(
    FunctionName=lambda_name,
    StatementId='allow_bedrock',
    Action='lambda:InvokeFunction',
    Principal='bedrock.amazonaws.com',
    SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}",
)
```

<h3>Preparing Agent</h3>
Let's create a DRAFT version of the agent that can be used for internal testing.


```python
agent_prepare = bedrock_agent_client.prepare_agent(agentId=agent_id)
agent_prepare
```

<h3>Create Agent alias</h3>
We will now create an alias of the agent that can be used to deploy the agent.


```python
<h2>Pause to make sure agent is prepared</h2>
time.sleep(30)
agent_alias = bedrock_agent_client.create_agent_alias(
    agentId=agent_id,
    agentAliasName=agent_alias_name
)
```


```python
agent_alias
```

<h3>Invoke Agent</h3>
Now that we've created the agent, let's use the `bedrock-agent-runtime` client to invoke this agent and perform some tasks.


```python
time.sleep(30)
<h2>Extract the agentAliasId from the response</h2>
agent_alias_id = agent_alias['agentAlias']['agentAliasId']
```


```python
<h2>create a random id for session initiator id</h2>
session_id:str = str(uuid.uuid1())
enable_trace:bool = False
end_session:bool = False
<h2>Pause to make sure agent alias is ready</h2>
<h2>time.sleep(30)</h2>

<h2>invoke the agent API</h2>
agentResponse = bedrock_agent_runtime_client.invoke_agent(
    inputText="what are the open claims?",
    agentId=agent_id,
    agentAliasId=agent_alias_id, 
    sessionId=session_id,
    enableTrace=enable_trace, 
    endSession= end_session
)

logger.info(pprint.pprint(agentResponse))
```


```python
%%time
event_stream = agentResponse['completion']
try:
    for event in event_stream:        
        if 'chunk' in event:
            data = event['chunk']['bytes']
            logger.info(f"Final answer ->\n{data.decode('utf8')}")
            agent_answer = data.decode('utf8')
            end_event_received = True
            # End event indicates that the request finished successfully
        elif 'trace' in event:
            logger.info(json.dumps(event['trace'], indent=2))
        else:
            raise Exception("unexpected event.", event)
except Exception as e:
    raise Exception("unexpected event.", e)
```


```python
<h2>And here is the response if you just want to see agent's reply</h2>
print(agent_answer)
```


```python
def simple_agent_invoke(input_text, agent_id, agent_alias_id, session_id=None, enable_trace=False, end_session=False):
    agentResponse = bedrock_agent_runtime_client.invoke_agent(
        inputText=input_text,
        agentId=agent_id,
        agentAliasId=agent_alias_id, 
        sessionId=session_id,
        enableTrace=enable_trace, 
        endSession= end_session
    )
    
    event_stream = agentResponse['completion']
    try:
        for event in event_stream:        
            if 'chunk' in event:
                data = event['chunk']['bytes']
                logger.info(f"Final answer ->\n{data.decode('utf8')}")
                agent_answer = data.decode('utf8')
                end_event_received = True
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                logger.info(json.dumps(event['trace'], indent=2))
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)
```


```python
simple_agent_invoke("tell me about claim-857", agent_id, agent_alias_id, session_id)
```


```python
simple_agent_invoke("send reminders for all open claims that have missing paperwork", agent_id, agent_alias_id, session_id)
```

<h3>Clean up (optional)</h3>
The next steps are optional and demonstrate how to delete our agent. To delete the agent we need to:
1. update the action group to disable it
2. delete agent action group
3. delete agent alias
4. delete agent
5. delete lambda function
6. empty created s3 bucket
7. delete s3 bucket


```python
 # This is not needed, you can delete agent successfully after deleting alias only
<h2>Additionaly, you need to disable it first</h2>

action_group_id = agent_action_group_response['agentActionGroup']['actionGroupId']
action_group_name = agent_action_group_response['agentActionGroup']['actionGroupName']

response = bedrock_agent_client.update_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupId= action_group_id,
    actionGroupName=action_group_name,
    actionGroupExecutor={
        'lambda': lambda_function['FunctionArn']
    },
    apiSchema={
        's3': {
            's3BucketName': bucket_name,
            's3ObjectKey': bucket_key
        }
    },
    actionGroupState='DISABLED',
)

action_group_deletion = bedrock_agent_client.delete_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupId= action_group_id
)
```


```python
agent_alias_deletion = bedrock_agent_client.delete_agent_alias(
    agentId=agent_id,
    agentAliasId=agent_alias['agentAlias']['agentAliasId']
)
```


```python
agent_deletion = bedrock_agent_client.delete_agent(
    agentId=agent_id
)
```


```python
<h2>Delete Lambda function</h2>
lambda_client.delete_function(
    FunctionName=lambda_name
)
```


```python
<h2>Empty and delete S3 Bucket</h2>

objects = s3_client.list_objects(Bucket=bucket_name)  
if 'Contents' in objects:
    for obj in objects['Contents']:
        s3_client.delete_object(Bucket=bucket_name, Key=obj['Key']) 
s3_client.delete_bucket(Bucket=bucket_name)
```


```python
<h2>Delete IAM Roles and policies</h2>

for policy in [bedrock_agent_bedrock_allow_policy_name, bedrock_agent_s3_allow_policy_name]:
    iam_client.detach_role_policy(RoleName=agent_role_name, PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}')
    
iam_client.detach_role_policy(RoleName=lambda_role_name, PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')

for role_name in [agent_role_name, lambda_role_name]:
    iam_client.delete_role(
        RoleName=role_name
    )

for policy in [agent_bedrock_policy, agent_s3_schema_policy]:
    iam_client.delete_policy(
        PolicyArn=policy['Policy']['Arn']
)
```

<h2>Conclusion</h2>
We have now experimented with using `boto3` SDK to create, invoke and delete an agent.

<h3>Take aways</h3>
- Adapt this notebook to create new agents for your application

<h2>Thank You</h2>
