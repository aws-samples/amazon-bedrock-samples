import base64
import email
import json
import os
import quopri
from decimal import Decimal

import boto3

bedrock_client = boto3.client("bedrock-runtime")

TABLE_NAME = os.getenv("TABLE_NAME")
table = boto3.resource("dynamodb").Table(TABLE_NAME)

PROMPT = """
Extract the following details from the emails below and provide the information as a structured JSON and ONLY output the JSON. 
Do not add any introduction to the reply and start directly with the JSON indicated by "{".
1. Sender Name as "SenderName"
2. Sender Address as "SenderAddress"
3. Receiver Name as "ReceiverName"
4. Receiver Address as "ReceiverAddress"
5. messageId as "MessageId"
6. timestamp as "Timestamp"
7. subject as "Subject"
8. Thread-Index as "ThreadIndex"
9. decoded_message as "Message"
10. Number of parcels as "NumberOfParcels"
11. Weight of each parcel in a list in Grams as "WeightPerParcels"
12. Total weight of parcels in Grams as "TotalWeightOfParcels"
13. Price as "Price"
14. Price currency as "PriceCurrency"
15. Delivery Timeframe as "DeliveryTimeframe"
"""


def get_decoded_content_text(message_content):
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
    try:
        return Decimal(str(value))
    except ValueError:
        return value


def process_emails_with_bedrock(emails):
    body = {
        "prompt": f"Human: \n\nHuman: {PROMPT} <emails>{emails}</emails> \n\nAssistant:",
        "max_tokens_to_sample": 500,
        "temperature": 0,
        "top_k": 250,
        "top_p": 0.999,
        "stop_sequences": ["\n\nHuman:"],
        "anthropic_version": "bedrock-2023-05-31",
    }
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

    for message in messages:
        print("OUTPUT #2: message:", message)
        decoded_message = get_decoded_content_text(message["content"])
        mail = message["mail"]
        mail.update({"decoded_message": decoded_message})
        emails.append(mail)

    print("OUTPUT #3: emails:", emails)

    bedrock_response = process_emails_with_bedrock(emails)
    print("OUTPUT #4: Bedrock response", bedrock_response)

    parsed_email = json.loads(bedrock_response, parse_float=parse_float)
    print("OUTPUT #4: Parsed email", parsed_email)
    table.put_item(Item=parsed_email)

    return {"body": parsed_email}
