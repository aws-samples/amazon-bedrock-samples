import boto3
import shutil
import os
import time
import json
import random


s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')
agent_client = boto3.client("bedrock-agent")
bedrock_runtime = boto3.client('bedrock-runtime')


LAMBDA_ROLE = os.environ.get('LAMBDA_ROLE_ARN') or "create_default_lambda_role_for_me"
MODEL_ID = os.environ.get('MODEL_ID') or "anthropic.claude-v2"
AGENT_MODEL_NAME = os.environ.get('AGENT_MODEL_NAME') or "anthropic.claude-instant-v1"
PYTHON_VERSION = os.environ.get('PYTHON_VERSION') or "python3.11"
BASE_S3_KEY = os.environ.get('BASE_S3_KEY') or "create-agent"
REGION = os.environ.get('AWS_REGION')


with open('gen_lambda.template') as f:
    GEN_LAMBDA_PROMPT_TEMPLATE = f.read()

with open('gen_test_payloads.template') as f:
    GEN_TEST_PAYLOADS_PROMPT_TEMPLATE = f.read()

with open('gen_api_schema.template') as f:
    GEN_API_SCHEMA_PROMPT_TEMPLATE = f.read()

with open('example_lambda.py') as f:
    EXAMPLE_LAMBDA = f.read()

with open('example_test_payload.json') as f:
    EXAMPLE_TEST_PAYLOAD = f.read()


def get_named_parameter(event, name):
    if not 'parameters' in event:
        return ''
    else:
        return next(item for item in event['parameters'] if item['name'] == name)['value']


def get_named_property(event, name):
    return next(item for item in event['requestBody']['content']['application/json']['properties'] if item['name'] == name)['value']


def run_prompt_template(prompt_template, parameter_dict,
                        model_id=MODEL_ID,
                        max_tokens_to_sample=3000, temperature=1.0, top_p=0.9):
    prompt = prompt_template
    model_id = model_id or "anthropic.claude-v2"

    for key in parameter_dict:
        prompt = prompt.replace(key, parameter_dict[key])

    body = json.dumps({
        "prompt": prompt,
        "max_tokens_to_sample": max_tokens_to_sample,
        "temperature": temperature,
        "top_p": top_p,
    })

    response = bedrock_runtime.invoke_model(
        body=body,
        modelId=model_id,
        accept='application/json',
        contentType='application/json'
    )

    response_body = json.loads(response.get('body').read())
    return response_body.get('completion')


def create_api_schema(agent_name, api_description):
    return run_prompt_template(GEN_API_SCHEMA_PROMPT_TEMPLATE,
                               {"{agent_name}": agent_name,
                                "{api_description}": api_description})


def create_lambda_function_code(agent_name, api_schema_json_text):
    return run_prompt_template(GEN_LAMBDA_PROMPT_TEMPLATE,
                               {"{api_schema_json_text}": api_schema_json_text,
                                "{example_lambda}": EXAMPLE_LAMBDA})


def create_test_payloads(api_schema_json_text):
    return run_prompt_template(GEN_TEST_PAYLOADS_PROMPT_TEMPLATE,
                               {"{api_schema_json_text}": api_schema_json_text,
                                "{example_payload}": EXAMPLE_TEST_PAYLOAD})


def create_lambda_iam_role(role_name):

    basic_role = """{
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
  }"""

    iam.create_role(RoleName=role_name,
                    AssumeRolePolicyDocument=basic_role)

    # This role has the AWSLambdaBasicExecutionRole managed policy.
    iam.attach_role_policy(RoleName=role_name,
                           PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')

    return iam.get_role(RoleName=role_name)['Role']['Arn']


def create_agent_policies(bedrock_policy_name,
                          lambda_policy_name,
                          s3_policy_name,
                          s3_bucket_name,
                          lambda_arn,
                          schema_key):

    schema_arn = f'arn:aws:s3:::{s3_bucket_name}/{schema_key}'

    bedrock_agent_bedrock_allow_policy_statement = """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*"
      ],
      "Resource": "*"
    }
  ]
  }"""

    bedrock_agent_s3_allow_policy_statement = """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAgentAccessOpenAPISchema",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        \"""" + schema_arn + """\"
      ]
    }
  ]
  }"""

    bedrock_agent_lambda_allow_policy_statement = """{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAgentInvokeLambdaFunction",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": \"""" + lambda_arn + """\"
    }
  ]
  }"""

    bedrock_policy = iam.create_policy(
        PolicyName=bedrock_policy_name,
        Description=f"Policy for Bedrock Invoke Model, List Models and ListFoundationModels create by an agent.",
        PolicyDocument=bedrock_agent_bedrock_allow_policy_statement,
    )

    lambda_policy = iam.create_policy(
        PolicyName=lambda_policy_name,
        Description=f"Policy to allow invoke Lambda that was provisioned for it.",
        PolicyDocument=bedrock_agent_lambda_allow_policy_statement,
    )

    s3_policy = iam.create_policy(
        PolicyName=s3_policy_name,
        Description=f"Policy to allow agent access S3 with API schemas.",
        PolicyDocument=bedrock_agent_s3_allow_policy_statement,
    )

    return bedrock_policy['Policy']['Arn'], lambda_policy['Policy']['Arn'], s3_policy['Policy']['Arn']


def create_agent_iam_role(role_name):

    basic_assume_policy = """{
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
  }"""

    response = iam.create_role(RoleName=role_name,
                               AssumeRolePolicyDocument=basic_assume_policy)

    return iam.get_role(RoleName=role_name)['Role']['Arn']


def attach_policies_to_agent_iam_role(agent_role_name,
                                      bedrock_policy_arn,
                                      lambda_policy_arn,
                                      s3_policy_arn):

    iam.attach_role_policy(RoleName=agent_role_name,
                           PolicyArn=bedrock_policy_arn)
    iam.attach_role_policy(RoleName=agent_role_name,
                           PolicyArn=lambda_policy_arn)
    iam.attach_role_policy(RoleName=agent_role_name,
                           PolicyArn=s3_policy_arn)

    return


def save_file_to_s3(s3_bucket, object_key, text):
    return s3_client.put_object(Bucket=s3_bucket, Key=object_key, Body=text)


def create_lambda_function(function_name, lambda_function_code, role):

    try:
        os.mkdir('/tmp/tmp_folder')
    except Exception:
        pass

    with open('/tmp/tmp_folder/lambda_function.py', 'w') as fp:
        fp.write(lambda_function_code)
        pass

    shutil.make_archive('/tmp/lambda_function', 'zip', '/tmp/tmp_folder/')

    with open('/tmp/lambda_function.zip', 'rb') as f:
        zipped_code = f.read()

    response = lambda_client.create_function(FunctionName=function_name,
                                             Role=role,
                                             Code={'ZipFile': zipped_code},
                                             Runtime=PYTHON_VERSION,
                                             Handler='lambda_function.lambda_handler',
                                             Timeout=180)
    
    try:
        shutil.rmtree('/tmp/tmp_folder')
    except Exception:
        pass

    return response['FunctionArn']


def lambda_add_agent_permission(lambda_name, region, account_id, agent_id):

    response = lambda_client.add_permission(
        FunctionName=lambda_name,
        StatementId='allow_bedrock',
        Action='lambda:InvokeFunction',
        Principal='bedrock.amazonaws.com',
        SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}",
    )

    return response

def create_agent_alias(agent_id, alias_name):
    agent_alias = agent_client.create_agent_alias(agentId=agent_id, 
                                                  agentAliasName=alias_name)
    return agent_alias['agentAlias']['agentAliasId']

def prepare_agent(agent_id):
    return agent_client.prepare_agent(agentId=agent_id)


def draft_and_create_agent(event, context):

    # Generate random prefix number to avoid policies, 
    # roles and lambda name duplicates
    random_prefix = random.randrange(999)

    agent_name = get_named_property(event, 'agentName') + "-" + str(random_prefix)
    s3_bucket = get_named_property(event, 's3Bucket')
    api_description = get_named_property(event, 'apiDescription')
    agent_instruction = get_named_property(event, "agentInstruction")
    account_id = context.invoked_function_arn.split(":")[4]
    agent_alias_name = f"{agent_name}-alias"
    lambda_function_name = f'{agent_name}-actions'
    lambda_role_name = f"{agent_name}-lambda-role"
    agent_role_name = f"AmazonBedrockExecutionRoleForAgents_{random_prefix}"
    bedrock_agent_bedrock_allow_policy_name = f"bedrock-agent-allow-{agent_name}"
    bedrock_agent_s3_allow_policy_name = f"bedrock-s3-allow-{agent_name}"
    bedrock_agent_lambda_allow_policy_name = f"bedrock-lambda-allow-{agent_name}"
    base_key = f'{BASE_S3_KEY}/{agent_name}'

    schema_filename = f'{agent_name}-schema.json'
    schema_key = f'{base_key}/{schema_filename}'
    print(
        f'Drafting {agent_name} OpenAPI Schema to {s3_bucket}/{schema_key}, based on:\n{api_description}...')
    api_schema_json_text = create_api_schema(agent_name, api_description)
    save_file_to_s3(s3_bucket, schema_key, api_schema_json_text)

    lambda_key = f'{base_key}/{agent_name}-lambda.py'
    print(f'Drafting {agent_name} Lambda function to {s3_bucket}/{lambda_key}...')
    lambda_function_code = create_lambda_function_code(
        agent_name, api_schema_json_text)
    save_file_to_s3(s3_bucket, lambda_key, lambda_function_code)

    test_payloads_filename = f'{agent_name}-test-payloads.json'
    payload_key = f'{base_key}/{test_payloads_filename}'
    print(f'Drafting {agent_name} test payloads to {s3_bucket}/{payload_key}...')
    test_payloads_text = create_test_payloads(api_schema_json_text)
    save_file_to_s3(s3_bucket, payload_key, test_payloads_text)

    
    if LAMBDA_ROLE == "create_default_lambda_role_for_me":
        print(
        f"""Lambda ARN was not provided. 
           Creating a default Lambda IAM role called {lambda_role_name}"""
        )
        lambda_role_arn = create_lambda_iam_role(lambda_role_name)
    else:
        lambda_role_arn = LAMBDA_ROLE

    print(
        f"""Creating a Lambda IAM role called {lambda_role_name} 
          and an agent IAM role called {agent_role_name}..."""
        )
    agent_role_arn = create_agent_iam_role(role_name=agent_role_name)

    # Pause to make sure iam roles are created
    time.sleep(10)

    print(
        f'Creating an actual Lambda function called {lambda_function_name}...')
    lambda_arn = create_lambda_function(lambda_function_name,
                           lambda_function_code, lambda_role_arn)
    
    print(
        f"""Creating Bedrock policy called {bedrock_agent_bedrock_allow_policy_name}
          and Lambda policy called {bedrock_agent_lambda_allow_policy_name} and
          S3 policy called {bedrock_agent_s3_allow_policy_name}..."""
        )
    (bedrock_policy_arn, 
     lambda_policy_arn, 
     s3_policy_arn) = create_agent_policies(bedrock_policy_name=bedrock_agent_bedrock_allow_policy_name,
                                            s3_policy_name=bedrock_agent_s3_allow_policy_name,
                                            lambda_policy_name=bedrock_agent_lambda_allow_policy_name,
                                            lambda_arn=lambda_arn, 
                                            s3_bucket_name=s3_bucket,
                                            schema_key=schema_key)

    # Pause to make sure iam policies are created
    time.sleep(10)

    print(
        f'Attaching this policies to {agent_role_name} IAM role...')
    attach_policies_to_agent_iam_role(agent_role_name,
                                      bedrock_policy_arn,
                                      lambda_policy_arn,
                                      s3_policy_arn)
    
    print(
        f'Creating agent called {agent_name}...')
    agent_id = create_agent(agent_name=agent_name,
                            agent_resource_role_arn=agent_role_arn,
                            bucket=s3_bucket,
                            model_name=AGENT_MODEL_NAME,
                            lambda_arn=lambda_arn,
                            instruction=agent_instruction,
                            key=schema_key)
    
    print(
        f"""Creating an agent with id {agent_id} and adding agent resource-based policy 
        to Lambda named {lambda_function_name} that is attached to this agent...""")
    lambda_add_agent_permission(agent_id=agent_id, region=REGION,
                                account_id=account_id, lambda_name=lambda_function_name)
    
    print(
        f'Preparing agent with {agent_id} id ...')
    prepare_agent(agent_id=agent_id)

    # Pause to make sure agent is in prepared state
    time.sleep(7)

    print(
        f'Creating an alias for an agent with {agent_id} id ...')
    alias_id = create_agent_alias(agent_id=agent_id, alias_name=agent_alias_name)
    

    return {"status": f"""
    for an agent called {agent_name}, drafted an agent schema in {schema_filename},  
    a lambda function called {lambda_function_name}, 
    test payloads called {test_payloads_filename},
    created an agent with id {agent_id} and 
    attached an IAM role {agent_role_name} to it
    with access to {s3_bucket} S3 bucket,
    lambda function {lambda_function_name} and bedrock models;
    finally created an alias called {agent_alias_name} with 
    {alias_id} id for agent {agent_name} and prepared 
    the agent to be used. 
    Files were saved in s3://{s3_bucket}/{base_key}/
    """
            }


def create_agent(bucket, agent_resource_role_arn,
                 lambda_arn, agent_name, key, model_name,
                 instruction):

    response = agent_client.create_agent(
        agentName=agent_name,
        agentResourceRoleArn=agent_resource_role_arn,
        foundationModel=model_name,
        description="Agent created by another agent based on user request.",
        idleSessionTTLInSeconds=1800,
        instruction=instruction,
    )

    agent_id = response['agent']['agentId']

    # Pause to make sure agents has been created
    time.sleep(10)

    agent_client.create_agent_action_group(
        agentId=agent_id,
        agentVersion='DRAFT',
        actionGroupExecutor={
            'lambda': lambda_arn
        },
        actionGroupName='ActionGroup',
        apiSchema={
            's3': {
                's3BucketName': bucket,
                's3ObjectKey': key
            }
        },
        description='This is a default description made by an agent. Modify it as needed.'
    )

    return agent_id


def lambda_handler(event, context):

    print("Event payload: " + json.dumps(event))

    response_code = 200
    action_group = event['actionGroup']
    api_path = event['apiPath']

    if api_path == '/create-agent':
        result = draft_and_create_agent(event, context)
    else:
        response_code = 404
        result = f"Unrecognized api path: {action_group}::{api_path}"

    response_body = {
        'application/json': {
            'body': result
        }
    }

    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': response_code,
        'responseBody': response_body
    }

    api_response = {
        'messageVersion': '1.0',
        'response': action_response
    }

    print("API response payload: " + json.dumps(api_response))

    return api_response
