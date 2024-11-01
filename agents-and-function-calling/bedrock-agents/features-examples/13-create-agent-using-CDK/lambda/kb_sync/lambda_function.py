import os
import boto3
import hashlib


def handler(event: dict, context: dict):
    """
    This function handles the S3 events resulting from a new `PutObject`
    event corresponding to a file upload

    Parameters
    ----------
    event : Event details
    context : Extra event context
    """
    # Instruct the KB to start the ingestion job
    client = boto3.client('bedrock-agent')
    client_token = hashlib.sha256(
        event['Records'][0]
        ['responseElements']['x-amz-request-id'].encode()).hexdigest()
    client.start_ingestion_job(clientToken=client_token,
                               dataSourceId=os.environ['DATA_SOURCE_ID'],
                               knowledgeBaseId=os.environ['KNOWLEDGE_BASE_ID'],
                               description='S3-originated data sync event')
    # write the event details to the CloudWatch logs
    print(event)
    # print value of environment variable
    print(os.environ['DATA_SOURCE_ID'])
    print(os.environ['KNOWLEDGE_BASE_ID'])
