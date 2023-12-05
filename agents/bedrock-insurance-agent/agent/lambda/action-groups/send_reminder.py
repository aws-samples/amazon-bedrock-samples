import os
import io
import re
import json
import time
import boto3
import base64
import string
import secrets
import requests

# Agents for Bedrock boto3 clients and variables
bedrock_client = boto3.client('bedrock')
bedrock_runtime_client = boto3.client('bedrock-runtime')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
knowledgeBaseId = os.environ['BEDROCK_KB_ID']

# DynamoDB boto3 clients and variables
dynamodb = boto3.resource('dynamodb',region_name=os.environ['AWS_REGION'])
dynamodb_client = boto3.client('dynamodb')
existing_claims_table_name = os.environ['EXISTING_CLAIMS_TABLE_NAME']

# SNS boto3 clients and variables
sns_topic_arn = os.environ['SNS_TOPIC_ARN']
sns_client = boto3.client('sns')

def open_claims():
    print("Finding Open Claims")

    response = dynamodb_client.scan(
        TableName=existing_claims_table_name,
        FilterExpression='#s = :s',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={
            ':s': {'S': 'Open'}
        }
    )

    return response['Items'] if 'Items' in response else []

def generate_reminder_id(length):
    print("Generate Reminder ID")
    # Define the characters that can be used in the random string
    characters = string.ascii_letters + string.digits
    
    # Generate a random string of the specified length
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    
    return random_string

def send_reminder(claim_id, pending_documents):
    print("Send Reminder")

    subject = "Insurance Claim ID: " + str(claim_id)
    message = "Here is a reminder to upload your pending documents: " + str(pending_documents)
    print("Email Message: " + message)

    sns_client.publish(
        TopicArn=sns_topic_arn,
        Subject=subject,
        Message=message,
    )
    
    # Generate a random string of length 7 (to match the format '12a3456')
    reminder_id = generate_reminder_id(7)
    print("Reminder ID: " + str(reminder_id))

    return reminder_id

## Agent runtime Retrieve API with boto3 client ##
def notify_pending_documents(event):
    print("Notify Pending Documents")

    # Define HTTP request payload (Retrieve API)
    kb_query = event["inputText"]
    retrieval_query = {"text": kb_query}
    print("KB Query: " + str(kb_query))

    response = bedrock_agent_runtime_client.retrieve(knowledgeBaseId=knowledgeBaseId, retrievalQuery=retrieval_query)
    print("KB Response: " + str(response))

    pending_documents = response['retrievalResults'][0]['content']['text']
    print("KB Pending Docs: " + str(pending_documents))

    # Extracting claimId value from event parameters
    claim_id = None
    for param in event.get('parameters', []):
        if param.get('name') == 'claimId':
            claim_id = param.get('value')
            break

    print("claimId = " + str(claim_id))

    if not claim_id:
        return {
            'statusCode': 400,
            'response': 'Missing claimId parameter'
        }

    # Generate a random string of length 7 (to match the format '12a3456')
    reminder_tracking_id = send_reminder(claim_id, pending_documents)
    print("Reminder tracking ID = " + str(reminder_tracking_id))

    return {
        'response': {
            'sendReminderTrackingId': reminder_tracking_id,  # Add appropriate tracking ID
            'sendReminderStatus': 'InProgress',  # Modify based on the actual reminder status
            'pendingDocuments': pending_documents
        }
    }
 
def lambda_handler(event, context):
    response_code = 200
    action_group = event['actionGroup']
    api_path = event['apiPath']

    if api_path == '/open-claims':
        body = open_claims() 
    elif api_path == '/claims/{claimId}/notify-pending-documents':
        # parameters = event['parameters']
        body = notify_pending_documents(event)
    else:
        response_code = 400
        body = {"{}::{} is not a valid api, try another one.".format(action_group, api_path)}
    
    response_body = {
        'application/json': {
            'body': str(body)
        }
    }
    
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