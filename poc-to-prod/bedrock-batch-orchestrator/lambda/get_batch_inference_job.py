from custom_types import TaskItem
import boto3
import os
import json
import utils


logger = utils.get_logger()

bedrock_client = boto3.client('bedrock')

dynamodb = boto3.resource('dynamodb')
task_table = dynamodb.Table(os.environ['TASK_TABLE'])

sfn_client = boto3.client('stepfunctions')

BATCH_INFERENCE_ERROR_STATES = ['Failed', 'Stopped', 'PartiallyCompleted', 'Expired']


def lambda_handler(event, context) -> TaskItem:
    """
    Triggered by an EventBridge rule that tracks status updates to Bedrock batch invocation jobs.
    Updates are sent back to the step function via the task token associated with each job ARN.

    Status updates fall into 3 categories:
    - In-Progress changes (e.g. Submitted -> Validating -> Running): these send "heartbeats" back to the SFN task
    - Failures (e.g. Failed, Stopped, Expired): these send task errors back to the task
    - Success: sends a success back to the SFN

    Also updates the DDB record with the latest status for visibility/monitoring purposes.
    """
    logger.info(event)
    job_arn = event['detail']['batchJobArn']

    job_details = bedrock_client.get_model_invocation_job(
        jobIdentifier=job_arn,
    )

    # get task token from dynamodb
    task_item_ddb: TaskItem = task_table.get_item(
        Key={
            'job_arn': job_arn,
        }
    )['Item']
    task_token = task_item_ddb['task_token']
    logger.info(f'Retrieved task token for job_arn {job_arn} from DynamoDB')

    job_status = job_details['status']
    logger.info(f'Current job status: {job_status}')

    task_item: TaskItem = {
        'job_arn': job_arn,
        'model_id': job_details['modelId'],
        'input_parquet_path': task_item_ddb['input_parquet_path'],
        's3_uri_output': task_item_ddb['s3_uri_output'],
        'status': job_status,
        'error_message': job_status if job_status in BATCH_INFERENCE_ERROR_STATES else None,
        'task_token': task_token,
    }
    # send task response to async step function state
    if job_status == 'Completed':
        logger.info('Job completed successfully. Sending task success to step function.')
        sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps(task_item),
        )
    elif job_status in BATCH_INFERENCE_ERROR_STATES:
        logger.info(f'Task failed with status {job_status}. Sending task failure to step function.')
        sfn_client.send_task_failure(
            taskToken=task_token,
            error=job_status,
        )
    else:
        logger.info(f'Job in-progress with status {job_status}. Sending task heartbeat to step function.')
        sfn_client.send_task_heartbeat(
            taskToken=task_token,
        )

    # update task table
    logger.info(f'Updating dynamo item with job_arn: {job_arn}')
    task_table.put_item(
        Item=task_item
    )

    return task_item
