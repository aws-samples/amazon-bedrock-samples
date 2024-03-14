import boto3
import os
outputLocation = os.environ['outputLocation']

def get_schema():
    try:
        glue_client = boto3.client('glue') 
    
        database_name = 'thehistoryofbaseball' 
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

def execute_athena_query(query):
    # Initialize Athena client
    athena_client = boto3.client('athena')

    # Start query execution
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': 'thehistoryofbaseball'
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

def lambda_handler(event, context):
    result = None
    
    if event['apiPath'] == "/getschema":
        result = get_schema()
        
    
    if event['apiPath'] == "/querydatabase":
      
        print(event['requestBody']['content']['application/json']['properties'])
        query = event['requestBody']['content']['application/json']['properties'][0]['value']
        result = execute_athena_query(query)

    if result:
        print("Query Result:", result)
       
    else:
        result="Query Failed."

    
    response_body = {
    'application/json': {
        'body':str(result)
    }
}
    
    action_response = {
    'actionGroup': event['actionGroup'],
    'apiPath': event['apiPath'],
    'httpMethod': event['httpMethod'],
    'httpStatusCode': 200,
    'responseBody': response_body
    }

    session_attributes = event['sessionAttributes']
    prompt_session_attributes = event['promptSessionAttributes']
    
    api_response = {
        'messageVersion': '1.0', 
        'response': action_response,
        'sessionAttributes': session_attributes,
        'promptSessionAttributes': prompt_session_attributes
    }
        
    return api_response
    
    
    