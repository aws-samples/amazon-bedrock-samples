import boto3
import cfnresponse
import json
import os
import traceback

data_path = os.environ['DATA_PATH']
s3_bucket = os.environ['S3_BUCKET']
table_name = os.environ.get("TABLE_NAME", None)

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

def populate_dynamodb(data):
    try:
        added = 0
        connections = dynamodb.Table(table_name)

        for item in data:
            tmp_item = item

            tmp_item["composite_pk"] = f'{tmp_item["model_name"]}_{tmp_item["model_id"]}_{tmp_item["year"]}'

            print(f"Item: {tmp_item}")

            response = connections.put_item(Item=tmp_item)

            if "ResponseMetadata" in response and "HTTPStatusCode" in response["ResponseMetadata"]:
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    added += 1


        print(f"Added {added} items")

        return added
    except Exception as e:
        stacktrace = traceback.format_exc()
        print(stacktrace)

        raise e
def read_data():
    try:
        obj = s3.get_object(Bucket=s3_bucket, Key=data_path)

        content = obj['Body'].read()

        data = json.loads(content)

        return data
    except Exception as e:
        stacktrace = traceback.format_exc()
        print(stacktrace)

        raise e

def lambda_handler(event, context):
    print("Event: ", event)
    responseData = {}
    reason = ""
    status = cfnresponse.SUCCESS
    try:
        if event['RequestType'] != 'Delete':
            data = read_data()
            added = populate_dynamodb(data)

            responseData = {"DynamoDB": table_name, "Elements": added}
    except Exception as e:
        print(e)
        status = cfnresponse.FAILED
        reason = f"Exception thrown: {e}"

    cfnresponse.send(event, context, status, responseData, reason=reason)