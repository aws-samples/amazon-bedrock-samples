# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# PDX-License-Identifier: MIT-0 (For details, see https://github.com/awsdocs/amazon-rekognition-developer-guide/blob/master/LICENSE-SAMPLECODE.)

import boto3
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from langchain.llms.bedrock import Bedrock
from langchain.prompts import PromptTemplate
from langchain.output_parsers import XMLOutputParser   


def get_bedrock_client():
    bedrock_client = boto3.client("bedrock-runtime")
    return bedrock_client


def create_bedrock_llm(bedrock_client, model_version_id):
    bedrock_llm = Bedrock(
        model_id=model_version_id, 
        client=bedrock_client,
        model_kwargs={'temperature': 0,'max_tokens_to_sample': 300, 'top_p': 0.9 }
        )
    return bedrock_llm

def detect_text(photo, bucket):

    session = boto3.Session()
    client = session.client('rekognition')

    response = client.detect_text(Image={'S3Object': {'Bucket': bucket, 'Name': photo}})

    textDetections = response['TextDetections']
    fullText = ''
    print('Detected text\n----------')
    for text in textDetections:
        print('Detected text:' + text['DetectedText'])
        print('Confidence: ' + "{:.2f}".format(text['Confidence']) + "%")
        if text['Type'] == 'LINE' and text['Confidence'] > 60:
            fullText += text['DetectedText'] + ' '


    print('Full text: ' + fullText + "\n\n")    
    return fullText


def detect_restaurant_closure(text, current_daytime):

    bedrock = get_bedrock_client();

    bedrock_llm = create_bedrock_llm(bedrock, 'anthropic.claude-v2');

    parser = XMLOutputParser(tags=["response","reason", "outcome"])

    multi_var_prompt  = PromptTemplate(
        template="""

              Human:Current day is MONDAY and time is 8:00 AM. Take into account the current day and time and Based on the following text, tell if the restaurant is Closed or not closed.
              Show your reasoning and respond with Closed or Not Closed. <text>Hours of Operation MON-FRI 10AM - 8PM SAT-SUN 10AM - 1PM</text>

              Assistant:The current day is Monday and the current time is 8:00 AM. Since it is Monday and the restaurant is open 10AM - 8PM on weekdays, the restaurant is closed at the current time of 8:00 AM.

              Human:Current day and time is {current_daytime}. Take into account the current day and time and Based on the following text, tell if the restaurant is Closed or not closed.
              Show your detailed reasoning and respond with Closed or Not Closed. If you are unable to make a decision, say Unable to answer<text>{text}</text>
              {format_instructions}
              Assistant: """,

              input_variables=["current_daytime","text"],
              partial_variables={"format_instructions": parser.get_format_instructions()},

    )

    
    prompt = multi_var_prompt.format(current_daytime=current_daytime, text=text)
    response = bedrock_llm(prompt)

    print("XMLResponse:: " + response + "\n\n")

    response_body = parser.parse(response)

    print("Reason:: " +response_body.get('response')[0]['reason'])
    print("Outcome:: " +response_body.get('response')[1]['outcome'])
    return response_body.get('response')[0]['reason'], response_body.get('response')[1]['outcome']



def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    s3_client = boto3.client('s3')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    # get the object from the event
    print(event)
    print(context)
    # get object from event
    object_key = event['Records'][0]['s3']['object']['key']
    bucket = event['Records'][0]['s3']['bucket']['name']
    fullText = detect_text(object_key, bucket)

    response = s3_client.head_object(Bucket=bucket, Key=object_key)
    print(response)
    # Extract metadata
    metadata = response['ResponseMetadata']
    metadata = json.dumps(metadata)
   
    now = datetime.now()
    current_time = now.strftime("%A %B %d, %Y %H:%M:%S")
    print("Current Time =", current_time + "\n\n")
    reason, outcome = detect_restaurant_closure(fullText, current_time)
    table.put_item(
        Item={
            'id': object_key,
            'creationTime': now.strftime("%Y-%m-%d %H:%M:%S"),
            'reason': reason,
            'outcome': outcome,
            'metadata': metadata
        }
    )

    

