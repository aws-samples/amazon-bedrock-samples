import os
import io
import re
import json
import time
import boto3
import botocore
import base64
import string
import secrets

# Other boto3 clients and variables
boto3_session = boto3.Session(region_name=os.environ['AWS_REGION'])
dynamodb = boto3.resource('dynamodb',region_name=os.environ['AWS_REGION'])

# SNS boto3 clients and variables
sns_topic_arn = os.environ['SNS_TOPIC_ARN']
sns_client = boto3.client('sns')

# URL
url = os.environ['CUSTOMER_WEBSITE_URL']

def get_named_parameter(event, name):
    return next(item for item in event['parameters'] if item['name'] == name)['value']

def get_named_property(event, name):
    return next(item for item in event['requestBody']['content']['application/json']['properties'] if item['name'] == name)['value']

def generate_upload_id(length):
    print("Generating Upload ID")

    # Define the characters that can be used in the random string
    characters = string.ascii_letters + string.digits
    
    # Generate a random string of the specified length
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    
    return random_string

def send_evidence_url(claim_id):
    print("Send Evidence URL")

    subject = "Gathering Evidence for Claim ID: " + claim_id
    message = "Please upload your claim evidence in the AnyCompany Insurance Portal: " + url

    sns_client.publish(
        TopicArn=sns_topic_arn,
        Subject=subject,
        Message=message,
    )

def gather_evidence(event):
    print("Gathering Evidence")

    # Extracting claimId value from event parameters
    claim_id = get_named_parameter(event, 'claimId')
    '''
    for param in event.get('parameters', []):
        if param.get('name') == 'claimId': 
            claim_id = param.get('value')
            break'''

    print("Claim ID: " + str(claim_id))

    send_evidence_url(claim_id)

    # Generate a random string of length 7 (to match the format '12a3456')
    upload_id = generate_upload_id(7)
    print("Upload ID: " + str(upload_id))

    return {
        "response": {
            "documentUploadUrl": url,
            "documentUploadTrackingId": upload_id,
            "documentUploadStatus": "InProgress"
        }
    }

def lambda_handler(event, context):
    response_code = 200
    action_group = event['actionGroup']
    api_path = event['apiPath']
    
    # API path routing
    if api_path == '/claims/{claimId}/gather-evidence':
        body = gather_evidence(event)
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