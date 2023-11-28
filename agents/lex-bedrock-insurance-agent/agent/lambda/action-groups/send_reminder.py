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

from sigv4 import SigV4HttpRequester

# Instantiate boto3 clients and variables
dynamodb = boto3.resource('dynamodb',region_name=os.environ['AWS_REGION'])
dynamodb_client = boto3.client('dynamodb')
existing_claims_table_name = os.environ['EXISTING_CLAIMS_TABLE_NAME']

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
    # Define the characters that can be used in the random string
    characters = string.ascii_letters + string.digits
    
    # Generate a random string of the specified length
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    
    return random_string

def send_reminder(claim_id, pending_documents):
    print("Send Reminder")

    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
    sns_client = boto3.client('sns')
    subject = "Insurance Claim ID: " + str(claim_id)
    message = "Here is a reminder to upload your pending documents: " + str(pending_documents)

    print("Email message = " + message)

    email = "Dear policy holder, <br/>Please provide the following documents for your claim " + str(claim_id) + ": <br/><ul>"
    for doc in pending_documents:
        email += "<li><b>" + str(doc) + "</b>: </li>"
    email += "</ul>Thanks for your prompt attention to this matter so that we can finish processing your claim<br/><br/>"
    email += "Best regards,<br/>ACME Insurances"
    print(email)

    sns_client.publish(
        TopicArn=sns_topic_arn,
        Subject=subject,
        Message=str(email),
    )
    
    # Generate a random string of length 7 (to match the format '12a3456')
    reminder_id = generate_reminder_id(7)
    print("reminder_id = " + str(reminder_id))

    return reminder_id

## Agent runtime Retrieve API with boto3 client ##
def notify_pending_documents(event):
    kb_query = event["inputText"]

    # Agents for Bedrock boto3 client instantiation
    bedrock_client = boto3.client('bedrock')
    bedrock_runtime_client = boto3.client('bedrock-runtime')
    bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
    knowledgeBaseId = "QOQG1W8FUH"  

    # Define HTTP request payload (StartIngestionJobRequestContent)
    retrieval_query = {"text": kb_query}

    response = bedrock_agent_runtime_client.retrieve(knowledgeBaseId=knowledgeBaseId, retrievalQuery=retrieval_query)
    print("KB Response = " + str(response))

    pending_documents = response['retrievalResults'][0]['content']['text']
    print("KB Pending Docs = " + str(pending_documents))

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

    print("reminder_tracking_id = " + str(reminder_tracking_id))

    return {
        'response': {
            'sendReminderTrackingId': reminder_tracking_id,  # Add appropriate tracking ID
            'sendReminderStatus': 'InProgress',  # Modify based on the actual reminder status
            'pendingDocuments': pending_documents
        }
    }

'''
    ## DynamoDB ##
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

    # Querying DynamoDB for the specific claimId and fetching the 'pendingDocuments'
    table = dynamodb.Table(existing_claims_table_name)
    response = table.query(
        KeyConditionExpression='claimId = :claimId',
        ExpressionAttributeValues={':claimId': claim_id}
    )

    # Extracting 'pendingDocuments' from the response
    items = response.get('Items', [])
    if not items:
        return {
            'statusCode': 404,
            'response': 'ClaimId not found or no pending documents'
        }

    pending_documents = [item.get('pendingDocuments', []) for item in items]

'''

'''
def notify_pending_documents(event):
    print("Identifying Missing Documents")
    print("identify_missing_documents event = " + str(event))
    kb_query = event["inputText"]

    ## Direct Retrieve API invocation ##
    # Define Bedrock parameters
    knowledgeBaseId = "MAI2JAXIHE" 
    
    # agents = invoke-agent-bedrock.us-east-1.amazonaws.com
    # knowledgebases = bedrock-agent.us-east-1.amazonaws.com
    # Retrieve (POST /knowledgebases/knowledgeBaseId/retrieve HTTP/1.1)
    url = f'https://bedrock-agent.us-east-1.amazonaws.com/knowledgebases/{knowledgeBaseId}/retrieve/'

    requester = SigV4HttpRequester()
    # Define HTTP request payload (StartIngestionJobRequestContent)
    request_payload = {
         "retrievalQuery": {"text": kb_query}
    }

    response = requester.send_signed_request(
        url=url,
        method='POST',
        service='bedrock-runtime',
        headers={
            'content-type': 'application/json', 
            'accept': 'application/json',
        },
        region='us-east-1',
        body=json.dumps(request_payload)
    )


    print("notify_pending_documents response = " + str(response))
    # Check HTTP response
    if response.status_code == 200:
        print("PUT request successful!")
        print("Response:" + str(response))
    else:
        print(f"PUT request failed. Status code: {response.status_code}")
        print("Response:", response.text)

    # Need to assign pending documents based on Retrieve API response payload
    pending_documents = response['retrievalResults'][0]['content']['text']
'''
 
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