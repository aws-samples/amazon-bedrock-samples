import os
import io
import re
import json
import time
import boto3
import base64
import string
import secrets

def generate_upload_id(length):
    print("Generating Upload ID")

    # Define the characters that can be used in the random string
    characters = string.ascii_letters + string.digits
    
    # Generate a random string of the specified length
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    
    return random_string

def gather_evidence(event):
    print("Gathering Evidence")

    # Generate a random string of length 7 (to match the format '12a3456')
    upload_id = generate_upload_id(7)
    print("upload_id = " + str(upload_id))

    return {
        "response": {
            "documentUploadUrl": "https://claimsdev.dkmn9jc6ric9u.amplifyapp.com/",
            "documentUploadTrackingId": upload_id,
            "documentUploadStatus": "InProgress"
        }
    }

def lambda_handler(event, context):
    response_code = 200
    action_group = event['actionGroup']
    api_path = event['apiPath']
    
    # API path routing
    if api_path == '/gather-evidence':
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