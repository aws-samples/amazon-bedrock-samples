import boto3
import uuid
import json
import boto3
import pandas as pd
from IPython.display import display, HTML

dynamodb = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')

# Define the Lambda function name
function_name = 'PutTicketDynamoDBFunction'

def create_ticket(ticket, employeeId):
    # Define the payload (event data) for the Lambda function
    ticket_id = str(uuid.uuid4())
    payload = {
        'ticket': {
            'ticketId': ticket_id,
            'assignStatus': 'unassigned',
            'ticket_content': ticket,
            'communication': '',
            'employeeId': employeeId
        }
    }

    # Invoke the Lambda function
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',  # 'Event' for asynchronous invocation
        Payload=bytes(json.dumps(payload), encoding='utf-8')
    )

    # Print the response
    return ticket_id

def display_table(table_name):
    # Scan the table and retrieve all items
    response = dynamodb.scan(TableName=table_name)
    items = response['Items']

    # If the response is truncated, continue scanning
    while 'LastEvaluatedKey' in response:
        response = dynamodb.scan(
            TableName=table_name,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])

    data = list()
    if len(items) != 0:
        cols = items[0].keys()
        for item in items:
            temp_list = list()
            for col in cols:
                temp_list.append(item[col]['S'])
            data.append(temp_list)
        # Convert the items to a DataFrame
        df = pd.DataFrame(data=data, columns=cols)
    else:
        df = pd.DataFrame(data=[], columns=["ticketId", "assignStatus", "ticket_content", "communication", "employeeId"])
    # Print the DataFrame
    display(HTML(df.to_html()))
