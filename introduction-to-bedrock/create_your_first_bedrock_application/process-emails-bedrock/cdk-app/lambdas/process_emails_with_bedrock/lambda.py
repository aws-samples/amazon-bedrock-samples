# import required packages
import base64
import email
import json
import os
import quopri
from decimal import Decimal
import boto3

# get bedrock boto3 client
bedrock_client = boto3.client("bedrock-runtime")

# getting the dynamoDB table name from OS environment
TABLE_NAME = os.getenv("TABLE_NAME")
# get dynamodb table resource
table = boto3.resource("dynamodb").Table(TABLE_NAME)


def get_decoded_content_text(message_content):
    """
    Decode email text from message context
    Args:
        message_content (): the email to process
    Returns:
        (str): the decoded email
    """
    content = base64.b64decode(message_content)
    content_msg = email.message_from_string(content.decode("utf-8"))
    content_msg_text = None

    # see https://docs.aws.amazon.com/ses/latest/dg/send-email-raw.html
    # for info on content types and parts
    if content_msg.get_content_type() == "multipart/mixed":
        # multipart/mixed has two parts: multipart/alternative and the attachment
        for payload in content_msg.get_payload():
            if payload.get_content_type() == "multipart/alternative":
                for sub_payload in payload.get_payload():
                    if sub_payload.get_content_type() == "text/plain":
                        content_msg_text = sub_payload.get_payload()
                        break
    elif content_msg.get_content_type() == "multipart/alternative":
        # multipart/alternative has two parts: text/plain and text/html
        for payload in content_msg.get_payload():
            if payload.get_content_type() == "text/plain":
                content_msg_text = payload.get_payload()
                break

    if content_msg_text:
        # may need to base64 decode again
        try:
            content_msg_text = base64.b64decode(content_msg_text).decode("utf-8")
        except Exception:
            pass
        content_msg_text = content_msg_text.replace("\r\n", "\\r\\n").replace(
            "\xa0", "\\xa0"
        )
        return quopri.decodestring(content_msg_text).decode("utf-8")
    else:
        # raise Exception("No text/plain part found in email:\n" + content_msg.as_string())
        raise Exception("No text/plain part found in email")


def parse_float(value):
    """
    Support function used to parse floats from the bedrock response
    Args:
        value (str): string to parse
    Returns:
        (Decimal or str): parse float or original string
    """
    try:
        return Decimal(str(value))
    except ValueError:
        return value


def process_emails_with_bedrock(emails):
    """
    Function that uses the prompt in prompt.txt to extract the information from the emails
    Args:
        emails (str): string with emails
    Returns:
        (dict): bedrock response in JSON format loaded to dictionary
    """
    # read the prompt template
    prompt = open("prompt.txt", "r").read()

    # set the parameters to invoke bedrock
    body = {
        "prompt": f"Human: \n\nHuman: {prompt} <emails>{emails}</emails> \n\nAssistant:",
        "max_tokens_to_sample": 500,
        "temperature": 1,
        "top_k": 250,
        "top_p": 0.999,
        "stop_sequences": ["\n\nHuman:"],
        "anthropic_version": "bedrock-2023-05-31",
    }
    # invoke Bedrock model with claude V2
    response = bedrock_client.invoke_model(
        accept="application/json",
        contentType="application/json",
        body=json.dumps(body),
        modelId="anthropic.claude-v2",
    )
    return json.loads(response.get("body").read()).get("completion")


def lambda_handler(event, context):
    print("OUTPUT #1: event:", event)
    # read messages from SNS
    messages = [
        json.loads(record["Sns"]["Message"])
        for record in event["Records"]
        if record["EventSource"] == "aws:sns"
    ]

    # get list of decoded emails
    emails = []
    for message in messages:
        print("message context type:", type(message["content"]))
        decoded_message = get_decoded_content_text(message["content"])
        mail = message["mail"]
        mail.update({"decoded_message": decoded_message})
        emails.append(mail)
    print("OUTPUT #2: emails:", emails)

    # extra information from emails with bedrock using prompt engineering
    bedrock_response = process_emails_with_bedrock(emails)
    print("OUTPUT #3: Bedrock response", bedrock_response)

    # parse the extracted information and store it in DynamoDB
    parsed_email = json.loads(bedrock_response, parse_float=parse_float)
    print("OUTPUT #4: Parsed email", parsed_email)
    table.put_item(Item=parsed_email)
    return {"body": parsed_email}
