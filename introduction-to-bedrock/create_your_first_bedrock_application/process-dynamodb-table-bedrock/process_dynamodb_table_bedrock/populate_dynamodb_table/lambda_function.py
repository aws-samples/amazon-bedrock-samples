import boto3
import os

# getting the dynamoDB tables, partition keys and AWS region from OS environment
emails_data_table = os.environ['emails_data_table']
region = os.environ['region']
emails_data_table_partition_key = os.environ['emails_data_table_partition_key']


def save_data_to_dynamodb():
    """
    Function that reads sample email data from the emails.csv file and stores it into a DynamoDB table
    """
    dynamodb = boto3.client('dynamodb')
    i = 0
    with open('emails.csv') as file:
        while line := file.readline():
            if i != 0:
                data = line.rstrip().split('","')
                print(data)
                item = {
                    emails_data_table_partition_key: {
                        "N": str(data[0].replace('"', ''))
                    },
                    "date": {
                        "S": str(data[1].replace('"', ''))
                    },
                    "message": {
                        "S": str(data[2].replace('"', ''))
                    },
                    "subject": {
                        "S": str(data[3].replace('"', ''))
                    },
                    "thread_email_id": {
                        "N": str(data[4].replace('"', ''))
                    },
                    "thread_id": {
                        "N": str(data[5].replace('"', ''))
                    },
                    "time": {
                        "S": str(data[6].replace('"', ''))
                    }
                }
                response = dynamodb.put_item(
                    TableName=emails_data_table,
                    Item=item
                )
                print(response)
            i += 1


def lambda_handler(event, context):
    save_data_to_dynamodb()
    return {
        'statusCode': 200,
        'body': ""
    }
