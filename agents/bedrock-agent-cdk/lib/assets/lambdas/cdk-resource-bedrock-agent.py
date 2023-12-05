import boto3
import os
import time
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import botocore.session

agent_client = boto3.client("bedrock-agent")

def on_event(event, context):
  agent_name = os.environ['AGENT_NAME']
  s3_bucket = os.environ['S3_BUCKET']
  s3_bucket_key = os.environ['S3_BUCKET_KEY']
  bedrock_agent_role_arn = os.environ['BEDROCK_AGENT_ROLE_ARN']
  bedrock_agent_lambda_arn = os.environ['BEDROCK_AGENT_LAMBDA_ARN']
  physical_id = "PhysicalId"

  print(json.dumps(event))
  request_type = event['RequestType']
  if request_type == 'Create': return on_create(event, agent_name=agent_name, s3_bucket=s3_bucket, 
                                                bedrock_agent_role_arn=bedrock_agent_role_arn,
                                                bedrock_agent_lambda_arn=bedrock_agent_lambda_arn,
                                                s3_bucket_key=s3_bucket_key, physical_id=physical_id)
  if request_type == 'Update': return on_update(event, physical_id=physical_id)
  if request_type == 'Delete': return on_delete(event, physical_id=physical_id, agent_name=agent_name)
  raise Exception("Invalid request type: %s" % request_type)


def on_create(event, agent_name, s3_bucket, bedrock_agent_role_arn, 
              bedrock_agent_lambda_arn, s3_bucket_key, physical_id):
  props = event["ResourceProperties"]
  print("create new resource with props %s" % props)

  agent_id = create_agent(agent_resource_role_arn=bedrock_agent_role_arn, agent_name=agent_name)
  # Pause to make sure agents has been created                           
  time.sleep(15)
  create_agent_action_group(bucket=s3_bucket, agent_id=agent_id,
                            lambda_arn=bedrock_agent_lambda_arn,
                            key=s3_bucket_key)

  return { 'PhysicalResourceId': physical_id } 


def on_update(event, physical_id):
  # physical_id = event["PhysicalResourceId"]
  props = event["ResourceProperties"]
  print("update resource %s with props %s" % (physical_id, props))

  return { 'PhysicalResourceId': physical_id } 


def on_delete(event, agent_name, physical_id):
  # physical_id = event["PhysicalResourceId"]
  print("delete resource %s" % physical_id)
  delete_agent(agent_name)

  return { 'PhysicalResourceId': physical_id } 


def create_agent(agent_resource_role_arn, agent_name):
  
  response = agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_resource_role_arn,
    foundationModel="anthropic.claude-v2",
    description="Agent created by CDK.",
    idleSessionTTLInSeconds=1800,
    instruction="This is a default instruction made by CDK. Modify it as needed.",
  )

  return response['agent']['agentId']


def create_agent_action_group(agent_id, lambda_arn, bucket, key):
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
    description='This is a default description made by CDK. Modify it as needed.'
    )
    
    return


def delete_agent(agent_name):
    # Get list of all agents
    response = agent_client.list_agents()
    print('This is agent name from delete: ', agent_name)
    # Find agent with the given name
    for agent in response["agentSummaries"]:
        if agent["agentName"] == agent_name:
            agent_id = agent["agentId"]
            return agent_client.delete_agent(agentId=agent_id)
    
    return None


