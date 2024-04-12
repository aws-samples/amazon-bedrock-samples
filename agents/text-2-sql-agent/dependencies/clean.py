from config import *

# Initialize the Glue client
glue_client = boto3.client('glue')


# Function to delete a Glue crawler
def delete_crawler(crawler_name):
    try:
        glue_client.delete_crawler(Name=crawler_name)
        print(f"Crawler '{crawler_name}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting crawler '{crawler_name}':", e)

# Function to delete Glue tables in a database
def delete_tables(database_name):
    try:
        # List all tables in the database
        response = glue_client.get_tables(DatabaseName=database_name)
        table_list = response['TableList']
        
        # Delete each table
        for table in table_list:
            table_name = table['Name']
            glue_client.delete_table(DatabaseName=database_name, Name=table_name)
            print(f"Table '{table_name}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting tables in database '{database_name}':", e)

# Function to delete a Glue database
def delete_database(database_name):
    try:
        glue_client.delete_database(Name=database_name)
        print(f"Database '{database_name}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting database '{database_name}':", e)


# Empty and delete S3 Bucket
try:
    objects = s3_client.list_objects(Bucket=bucket_name)  
    if 'Contents' in objects:
        for obj in objects['Contents']:
            s3_client.delete_object(Bucket=bucket_name, Key=obj['Key']) 
    s3_client.delete_bucket(Bucket=bucket_name)
except:
    pass



try:
    delete_crawler(glue_crawler_name)
    delete_tables(glue_database_name)
    delete_database(glue_database_name)
except:
    pass







list_agent=bedrock_agent_client.list_agents()['agentSummaries']
list_agent
#print(list_agent)
# Search for the agent with the name 'text2sql' and extract its ID
agent_id = next((agent['agentId'] for agent in list_agent if agent['agentName'] == agent_name), None)

print(agent_id)
try:
    response = bedrock_agent_client.list_agent_action_groups(
        agentId=agent_id,
        agentVersion='1',

    )
    list_action_group=response['actionGroupSummaries']
    print(list_action_group)

    action_group_name='QueryAthenaActionGroup'

    action_group_id=next((agent['actionGroupId'] for agent in list_action_group if agent['actionGroupName'] == action_group_name), None)
    print(action_group_id)

    response = bedrock_agent_client.list_agent_aliases(
        agentId=agent_id,
    )
    response['agentAliasSummaries']
    print(type(response['agentAliasSummaries']))
    agentAliasId=next((agent['agentAliasId'] for agent in response['agentAliasSummaries'] if agent['agentAliasName'] == agent_alias_name), None)
    agentAliasId
except:
    pass

lambda_name = f'{agent_name}-{suffix}'
print(lambda_name)
try:
    resp=lambda_client.get_function(FunctionName=lambda_name)
    print(resp['Configuration']['FunctionArn'])
    FunctionArn=resp['Configuration']['FunctionArn']

    response = bedrock_agent_client.update_agent_action_group(
       agentId=agent_id,
       agentVersion='DRAFT',
       actionGroupId= action_group_id,
       actionGroupName=action_group_name,
       actionGroupExecutor={
           'lambda': FunctionArn
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
except:
    print('can not delete')

try:
    agent_alias_deletion = bedrock_agent_client.delete_agent_alias(
    agentId=agent_id,
    agentAliasId=agentAliasId
    )
except:
    pass
try:
    agent_deletion = bedrock_agent_client.delete_agent(
    agentId=agent_id
    )
except:
    pass



try:
    # Delete Lambda function
    lambda_client.delete_function(
        FunctionName=lambda_name
    )
except:
    pass







policy_arns = [
    'arn:aws:iam::aws:policy/AmazonAthenaFullAccess',
    'arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess',
    'arn:aws:iam::aws:policy/AmazonS3FullAccess',
    'arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole',
    'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
]  
try:
    for policy_arn in policy_arns:
        iam_client.detach_role_policy(
            RoleName=lambda_role_name,
            PolicyArn=policy_arn
        )    

    policy_arns = [
        'arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess',
        'arn:aws:iam::aws:policy/AmazonS3FullAccess',
    ]  
    for policy_arn in policy_arns:
        iam_client.detach_role_policy(
            RoleName=glue_role_name,
            PolicyArn=policy_arn
        )    

    bedrock_agent_s3_allow_policy_name
    for policy in [bedrock_agent_bedrock_allow_policy_name]:
        iam_client.detach_role_policy(RoleName=agent_role_name, PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}')


    for policy in [bedrock_agent_s3_allow_policy_name]:
        iam_client.detach_role_policy(RoleName=agent_role_name, PolicyArn=f'arn:aws:iam::{account_id}:policy/{policy}')

except:
    pass






try:

    for role_name in [agent_role_name]:
        iam_client.delete_role(
            RoleName=role_name
        )
        





    for role_name in [lambda_role_name]:
        iam_client.delete_role(
            RoleName=role_name
        )
except:
    pass    

# Initialize the IAM client

# The name of the policy you want to delete
#bedrock_agent_bedrock_allow_policy_name = 'YourPolicyNameHere'

def delete_policy_by_name(policy_name):
    # List all policies
    paginator = iam_client.get_paginator('list_policies')
    for response in paginator.paginate(Scope='Local'):
        for policy in response['Policies']:
            if policy['PolicyName'] == policy_name:
                policy_arn = policy['Arn']
                # Delete the policy by ARN
                try:
                    iam_client.delete_policy(PolicyArn=policy_arn)
                    print(f"Policy '{policy_name}' deleted successfully.")
                    return
                except Exception as e:
                    print(f"Error deleting policy '{policy_name}':", e)
                    return
    print(f"Policy '{policy_name}' not found.")
try:
    # Example usage
    delete_policy_by_name(bedrock_agent_bedrock_allow_policy_name)
    delete_policy_by_name(bedrock_agent_s3_allow_policy_name)
except:
    pass
try:
    for role_name in [glue_role_name]:
        iam_client.delete_role(
            RoleName=role_name
        )
except:
    pass   






