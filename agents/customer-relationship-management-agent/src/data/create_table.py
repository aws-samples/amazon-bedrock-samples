import boto3
import json
import time
import sys
import os

dynamodb = boto3.client("dynamodb")

EnvironmentName = sys.argv[1]

customer_table_name = f"customer-{EnvironmentName}"
interactions_table_name = f"interactions-{EnvironmentName}"

# Data files
script_dir = os.path.dirname(os.path.abspath(__file__))
CUSTOMER_DATA = os.path.join(script_dir, "customer.json")
INTERACTIONS_DATA = os.path.join(script_dir, "interactions.json")


def getTableStatus(table):
    interactionsTableDescription = dynamodb.describe_table(TableName=table)
    tableStatus = interactionsTableDescription["Table"]["TableStatus"]
    return tableStatus


def create_table():
    print(f"Creating {customer_table_name} table")
    customerTable = dynamodb.create_table(
        TableName=customer_table_name,
        KeySchema=[{"AttributeName": "customer_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "customer_id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    time.sleep(15)

    customerTableStatus = getTableStatus(customer_table_name)
    while customerTableStatus != "ACTIVE":
        print("Waiting for table status change before adding data")
        print("Table status:", customerTableStatus)
        time.sleep(5)
        customerTableStatus = getTableStatus(customer_table_name)
    time.sleep(5)

    print(f"Creating {interactions_table_name} table")

    interactionsTable = dynamodb.create_table(
        TableName=interactions_table_name,
        KeySchema=[
            {"AttributeName": "customer_id", "KeyType": "HASH"},
            {"AttributeName": "date", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "customer_id", "AttributeType": "S"},
            {"AttributeName": "date", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    interactionsTableStatus = getTableStatus(interactions_table_name)
    while interactionsTableStatus != "ACTIVE":
        print("Waiting for table status change before adding data")
        print("Table status:", interactionsTableStatus)
        time.sleep(5)
        interactionsTableStatus = getTableStatus(interactions_table_name)
    time.sleep(5)


def upload_data():
    with open(CUSTOMER_DATA, "r") as file:
        data = json.load(file)

    for item in data:
        dynamodb.put_item(
            TableName=customer_table_name,
            Item={
                "customer_id": {"S": item["customer_id"]},
                "company_name": {"S": item["company_name"]},
                "overview": {"S": item["overview"]},
                "meetingType": {"S": item["meetingType"]},
                "dayOfWeek": {"S": item["dayOfWeek"]},
                "timeofDay": {"S": item["timeofDay"]},
                "email": {"S": item["email"]},
            },
        )

    print(f"Data inserted into {customer_table_name} table successfully.")

    with open(INTERACTIONS_DATA, "r") as file:
        data = json.load(file)
    for item in data:
        dynamodb.put_item(
            TableName=interactions_table_name,
            Item={
                "customer_id": {"S": item["customer_id"]},
                "date": {"S": item["date"]},
                "notes": {"S": item["notes"]},
            },
        )

    print(f"Data inserted into {interactions_table_name} table successfully.")


if __name__ == "__main__":

    # Step 1: Create Table
    create_table()

    # Step 2: Upload Data
    upload_data()
