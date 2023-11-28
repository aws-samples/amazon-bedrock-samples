import os
import io
import re
import json
import time
import boto3
import base64
import pandas
import random
import string
import decimal
import requests

from sigv4 import SigV4HttpRequester

def claim_generator():
    # Generate random characters and digits
    digits = ''.join(random.choice(string.digits) for _ in range(4))  # Generating 4 random digits
    chars = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))  # Generating 3 random characters
    
    # Construct the pattern (1a23b-4c)
    pattern = f"{digits[0]}{chars[0]}{digits[1:3]}{chars[1]}-{digits[3]}{chars[2]}"
    print("claim_generator pattern = " + str(pattern))

    return pattern

def create_claim(event):
    print("Creating Claim")

    # Instantiate boto3 session and clients
    boto3_session = boto3.Session(region_name=os.environ['AWS_REGION'])
    dynamodb = boto3.resource('dynamodb',region_name=os.environ['AWS_REGION'])
    s3_client = boto3.client('s3',region_name=os.environ['AWS_REGION'],config=boto3.session.Config(signature_version='s3v4',))

    # Define variables
    existing_claims_table_name = os.environ['EXISTING_CLAIMS_TABLE_NAME']
    knowledge_base_s3_bucket = os.environ['KB_BUCKET_NAME']
    knowledge_base_s3_key = os.environ['KB_BUCKET_KEY']

    # Download Excel file from S3
    response = s3_client.get_object(Bucket=knowledge_base_s3_bucket, Key=knowledge_base_s3_key)
    excel_buffer = io.BytesIO(response['Body'].read())
    excel_data = pandas.read_excel(excel_buffer)

    # TODO: Claim creation logic
    generated_claim = claim_generator()

    # Update Excel data as needed (for example, add a new row with a new claim)
    new_claim_data = {'claimId': generated_claim, 'policyId': '123456789', 'status': 'Open', 'pendingDocuments': ['Drivers License', 'Registration', 'Evidence']}  # Update column names and values
    new_data_frame = pandas.DataFrame([new_claim_data])
    excel_data = pandas.concat([excel_data, new_data_frame], ignore_index=True)

    # Upload updated Excel file back to S3
    excel_buffer = io.BytesIO()
    excel_data.to_excel(excel_buffer, index=False)
    s3_client.put_object(Body=excel_buffer.getvalue(), Bucket=knowledge_base_s3_bucket, Key=knowledge_base_s3_key) #, ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Update DynamoDB
    print("Updating DynamoDB")

    # Convert JSON document to DynamoDB format
    dynamodb_item = json.loads(json.dumps(new_claim_data), parse_float=decimal.Decimal)
    existing_claims_table = dynamodb.Table(existing_claims_table_name)
    response = existing_claims_table.put_item(
        Item=dynamodb_item
    )

    # Sync Bedrock knowledge base data source
    print("Syncing Bedrock Knowledge Base")

    # Define Bedrock parameters
    agentId = "OXI4KB2UUM"
    agentAliasId = "G3UE3MGNEQ"
    sessionId = event["sessionId"]
    knowledgeBaseId = "QOQG1W8FUH"
    dataSourceId = "K3W6CCI9Q0"
    
    # agents = invoke-agent-bedrock.us-east-1.amazonaws.com
    # knowledgebases = bedrock-agent.us-east-1.amazonaws.com
    # url = f'https://bedrock-agent.us-east-1.amazonaws.com/knowledgebases/{knowledgeBaseId}/datasources/{dataSourceId}/ingestionjobs/'

    # Agents for Bedrock boto3 client instantiation
    agent_client = boto3.client('bedrock-agent')

    # Define HTTP request payload (StartIngestionJobRequestContent)
    description = "Programmatic update of Bedrock KB data source"

    print("agent_client.start_ingestion_job(knowledgeBaseId=knowledgeBaseId, dataSourceId=dataSourceId)")
    agent_client.start_ingestion_job(knowledgeBaseId=knowledgeBaseId, dataSourceId=dataSourceId, description=description)  

    return {
        "response": [new_claim_data]   
    }

    '''requester = SigV4HttpRequester()
    response = requester.send_signed_request(
        url=url,
        method='PUT',
        service='bedrock',
        headers={
            'content-type': 'application/json', 
            'accept': 'application/json',
        },
        region='us-east-1',
        body=json.dumps(request_payload)
    )

    # Check HTTP response
    if response.status_code == 200:
        print("PUT request successful!")
        print("Response:" + str(response))
    else:
        print(f"PUT request failed. Status code: {response.status_code}")
        print("Response:", response.text)'''
 
def lambda_handler(event, context):
    response_code = 200
    action_group = event['actionGroup']
    api_path = event['apiPath']
    
    # API path routing
    if api_path == '/create-claim':
        body = create_claim(event)
    else:
        response_code = 400
        body = {"{}::{} is not a valid api, try another one.".format(action_group, api_path)}

    response_body = {
        'application/json': {
            'body': str(body)
        }
    }
    
    # Bedrock action group response format
    action_response = {
        "messageVersion": "1.0",
        "response": {
            'actionGroup': action_group,
            'apiPath': api_path,
            'httpMethod': event['httpMethod'],
            'httpStatusCode': response_code,
            'responseBody': response_body
        }
    }
 
    return action_response