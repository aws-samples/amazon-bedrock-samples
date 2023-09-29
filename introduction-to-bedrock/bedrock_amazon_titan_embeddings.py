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

# Let's see all available Amazon Models
available_models = bedrock.list_foundation_models()

for model in available_models['modelSummaries']:
  if 'amazon' in model['modelId']:
    print(model)

# Define prompt and model parameters
prompt_data = """Write me a poem about apples"""

body = json.dumps({
    "inputText": prompt_data,
})

model_id = 'amazon.titan-embed-g1-text-02' #look for embeddings in the modelID
accept = 'application/json' 
content_type = 'application/json'

# Invoke model 
response = bedrock_runtime.invoke_model(
    body=body, 
    modelId=model_id, 
    accept=accept, 
    contentType=content_type
)

# Print response
response_body = json.loads(response['body'].read())
embedding = response_body.get('embedding')

#Print the Embedding

print(embedding)