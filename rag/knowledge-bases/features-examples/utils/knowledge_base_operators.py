import boto3
import re
import random
import time
import json
import os
import uuid
import logging
from botocore.exceptions import ClientError

suffix = random.randrange(200, 900)
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
iam_client = boto3_session.client('iam')
s3_client = boto3_session.client('s3')
account_number = boto3.client('sts').get_caller_identity().get('Account')
identity = boto3.client('sts').get_caller_identity()['Arn']

bedrock_agent_client = boto3.client('bedrock-agent')

def interactive_sleep(seconds: int):
    dots = ''
    for i in range(seconds):
        dots += '.'
        print(dots, end='\r')
        time.sleep(1)

def print_results(kb_response, response):
    # Print the KB retrieval results
    print("Knowledge Base retrieval results:\n")
    for i, result in enumerate(kb_response['retrievalResults'], start=1):
        text = result['content']['text']
        text = re.sub(r'\s+', ' ', text)
        print(f"Chunk {i}:\n{text}\n")
    
    # Print the text
    print(f"MODEL RESPONSE:\n")
    print(response['output']['message']['content'][0]['text'])

def print_results_with_guardrail(kb_response, response):
    # Print the KB retrieval results
    print("Knowledge Base retrieval results:\n")
    for i, result in enumerate(kb_response['retrievalResults'], start=1):
        text = result['content']['text']
        text = re.sub(r'\s+', ' ', text)
        print(f"Chunk {i}:\n{text}\n")
    
    # Print the text
    print(f"MODEL RESPONSE:\n")
    print(response['output']['message']['content'][0]['text'])
    
    # Print the outputAssessments scores
    print("\nCONTEXTUAL GROUNDING SCORES:\n")
    for key, assessments in response['trace']['guardrail']['outputAssessments'].items():
        for assessment in assessments:
            for filter in assessment['contextualGroundingPolicy']['filters']:
                print(f"Filter type: {filter['type']}, Score: {filter['score']}, Threshold: {filter['threshold']}, Passed: {filter['score'] >= filter['threshold']}")
    
    if response['stopReason'] == 'guardrail_intervened':
        print("\nGuardrail intervened")
        print("Model final response ->", response['output']['message']['content'][0]['text'])
        print("Model response ->", json.dumps(json.loads(response['trace']['guardrail']['modelOutput'][0]), indent=2))

import base64
from typing import List, Dict, Union


# Function to create document config to ingest document into a Bedrock Knowledge Base using DLA
def create_document_config(
    data_source_type: str,
    document_id: str = None,
    s3_uri: str = None,
    inline_content: Dict = None,
    metadata: Union[List[Dict], Dict] = None
) -> Dict:
    """
    Create a document configuration for ingestion.

    :param data_source_type: Either 'CUSTOM' or 'S3'.
    :param document_id: The ID for a custom document.
    :param s3_uri: The S3 URI for S3 data source.
    :param inline_content: The inline content configuration for custom data source.
    :param metadata: Metadata for the document. Can be a list of inline attributes or an S3 location.
    :return: A document configuration dictionary.
    """
    document = {'content': {'dataSourceType': data_source_type}}

    if data_source_type == 'CUSTOM':
        document['content']['custom'] = {
            'customDocumentIdentifier': {'id': document_id},
            'sourceType': 'IN_LINE' if inline_content else 'S3_LOCATION'
        }
        if inline_content:
            content_type = inline_content.get('type', 'TEXT')
            document['content']['custom']['inlineContent'] = {
                'type': content_type
            }
            if content_type == 'BYTE':
                document['content']['custom']['inlineContent']['byteContent'] = {
                    'data': inline_content['data'],
                    'mimeType': inline_content['mimeType']
                }
            else:  # TEXT
                document['content']['custom']['inlineContent']['textContent'] = {
                    'data': inline_content['data']
                }
        elif s3_uri:
            document['content']['custom']['s3Location'] = {'uri': s3_uri}
    elif data_source_type == 'S3':
        document['content']['s3'] = {'s3Location': {'uri': s3_uri}}

    if metadata:
        if isinstance(metadata, list):
            document['metadata'] = {
                'type': 'IN_LINE_ATTRIBUTE',
                'inlineAttributes': metadata
            }
        elif isinstance(metadata, dict) and 'uri' in metadata:
            document['metadata'] = {
                'type': 'S3_LOCATION',
                's3Location': {
                    'uri': metadata['uri'],
                    'bucketOwnerAccountId': metadata.get('bucketOwnerAccountId')
                }
            }
            if 'bucketOwnerAccountId' in document['metadata']['s3Location'] and document['metadata']['s3Location']['bucketOwnerAccountId'] is None:
                del document['metadata']['s3Location']['bucketOwnerAccountId']

    return document


# Function to to ingest document into a Bedrock Knowledge Base using DLA

def ingest_documents_dla(
    knowledge_base_id: str,
    data_source_id: str,
    documents: List[Dict[str, Union[Dict, str]]],
    client_token: str = None
) -> Dict:
    """
    Ingest documents into a knowledge base using the Amazon Bedrock API.

    :param knowledge_base_id: The ID of the knowledge base.
    :param data_source_id: The ID of the data source.
    :param documents: A list of document configurations to ingest.
    :param client_token: Optional unique token for request idempotency.
    :return: The API response.
    """
    bedrock_agent_client = boto3.client('bedrock-agent')  

    request = {
        'knowledgeBaseId': knowledge_base_id,
        'dataSourceId': data_source_id,
        'documents': documents
    }

    if client_token:
        request['clientToken'] = client_token

    return bedrock_agent_client.ingest_knowledge_base_documents(**request)


def create_kedra_genai_index_role(kendra_role_name, bucket_name, account_id):
    kendra_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "cloudwatch:namespace": "AWS/Kendra"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogGroups"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup"
                ],
                "Resource": [
                    f"arn:aws:logs:{region_name}:{account_id}:log-group:/aws/kendra/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogStreams",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": [
                    f"arn:aws:logs:{region_name}:{account_id}:log-group:/aws/kendra/*:log-stream:*"
                ]
            }
        ]
    }

    s3_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": f"{account_id}"
                    }
                }
            }
        ]
    }

    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "kendra.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # create policies based on the policy documents
    s3_policy = iam_client.create_policy(
        PolicyName='s3_permissions',
        PolicyDocument=json.dumps(s3_policy_document),
        Description='Policy for kendra to access and write to s3 bucket'
        )
    
    kendra_policy = iam_client.create_policy(
        PolicyName='kendra_permissions',
        PolicyDocument=json.dumps(kendra_policy_document),
        Description='Policy for kendra to access and write to cloudwatch'
        )

    
    # create Kendra Gen AI Index role
    kendra_genai_index_role=iam_client.create_role(
        RoleName=kendra_role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        Description='Role for Kendra Gen AI Index',
        MaxSessionDuration=3600
        )

    # fetch arn of the policies and role created above
    kendra_genai_index_role_arn=kendra_genai_index_role['Role']['Arn']
    s3_policy_arn=s3_policy['Policy']['Arn']
    kendra_policy_arn=kendra_policy['Policy']['Arn']
    

    # attach policies to Kendra Gen AI Index role
    iam_client.attach_role_policy(
        RoleName=kendra_role_name,
        PolicyArn=s3_policy_arn
    )

    iam_client.attach_role_policy(
        RoleName=kendra_role_name,
        PolicyArn=kendra_policy_arn
    )

    return kendra_genai_index_role

# create s3 bucket

def create_bucket(bucket_name, region=None):
    """Create an S3 bucket in a specified region

    If a region is not specified, the bucket is created in the S3 default
    region (us-east-1).

    :param bucket_name: Bucket to create
    :param region: String region to create bucket in, e.g., 'us-west-2'
    :return: True if bucket created, else False
    """

    # Create bucket
    try:
        if region is None:
            s3_client = boto3.client('s3')
            resp=s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client = boto3.client('s3', region_name=region)
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name,
                                    CreateBucketConfiguration=location)
    except ClientError as e:
        logging.error(e)
        return False
    return resp

# upload data to s3

def upload_to_s3(path, bucket_name):
        for root,dirs,files in os.walk(path):
            for file in files:
                file_to_upload = os.path.join(root,file)
                print(f"uploading file {file_to_upload} to {bucket_name}")
                s3_client.upload_file(file_to_upload,bucket_name,file)
