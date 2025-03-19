import os

from custom_types import JobConfig, TaskItem
import boto3
from botocore.config import Config

import utils


logger = utils.get_logger()

# increase the retries - can experience throttling when starting too many batch inference jobs at the same time
config = Config(
    retries = {
        'max_attempts': 100,
        'mode': 'standard'
    }
)

bedrock_client = boto3.client('bedrock', config=config)
dynamodb = boto3.resource('dynamodb')
task_table = dynamodb.Table(os.environ['TASK_TABLE'])


def lambda_handler(event, context) -> TaskItem:
    """
    Kicks off async bedrock batch inference jobs based on provided configs and stores key metadata
    (including the task token from the step function) in a DynamoDB table.

    As jobs are updated, they will use the task token to send their status back to the step function.
    """
    task_token = event['taskToken']
    logger.info(f'Got task token {task_token}')
    payload: JobConfig = event['taskInput']

    # additional job kwargs, if provided
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock/client/create_model_invocation_job.html
    additional_kwargs = {}
    job_timeout_hours = int(os.environ.get('JOB_TIMEOUT_HOURS', -1))
    if job_timeout_hours > 0:
        additional_kwargs['timeoutDurationInHours'] = job_timeout_hours

    # kick off the async job
    job_arn = bedrock_client.create_model_invocation_job(
        jobName=payload['job_name'],
        roleArn=os.environ['BEDROCK_ROLE_ARN'],
        modelId=payload['model_id'],
        inputDataConfig={
            's3InputDataConfig': {
                's3InputFormat': 'JSONL',
                's3Uri': payload['s3_uri_input'],
            }
        },
        outputDataConfig={
            's3OutputDataConfig': {
                's3Uri': payload['s3_uri_output'],
            }
        },
        **additional_kwargs,
    )['jobArn']
    logger.info(f'Started job: {job_arn}')

    # make sure it was submitted successfully
    job_details = bedrock_client.get_model_invocation_job(
        jobIdentifier=job_arn,
    )
    logger.info(f'Job status: {job_details["status"]}')

    # put the item in the task table
    task_item: TaskItem = {
        'job_arn': job_arn,
        'model_id': payload['model_id'],
        'input_parquet_path': payload['input_parquet_path'],
        's3_uri_output': payload['s3_uri_output'],
        'status': job_details['status'],
        'error_message': None,
        'task_token': task_token,
    }

    logger.info('Updating task table')
    task_table.put_item(
        Item=task_item
    )

    return task_item
