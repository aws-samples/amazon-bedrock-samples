import boto3
import zipfile
import os
import time
import random
import json
from io import BytesIO


s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')
agent_client = boto3.client("bedrock-agent")


def create_api_schema(agent_name, api_description):
    bedrock = boto3.client(service_name='bedrock-runtime')
    
    prompt = f"""

Human: you will be generating an OpenAPI schema document in JSON format.
here is brief description of the APIs that must be covered by this document:
<apis>
{api_description}
</apis>
    
Generate an OpenAPI 3.0 schema document in JSON format covering the APIs listed above. 

Do include:
- Metadata like title, description, version
- Paths section with route paths and operations
- Operations have parameters, descriptions, responses
- Responses have status codes, descriptions and schemas
- Schemas define the data types
- Specify the title as "{agent_name} API"
- Unless the API description says otherwise, use camel case for naming the API paths

Do not include a server URL. 
Do not generate a global components section. Instead create definitions inline 
without having to use a ref tag.

Only generate the JSON document, without providing any explanations or preamble.
Start immediately with the open curly brace and end with the closing curly brace,
without the triple backtick markdown language specifier.

Assistant: here is the resulting schema:
"""

    body = json.dumps({
      "prompt": prompt,
      "max_tokens_to_sample": 2000,
      "temperature": 1.0,
      "top_p": 0.9,
    })
    
    response = bedrock.invoke_model(
      body=body, 
      modelId='anthropic.claude-v2', 
      accept='application/json', 
      contentType='application/json'
    )
    
    response_body = json.loads(response.get('body').read())
    json_schema_text = response_body.get('completion')
    
    return json_schema_text
    
    
def create_lambda_function_code(agent_name, api_schema_json_text):
  
    bedrock = boto3.client(service_name='bedrock-runtime')

    example_lambda = """
import json 

def get_named_parameter(event, name):
    return next(item for item in event['parameters'] if item['name'] == name)['value']

def get_named_property(event, name):
    return next(item for item in event['requestBody']['content']['application/json']['properties'] if item['name'] == name)['value']
    
def doSomethingUsingProperties(event):
    int_property_value1 = int(get_named_property(event, 'property_name1'))
    float_property_value2 = float(get_named_property(event, 'property_name2'))
    string_property_value3 = get_named_property(event, 'property_name3'))

   # TODO: implement

    return  {
              "attribute1": "some value",
              "attribute2": "some other value"
        }
 
def doSomethingUsingParameters(event):
   my_input_parameter = get_named_value(event['parameters'], 'my_parameter_name')

   # TODO: implement

    return  {
              "attribute1": "some value",
              "attribute2": "some other value"
        }

def lambda_handler(event, context):

result = ''
response_code = 200
action_group = event['actionGroup']
api_path = event['apiPath']

if api_path == '/doSomethingUsingParameters':
    result = doSomethingUsingParameters(event) 
elif api_path == '/doSomethingUsingProperties':
    result = doSomethingUsingProperties(event)
else:
    response_code = 404
    result = f"Unrecognized api path: {action_group}::{api_path}"
    
    response_body = {
        'application/json': {
            'body': json.dumps(result)
        }
    }
        
    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': response_code,
        'responseBody': response_body
    }

    api_response = {'messageVersion': '1.0', 'response': action_response}
    return api_response
    """
    
    prompt = f"""

Human: you will be generating a Python Lambda function based on an OpenAPI schema document.

<schema>
{api_schema_json_text}
</schema>
    
here is an example of what the generated lambda function would look like
for a schema with one api path that takes in parameters and another api path
that takes in a json requestBody:

<example>
{example_lambda}
</example>

Generate a Python Lambda function based on the above OpenAPI schema document. 
The handler acts as a dispatcher based on the api path. 
For each api path, it calls a generated function to handle the operations for that path,
passing the Lambda event object as input. If the api path is not recognized, the handler
returns an appropriate error including the unrecognized path. If you reference the httpMethod,
be sure to uppercase the value that comes in on the event.

Each generated operation handler must extract its required inputs from the event object,
using the get_named_value function supplied in the example.
The input extraction must use either event parameters or the event requestBody properties depending on
the way the inputs are specified in the OpenAPI schema for the given API path and operation.
The function must also have a TODO comment for implementing the code for the real work of the function, 
and must return a dummy response that satisfies the API response content defined in the OpenAPI schema for
its path.

The overall Python lambda_handler function must return an api response json object that includes the following elements:

- messageVersion "1.0"
- response object containing the action response

The action response is a json object that includes the following elements:

- actionGroup taken from the event actionGroup
- apiPath taken from the event apiPath
- httpMethod taken from the event httpMethod
- httpStatusCode 
- responseBody as a json object containing the json object returned from the individual generated api path handler

Generate the Lambda function, without providing any explanations or preamble.
Start immediately with the import statements, without the triple backtick markdown language specifier.

Assistant: here is the resulting function based on the specified schema:
"""

    body = json.dumps({
      "prompt": prompt,
      "max_tokens_to_sample": 3000,
      "temperature": 1.0,
      "top_p": 0.9,
    })
    
    response = bedrock.invoke_model(
      body=body, 
      modelId='anthropic.claude-v2', 
      accept='application/json', 
      contentType='application/json'
    )
    
    response_body = json.loads(response.get('body').read())
    lambda_function_code = response_body.get('completion')
    
    return lambda_function_code
    

def create_test_payloads(api_schema_json_text):
    bedrock = boto3.client(service_name='bedrock-runtime')

    example_payload = """
{
  "actionGroup": "AG",
  "apiPath": "/somePath",
  "action": "name of operation",
  "httpMethod": "get",
  "messageVersion": "1.0",
  "parameters": [
          {
            "name": "color",
            "type": "string",
            "value": "blue"
          },
          {
            "name": "age",
            "type": "integer",
            "value": "57"
          }        ]
  "requestBody": {
    "content": {
      "application/json": {
        "properties": [
          {
            "name": "average_output_tokens_per_request",
            "type": "integer",
            "value": "100"
          }
   }
}
"""
    
    prompt = f"""

Human: Here is an OpenAPI schema:

<schema>
{api_schema_json_text}
</schema>
    
Here is the structure for a payload:

<payload>
{example_payload}
</payload>

Generate a json array containing a list of payloads to help me test my api. Generate only json, not any preamble or explanation. Generate one or two payloads for each api path.
ensure that the payload accurately and precisely matches the expected input to the api path. Some will expect parameters. Others will expect requestBody. Others will need both.
Do not make up any api paths. Each payload must include all of the parameters or properties that the schema says are required for that given api path.
Only generate payloads for api paths that are represented in the schema.

Assistant: Here is the set of payloads:    
"""

    body = json.dumps({
      "prompt": prompt,
      "max_tokens_to_sample": 3000,
      "temperature": 1.0,
      "top_p": 0.9,
    })
    
    response = bedrock.invoke_model(
      body=body, 
      modelId='anthropic.claude-v2', 
      accept='application/json', 
      contentType='application/json'
    )
    
    response_body = json.loads(response.get('body').read())
    payloads_text = response_body.get('completion')
    
    return payloads_text
  

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
  
  
def create_agent_iam_role(role_name):
  
  basic_role = """{
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
  
  iam.create_role(RoleName=role_name, 
      AssumeRolePolicyDocument=basic_role)
      
  return iam.get_role(RoleName=role_name)['Role']['Arn'] 
  
  
def save_file_to_s3(s3_bucket, object_key, text):
  return s3_client.put_object(Bucket=s3_bucket, Key=object_key, Body=text)
  

def upload_zip_file_to_s3(bucket, key):
  
  zipped_key = key[:-3] + '.zip'
  bucket_obj = s3.Bucket(bucket)
  files_collection = bucket_obj.objects.filter(Prefix=key).all()
  archive = BytesIO()
  
  # Zip python file for lambda deployment
  with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zip_archive:
    for file in files_collection:
      if file.key.endswith('.py'):
        with zip_archive.open(file.key, 'w') as _file:
          _file.write(file.get()['Body'].read()) 

  archive.seek(0)
  s3.Object(bucket, zipped_key).upload_fileobj(archive)
  archive.close()
  
  return zipped_key
  
  
def create_lambda_function(lambda_name, bucket, 
                           key, role_arn):
  
  response = lambda_client.create_function(
    FunctionName=lambda_name,
    Runtime='python3.11',
    Role=role_arn,  
    Handler='lambda_function.lambda_handler',
    Timeout=300,
    Code={
      'S3Bucket': bucket, 
      'S3Key': key
    }
  )

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
  
  
def draft_an_agent(event, random_prefix):
  
    props = event['requestBody']['content']['application/json']['properties']
    print(f'Properties: {props}')
    agent_name = ''
    s3_bucket = ''
    api_description = ''
    
    for prop in props:
        print(prop)
        if prop['name'] == 'agentName':
            agent_name = prop['value']
        elif prop['name'] == 's3Bucket':
            s3_bucket = prop['value']
        else:
            api_description = prop['value']
    
    schema_key = f'{agent_name}/{agent_name}-schema.json'
    print(f'Drafting {agent_name} OpenAPI Schema to {s3_bucket}/{schema_key}, based on:\n{api_description}...')
    api_schema_json_text = create_api_schema(agent_name, api_description)
    save_file_to_s3(s3_bucket, schema_key, api_schema_json_text)
    
    lambda_key = f'{agent_name}/{agent_name}-lambda.py'
    print(f'Drafting {agent_name} Lambda function to {s3_bucket}/{lambda_key}...')
    lambda_text = create_lambda_function_code(agent_name, api_schema_json_text)
    save_file_to_s3(s3_bucket, lambda_key, lambda_text)
    
    payload_key = f'{agent_name}/{agent_name}-test-payloads.json'
    print(f'Drafting {agent_name} test payloads to {s3_bucket}/{payload_key}...')
    test_payloads_text = create_test_payloads(api_schema_json_text)
    save_file_to_s3(s3_bucket, payload_key, test_payloads_text)

    return agent_name, s3_bucket, lambda_key, schema_key
  

def create_agent(bucket, agent_resource_role_arn, 
                 lambda_arn, agent_name, key):
  
  response = agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_resource_role_arn,
    description="Agent created by another agent based on user request.",
    idleSessionTTLInSeconds=1800,
    foundationalModel="anthropic.claude-v2",
    instruction="This is a default instruction made by an agent. Modify it as needed.",
  )

  agent_id = response['agent']['agentId']
  
  # Pause to make sure agents has been created                           
  time.sleep(10)
  
  agent_action_group_response = agent_client.create_agent_action_group(
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
  action = event['actionGroup']
  api_path = event['apiPath']
  
  # Generate random number to avoid roles and lambda duplicates
  random_prefix = random.randrange(99999)
  
  region = os.environ['AWS_REGION']
  account_id = context.invoked_function_arn.split(":")[4]

  lambda_name = f"bedrock-agent-lambda-{random_prefix}"
  lambda_role_name = f"bedrock-agent-lambda-role-{random_prefix}"
  agent_role_name = f"AmazonBedrockExecutionRoleForAgents_{random_prefix}"

  ##### Start of function calls
  role_arn_lambda = create_lambda_iam_role(role_name=lambda_role_name)
  
  role_arn_agent = create_agent_iam_role(role_name=agent_role_name)
  
  # Pause to make sure iam roles are created                           
  time.sleep(10)
  
  agent_name, s3_bucket, lambda_key, schema_key = draft_an_agent(event=event, random_prefix=random_prefix)
  
  zipped_key = upload_zip_file_to_s3(bucket=s3_bucket, key=lambda_key)
  
  lambda_arn = create_lambda_function(lambda_name=lambda_name, 
                                      bucket=s3_bucket, 
                                      key=zipped_key, 
                                      role_arn=role_arn_lambda)
                         
  agent_id = create_agent(agent_name=agent_name, 
                          agent_resource_role_arn=role_arn_agent, 
                          bucket=s3_bucket, 
                          lambda_arn=lambda_arn,
                          key=schema_key)
  
  lambda_add_agent_permission(agent_id=agent_id, region=region, 
                              account_id=account_id, lambda_name=lambda_name)
                              
                              
  ##### End of function calls
  
  response_body = {
    'application/json': {
      'body': f"""I successfully created an agent. Created agent's name is {agent_name} and it's id is {agent_id}. Bucket name is {s3_bucket}. Lambda name is {lambda_name}.
Please make sure you check all of the IAM roles and attach appropriate policies based on your needs.
The agent's IAM role - {agent_role_name} - currently has no allowed permissions. 
The lambda's IAM role - {lambda_role_name} - has AWSLambdaBasicExecutionRole role attached to it. To learn more about it, following this link - https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html.
Make sure you change agent's instruction based on your needs."""
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