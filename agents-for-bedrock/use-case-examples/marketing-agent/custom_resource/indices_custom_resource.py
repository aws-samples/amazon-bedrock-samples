from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import time
import json
import os


region = os.environ['AWS_REGION']
collection_endpoint = os.environ['COLLECTION_ENDPOINT']
vector_field = os.environ['VECTOR_FIELD_NAME']
vector_index_name = os.environ['VECTOR_INDEX_NAME']
text_field = os.environ['TEXT_FIELD']
metadata_field = os.environ['METADATA_FIELD']


def on_event(event, context):
  physical_id = "CreatedIndexId"

  print(json.dumps(event))
  request_type = event['RequestType']
  if request_type == 'Create': return on_create(event, physical_id=physical_id, region=region,
                                                endpoint=collection_endpoint, vector_field=vector_field,
                                                vector_index_name=vector_index_name, text_field=text_field,
                                                metadata_field=metadata_field)
  if request_type == 'Update': return on_update(event, physical_id=physical_id)
  if request_type == 'Delete': return on_delete(event, physical_id=physical_id)
  raise Exception("Invalid request type: %s" % request_type)
 


def on_create(event, physical_id, region, endpoint, vector_index_name,
              vector_field, text_field, metadata_field):
  props = event["ResourceProperties"]
  print("create new resource with props %s" % props)

  index_data(region=region, vector_index_name=vector_index_name, 
             text_field=text_field, metadata_field=metadata_field, 
             vector_field=vector_field, endpoint=endpoint)

  return { 'PhysicalResourceId': physical_id } 


def on_update(event, physical_id):
  # physical_id = event["PhysicalResourceId"]
  props = event["ResourceProperties"]
  print("update resource %s with props %s" % (physical_id, props))

  return { 'PhysicalResourceId': physical_id } 


def on_delete(event, physical_id):
  # physical_id = event["PhysicalResourceId"]
  print("delete resource %s" % physical_id)

  return { 'PhysicalResourceId': physical_id } 


def index_data(region, vector_index_name, text_field, 
               metadata_field, vector_field, endpoint):
    
    host = endpoint.replace("https://", "")
    
    # Set up auth for Opensearch client
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                       region, service, session_token=credentials.token)
    
    """Create an index"""
    # Build the OpenSearch client
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )
    # It can take up to a minute for data access rules to be enforced
    time.sleep(45)
    
    # Create index
    body = {
      "mappings": {
        "properties": {
          f"{metadata_field}": {
            "type": "text",
            "index": False
          },
          "id": {
            "type": "text",
            "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
              }
            }
          },
          f"{text_field}": {
            "type": "text",
            "index": False
          },
          f"{vector_field}": {
            "type": "knn_vector",
            "dimension": 1536,
            "method": {
              "engine": "nmslib",
              "space_type": "cosinesimil",
              "name": "hnsw"
            }
          }
        }
      },
      "settings": {
        "index": {
          "number_of_shards": 2,
          "knn.algo_param": {
            "ef_search": 512
          },
          "knn": True,
        }
      }
    }

    response = client.indices.create(index=vector_index_name, body=body)
    print('\nCreating index:')
    print(response)
    