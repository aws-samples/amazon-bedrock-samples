import boto3
import os
import time
import json

agent_client = boto3.client("bedrock-agent")
event_bridge_client = boto3.client("events")

agent_name = os.environ['AGENT_NAME']
s3_bucket = os.environ['S3_BUCKET']
s3_bucket_create_agent_key = os.environ['S3_BUCKET_CREATE_AGENT_KEY']
s3_bucket_create_kb_key = os.environ['S3_BUCKET_CREATE_KB_KEY']
bedrock_agent_role_arn = os.environ['BEDROCK_AGENT_ROLE_ARN']
bedrock_invoke_create_agent_lambda_arn = os.environ['BEDROCK_CREATE_AGENT_LAMBDA_ARN']
bedrock_invoke_create_kb_lambda_arn = os.environ['BEDROCK_INVOKE_CREATE_KB_LAMBDA_ARN']
instruction = os.environ['INSTRUCTION']
model_name = os.environ['MODEL_NAME']
physical_id = os.environ['RESOURCE_ID']

def on_event(event, context):

  print(json.dumps(event))
  request_type = event['RequestType']
  if request_type == 'Create': return on_create(event, agent_name=agent_name, 
                                                s3_bucket=s3_bucket, 
                                                bedrock_agent_role_arn=bedrock_agent_role_arn,
                                                bedrock_invoke_create_agent_lambda_arn=bedrock_invoke_create_agent_lambda_arn,
                                                bedrock_invoke_create_kb_lambda_arn=bedrock_invoke_create_kb_lambda_arn,
                                                s3_bucket_create_agent_key=s3_bucket_create_agent_key,
                                                s3_bucket_create_kb_key=s3_bucket_create_kb_key,
                                                model_name=model_name,
                                                instruction=instruction, 
                                                physical_id=physical_id)
  if request_type == 'Update': return on_update(event, physical_id=physical_id)
  if request_type == 'Delete': return on_delete(event, 
                                                physical_id=physical_id,
                                                agent_name=agent_name)
  raise Exception("Invalid request type: %s" % request_type)


def on_create(event, agent_name, s3_bucket, 
              bedrock_agent_role_arn, 
              bedrock_invoke_create_agent_lambda_arn,
              bedrock_invoke_create_kb_lambda_arn,
              physical_id,
              s3_bucket_create_agent_key,
              s3_bucket_create_kb_key,
              model_name, instruction):
  props = event["ResourceProperties"]
  print("create new resource with props %s" % props)

  agent_id = create_agent(agent_resource_role_arn=bedrock_agent_role_arn, 
                          agent_name=agent_name, model_name=model_name,
                          instruction=instruction)
  # Pause to make sure agents has been created                           
  time.sleep(15)

  # Enable User Input
  print(
      f'Enabling user input for an agent with {agent_id} id ...')
  enable_user_input(agent_id)

  # Create agent action group
  create_agent_action_group(action_group_name='Create-Agent',
                            bucket=s3_bucket, 
                            agent_id=agent_id,
                            lambda_arn=bedrock_invoke_create_agent_lambda_arn,
                            key=s3_bucket_create_agent_key)
  # Invoke Create Kb action group
  create_agent_action_group(action_group_name='Create-KnowledgeBase',
                            bucket=s3_bucket, 
                            agent_id=agent_id,
                            lambda_arn=bedrock_invoke_create_kb_lambda_arn,
                            key=s3_bucket_create_kb_key)
  
  print(
      f'Preparing agent with {agent_id} id ...')
  prepare_agent(agent_id=agent_id)

  # Pause to make sure agent is in prepared state
  time.sleep(7)

  print(
      f'Creating an alias for an agent with {agent_id} id ...')
  create_agent_alias(agent_id=agent_id, alias_name=f'{agent_name}-alias')

  return { 'PhysicalResourceId': physical_id } 


def on_update(event, physical_id):
  # physical_id = event["PhysicalResourceId"]
  props = event["ResourceProperties"]
  print("update resource %s with props %s" % (physical_id, props))

  return { 'PhysicalResourceId': physical_id } 


def on_delete(event, agent_name, physical_id):
  # physical_id = event["PhysicalResourceId"]
  print("delete resource %s" % physical_id)
  delete_agent_alias(agent_name=agent_name)
  # Make sure alias is removed
  time.sleep(7)
  delete_agent(agent_name=agent_name)

  return { 'PhysicalResourceId': physical_id } 


def create_agent(agent_resource_role_arn, agent_name, 
                 model_name, instruction):
  
  response = agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_resource_role_arn,
    foundationModel=model_name,
    description="Agent created by CDK.",
    idleSessionTTLInSeconds=1800,
    instruction=instruction,
  )

  return response['agent']['agentId']


def enable_user_input(agent_id):
   response = agent_client.list_agent_action_groups(agentId=agent_id, agentVersion='DRAFT')
   for action_group in response['actionGroupSummaries']:
     if action_group['actionGroupName'] == 'UserInputAction':
        agent_client.update_agent_action_group(agentId=agent_id,
                                               agentVersion='DRAFT',
                                               actionGroupId=action_group['actionGroupId'],
                                               actionGroupName='UserInputAction',
                                               actionGroupState='ENABLED')
          


def prepare_agent(agent_id):
    return agent_client.prepare_agent(agentId=agent_id)


def create_agent_alias(agent_id, alias_name):
    agent_alias = agent_client.create_agent_alias(agentId=agent_id, 
                                                  agentAliasName=alias_name)
    return agent_alias['agentAlias']['agentAliasId']


def create_agent_action_group(action_group_name, agent_id, lambda_arn, bucket, key):
    agent_client.create_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupExecutor={
        'lambda': lambda_arn
    },
    actionGroupName=action_group_name,
    apiSchema={
        's3': {
            's3BucketName': bucket,
            's3ObjectKey': key
        }
    },
    description='This is a default description made by CDK. Modify it as needed.'
    )
    
    return


def delete_agent_alias(agent_name):
    
    # Find agentId related to our agent
    response_agents = agent_client.list_agents()
    for agent in response_agents["agentSummaries"]:
      if agent["agentName"] == agent_name:
          agent_id = agent["agentId"]
          break
      
    # Delete all aliases associated to an agent
    response_aliases = agent_client.list_agent_aliases(agentId=agent_id)
    for alias in response_aliases["agentAliasSummaries"]:
        agent_alias_id = alias["agentAliasId"]
        agent_client.delete_agent_alias(agentId=agent_id, 
                                        agentAliasId=agent_alias_id)
        

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




