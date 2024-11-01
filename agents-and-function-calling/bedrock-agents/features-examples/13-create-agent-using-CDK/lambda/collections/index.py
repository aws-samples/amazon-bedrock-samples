#!/usr/bin/env python3

import os
import time
import boto3
from urllib import parse
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection


def create_collection_index(host: str, index_name: str,
                            metadata_field_name: str, text_field_name: str,
                            vector_field_name: str, vector_size: int = 1024):
    """
    Create an index in the given collection with the given param

    Parameters
    ----------
    host : endpoint for OpenSearch Collection
    index_name : name of the index to create
    metadata_field_name: name of the metadata field
    text_field_name: name of the text field
    vector_field_name : name of the vector field
    vector_size : Dimension of the vector. Depends on the embeddings model used. Check:
                       https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-setup.html
    """
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                       os.environ['AWS_REGION'], 'aoss', session_token=credentials.token)

    # Build the OpenSearch client
    client = OpenSearch(hosts=[{'host': host, 'port': 443}],
                        http_auth=awsauth,
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection,
                        timeout=300)
    # Create index
    response = client.indices.create(
        index=index_name,
        body={'settings': {'index.knn': True},
              'mappings': {'properties': {
                  metadata_field_name: {'type': 'text', 'index': False},
                  text_field_name: {'type': 'text'},
                  'id': {'type': 'text',
                         'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}}},
                  'x-amz-bedrock-kb-source-uri': {'type': 'text',
                                                  'fields': {'keyword': {'type': 'keyword',
                                                                         'ignore_above': 256}}},
                  vector_field_name: {'type': 'knn_vector',
                                      'dimension': vector_size,
                                      'method': {'name': 'hnsw',
                                                 'engine': 'faiss',
                                                 'parameters': {
                                                     'ef_construction': 512,
                                                     'm': 16}}}}}})
    print(response)
    time.sleep(5)


def handler(event, context):
    """
    Handle the Custom Resource eevnts from CDK.

    In practice, it will only create the index in the Collection provided 
    in the event ResourceProperties

    This lambda expects the Collection to be created already, 
    but will wait for it to be available if status is 'CREATING'

    Parameters
    ----------
    event : Event information
    """
    # Ignore all non-create events
    if event['RequestType'] != 'Create':
        return

    # Get Collection name
    collection_name = event.get('ResourceProperties', dict()).get('collection')
    if collection_name is None:
        raise RuntimeError('Could not get collection name from event')
    endpoint = event.get('ResourceProperties', dict()).get('endpoint')
    index_name = event.get('ResourceProperties', dict()
                           ).get('vector_index_name')
    metadata_field = event.get(
        'ResourceProperties', dict()).get('metadata_field')
    text_field = event.get('ResourceProperties', dict()).get('text_field')
    vector_field = event.get('ResourceProperties', dict()).get('vector_field')
    vector_size = event.get('ResourceProperties', dict()).get('vector_size')
    print(f'Creating index on collection {
          collection_name} in endpoint {endpoint}')

    # Read the basic Collection information
    parts = parse.urlparse(endpoint)
    hostname = parts.hostname

    # Check the status and retry if the collection is still being created
    create_collection_index(host=hostname, index_name=index_name,
                            vector_field_name=vector_field,
                            text_field_name=text_field,
                            metadata_field_name=metadata_field,
                            vector_size=vector_size)
