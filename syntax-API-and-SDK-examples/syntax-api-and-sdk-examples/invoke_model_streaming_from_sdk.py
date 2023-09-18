import json
import os
import sys
import boto3
from IPython.display import clear_output, display, display_markdown, Markdown

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
contentType: str = 'application/json'

# Define a prompt and the payload for inputs to Bedrock
prompt: str = "Who is Andy Jassy?"
body: str = json.dumps(
    {   "prompt": prompt,
        "max_tokens_to_sample":4096, # Maximum number of tokens to generate. Responses are not guaranteed to fill up to the maximum desired length.
        "temperature":0.5, # Tunes the degree of randomness in generation. Lower temperatures mean less random generations.
        "top_k": 250, # Can be used to reduce repetitiveness of generated tokens. The higher the value, the stronger a penalty is applied to previously present tokens, proportional to how many times they have already appeared in the prompt or prior generation.
        "top_p": 0.5, # If set to float less than 1, only the smallest set of most probable tokens with probabilities that add up to top_p or higher are kept for generation.
        "stop_sequences":[] #  Up to four sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.
    }
) 

# Create the request
response: dict = boto3_bedrock.invoke_model_with_response_stream(
    body=body, modelId=modelId, accept=accept, contentType=contentType
)

# Handle and print response
stream = response.get('body')
output = []
if stream:
    for event in stream:
        chunk = event.get('chunk')
        if chunk:
            chunk_obj = json.loads(chunk.get('bytes').decode())
            text = chunk_obj['completion']
            output.append(text)
            print_ww(f'\t\t\x1b[31m\x1b[0m\n{text}')

