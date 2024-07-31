import boto3
from boto3.dynamodb.conditions import Attr, Key
from decimal import Decimal
import json
import logging
import os
import traceback

dynamodb = boto3.resource('dynamodb')

logger = logging.getLogger(__name__)
if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)

table_name = os.environ.get("TABLE_NAME", None)

def return_car_info(model_name, year, model_id=None):
    try:
        connections = dynamodb.Table(table_name)

        if model_id is not None:
            response = connections.get_item(Key={"composite_pk": f"{model_name}_{model_id}_{year}"})

            if "Item" in response:
                response = [response.get("Item")]
            else:
                response = []

            logger.info(f"Items: {response}")

            for el in response:
                el['year'] = int(el['year'])
                el['price'] = int(el['price'])
        else:
            response = connections.query(
                IndexName='model_name_index',
                KeyConditionExpression=Key('model_name').eq(model_name),
                FilterExpression=Attr('year').eq(Decimal(year))
            )

            if "Items" in response:
                response = response.get("Items")

                logger.info(f"Items: {response}")

                for el in response:
                    el['year'] = int(el['year'])
                    el['price'] = int(el['price'])
            else:
                response = []

        return response

    except Exception as e:
        stacktrace = traceback.format_exc()

        logger.error(stacktrace)

        raise e

def lambda_handler(event, context):
    responses = []

    api_path = event['apiPath']
    logger.info(f'API Path: {api_path}')

    if api_path == '/get_car_info':
        parameters = event['parameters']

        logger.info(f"Parameters: {parameters}")

        model_name = None
        year = None
        model_id = None

        for parameter in parameters:
            if parameter["name"] == "model_name":
                model_name = parameter["value"]
            elif parameter["name"] == "year":
                year = int(parameter["value"])
            elif parameter["name"] == "model_id":
                model_id = parameter["value"]

        if model_name is not None and year is not None:
            body = return_car_info(model_name, year, model_id)
        else:
            body = {"Please provide at least the model name and the year of the car you are looking for"}
    else:
        body = {"{} is not a valid api, try another one.".format(api_path)}

    response_body = {
        'application/json': {
            'body': json.dumps(body)
        }
    }

    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': 200,
        'responseBody': response_body
    }

    responses.append(action_response)

    api_response = {
        'messageVersion': '1.0',
        'response': action_response}

    return api_response
