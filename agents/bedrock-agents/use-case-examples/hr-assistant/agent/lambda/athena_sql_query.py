import os
from time import sleep

import boto3

athena_client = boto3.client("athena")
output_location = "s3://" + os.environ["S3_BUCKET_NAME"] + "/query_output"


# Execute the given query on Athena database
def get_data_from_database(query: str) -> dict:
    print("Received query:", query)

    # Execute the query and wait for completion
    execution_id = execute_athena_query(query, output_location)
    result = get_query_results(execution_id)

    return {"result": result}


def execute_athena_query(query, s3_output):
    response = athena_client.start_query_execution(
        QueryString=query, ResultConfiguration={"OutputLocation": s3_output}
    )
    return response["QueryExecutionId"]


def check_query_status(execution_id):
    response = athena_client.get_query_execution(QueryExecutionId=execution_id)
    return response["QueryExecution"]["Status"]


def get_query_results(execution_id):
    while True:
        querystatus = check_query_status(execution_id)
        print(querystatus)
        status = querystatus["State"]
        if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        sleep(1)  # Polling interval

    if status == "SUCCEEDED":
        return athena_client.get_query_results(QueryExecutionId=execution_id)
    else:
        raise Exception(f"Query failed with status '{status}'")
