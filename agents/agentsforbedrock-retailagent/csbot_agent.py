
import json
import boto3
import sqlite3
from datetime import datetime
import random
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
bucket = os.environ.get('BUCKET_NAME')  #Name of bucket with data file and OpenAPI file
db_name = 'demo_csbot_db' #Location of data file in S3
local_db = '/tmp/csbot.db' #Location in Lambda /tmp folder where data file will be copied

#Download data file from S3
s3.download_file(bucket, db_name, local_db)

cursor = None
conn = None

#Initial data load and SQLite3 cursor creation 
def load_data():
    #load SQL Lite database from S3
    # create the db
    global conn
    conn = sqlite3.connect(local_db)
    cursor = conn.cursor()
    logger.info('Completed initial data load ')

    return cursor
    
#Function returns all customer info for a particular customerId
def return_customer_info(custName):
    query = 'SELECT customerId, customerName, Addr1, Addr2, City, State, Zipcode, PreferredActivity, ShoeSize, OtherInfo from CustomerInfo where customerName like "%' +  custName +'%"'
    cursor.execute(query)
    resp = cursor.fetchall()
    #adding column names to response values
    names = [description[0] for description in cursor.description]
    valDict = {}
    index = 0
    for name in names:
        valDict[name]=resp[0][index]
        index = index + 1
    logger.info('Customer Info retrieved')
    return valDict
   
    
#Function returns shoe inventory for a particular shoeid 
def return_shoe_inventory():
    query = 'SELECT ShoeID, BestFitActivity, StyleDesc, ShoeColors, Price, InvCount from ShoeInventory' 
    cursor.execute(query)
    resp = cursor.fetchall()
    
    #adding column names to response values
    names = [description[0] for description in cursor.description]
    valDict = []
    interimDict = {}
    index = 0
    for item in resp:
        for name in names:
            interimDict[name]=item[index]
            index = index + 1
        index = 0
        valDict.append(interimDict)
        interimDict={}
    logger.info('Shoe info retrieved')
    return valDict

    
#function places order -- reduces shoe inventory, updates order_details table --> all actions resulting from a shoe purchase  
def place_shoe_order(ssId, custId):
    global cursor
    global conn
    query = 'Update ShoeInventory set InvCount = InvCount - 1 where ShoeID = ' + str(ssId)
    ret = cursor.execute(query)
    
    today = datetime.today().strftime('%Y-%m-%d')
    query = 'INSERT INTO OrderDetails (orderdate, shoeId, CustomerId) VALUES ("'+today+'",'+str(ssId)+','+ str(custId)+')'
    ret = cursor.execute(query)
    conn.commit()

    #Writing updated db file to S3 and setting cursor to None to force reload of data
    s3.upload_file(local_db, bucket, db_name)
    cursor = None
    logger.info('Shoe order placed')
    return 1;
     

def lambda_handler(event, context):
    responses = []
    global cursor
    if cursor == None:
        cursor = load_data()
    id = ''
    api_path = event['apiPath']
    logger.info('API Path')
    logger.info(api_path)
    
    if api_path == '/customer/{CustomerName}':
        parameters = event['parameters']
        for parameter in parameters:
            if parameter["name"] == "CustomerName":
                cName = parameter["value"]
        body = return_customer_info(cName)
    elif api_path == '/place_order':
        parameters = event['parameters']
        for parameter in parameters:
            if parameter["name"] == "ShoeID":
                id = parameter["value"]
            if parameter["name"] == "CustomerID":
                cid = parameter["value"]
        body = place_shoe_order(id, cid)
    elif api_path == '/check_inventory':
        body = return_shoe_inventory()
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
    
    