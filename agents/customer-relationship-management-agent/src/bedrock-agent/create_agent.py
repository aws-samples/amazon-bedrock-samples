import boto3
import time
import zipfile
import json
import sys
import os

# boto3 clients
sts_client = boto3.client("sts")
iam_client = boto3.client("iam")
s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")
bedrock_agent_client = boto3.client("bedrock-agent")
ssm_client = boto3.client("ssm")
session = boto3.session.Session()

# Global variables
REGION = session.region_name
ACCOUNT_ID = sts_client.get_caller_identity()["Account"]

# Input file path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Command line Arguments
ENV = sys.argv[1]
CODE_BUCKET = sys.argv[2]
IS_JIRA = sys.argv[3]

# (optinal) Jira Arguments
lambda_code_path = ""
schema_path = ""
jira_username = None
jira_url = None
jira_api_token = None

if IS_JIRA == "true":
    
    lambda_code_path = os.path.join(CURRENT_DIR, "jira", "crm-bot-lambda.py")
    schema_path = os.path.join(CURRENT_DIR, "jira", "crm_schema.json")
    
    jira_username = sys.argv[4]
    jira_url = sys.argv[5]
    jira_api_token = sys.argv[6]
    
    agent_instruction = """
        You are a customer relationship management agent tasked with helping a sales person plan their work with customers. 
        You can provide information like company overview, company interaction history (meeting times and notes), company meeting preferences (meeting type, day of week, and time of day). 
        You can also query Jira tasks and update their timeline. 
        After receiving a response, clean it up into a readable format.If the output is a numbered list, format it as such with newline characters and numbers. 
        You cannot output JSON structures. 
    """

elif IS_JIRA == "false":
    lambda_code_path = os.path.join(CURRENT_DIR, "basic", "crm-bot-lambda.py")
    schema_path = os.path.join(CURRENT_DIR, "basic", "crm_schema.json")
    
    
    agent_instruction = """
        You are a customer relationship management agent tasked with helping a sales person plan their work with customers. 
        You can provide information like company overview, company interaction history (meeting times and notes), company meeting preferences (meeting type, day of week, and time of day). 
        After receiving a response, clean it up into a readable format.If the output is a numbered list, format it as such with newline characters and numbers. 
        You cannot output JSON structures. 
    """

# Global variables
AGENT_NAME = f"crm-agent-{ENV}"
AGENT_ALIAS_NAME = f"crm-alias-{ENV}"
LAMBDA_ROLE_NAME = f"lambda-role-{ENV}"
AGENT_ROLE_NAME = f"AmazonBedrockExecutionRoleForAgents_{ENV}"
LAMBDA_NAME = f"crm-lambda-action-{ENV}"

def create_lambda_function(
    lambda_code_path,
    jira_username=None,
    jira_url=None,
    jira_api_token=None,
):
    try:
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "bedrock:InvokeModel",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        assume_role_policy_document_json = json.dumps(assume_role_policy_document)

        print(f"Creating Lambda Role {LAMBDA_ROLE_NAME}")
        lambda_iam_role = iam_client.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
        )

        # Pause to make sure role is created
        time.sleep(10)
    except:
        lambda_iam_role = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)

    iam_client.attach_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    dynamodb_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    # Add other actions as needed
                ],
                "Resource": [
                    f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/customer-{ENV}",
                    f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/interactions-{ENV}",
                ],
                # Specify the DynamoDB table ARN or other resource ARN
            }
        ],
    }
    iam_client.put_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyName=f"DynamoDBPolicy-{ENV}",
        PolicyDocument=json.dumps(dynamodb_policy),
    )

    # Package up the lambda function code
    print(f"Creating Lambda Function {LAMBDA_NAME}")

    with open(lambda_code_path, "r") as file:
        lambda_code = file.read()

    with zipfile.ZipFile("lambda_function.zip", "w") as zip_file:
        zip_file.writestr("lambda_function.py", lambda_code)

    with open("lambda_function.zip", "rb") as zip_file:
        # Create Lambda Function

        if IS_JIRA == "true":
            lambda_function = lambda_client.create_function(
                FunctionName=LAMBDA_NAME,
                Runtime="python3.12",
                Timeout=180,
                Role=lambda_iam_role["Role"]["Arn"],
                Code={"ZipFile": zip_file.read()},
                Handler="lambda_function.lambda_handler",
                Environment={
                    "Variables": {
                        "JIRA_USERNAME": jira_username,
                        "JIRA_URL": "https://" + jira_url,
                        "JIRA_API_TOKEN": jira_api_token,
                        "ENVIRONMENT_Name": ENV,
                    }
                },
            )
        else:
            lambda_function = lambda_client.create_function(
                FunctionName=LAMBDA_NAME,
                Runtime="python3.12",
                Timeout=180,
                Role=lambda_iam_role["Role"]["Arn"],
                Code={"ZipFile": zip_file.read()},
                Handler="lambda_function.lambda_handler",
                Environment={"Variables": {"ENVIRONMENT_Name": ENV}},
            )

    print("Lambda created successfully")

    return lambda_function

def create_agent(lambda_function, schema_path):
    bedrock_agent_bedrock_allow_policy_statement = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
                "Effect": "Allow",
                "Action": "bedrock:InvokeModel",
                "Resource": [
                    f"arn:aws:bedrock:{REGION}::foundation-model/anthropic.claude-v2:1"
                ],
            }
        ],
    }

    bedrock_policy_json = json.dumps(bedrock_agent_bedrock_allow_policy_statement)

    agent_bedrock_policy = iam_client.create_policy(
        PolicyName=f"BedrockAgentPolicy-{ENV}",
        PolicyDocument=bedrock_policy_json,
    )
    bedrock_agent_s3_allow_policy_statement = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowAgentAccessOpenAPISchema",
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{CODE_BUCKET}/crm_schema.json"],
            }
        ],
    }

    bedrock_agent_s3_json = json.dumps(bedrock_agent_s3_allow_policy_statement)
    agent_s3_schema_policy = iam_client.create_policy(
        PolicyName=f"S3Allow-{ENV}",
        Description=f"Policy to allow invoke Lambda that was provisioned for it.",
        PolicyDocument=bedrock_agent_s3_json,
    )

    # Create IAM Role for the agent and attach IAM policies
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    try:
        assume_role_policy_document_json = json.dumps(assume_role_policy_document)
        print(f"Creating Agent Role {AGENT_ROLE_NAME}")

        agent_role = iam_client.create_role(
            RoleName=AGENT_ROLE_NAME,
            AssumeRolePolicyDocument=assume_role_policy_document_json,
        )

        # Pause to make sure role is created
        time.sleep(10)

        iam_client.attach_role_policy(
            RoleName=AGENT_ROLE_NAME, PolicyArn=agent_bedrock_policy["Policy"]["Arn"]
        )

        iam_client.attach_role_policy(
            RoleName=AGENT_ROLE_NAME, PolicyArn=agent_s3_schema_policy["Policy"]["Arn"]
        )
        iam_client.attach_role_policy(
            RoleName=AGENT_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
        )
    except:
        agent_role = response = iam_client.get_role(RoleName=AGENT_ROLE_NAME)
    print(f"Creating Agent {AGENT_NAME}")

    response = bedrock_agent_client.create_agent(
        agentName=AGENT_NAME,
        agentResourceRoleArn=agent_role["Role"]["Arn"],
        description="Agent for Customer Relationship Management.",
        idleSessionTTLInSeconds=1800,
        foundationModel="anthropic.claude-v2:1",
        instruction=agent_instruction,
        promptOverrideConfiguration={
            "promptConfigurations": [
                {
                    "promptType": "PRE_PROCESSING",
                    "promptCreationMode": "OVERRIDDEN",
                    "promptState": "DISABLED",
                    "basePromptTemplate": " ",
                    "inferenceConfiguration": {
                        "temperature": 0,
                        "topP": 1,
                        "topK": 123,
                        "maximumLength": 2048,
                        "stopSequences": [
                            "Human",
                        ],
                    },
                }
            ]
        },
    )

    agent_id = response["agent"]["agentId"]

    # upload the OpenAPI Schema
    s3_client.put_object(
        Body=open(schema_path, "rb"),
        Bucket=CODE_BUCKET,
        Key="crm_schema.json",
    )

    # Pause to make sure agent is created and crm-bot-schema.json is uploaded
    time.sleep(30)
    # Now, we can configure and create an action group here:
    agent_action_group_response = bedrock_agent_client.create_agent_action_group(
        agentId=agent_id,
        agentVersion="DRAFT",
        actionGroupExecutor={"lambda": lambda_function["FunctionArn"]},
        actionGroupName="crmActionGroup",
        apiSchema={
            "s3": {"s3BucketName": CODE_BUCKET, "s3ObjectKey": "crm_schema.json"}
        },
        description="Action for getting database table schema claims",
    )
    response = lambda_client.add_permission(
        FunctionName=LAMBDA_NAME,
        StatementId="allow_bedrock",
        Action="lambda:InvokeFunction",
        Principal="bedrock.amazonaws.com",
        SourceArn=f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent/{agent_id}",
    )

    agent_prepare = bedrock_agent_client.prepare_agent(agentId=agent_id)

    time.sleep(30)
    agent_alias = bedrock_agent_client.create_agent_alias(
        agentId=agent_id, agentAliasName=AGENT_ALIAS_NAME
    )
    time.sleep(15)
    # Extract the agentAliasId from the response
    agent_alias_id = agent_alias["agentAlias"]["agentAliasId"]

    # Pause to make sure agent alias is ready
    time.sleep(30)
    print("Agent created successfully")

    return agent_id, agent_alias_id

def create_agent_parameter(agent_id, agent_alias_id):

    print(f"Creating SSM Parameter /streamlitapp/AGENT_ID")
    response_agent_id = ssm_client.put_parameter(
        Name=f"/streamlitapp/{ENV}/AGENT_ID",
        Description="string",
        Value=agent_id,
        Type="SecureString",
        KeyId="alias/aws/ssm",
        Tier="Standard",
        DataType="text",
    )

    print(f"Creating SSM Parameter /streamlitapp/agent_alias_id")
    response_agent_alias_id = ssm_client.put_parameter(
        Name=f"/streamlitapp/{ENV}/AGENT_ALIAS_ID",
        Value=agent_alias_id,
        Type="SecureString",
        KeyId="alias/aws/ssm",
        Tier="Standard",
        DataType="text",
    )

    print("SSM Parameters created successfully")

    return response_agent_id, response_agent_alias_id

if __name__ == "__main__":

    # Step 1: Create Lambda function
    lambda_function = create_lambda_function(
        lambda_code_path=lambda_code_path,
        jira_username=jira_username,
        jira_url=jira_url,
        jira_api_token=jira_api_token,
    )

    # Step 2: Create Agent
    agent_id, agent_alias_id = create_agent(
        lambda_function=lambda_function, schema_path=schema_path
    )

    # Step 3: Create Parameter store
    create_agent_parameter(agent_id=agent_id, agent_alias_id=agent_alias_id)
