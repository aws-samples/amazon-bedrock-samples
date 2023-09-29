import boto3
import json

#Create the connection to Bedrock
bedrock = boto3.client(
    service_name='bedrock',
    region_name='us-west-2', 
    
)

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2', 
    
)

# Let's see all available Anthropic Models
available_models = bedrock.list_foundation_models()

for model in available_models['modelSummaries']:
  if 'anthropic' in model['modelId']:
    print(model)


# Define prompt and model parameters
prompt_data = """Write me a poem about apples"""

body = {"prompt": "Human: " + prompt_data + " \\nAssistant:",
        "max_tokens_to_sample": 300, 
        "temperature": 1,
        "top_k": 250,
        "top_p": 0.999,
        "stop_sequences": ["\\n\\nHuman:"],
        "anthropic_version": "bedrock-2023-05-31"}

body = json.dumps(body) # Encode body as JSON string

modelId = 'anthropic.claude-instant-v1' 
accept = 'application/json'
contentType = 'application/json'

#Invoke the model
response = bedrock_runtime.invoke_model(body=body.encode('utf-8'), # Encode to bytes
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

response_body = json.loads(response.get('body').read())
print(response_body.get('completion'))


#We can also call the Anthropic Claude models via the streaming API

response = bedrock_runtime.invoke_model_with_response_stream(body=body.encode('utf-8'), # Encode to bytes
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

for event in response['body']:
    data = json.loads(event['chunk']['bytes'])
    print(data['completion'])
