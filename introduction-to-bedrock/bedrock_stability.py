from botocore.config import Config
from botocore.exceptions import ClientError
import json
from PIL import Image
from io import BytesIO
import base64
from base64 import b64encode
from base64 import b64decode
import boto3


#Create the connection to Bedrock

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2', 
    
)

bedrock = boto3.client(
    service_name='bedrock',
    region_name='us-west-2', 
    
)

# Let's see all available Stability Models
available_models = bedrock.list_foundation_models()

for model in available_models['modelSummaries']:
  if 'stability' in model['modelId']:
    print(model)


# Define prompt and model parameters
prompt_data = """Middle age man walking through times square on a snowy day"""

body = json.dumps({"text_prompts":[{"text":prompt_data}],
  "cfg_scale":6,
  "seed":10,
  "steps":50}) 

modelId = 'stability.stable-diffusion-xl'
accept = 'application/json'
contentType = 'application/json'

response = bedrock_runtime.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
response = json.loads(response.get('body').read())
images = response.get('artifacts')

image = Image.open(BytesIO(b64decode(images[0].get('base64'))))
image.save("generated_image.png")

#Stable Diffusion let's us do some interesting stuff with our images like adding new characters or modifying scenery let's give it a try

prompt_data = """Change the character to a grandma and her grandaughter on a snowy day""" #If you'd like to try your own prompt, edit this parameter!

buffer = BytesIO()
img = Image.open("generated_image.png")
img.save(buffer, format="PNG")
img_bytes = buffer.getvalue()

body = json.dumps({"text_prompts":[{"text": prompt_data }], "init_image": base64.b64encode(img_bytes).decode()})
modelId = 'stability.stable-diffusion-xl'

try: 
    response = bedrock_runtime.invoke_model(body=body, modelId=modelId, contentType="application/json", accept="image/png")
except ClientError as error:
    print(error.response)
 
if response['contentType'] == 'image/png':
    # Get the response body as bytes
    image_data = response['body'].read()
else:
    image_data = response['body']

image = Image.open(BytesIO(image_data))
file_name = 'converted.png'

#save file
image.save(file_name)
