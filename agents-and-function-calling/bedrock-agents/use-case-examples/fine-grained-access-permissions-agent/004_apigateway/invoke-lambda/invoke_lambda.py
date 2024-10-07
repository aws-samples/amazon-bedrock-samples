import json
import boto3
import os
import urllib

# Initialize the Bedrock client
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

def lambda_handler(event, context):
    
    print(event)
    
    # Retrieve the necessary parameters from environment variables
    agent_id = os.environ['AGENT_ID']
    agent_alias_id = os.environ['AGENT_ALIAS_ID']
    
    # Retrieve the authorization header from the event
    authorization_header = event.get('headers', {}).get('Authorization', '')
    
    # Use the authorization header as the session_id
    # authorization_header
    
    # Get the prompt from the query string parameter 'inputPrompt'
    query_params = event.get('queryStringParameters', {})
    inputPrompt = query_params.get('inputPrompt', '')
    session_id = query_params.get('sessionId', '')

    print("authorization_header",authorization_header)
   
    print("query_params",query_params)
    print("inputPrompt",inputPrompt)
    prompt=urllib.parse.unquote(inputPrompt)
    
    
    print(prompt)

    # Invoke the Bedrock Agent
    response = bedrock_agent_runtime_client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        inputText=prompt,
        # enableTrace=True,  # Set enableTrace to True or False as needed
        sessionState={
        'sessionAttributes': {
            'authorization_header': authorization_header
            },
        }
    ) 

    # Process the response
    completion = ''
    for event in response.get('completion', []):
        chunk = event['chunk']
        completion += chunk['bytes'].decode()

        
    # Set the CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    
    print("completion", completion)

    return {
        'statusCode': 200,
         'headers': headers,
        'body': json.dumps({
            'completion': completion
        })
    }