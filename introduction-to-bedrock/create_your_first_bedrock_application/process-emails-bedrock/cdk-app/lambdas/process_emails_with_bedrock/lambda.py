import base64
import email
import json
import os
import quopri
from decimal import Decimal
import boto3

# get the bedrock client to invoke the foundation models
bedrock_client = boto3.client("bedrock-runtime")
# read the environment variable containing the dynamoDB table name
TABLE_NAME = os.getenv("TABLE_NAME")
# get the dynamoDB table name resource to populate with extracted information
table = boto3.resource("dynamodb").Table(TABLE_NAME)


def get_decoded_content_text(message_content):
    """
    Decode the email message
    Args:
        message_content: encoded message
    Returns:
        decoded message
    """
    content = base64.b64decode(message_content)
    content_msg = email.message_from_string(content.decode("utf-8"))
    content_msg_text = None

    print("OUTPUT #2.1: content_msg:", content_msg)
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
    Support function to parse decimal numbers
    """
    try:
        return Decimal(str(value))
    except ValueError:
        return value


def process_emails_with_bedrock(emails):
    """
    Process the emails with a Bedrock foundation model
    Args:
        emails (list): list of emails to process
    Returns:
        Bedrock message
    """
    # read the prompt template
    prompt = open("prompt.txt", "r").read()

    # Prompt engineering: extract the necessary information from the emails to create the optimal prompt
    emails_str = "<emails>"
    for e in emails:
        thread_index = None
        for header in e["headers"]:
            if header["name"] == "Thread-Index":
                thread_index = header["value"]
        emails_str += "<email>"
        emails_str += "<messageId>" + str(e["messageId"]) + "</messageId>"
        emails_str += "<Timestamp>" + str(e["timestamp"]) + "</Timestamp>"
        emails_str += "<ThreadIndex>" + str(thread_index) + "</ThreadIndex>"
        emails_str += "<subject>" + str(e["commonHeaders"]["subject"]) + "</subject>"
        emails_str += "<message>" + str(e["decoded_message"]) + "</message>"
        emails_str += "</email>"
    emails_str += "</emails>"
    prompt = prompt.replace("<emails></emails>", emails_str)
    print("OUTPUT #4: prompt:", prompt)

    # prepare the parameter to invoke the Antropic Claude on Bedrock
    body = {
        "prompt": prompt,
        "max_tokens_to_sample": 500,
        "temperature": 0,
        "top_k": 250,
        "top_p": 0.999,
        "stop_sequences": ["\n\nHuman:"],
        "anthropic_version": "bedrock-2023-05-31",
    }
    # invoke the bedrock model
    response = bedrock_client.invoke_model(
        accept="application/json",
        contentType="application/json",
        body=json.dumps(body),
        modelId="anthropic.claude-v2",
    )
    return json.loads(response.get("body").read()).get("completion")


def lambda_handler(event, context):
    print("OUTPUT #1: event:", event)
    messages = [
        json.loads(record["Sns"]["Message"])
        for record in event["Records"]
        if record["EventSource"] == "aws:sns"
    ]
    emails = []
    # process the emails from SNS
    for message in messages:
        print("OUTPUT #2: message:", message)
        decoded_message = get_decoded_content_text(message["content"])
        mail = message["mail"]
        mail.update({"decoded_message": decoded_message})
        emails.append(mail)

    print("OUTPUT #3: emails:", emails)

    bedrock_response = process_emails_with_bedrock(emails)
    print("OUTPUT #5: Bedrock response", bedrock_response)

    # Save the email information to dynamoDB
    parsed_email = json.loads(bedrock_response, parse_float=parse_float)
    print("OUTPUT #6: Parsed email", parsed_email)
    table.put_item(Item=parsed_email)

    return {"body": parsed_email}
