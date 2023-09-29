import boto3
import json

#Create the connection to Bedrock
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2', 
    
)


# Define prompt and model parameters
prompt_data = """Write an essay about why someone should drink coffee"""

text_gen_config = {
    "maxTokenCount": 1000,
    "stopSequences": [], 
    "temperature": 0,
    "topP": 0.9
}

body = json.dumps({
    "inputText": prompt_data,
    "textGenerationConfig": text_gen_config  
})

model_id = 'amazon.titan-tg1-large'
accept = 'application/json' 
content_type = 'application/json'

#invoke the model with a streamed response 
response = bedrock_runtime.invoke_model_with_response_stream(
    body=body, 
    modelId=model_id, 
    accept=accept, 
    contentType=content_type
)

for event in response['body']:
    data = json.loads(event['chunk']['bytes'])
    print(data['outputText'])
