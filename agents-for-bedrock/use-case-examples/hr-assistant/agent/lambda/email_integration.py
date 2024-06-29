import os

import boto3

sns_client = boto3.client("sns")

email_topic_arn = os.environ["EMAIL_TOPIC_ARN"]


# Sends an email by publishing a message to the SNS topic
def send_email(email_address: str, subject: str, body: str) -> dict:
    message_attributes = {"email": {"DataType": "String", "StringValue": email_address}}

    response = sns_client.publish(
        TopicArn=email_topic_arn,
        Message=body,
        Subject=subject,
        MessageAttributes=message_attributes,
    )

    return {
        "response": "Message published to topic with email: "
        + email_address
        + ". Response: "
        + str(response)
    }
