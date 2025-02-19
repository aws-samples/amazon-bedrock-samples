# This lambda function contains code to 
# set the bedrock client, and then query the search
# results from a knowledge base based on the user query. 
import os
import json
import logging
import boto3
from typing import Optional
from botocore.config import Config
# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Default region for the bedrock client
DEFAULT_REGION: str = 'us-east-1'
DEFAULT_NUM_RESULTS: str = 5

def get_bedrock_client(region: str) -> boto3.client:
    """
    Create and return a Bedrock client with the specified configuration
    """
    config = Config(
        region_name=region,
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    return boto3.client('bedrock-agent-runtime', config=config)

def query_knowledge_base(query: str, kb_id: str, region: str, num_results: int = 5) -> Optional[dict]:
    """
    Query the knowledge base using Retrieve API and return results
    Args:
        query (str): The query to send to the knowledge base
        kb_id (str): Knowledge base ID
        region (str): AWS region
        num_results (int): Number of results to retrieve
    Returns:
        dict: Dictionary containing retrieved chunks and their scores
    """
    try:
        result: Optional[dict] = None
        bedrock_client = get_bedrock_client(region)
        
        response_ret = bedrock_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': num_results,
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

def lambda_handler(event, context):
    """
    AWS Lambda handler function
    """
    try:
        # Log the incoming event for debugging
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract the query from the event
        query = None
        if "node" in event and "inputs" in event["node"]:
            for input_item in event["node"]["inputs"]:
                if input_item["name"] == "input":
                    query = input_item.get("value")
                    print(f"Query which will be used: {query}")

        # Extract other parameters
        kb_id = os.environ.get("KB_ID")
        print(f"KB id which will be used: {kb_id}")
        region = os.environ.get("REGION", DEFAULT_REGION)
        num_results = DEFAULT_NUM_RESULTS  

        # Validate required parameters
        if not query:
            return 'error: Query parameter is required'

        # Query the knowledge base
        result = query_knowledge_base(
            query=query,
            kb_id=kb_id,
            region=region,
            num_results=num_results
        )
        print(f"Results from the KB: {result}")
        
        if result is None:
            return 'body: Failed to query knowledge base'

        # Concatenate the chunk texts into a single string
        chunks = result.get('chunks', [])
        chunk_texts = [chunk['text'] for chunk in chunks]
        response_text = "\n\n".join(chunk_texts)
        print(f"Response text: {response_text}")
        # Return only the concatenated string
        return response_text

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return None
