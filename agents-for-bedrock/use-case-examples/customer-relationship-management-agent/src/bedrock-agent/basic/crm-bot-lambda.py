import json
import boto3
from boto3.dynamodb.conditions import Key
import os

env_name = os.environ["EnvironmentName"]

dynamodb = boto3.resource("dynamodb")
customer_table = dynamodb.Table(f"customer-{env_name}")
interactions_table = dynamodb.Table(f"interactions-{env_name}")


def get_customer_interactions(customerId, count):
    response = interactions_table.query(
        ScanIndexForward=False,  # Sort in descending order based on date
        Limit=count,  # Limit the result to the latest 5 items
        KeyConditionExpression=Key("customer_id").eq(
            customerId
        ),  # Ensure the 'date' attribute exists
        ProjectionExpression="#interaction_date,notes",
        ExpressionAttributeNames={"#interaction_date": "date"},
    )
    return response["Items"]


def get_customer(customerId, *args):

    response = customer_table.get_item(
        Key={"customer_id": customerId}, ProjectionExpression=",".join(map(str, args))
    )
    return response.get("Item", None)


def get_named_parameter(event, name):
    return next(item for item in event["parameters"] if item["name"] == name)["value"]


def get_named_property(event, name):
    return next(
        item
        for item in event["requestBody"]["content"]["application/json"]["properties"]
        if item["name"] == name
    )["value"]


def listRecentInteractions(event):
    customerId = get_named_parameter(event, "customerId")
    count = int(get_named_parameter(event, "count"))

    return get_customer_interactions(customerId, count)


def companyOverview(event):
    customerId = get_named_parameter(event, "customerId")

    response_obj = get_customer(customerId, "overview")
    if response_obj:
        return get_customer(customerId, "overview")["overview"]
    else:
        return {}


def getPreferences(event):
    customerId = get_named_parameter(event, "customerId")

    return get_customer(customerId, "meetingType", "timeofDay", "dayOfWeek")


def lambda_handler(event, context):

    response_code = 200
    action_group = event["actionGroup"]
    api_path = event["apiPath"]

    if api_path == "/listRecentInteractions":
        result = listRecentInteractions(event)
    elif api_path == "/getPreferences":
        result = getPreferences(event)
    elif api_path == "/companyOverview":
        result = companyOverview(event)
    else:
        response_code = 404
        result = f"Unrecognized api path: {action_group}::{api_path}"

    response_body = {"application/json": {"body": result}}

    action_response = {
        "actionGroup": event["actionGroup"],
        "apiPath": event["apiPath"],
        "httpMethod": event["httpMethod"],
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    api_response = {"messageVersion": "1.0", "response": action_response}
    print(api_response)
    return api_response
