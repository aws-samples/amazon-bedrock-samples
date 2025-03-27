import json
import logging
import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
s3 = boto3.client("s3")
paginator = s3.get_paginator("list_objects_v2")
macie = boto3.client("macie2")
dynamodb = boto3.resource("dynamodb")
comprehend = boto3.client("comprehend")
account_id = boto3.client("sts").get_caller_identity()["Account"]

# Environment variables
SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
SAFE_BUCKET = os.environ["SAFE_BUCKET"]
JOB_TABLE_NAME = os.environ["JOB_TABLE_NAME"]
KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATASOURCE_ID = os.environ["DATASOURCE_ID"]
table = dynamodb.Table(JOB_TABLE_NAME)
# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_files_to_scan():
    """Get all .txt files from for_macie_scan folder"""
    files = []
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=SOURCE_BUCKET, Prefix="for_macie_scan/"):
        if "Contents" in page:
            files.extend(
                [obj["Key"] for obj in page["Contents"] if obj["Key"].endswith(".txt")]
            )
    return files


def create_macie_job(job_name, comprehend_job_id):
    """Create a one-time Macie sensitive data discovery job"""
    try:
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        scan_files_prefix = f"for_macie_scan/{account_id}-PII-{comprehend_job_id}/"
        response = macie.create_classification_job(
            description="Scanning redacted files for remaining sensitive data",
            initialRun=True,
            jobType="ONE_TIME",
            name=job_name,
            s3JobDefinition={
                "bucketDefinitions": [
                    {"accountId": account_id, "buckets": [SOURCE_BUCKET]}
                ],
                "scoping": {
                    "includes": {
                        "and": [
                            {
                                "simpleScopeTerm": {
                                    "comparator": "STARTS_WITH",
                                    "key": "OBJECT_KEY",
                                    "values": [scan_files_prefix],
                                }
                            },
                            {
                                "simpleScopeTerm": {
                                    "comparator": "EQ",
                                    "key": "OBJECT_EXTENSION",
                                    "values": ["txt"],
                                }
                            },
                        ]
                    }
                },
            },
            managedDataIdentifierSelector="ALL",
        )
        logger.info(f"Launching Macie job: {job_name} JobID: {response['jobId']}")
        logger.info(
            f"Scanning files in prefix s3://{SOURCE_BUCKET}/{scan_files_prefix}"
        )
        return response["jobId"]
    except ClientError as e:
        logger.error(f"Error creating Macie job: {str(e)}")
        raise


def check_macie_status(job_id: str) -> str:
    """Check Macie job status with error handling"""
    try:
        response = macie.describe_classification_job(jobId=job_id)
        return response["jobStatus"]
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            return "NOT_FOUND"
        raise e


def update_job_status(
    comprehend_job_id, macie_job_id, macie_job_status, macie_scan_status
):
    """Update job status in DynamoDB"""
    table.update_item(
        Key={"comprehend_job_id": comprehend_job_id},
        UpdateExpression=(
            "SET macie_job_id = :macie_job_id, "
            "macie_job_status = :macie_job_status, "
            "macie_scan_status = :macie_scan_status"
        ),
        ExpressionAttributeValues={
            ":macie_job_id": macie_job_id,
            ":macie_job_status": macie_job_status,
            ":macie_scan_status": macie_scan_status,
        },
    )


def get_macie_findings(job_id):
    """Get findings from Macie job"""
    findings = []
    next_token = None

    while True:
        params = {
            "findingCriteria": {
                "criterion": {"classificationDetails.jobId": {"eq": [job_id]}}
            },
            "maxResults": 50,
        }
        if next_token:
            params["nextToken"] = next_token

        response = macie.list_findings(**params)

        if response.get("findingIds"):
            findings_details = macie.get_findings(
                findingIds=response["findingIds"],
                sortCriteria={"attributeName": "severity.score", "orderBy": "DESC"},
            )
            if "findings" in findings_details:
                findings.extend(findings_details["findings"])

        next_token = response.get("nextToken")
        if not next_token:
            break

    return findings


def process_findings(findings):
    """Process Macie findings and return files to quarantine"""
    files_to_quarantine = set()
    logger.info(f"Inside process_findings fn. Findings:\n{findings}")

    for finding in findings:
        if "resourcesAffected" in finding:
            s3_object = finding["resourcesAffected"]["s3Object"]
            # filter findings with severity with 3 (HIGH) or above. Default is 1 (LOW)
            if finding.get("severity", {}).get("score", 1) >= 3:
                logger.info(f"High severity finding: {s3_object}")
                files_to_quarantine.add(s3_object["key"])

    return list(files_to_quarantine)


def move_files(files_to_quarantine):
    """Move files to appropriate locations based on Macie findings"""
    try:
        # Get all files in for_macie_scan folder
        all_files = get_files_to_scan()
        for file_key in all_files:
            file_name = file_key.split("/")[-1]

            if file_key in files_to_quarantine:
                # create .temp file in quarantine bucket
                s3.put_object(Bucket=SOURCE_BUCKET, Key="quarantine/.temp")
                # Move to quarantine folder
                new_key = f"quarantine/{file_name}"
                s3.copy_object(
                    Bucket=SOURCE_BUCKET,
                    CopySource={"Bucket": SOURCE_BUCKET, "Key": file_key},
                    Key=new_key,
                )
            # Delete original file
            s3.delete_object(Bucket=SOURCE_BUCKET, Key=file_key)
    except ClientError as e:
        logger.error(f"Error moving files: {str(e)}")
        raise


def check_running_jobs():
    """Check if there are any jobs that have macie_scanned = 'NO', macie_job_id is None, and macie_job_status is None"""
    # Scan for Comprehend COMPLETED jobs without Macie processing
    response = table.scan(
        FilterExpression="comprehend_job_status = :js AND macie_scan_status IN (:ms1, :ms2)",
        ExpressionAttributeValues={
            ":js": "COMPLETED",
            ":ms1": "NO",
            ":ms2": "RUNNING",
        },
    )
    if response.get("Items"):
        # logger.info(f"Found a job to scan: {response['Items']}")
        return response.get("Items")[0]

    return {}


def start_kb_ingestion(knowledgebase_id, datasource_id):
    """Start knowledge base ingestion job"""
    kb_client = boto3.client("bedrock-agent")
    try:
        logger.info(
            f"Starting knowledge base ingestion job for datasource: {datasource_id}"
        )
        response = kb_client.start_ingestion_job(
            knowledgeBaseId=knowledgebase_id,
            description=f"Knowledge Base Ingestion Job for {datasource_id}",
            dataSourceId=datasource_id,
        )
        return response
    except ClientError as e:
        logger.error(f"Error starting knowledge base ingestion job: {str(e)}")
        raise


def handler(event, context):
    try:
        # First check if there are any running jobs. items is a dict.
        items = check_running_jobs()
        if items:
            comprehend_job_id = str(items.get("comprehend_job_id"))
            macie_job_id = str(items.get("macie_job_id"))
            macie_scan_status = str(items.get("macie_scan_status"))
            macie_job_status = str(items.get("macie_job_status"))
            if macie_job_id == "NONE" and macie_scan_status == "NO":
                logger.info(f"Found a job to scan: {comprehend_job_id}")
                # Create and start Macie job
                job_name = f"macie-scan-{str(uuid4())[:8]}"
                macie_job_id = create_macie_job(job_name, comprehend_job_id)

                # get job status
                logger.info(f"Launched Macie job with id: {macie_job_id}")
                macie_job_status = check_macie_status(job_id=macie_job_id)
                logger.info(f"Macie job status: {macie_job_status}")

                # Update initial job status
                update_job_status(
                    comprehend_job_id, macie_job_id, macie_job_status, macie_scan_status
                )
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "message": f"Macie job {macie_job_id} Launched successfully.",
                            "status": "SUCCESS",
                        }
                    ),
                }

            if macie_job_status == "RUNNING" and macie_scan_status == "NO":
                macie_job_status = check_macie_status(job_id=macie_job_id)
                log_message = (
                    f"Macie job ID={macie_job_id} is still {macie_job_status}. Skipping."
                )
                if macie_job_status == "COMPLETE":
                    update_job_status(
                        comprehend_job_id,
                        macie_job_id,
                        macie_job_status,
                        macie_scan_status,
                    )
                logger.info(log_message)
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "message": log_message,
                            "status": "SKIPPED",
                        }
                    ),
                }

            if macie_job_status == "COMPLETE" and macie_scan_status == "NO":
                logger.info(f"Macie job {macie_job_id} completed successfully")

                # Get and process findings
                logger.info("Getting and processing macie findings")
                findings = get_macie_findings(macie_job_id)
                files_to_quarantine = process_findings(findings)

                # Move files based on findings
                if len(files_to_quarantine) > 0:
                    logger.info(f"Files to quarantine: {files_to_quarantine}")
                    move_files(files_to_quarantine)
                else:
                    logger.info(
                        f"No files to quarantine. Moving files to {SAFE_BUCKET}"
                    )
                    folder_prefix = f"{account_id}-PII-{comprehend_job_id}"
                    macie_output_prefix = f"for_macie_scan/{folder_prefix}/"
                    files_to_safe_bucket = []

                    for page in paginator.paginate(
                        Bucket=SOURCE_BUCKET, Prefix=macie_output_prefix
                    ):
                        if "Contents" in page:
                            files_to_safe_bucket.extend(
                                [
                                    obj["Key"]
                                    for obj in page["Contents"]
                                    if obj["Key"].endswith(".txt")
                                ]
                            )
                        logger.info(f"Files to safe bucket: {files_to_safe_bucket}")
                        # create .temp file in quarantine bucket
                        s3.put_object(Bucket=SAFE_BUCKET, Key=f"{folder_prefix}/.temp")
                        for file_key in files_to_safe_bucket:
                            file_name = file_key.split("/")[-1]
                            logger.info(f"Moving file : {file_name} to {SAFE_BUCKET}/{folder_prefix}")
                            # Move to quarantine folder
                            new_key = f"{folder_prefix}/{file_name}"
                            s3.copy_object(
                                Bucket=SAFE_BUCKET,
                                CopySource={"Bucket": SOURCE_BUCKET, "Key": file_key},
                                Key=new_key,
                            )
                            # Delete original file
                            logger.info(f"Deleting file: {SOURCE_BUCKET}/{file_key}")
                            s3.delete_object(Bucket=SOURCE_BUCKET, Key=file_key)
                        # Update macie scan status to YES in DDB Tracking table
                        update_job_status(
                            comprehend_job_id, macie_job_id, macie_job_status, "YES"
                        )
                    return {
                        "statusCode": 200,
                        "body": json.dumps(
                            {
                                "message": "Macie scan completed successfully",
                                "status": "COMPLETED",
                                "quarantined_files": len(files_to_quarantine),
                            }
                        ),
                    }

        if not items:
            logger.info(f"No jobs to start. No items found in DynamoDB Tracking Table={JOB_TABLE_NAME} ")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "No jobs to scan",
                        "status": "COMPLETED",
                    }
                ),
            }

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error: {error_message}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": error_message,
                    "status": "FAILED",
                    "macieJobId": macie_job_id if "macie_job_id" in locals() else None,
                }
            ),
        }
