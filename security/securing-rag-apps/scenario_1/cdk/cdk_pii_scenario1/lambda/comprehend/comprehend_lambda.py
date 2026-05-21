import json
import logging
import os
import time
from decimal import Decimal
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
comprehend = boto3.client("comprehend")
dynamodb = boto3.resource("dynamodb")
SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
SAFE_BUCKET = os.environ["SAFE_BUCKET"]
COMPREHEND_ROLE_ARN = os.environ["COMPREHEND_ROLE_ARN"]
JOB_TABLE_NAME = os.environ["JOB_TABLE_NAME"]
table = dynamodb.Table(JOB_TABLE_NAME)

# Constants
MAX_RETRIES = 3
WAIT_TIME = 30  # seconds between status checks
MAX_EXECUTION_TIME = 840  # 14 minutes (leaving 1 min buffer for 15 min Lambda)

# get logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def check_comprehend_status(job_id: str) -> str:
    """Check Comprehend job status with error handling"""
    try:
        response = comprehend.describe_pii_entities_detection_job(JobId=job_id)
        return response["PiiEntitiesDetectionJobProperties"]["JobStatus"]
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            return "NOT_FOUND"
        raise e


def get_files_in_folder(bucket, prefix, extension=".txt"):
    """Get all files with .txt extension in a specific S3 folder"""
    txt_files = []
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            txt_files.extend(
                [
                    obj["Key"]
                    for obj in page["Contents"]
                    if obj["Key"].endswith(extension)
                ]
            )
    return txt_files


def start_pii_detection_job(iam_role, s3_input_prefix, s3_output_prefix, job_name):
    """Start a PII detection job with error handling"""
    try:
        redaction_config = {
            "PiiEntityTypes": [
                "EMAIL",
                "ADDRESS",
                "PHONE",
                "SSN",
                "PASSPORT_NUMBER",
                "BANK_ACCOUNT_NUMBER",
                "CREDIT_DEBIT_NUMBER",
                "BANK_ROUTING",
            ],
            "MaskMode": "REPLACE_WITH_PII_ENTITY_TYPE",
        }

        response = comprehend.start_pii_entities_detection_job(
            InputDataConfig={
                "S3Uri": f"{s3_input_prefix}",
                "InputFormat": "ONE_DOC_PER_FILE",
            },
            OutputDataConfig={"S3Uri": f"{s3_output_prefix}"},
            Mode="ONLY_REDACTION",
            RedactionConfig=redaction_config,
            DataAccessRoleArn=iam_role,
            JobName=job_name,
            LanguageCode="en",
        )
        return response["JobId"]
    except ClientError as e:
        raise Exception(f"Failed to start Comprehend job: {str(e)}")


def check_running_jobs():
    """Check if there are any jobs in PROCESSING state"""
    # Scan for jobs in SUBMITTED or IN_PROGRESS status
    response = table.scan(
        FilterExpression="comprehend_job_status IN (:s1, :s2) AND macie_scan_status = :ms",
        ExpressionAttributeValues={
            ":s1": "SUBMITTED",
            ":s2": "IN_PROGRESS",
            ":ms": "NO",
        },
    )
    logger.info(response.get("Items", []))

    if response.get("Items"):
        return response.get("Items")[0]

    return {}


def update_job_status(job_id, status, files=None, error=None):
    """Update job status in DynamoDB"""
    item = {
        "comprehend_job_id": job_id,
        "comprehend_job_status": status,
        "macie_job_id": "NONE",
        "macie_job_status": "NONE",
        "macie_scan_status": "NO",
        "updated_at": Decimal(str(time.time())),
        "ttl": int(time.time()) + (7 * 24 * 60 * 60),  # 7 days TTL
    }

    if files:
        item["files"] = files
    if error:
        item["error"] = error

    table.put_item(Item=item)


def move_redacted_files(job_id):
    """Move redacted files from Comprehend output to for_macie_scan folder"""
    logger.debug("Moving redacted files to for_macie_scan folder")
    try:
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        comprehend_output_prefix = f"processed/{account_id}-PII-{job_id}/output/"
        logger.info(
            f"Comprehend output prefix: s3://{SOURCE_BUCKET}{comprehend_output_prefix}"
        )

        # List all files in the Comprehend output folder
        redacted_files = get_files_in_folder(
            SOURCE_BUCKET, comprehend_output_prefix, ".txt.out"
        )
        logger.info("Redacted files list")
        logger.info(redacted_files)

        moved_files = []
        for file_key in redacted_files:
            if file_key.endswith(".txt.out"):  # Only process text files
                file_name = file_key.split("/")[-1].replace(".txt.out", ".txt")
                new_key = f"for_macie_scan/{account_id}-PII-{job_id}/{file_name}"

                # Copy to new location
                logger.info(f"Copying {file_key} to {new_key}")
                s3.copy_object(
                    Bucket=SOURCE_BUCKET,
                    CopySource={"Bucket": SOURCE_BUCKET, "Key": file_key},
                    Key=new_key,
                )
                # Delete from original location
                # s3.delete_object(Bucket=SOURCE_BUCKET, Key=file_key)
                moved_files.append(file_name)
        return moved_files
    except Exception as e:
        logger.error(f"Error moving redacted files {redacted_files}")
        logger.error(str(e))
        raise ValueError(f"Error moving redacted files: {str(e)}")


def handler(event, context):
    # First check if there are any running jobs
    items = check_running_jobs()
    # Get all files in inputs folder
    input_files = get_files_in_folder(SOURCE_BUCKET, "inputs/")
    processing_files = get_files_in_folder(SOURCE_BUCKET, "processing/")

    if items:
        job_id = str(items.get("comprehend_job_id"))
        job_status = check_comprehend_status(job_id=job_id)

        if not input_files and job_status == "IN_PROGRESS":
            logger.info(f"Comprehend job: {job_id} is currently in {job_status}")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": f"Another comprehend job: {job_id} is currently in {job_status}",
                        "status": "SKIPPED",
                    }
                ),
            }

        if not input_files and not processing_files and job_status == "COMPLETED":
            logger.info(f"Comprehend job: {job_id} is currently in {job_status}")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": f"Comprehend job: {job_id} is currently in {job_status}",
                        "status": "SKIPPED",
                    }
                ),
            }

        if not input_files and job_status == "COMPLETED" and processing_files:
            # Move redacted files to for_macie_scan folder
            moved_files = move_redacted_files(job_id)

            # Process completion tasks
            processing_files = get_files_in_folder(SOURCE_BUCKET, "processing/")
            logger.info("Job completed. Deleting files in processing/ folder")
            for processing_key in processing_files:
                s3.delete_object(Bucket=SOURCE_BUCKET, Key=processing_key)

            # Update job status to completed
            update_job_status(job_id, job_status, files=moved_files)

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Processing completed successfully",
                        "status": "COMPLETED",
                        "jobId": job_id,
                        "processedFiles": processing_files,
                        "redactedFiles": moved_files,
                    }
                ),
            }

        elif job_status in ["FAILED", "STOPPED", "NOT_FOUND"]:
            error_message = f"Error processing comprehend job: Status={job_status}"
            # Update job status with error
            update_job_status(job_id, job_status, error=error_message)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": error_message,
                        "status": job_status,
                        "jobId": job_id,
                    }
                ),
            }

    if input_files and not processing_files:
        logger.info("Found files in inputs/ folder. Starting a new job.")
        # If files are found in inputs/ dir then create additional directories
        # Create a .temp files in inputs, processing, processed, for_macie_scan folders
        s3.put_object(Bucket=SOURCE_BUCKET, Key="inputs/.temp")
        s3.put_object(Bucket=SOURCE_BUCKET, Key="processing/.temp")
        s3.put_object(Bucket=SOURCE_BUCKET, Key="processed/.temp")
        s3.put_object(Bucket=SOURCE_BUCKET, Key="for_macie_scan/.temp")

        processed_files = []

        # Move all files to processing folder
        for source_key in input_files:
            try:
                file_name = source_key.split("/")[-1]
                processing_key = f"processing/{file_name}"
                logging.info(f"Moving {source_key} to {processing_key}")

                s3.copy_object(
                    Bucket=SOURCE_BUCKET,
                    CopySource={"Bucket": SOURCE_BUCKET, "Key": source_key},
                    Key=processing_key,
                )
                s3.delete_object(Bucket=SOURCE_BUCKET, Key=source_key)
                processed_files.append(file_name)
            except ClientError as e:
                print(f"Error processing file {source_key}: {str(e)}")
                continue

        # Start Comprehend PII detection job
        job_name = f"pii_scenario1_redact_{str(uuid4())[:8]}"
        s3_input_prefix = f"s3://{SOURCE_BUCKET}/processing/"
        s3_output_prefix = f"s3://{SOURCE_BUCKET}/processed/"

        job_id = start_pii_detection_job(
            COMPREHEND_ROLE_ARN, s3_input_prefix, s3_output_prefix, job_name
        )

        logger.info(f"Comprehend job: {job_id} submitted. Sleeping for 15secs..")
        time.sleep(15)
        # Record job start in DynamoDB
        job_status = check_comprehend_status(job_id=job_id)
        logger.info(f"Comprehend job_id: {job_id}, current status: {job_status}")
        update_job_status(job_id, status=job_status, files=processed_files)
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": f"Comprehend job_id: {job_id}, current status: {job_status}",
                    "status": job_status,
                    "jobId": job_id,
                }
            ),
        }
    else:
        logger.info("No files in inputs/ folder. Nothing to do")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "No files in inputs/ folder. Nothing to do",
                }
            ),
        }
