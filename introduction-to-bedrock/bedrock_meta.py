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

# Let's see all available Meta Models

available_models = bedrock.list_foundation_models()
for model in available_models['modelSummaries']:
  if model['providerName']=='Meta':
    print(json.dumps(model, indent=2))

# Define prompt and model parameters
prompt = """What is the difference between a Llama and an Alpaca?"""

body = json.dumps({ 
	'prompt': prompt,
    'max_gen_len': 512,
	'top_p': 0.9,
	'temperature': 0.2
})

modelId = 'meta.llama2-13b-chat-v1'
accept = 'application/json'
contentType = 'application/json'

#Invoke the model
response = bedrock_runtime.invoke_model(body=body.encode('utf-8'), # Encode to bytes
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

response_body = json.loads(response.get('body').read().decode('utf-8'))
print(response_body.get('generation'))

#We can also call the Meta Llama 2 models via the streaming API
        
response = bedrock_runtime.invoke_model_with_response_stream(body=body.encode('utf-8'), # Encode to bytes
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

event_stream = response.get('body')
for b in iter(event_stream):
    bc = b['chunk']['bytes']
    gen = json.loads(bc.decode('utf-8'))
    line = gen.get('generation')
    if '\n' == line:
        print('')
        continue
    print(line, end='')
