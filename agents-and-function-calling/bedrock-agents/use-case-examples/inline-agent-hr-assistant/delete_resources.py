import boto3
import os
import json
from typing import Dict


# Global variable to store resources
RESOURCES = {}
client = boto3.client('bedrock-agent',
        region_name="us-east-1"
    )

def load_resources(resources_file: str = "resources_info.json") -> Dict:
    """Load resources information from resources.json file."""
    global RESOURCES
    
    if not os.path.exists(resources_file):
        raise FileNotFoundError(f"Resources file {resources_file} not found")
        
    with open(resources_file, 'r') as f:
        RESOURCES = json.load(f)
    
    return RESOURCES

def get_lambda_name(lambda_name: str) -> str:
    """Get Lambda ARN from loaded resources."""
    if not RESOURCES:
        load_resources()
    return RESOURCES['lambda'][lambda_name]['full_response']['FunctionName']

def get_lambda_role(lambda_name: str) -> str:
    """Get Lambda ARN from loaded resources."""
    if not RESOURCES:
        load_resources()
    return RESOURCES['lambda'][lambda_name]['full_response']['Role']

def get_kb_id() -> str:
    """Get Knowledge Base ID from loaded resources."""
    if not RESOURCES:
        load_resources()
    return RESOURCES['knowledge_base']['kb_id']

def get_data_source_id() -> str:
    """Get Knowledge Base ID from loaded resources."""
    if not RESOURCES:
        load_resources()
    return RESOURCES['knowledge_base']['data_source_id']

#######################
# delete KB resources #
#######################

kb_id = get_kb_id()
data_source_id = get_data_source_id()

print(f"KB_ID: {kb_id} Data Source ID: {data_source_id}")

# data_source_delete_response = client.delete_data_source(
#             dataSourceId=data_source_id,
#             knowledgeBaseId=kb_id
#         )

# print("Deleted datasource")
# print(data_source_delete_response)

# kb_delete_response = client.delete_knowledge_base(
#                     knowledgeBaseId=kb_id
#                 )

# print("Deleted knowledge base")
# print(kb_delete_response)


###########################
# delete lambda resources #
###########################
lambda_client = boto3.client('lambda')

list_of_function_names = ['compensation', 'vacation', 'budget']
for func in list_of_function_names:
    FunctionName = get_lambda_name(func)
    role = get_lambda_role(func)

    # delete lambda function
    response = lambda_client.delete_function(
        FunctionName=FunctionName
    )

print('lambda functions deleted')