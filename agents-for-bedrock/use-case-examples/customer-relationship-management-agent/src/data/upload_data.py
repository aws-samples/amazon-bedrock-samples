"""
Loads customer and interaction data from JSON files and inserts it into DynamoDB tables.

This script does the following:

1. Configures a boto3 session and DynamoDB client to access DynamoDB.

2. Opens the customer.json and interactions.json files and loads the data.

3. Loops through the customer data and inserts each item into the 'customer' table.

4. Loops through the interactions data and inserts each item into the 'interactions' table.

The customer DynamoDB table has the following attributes:
  - customer_id
  - company_name 
  - overview
  - meetingType
  - dayOfWeek
  - timeofDay
  - email

The interactions DynamoDB table has the following attributes: 
  - customer_id
  - date 
  - notes

This allows customer and interactions data to be loaded from JSON into DynamoDB.
"""

import json
from botocore.config import Config
from boto3.session import Session

SESSION = Session(profile_name="CRM-Agent")

DYNAMODB_CLIENT = SESSION.resource(
    "dynamodb", "us-east-1", config=Config(read_timeout=600)
)

CUSTOMER_TABLE = DYNAMODB_CLIENT.Table("customer")
INTERACTIONS_TABLE = DYNAMODB_CLIENT.Table("interactions")

with open("data/customer.json", "r") as myfile:
    customer_data = myfile.read()

with open("data/interactions.json", "r") as myfile:
    interactions_data = myfile.read()

for obj in json.loads(customer_data):
    response = CUSTOMER_TABLE.put_item(
        Item={
            "customer_id": obj["customer_id"],
            "company_name": obj["company_name"],
            "overview": obj["overview"],
            "meetingType": obj["meetingType"],
            "dayOfWeek": obj["dayOfWeek"],
            "timeofDay": obj["timeofDay"],
            "email": obj["email"],
        }
    )

for obj in json.loads(interactions_data):
    response = INTERACTIONS_TABLE.put_item(
        Item={
            "customer_id": obj["customer_id"],
            "date": obj["date"],
            "notes": obj["notes"],
        }
    )
