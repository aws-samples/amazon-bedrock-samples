import boto3
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
        else:
            response = connections.get_item(Key={"model_name": model_name, "year": year})

        logger.info(f"Response: {response}")

        if "Item" in response:
            response = response.get("Item")

            logger.info(f"Item: {response}")

    except Exception as e:
        stacktrace = traceback.format_exc()

        logger.error(stacktrace)

        raise e

def lambda_handler(event, context):
    responses = []
    global cursor
    if cursor == None:
        cursor = load_data()
    id = ''
    api_path = event['apiPath']
    logger.info('API Path')
    logger.info(api_path)

    if api_path == '/get_car_info':
        parameters = event['parameters']
        model_name = None
        year = None
        model_id = None
        for parameter in parameters:
            if parameter["name"] == "model_name":
                model_name = parameter["value"]
            elif parameter["name"] == "year":
                year = parameter["value"]
            elif parameter["name"] == "model_id":
                model_id = parameter["value"]

        if model_name is not None and year is not None:
            return_car_info(model_name, year, model_id)
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

