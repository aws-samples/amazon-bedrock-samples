import boto3
import json

#Create the connection to Bedrock
bedrock = boto3.client(
    service_name='bedrock',
    region_name='us-west-2', 
    endpoint_url='https://bedrock.us-west-2.amazonaws.com'
)

# Let's see all available Anthropic Models
available_models = bedrock.list_foundation_models()

for model in available_models['modelSummaries']:
  if 'anthropic' in model['modelId']:
    print(model)

# Define prompt and model parameters
prompt_data = """Write me a poem about apples"""

