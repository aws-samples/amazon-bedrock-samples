# installing the latest version of pip for bedrock support. The next 4 lines can be removed once the Lambda version of boto3 is updated
import sys
from pip._internal import main
main(['install', '-I', '-q', 'boto3', '--target', '/tmp/', '--no-cache-dir', '--disable-pip-version-check'])
sys.path.insert(0, '/tmp/')

import json
import boto3
from botocore.config import Config
from boto3.dynamodb.conditions import Key, Attr
import os

# getting the dynamoDB tables, partition keys and AWS region from OS environment
emails_data_table = os.environ['emails_data_table']
region = os.environ['region']
information_extracted_table = os.environ['information_extracted_table']
information_extracted_table_partition_key = os.environ['information_extracted_table_partition_key']


def create_emails_tags(thread_id):
    """
    Create the email's context information to be used in the Bedrock prompt.
    This function:
    1. Queries the DynamoDB table containing the emails data by the ThreadID
    2. For each email in the Tread, create an email tag for the Bedrock Prompt
    Args:
        thread_id (int): the id of the thread to process
    Returns:
        emails_tag (str): the xml tags for the emails data to be used in the prompt
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(emails_data_table)

    response = table.scan(
        FilterExpression=Attr(information_extracted_table_partition_key).eq(int(thread_id))
    )
    items = sorted(response['Items'], key=lambda x: int(x[information_extracted_table_partition_key]))
    emails_tag = "<emails>\n"
    for item in items:
        emails_tag += "\t<email>\n"
        emails_tag += "\t\t<date>" + item["date"] + " " + item["time"] + "</date>\n"
        emails_tag += "\t\t<subject>" + item["subject"] + "</subject>\n"
        emails_tag += "\t\t<message>\n" + item["message"] + "\n</message>\n"
        emails_tag += "\t</email>\n"
    emails_tag += "</emails>"
    return emails_tag


def save_extracted_info(extracted_info, thread_id):
    """
    This function save the extracted information to the dynamoDB table containing the processed email's data
    Args:
        extracted_info (dict): dictionary containing the extracted email information from the returned bedrock query
        thread_id (int): the thread id to connect the extratect information with the email's thread
    Returns:
        response (dict): the boto3 response from the put_item functionality
    """
    dynamodb = boto3.client('dynamodb')
    item = {
        information_extracted_table_partition_key: {
            "N": thread_id
        }
    }
    for info in extracted_info:
        item[info] = {
            "S": str(extracted_info[info])
        }

    response = dynamodb.put_item(
        TableName=information_extracted_table,
        Item=item
    )
    print(response)


def lambda_handler(event, context):
    # extract the thread id from the event
    thread_id = event[information_extracted_table_partition_key]

    # read the prompt template
    prompt = open("prompt.txt", "r").read()

    # create the model prompt based on the email's data
    emails_list = create_emails_tags(thread_id)
    prompt = prompt.replace("<emails></emails>", emails_list)
    # print(prompt)

    # invoke Bedrock Claude V2 with the prompt
    bedrock_config = Config(
        connect_timeout=60,
        retries={"max_attempts": 3},
    )
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
        config=bedrock_config
    )
    payload = {
        "prompt": prompt,
        "temperature": 1,
        "top_k": 250,
        "max_tokens_to_sample": 1024,
        "stop_sequences": ["\n\nHuman:"],

    }
    bedrock_response = client.invoke_model(
        body=json.dumps(payload),
        modelId="anthropic.claude-v2",
        accept="*/*",
        contentType="application/json"
    )

    # read bedrock response and save it to dynamoDB
    bedrock_response_body = json.loads(bedrock_response.get("body").read())
    save_extracted_info(json.loads(bedrock_response_body["completion"]), thread_id)

    # returns the response to the user
    return {
        'statusCode': 200,
        'body': bedrock_response_body["completion"]
    }
