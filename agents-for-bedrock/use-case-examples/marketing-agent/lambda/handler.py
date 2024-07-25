import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
import base64
import io
from io import StringIO
import pandas as pd

# bucket for personalize output
bucket=os.environ['BUCKET_PERSONALIZE_DATA']
# bucket="marketing-agent-1qaz"
# key for personalize ouput
# key="data/output/item.json.out"
key=os.environ['KEY_PERSONALIZE_DATA']
# bucket for image
# image_bucket="marketing-agent-1qaz"
image_bucket=os.environ['BUCKET_IMAGE']
image_prefix=os.environ['PREFIX_IMAGE']

def lambda_handler(event, context):
    print("Event Received:", event)
    api_path = event['apiPath']
    response_code = 200
    result = ''
    
    try:
        if api_path == '/getUserInfo':
            item_id = get_parameter(event, 'item_id')
            result = get_user_info(item_id)
        elif api_path == '/getItemInfo':
            item_id = get_parameter(event, 'item_id')
            result = get_item_info(item_id)
        elif api_path == '/contentGenerate':
            item = get_parameter(event, 'item')
            user = get_parameter(event, 'user')
            campaign = get_parameter(event, 'campaign')
            sample = get_parameter(event, 'sample')
            image = get_parameter(event, 'image')
            result = content_generate(item, user, campaign, sample, image)
        else:
            response_code = 404
            result = "Unrecognized API path: {}".format(api_path)
    except Exception as e:
        response_code = 404
        result = "An error occurred: {}".format(str(e))

    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event['actionGroup'],
            'apiPath': event['apiPath'],
            'httpMethod': event['httpMethod'],
            'httpStatusCode': response_code,
            'responseBody': {'application/json': {'body': result}}
        }
    }

def get_parameter(event, name):
    for param in event['parameters']:
        if param['name'] == name:
            return param['value']
    return None

def get_item_info(item_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('item_table')
    
    response = table.query(KeyConditionExpression=Key('ITEM_ID').eq(item_id))
    item = response['Items'][0]
    
    result = [{
        "item_id": str(item['ITEM_ID']),
        "title": str(item['NAME']),
        "price": str(item['PRICE']),
        "style": str(item['STYLE']),
        "image": str(item['IMAGE'])
    }]
    return json.dumps(result)

def get_user_info(item_id):
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, key)
    body = obj.get()['Body'].read().decode('utf-8')
    data = [json.loads(line) for line in body.splitlines()]
    dataframe = pd.json_normalize(data)
    filtered_df = dataframe[dataframe['input.itemId'] == item_id]
    user_ids = filtered_df['output.usersList'].tolist()[0]
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('user_table')
    users = []
    for user_id in user_ids:
        response = table.query(KeyConditionExpression=Key('USER_ID').eq(int(user_id)))
        user = response['Items'][0]
        users.append({"user_id": str(user['USER_ID']), "age": str(user['AGE']), "gender": str(user['GENDER'])})
    
    return json.dumps(call_bedrock(json.dumps("Summarize user persona for age and agenda: "+json.dumps(users))))

def content_generate(item, user, campaign, sample, image):
    image_data = download_and_decode_image(image_bucket, image)
    prompt = f"This is a {item} photo, please write a recommendation context about {campaign} campaign and follow the rules below \
        <rules> \
        1. Provide Primary text, Call to action, Headline, Description in new paragraphs with title. \
        2. Arrange them in the given sequence: Primary text, Call to action, Headline, Description\
        3. Start with an attention-grabbing subject line or opening sentence. This is crucial in marketing context where you need to capture interest quickly. \
        4. Clear Call-to-Action (CTA) offer a free trial, a discount, or an invitation to learn more. \
        5. Address Pain Points for general audience and demonstrate how your product or service provides a solution. \
        6. Highlight key features of the product or service that are most relevant to the target audience. \
        7. Include Social Testimonials by showing real-life benefits. \
        8. Keep it Concise and avoid overly complex language or lengthy paragraphs. \
        9. Consider your target audience including age, gender summarize in {user}. \
        10. Reference historical context sample: {sample}.\
        <\rules> "
    return call_bedrock(prompt, image_data)
    

def download_and_decode_image(bucket, key):
    s3 = boto3.client('s3')
    s3_response = s3.get_object(Bucket=bucket, Key=key)
    image_data = s3_response['Body'].read()
    return base64.b64encode(image_data).decode("utf-8")

def call_bedrock(prompt, image_data=None):
    model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
    max_tokens = 1000
    if image_data == None:
        messages = [{
            "role": "user",
             "content": [
                {
                    "type": "text", 
                    "text": prompt
                }
            ]
        }]
    else:
        messages = [{
            "role": "user",
             "content": [
                {
                    "type": "image", 
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg", 
                        "data": image_data
                    }
                },
                {
                    "type": "text", 
                    "text": prompt
                }
            ]
        }]
    bedrock_runtime = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages
        }
    )
    response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
    result = json.loads(response.get('body').read())['content'][0]['text']
    print(result)
    return result