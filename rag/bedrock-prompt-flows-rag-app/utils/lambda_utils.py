import re
import os
import json
import yaml
import time
import boto3
import zipfile
import logging
from io import BytesIO
from pathlib import Path
from typing import Union, Dict, Optional
from botocore.exceptions import ClientError

# set a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PYTHON_TIMEOUT: int = 180
PYTHON_RUNTIME: str = "python3.12"

# Initialize S3 client
s3_client = boto3.client('s3')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime') 

def create_kb_lambda(
    lambda_function_name: str,
    source_code_file: str,
    region: str,
    kb_id: str) -> str:
    """
    Creates a Lambda function for knowledge base queries
    
    Args:
        lambda_function_name (str): Name of the Lambda function to create
        source_code_file (str): Name of the file containing the Lambda source code
        region (str): AWS region for the Lambda
        kb_id (str): Knowledge base ID
    
    Returns:
        str: ARN of the created Lambda function
    """
    try:
        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name=region)
        iam = boto3.client('iam', region_name=region)
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']

        # Create IAM role for Lambda
        role_name = f"{lambda_function_name}-role"
        try:
            role = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                })
            )

            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{lambda_function_name}-policy",
                PolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            "Resource": [
                                f"arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/{lambda_function_name}:*"
                            ]
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "bedrock:*",
                                "bedrock-runtime:*",
                                "bedrock-agent-runtime:*"
                            ],
                            "Resource": "*"
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "bedrock:Retrieve",
                            ],
                            "Resource": [
                                f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/{kb_id}",
                                f"arn:aws:bedrock:{region}:{account_id}:knowledge-base/{kb_id}/*"
                            ]
                        }
                    ]
                })
            )

            # Attach AWS managed policies
            managed_policies = [
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
            ]
            
            for policy in managed_policies:
                iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy
                )

            # Wait for role to propagate
            time.sleep(10)

        except iam.exceptions.EntityAlreadyExistsException:
            # If role exists, get its ARN
            role = iam.get_role(RoleName=role_name)

        # Package the Lambda code
        _base_filename = source_code_file.split(".py")[0]
        s = BytesIO()
        with zipfile.ZipFile(s, "w") as z:
            z.write(f"{source_code_file}")
        zip_content = s.getvalue()

        # Set environment variables
        env_variables = {
            "Variables": {
                "KB_ID": kb_id,
                "REGION": region
            }
        }

        # Create Lambda function
        lambda_function = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime=PYTHON_RUNTIME,
            Timeout=PYTHON_TIMEOUT,
            Role=role['Role']['Arn'],
            Code={"ZipFile": zip_content},
            Handler=f"{_base_filename}.lambda_handler",
            Environment=env_variables
        )

        print(f"Lambda function created successfully: {lambda_function['FunctionArn']}")
        return lambda_function["FunctionArn"]

    except Exception as e:
        print(f"Error creating Lambda function: {str(e)}")
        raise

def query_knowledge_base(query: str, kb_id: str, kb_info: Dict) -> Optional[dict]:
    """
    Query the knowledge base using Retrieve API and return results
    Args:
        query (str): The query to send to the knowledge base
    Returns:
        dict: Dictionary containing retrieved chunks and their scores
        {
            'chunks': list of retrieved text chunks,
            'raw_response': complete API response
        }
    """
    try:
        result: Optional[dict] = None
        response_ret = bedrock_agent_runtime_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': kb_info.get('num_retrieved_results', 5),
                    'overrideSearchType': 'HYBRID'
                }
            }
        )
        contexts = []
        if 'retrievalResults' in response_ret:
            for chunk in response_ret['retrievalResults']:
                contexts.append({
                    'text': chunk['content']['text'],
                    'location': chunk['location'],
                    'score': chunk.get('score', 0),
                    'metadata': chunk.get('metadata', {})
                })
        result = {
            'chunks': contexts,
            'raw_response': response_ret
        }
    except Exception as e:
        logger.error(f"Error querying knowledge base: {str(e)}")
        result = None
    return result

def query_lambda(query: str, region: str, kb_id: str, lambda_fn_name: str):
    """
    Simple Lambda test function that matches local testing style
    """
    lambda_client = boto3.client('lambda', region_name=region)
    payload = {
        'body': json.dumps({
            'query': query,
            'kb_id': kb_id,
            'region': region,
            'num_results': 5
        })
    }
    response = lambda_client.invoke(
        FunctionName=lambda_fn_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    return json.loads(json.loads(response['Payload'].read())['body'])