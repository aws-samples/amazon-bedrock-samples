import boto3
import os
import re
import json
import gzip
from io import BytesIO

outputLocation = os.environ['outputLocation']
database_name =  os.environ['glue_database_name']
region = os.environ['region']
bucket_name= os.environ['bucket_name']
def get_schema():
    try:
        glue_client = boto3.client('glue') 
    
        #database_name = 'thehistoryofbaseball' 
        
        table_schema_list=[]
        response = glue_client.get_tables(DatabaseName=database_name)
        print(response)
        table_names = [table['Name'] for table in response['TableList']]
        for table_name in table_names:
            response = glue_client.get_table(DatabaseName=database_name, Name=table_name)
            columns = response['Table']['StorageDescriptor']['Columns']
            schema = {column['Name']: column['Type'] for column in columns}
            table_schema_list.append({"Table: {}".format(table_name): 'Schema: {}'.format(schema)})
    except Exception as e:
        print(f"Error: {str(e)}")
    return table_schema_list




def correct_query(query):
    import re

   

    return query


def execute_athena_query(query):
    # Initialize Athena client
    athena_client = boto3.client('athena', region_name=region)

    # Start query execution
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': database_name
        },
        ResultConfiguration={
            'OutputLocation': outputLocation
        }
    )

    # Get query execution ID
    query_execution_id = response['QueryExecutionId']
    print(f"Query Execution ID: {query_execution_id}")

    # Wait for the query to complete
    response_wait = athena_client.get_query_execution(QueryExecutionId=query_execution_id)

    while response_wait['QueryExecution']['Status']['State'] in ['QUEUED', 'RUNNING']:
        print("Query is still running...")
        response_wait = athena_client.get_query_execution(QueryExecutionId=query_execution_id)

    # Check if the query completed successfully
    if response_wait['QueryExecution']['Status']['State'] == 'SUCCEEDED':
        print("Query succeeded!")

        # Get query results
        query_results = athena_client.get_query_results(QueryExecutionId=query_execution_id)

        # Extract and return the result data
        return extract_result_data(query_results)

    else:
        print("Query failed!")
        return None

def extract_result_data(query_results):
    #Return a cleaned response to the agent
    result_data = []

    # Extract column names
    column_info = query_results['ResultSet']['ResultSetMetadata']['ColumnInfo']
    column_names = [column['Name'] for column in column_info]

    # Extract data rows
    for row in query_results['ResultSet']['Rows']:
        data = [item['VarCharValue'] for item in row['Data']]
        result_data.append(dict(zip(column_names, data)))

    return result_data

def compress_data(data):
    json_data = json.dumps(data)
    if len(json_data.encode('utf-8')) > 25000:
        out = BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb') as gz:
            gz.write(json_data.encode('utf-8'))
        compressed_data = out.getvalue()
        return compressed_data, True
    return json_data.encode('utf-8'), False

def save_to_s3(data, key):
    s3_client = boto3.client('s3', region_name=region)
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=json.dumps(data))


def lambda_handler(event, context):
    result = None
    headers = {}
    is_compressed= False
    if event['apiPath'] == "/getschema":
        result = get_schema()
        
    
    if event['apiPath'] == "/querydatabase":
      
        print(event['requestBody']['content']['application/json']['properties'])
        query = event['requestBody']['content']['application/json']['properties'][0]['value']
        
        # Correct the query to handle special characters and spaces
        original_query=query
        corrected_query = correct_query(original_query)
        print(f"Original Query: {original_query}")
        print(f"Corrected Query: {corrected_query}")
        
        
        result = execute_athena_query(corrected_query)
        #result, is_compressed = compress_data(result)
        
    

    if result:
        print("Query Result:", result)
       
    else:
        result="Query Failed."
        
        
    if result and len(json.dumps(result)) > 25000:
        key = f"Large_results/{database_name}/{context.aws_request_id}.json"
        save_to_s3(result, key)
        result = f"Data is large, saved to s3://{bucket_name}/{key}"
       
    response_body = {
    'application/json': {
        'body': json.dumps(result)
    }
    }  

   
    
    action_response = {
    'actionGroup': event['actionGroup'],
    'apiPath': event['apiPath'],
    'httpMethod': event['httpMethod'],
    'httpStatusCode': 200 if result else 400,
    'responseBody': response_body,
    'headers': headers
    }

    
    api_response = {
        'messageVersion': '1.0', 
        'response': action_response,
        'sessionAttributes': event.get('sessionAttributes', {}),
        'promptSessionAttributes': event.get('promptSessionAttributes', {})
    }
        
    return api_response
    
    
    