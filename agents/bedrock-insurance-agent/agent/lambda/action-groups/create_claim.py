import os
import io
import re
import json
import time
import boto3
import base64
import random
import string
import decimal
import requests

# DynamoDB boto3 resource and variable
dynamodb = boto3.resource('dynamodb',region_name=os.environ['AWS_REGION'])
existing_claims_table_name = os.environ['EXISTING_CLAIMS_TABLE_NAME']

def claim_generator():
    print("Generating Claim ID")

    # Generate random characters and digits
    digits = ''.join(random.choice(string.digits) for _ in range(4))  # Generating 4 random digits
    chars = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))  # Generating 3 random characters
    
    # Construct the pattern (1a23b-4c)
    pattern = f"{digits[0]}{chars[0]}{digits[1:3]}{chars[1]}-{digits[3]}{chars[2]}"

    return pattern

def create_claim(event):
    print("Creating Claim")

    # TODO: Claim creation logic
    generated_claim = claim_generator()

    # Update Excel data as needed (for example, add a new row with a new claim)
    new_claim_data = {'claimId': generated_claim, 'policyId': '123456789', 'status': 'Open', 'pendingDocuments': ['Drivers License', 'Registration', 'Evidence']}  # Update column names and values

    # Update DynamoDB
    print("Updating DynamoDB")

    # Convert JSON document to DynamoDB format
    dynamodb_item = json.loads(json.dumps(new_claim_data), parse_float=decimal.Decimal)
    existing_claims_table = dynamodb.Table(existing_claims_table_name)
    response = existing_claims_table.put_item(
        Item=dynamodb_item
    ) 

    return {
        "response": [new_claim_data]   
    }
 
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