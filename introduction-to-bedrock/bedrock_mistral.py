import boto3
import json

#Create the connection to Bedrock
# - These are available in us-west-2 for now 
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
  if model['providerName']=='Mistral AI':
    print(json.dumps(model, indent=2))

# Define prompt and model parameters
# - Mistral Instruct chat template is -- similiar to <s>[INST] Instruction [/INST] Model answer</s>[INST] Follow-up instruction [/INST]
#- Note that <s> and </s> are special tokens for beginning of string (BOS) and end of string (EOS) while [INST] and [/INST] are regular strings.
prompt = """<s>[INST]Craft a Python function to convert Celsius to Fahrenheit. If water boils at 100°C, what's that in Fahrenheit?[/INST]</s>"""

body = json.dumps({ 
    'prompt': prompt,
    'max_tokens': 200,
    'top_p': 0.9,
    'temperature': 0.2,
})

modelId = 'mistral.mistral-7b-instruct-v0:2'

accept = 'application/json'
contentType = 'application/json'

#Invoke the model
#- Response comes back as 'outputs' with a list
response = bedrock_runtime.invoke_model(body=body.encode('utf-8'), # Encode to bytes
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

response_body = json.loads(response.get('body').read().decode('utf-8'))
print(response_body.get('outputs')[0].get('text'))
#We can also call the Mistral models via the streaming API
        
response = bedrock_runtime.invoke_model_with_response_stream(body=body.encode('utf-8'), # Encode to bytes
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

event_stream = response.get('body')
for b in iter(event_stream):
    bc = b['chunk']['bytes']
    gen = json.loads(bc.decode('utf-8'))
    line = gen.get('outputs')[0].get('text')
    if '\n' == line:
        print('')
        continue
    print(line, end='')


# - Create a JSON response example
    
prompt="""
[INST] You are a helpful code assistant. Your task is to generate a valid JSON object based on the given information:

name: Person First Name
lastname: Person Last Name
address: #1 Samuel St.

Just generate the JSON object without explanations:
[/INST]"""

body = json.dumps({ 
    'prompt': prompt,
    'max_tokens': 200,
    'top_p': 0.9,
    'temperature': 0.2,
    'top_k' : 2
})

modelId = 'mistral.mistral-7b-instruct-v0:2'
accept = 'application/json'
contentType = 'application/json'

#Invoke the model
#- Response comes back as 'outputs' with a list
response = bedrock_runtime.invoke_model(body=body.encode('utf-8'), # Encode to bytes
                                 modelId=modelId, 
                                 accept=accept, 
                                 contentType=contentType)

response_body = json.loads(response.get('body').read().decode('utf-8'))
print(response_body.get('outputs')[0].get('text'))