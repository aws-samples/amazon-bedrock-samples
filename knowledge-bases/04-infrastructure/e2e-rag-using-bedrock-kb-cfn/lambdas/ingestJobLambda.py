import os
from typing import Dict
from boto3 import client
import json

KNOWLEDGE_BASE_ID = os.environ['KNOWLEDGE_BASE_ID']
DATA_SOURCE_ID = os.environ['DATA_SOURCE_ID']
AWS_REGION = os.environ['REGION']

bedrock_agent_client = client('bedrock-agent', region_name=AWS_REGION)

def lambda_handler(event, context):
    input_data = {
        'knowledgeBaseId': KNOWLEDGE_BASE_ID,
        'dataSourceId': DATA_SOURCE_ID,
        # 'clientToken': context.aws_request_id
    }
    
    response = bedrock_agent_client.start_ingestion_job(**input_data)
    print(response)
    
    return {
        'ingestionJob': response['ingestionJob']
    }

