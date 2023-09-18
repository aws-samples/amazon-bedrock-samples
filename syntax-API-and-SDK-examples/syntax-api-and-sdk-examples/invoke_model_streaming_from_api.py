import json
import os
import sys
import requests
import boto3
from botocore.awsrequest import AWSRequest 
from botocore.auth import SigV4Auth
import base64

module_path = ".."
sys.path.append(os.path.abspath(module_path))
from utils import bedrock, print_ww

# Run the 'download_dependencies.sh' script prior to execution of this file

# Instantiate a client to boto3
boto3_bedrock = bedrock.get_bedrock_client(
    assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
    endpoint_url=os.environ.get("BEDROCK_ENDPOINT_URL", None),
    region=os.environ.get("AWS_DEFAULT_REGION", None),
)

# List all models available for use
print(boto3_bedrock.list_foundation_models())

# Select one of the models available for use and the input/output formats
modelId: str = 'anthropic.claude-v2'
accept: str = 'application/json'
contentType: str = 'application/vnd.amazon.eventstream'

# Define a prompt, endpoint, and the payload for inputs to Bedrock
prompt: str = "Who is Andy Jassy?"
body: str = json.dumps(
    {   
        "prompt": prompt,
        "max_tokens_to_sample":4096, # Maximum number of tokens to generate. Responses are not guaranteed to fill up to the maximum desired length.
        "temperature":0.5, # Tunes the degree of randomness in generation. Lower temperatures mean less random generations.
        "top_k": 250, # Can be used to reduce repetitiveness of generated tokens. The higher the value, the stronger a penalty is applied to previously present tokens, proportional to how many times they have already appeared in the prompt or prior generation.
        "top_p": 0.5, # If set to float less than 1, only the smallest set of most probable tokens with probabilities that add up to top_p or higher are kept for generation.
        "stop_sequences":[] #  Up to four sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.
    }
)
invoke_model_streaming_endpoint: str = "https://bedrock.us-east-1.amazonaws.com/model/anthropic.claude-v2/invoke-with-response-stream"

# Create the request with Bedrock credentials
request = AWSRequest(method='POST', url=invoke_model_streaming_endpoint, data=body, params={}, headers={"Accept": "application/json", "Content-Type": "application/json"})
session = boto3.Session()
auth_credentials = session.get_credentials().get_frozen_credentials()
SigV4Auth(auth_credentials, "bedrock", 'us-east-1').add_auth(request)
response = requests.request(method='POST', url=invoke_model_streaming_endpoint, headers=dict(request.headers), data=body, stream=True)

# Handle and print response
if response.status_code == 200:
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            json_bytes = chunk[chunk.find(b'"bytes":"')+8:chunk.rfind(b'"')]
            json_text = base64.b64decode(json_bytes).decode('utf-8') 
            print(json_text)
else:
    print('Error, status code:', response.status_code)