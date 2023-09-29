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

# Let's see all available Cohere Models
available_models = bedrock.list_foundation_models()

for model in available_models['modelSummaries']:
  if 'cohere' in model['modelId']:
    print(model)



prompt_data = """Write me a poem about apples""" #edit with your prompt

body = {
    "prompt": prompt_data,
    "max_tokens": 400,
    "temperature": 0.75,
    "p": 0.01,
    "k": 0,
    "stop_sequences": [],
    "return_likelihoods": "NONE"
}

modelId = 'cohere.command-text-v14' 
accept = 'application/json'
contentType = 'application/json'


body = json.dumps(body).encode('utf-8')

#Invoke the model
response = bedrock_runtime.invoke_model(body=body,
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

response_body = json.loads(response.get('body').read())

print(response_body['generations'][0]['text'])

