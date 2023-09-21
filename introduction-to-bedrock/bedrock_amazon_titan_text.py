import boto3
import json

#Create the connection to Bedrock
bedrock = boto3.client(
    service_name='bedrock',
    region_name='us-west-2', 
    endpoint_url='https://bedrock.us-west-2.amazonaws.com'
)


#Using Titan Text

# Define prompt and model parameters
prompt_data = """Write me a poem about apples"""

#The Text Generation Configuration are Titans inference parameters 

text_gen_config = {
    "maxTokenCount": 512,
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

# Invoke model 
response = bedrock.invoke_model(
    body=body, 
    modelId=model_id, 
    accept=accept, 
    contentType=content_type
)

# Print response
response_body = json.loads(response['body'].read())
print(response_body['results'][0]['outputText'])
