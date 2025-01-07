import boto3
import random
import time
import json
import uuid

suffix = random.randrange(200, 900)
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
iam_client = boto3_session.client('iam')
account_number = boto3.client('sts').get_caller_identity().get('Account')
identity = boto3.client('sts').get_caller_identity()['Arn']

bedrock_agent_client = boto3.client('bedrock-agent')

def interactive_sleep(seconds: int):
    dots = ''
    for i in range(seconds):
        dots += '.'
        print(dots, end='\r')
        time.sleep(1)



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
