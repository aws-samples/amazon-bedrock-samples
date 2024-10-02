import json
import os
import boto3
import logging
import cfnresponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EXISTING_CLAIMS_TABLE_NAME = os.environ.get('EXISTING_CLAIMS_TABLE_NAME')
REGION = os.environ.get('AWS_REGION')

dynamodb = boto3.client('dynamodb', region_name=REGION)

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))

    request_type = event.get('RequestType')
    if request_type == 'Create' or request_type == 'Update':
        try:
            with open('claims.json', 'r') as file:
                claims_data = json.load(file)
            
            items = []
            for claim in claims_data:
                item = {}
                for key, value in claim.items():
                    if value:
                        if isinstance(value, dict):
                            nested_attributes = {}
                            for nested_key, nested_value in value.items():
                                if isinstance(nested_value, str):
                                    nested_attributes[nested_key] = {'S': nested_value}
                                elif isinstance(nested_value, int):
                                    nested_attributes[nested_key] = {'N': str(nested_value)}
                                elif isinstance(nested_value, dict):
                                    nested_attributes[nested_key] = {'M': {k: str(v) if isinstance(v, int) else v for k, v in nested_value.items()}}
                            item[key] = {'M': nested_attributes}
                        else:
                            item[key] = {'S': str(value)}
                items.append({'PutRequest': {'Item': item}})
            
            response = dynamodb.batch_write_item(
                RequestItems={
                    EXISTING_CLAIMS_TABLE_NAME: items
                }
            )
            logger.info("Batch write response: %s", json.dumps(response))
            cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData={})
        except Exception as e:
            logger.error("Failed to load data into DynamoDB table: %s", str(e))
            cfnresponse.send(event, context, cfnresponse.FAILED, responseData={"Error": str(e)})

    elif request_type == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData={})


    return {
        'statusCode': 200,
        'body': json.dumps('Function execution completed successfully')
    }
