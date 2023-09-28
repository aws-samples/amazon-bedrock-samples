import boto3 
import requests
from requests_aws4auth import AWS4Auth 

session = boto3.Session(region_name='us-west-2')

credentials = session.get_credentials()

model_id = "amazon.titan-tg1-large" #change depending on your model of choice

endpoint = f'https://bedrock-runtime.us-west-2.amazonaws.com/model/{model_id}/invoke'

payload = {
  'inputText': 'Why is the sky blue?',
  'textGenerationConfig': {
    'maxTokenCount': 512,
    'stopSequences': [],
    'temperature': 0,
    'topP': 0.9
  } 
}

signer = AWS4Auth(credentials.access_key,  
                   credentials.secret_key,
                   'us-west-2', 'bedrock') 
                   
response = requests.post(endpoint, json=payload, auth=signer)

print(response.text)