# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
bmkb.ingest_sync
===================
CloudFormation custom-resource handler for Stack 01. On Create/Update it uploads
the bundled synthetic corpora (packaged alongside this function under ``corpora/``)
into the KB source bucket, then triggers ``StartIngestionJob`` on each managed data
source and polls to a terminal state. On Delete it empties the (versioned) bucket so
the stack can remove it. It is deliberately deterministic glue — the KBs and data
sources themselves are native CloudFormation resources.

Resource properties
--------------------
BucketName : str
    Target S3 bucket for the corpora.
Ingestions : list[str]
    One entry per data source, formatted ``<kbId>|<dataSourceId>|<s3Prefix>``.
    The ``<kbId>|<dataSourceId>`` half is the ``Ref`` of an AWS::Bedrock::DataSource.
"""

import json
import time
import urllib.request
from pathlib import Path

import boto3

s3 = boto3.client("s3")
bedrock_agent = boto3.client("bedrock-agent")

CORPORA_DIR = Path(__file__).parent / "corpora"
POLL_SECONDS = 15
TERMINAL = {"COMPLETE", "FAILED"}


def _send(event, context, status, reason="", data=None):
    """Signal the pre-signed CloudFormation response URL."""
    body = json.dumps({
        "Status": status,
        "Reason": reason or f"See CloudWatch log stream: {context.log_stream_name}",
        "PhysicalResourceId": event.get("PhysicalResourceId") or context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": data or {},
    }).encode("utf-8")
    req = urllib.request.Request(
        event["ResponseURL"], data=body, method="PUT",
        headers={"content-type": "", "content-length": str(len(body))},
    )
    urllib.request.urlopen(req)  # nosec B310 - fixed https CFN response URL


def _upload_corpora(bucket, prefix):
    """Upload every bundled file under corpora/<theme>/ to s3://bucket/<prefix>."""
    theme = prefix.rstrip("/").split("/")[-1]
    src = CORPORA_DIR / theme
    uploaded = []
    for f in sorted(src.glob("*")):
        if f.is_file():
            key = f"{prefix}{f.name}"
            s3.upload_file(str(f), bucket, key)
            uploaded.append(key)
    print(f"  uploaded {len(uploaded)} file(s) to s3://{bucket}/{prefix}: {uploaded}")
    return uploaded


def _ingest(kb_id, ds_id):
    """Start an ingestion job and poll to a terminal state."""
    job = bedrock_agent.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
    job_id = job["ingestionJob"]["ingestionJobId"]
    print(f"  started ingestion {job_id} for kb={kb_id} ds={ds_id}")
    while True:
        status = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job_id,
        )["ingestionJob"]["status"]
        if status in TERMINAL:
            print(f"  ingestion {job_id} -> {status}")
            if status == "FAILED":
                raise RuntimeError(f"Ingestion job {job_id} FAILED for kb={kb_id}")
            return job_id
        time.sleep(POLL_SECONDS)


def _empty_bucket(bucket):
    """Delete all object versions and delete markers so the bucket can be removed."""
    paginator = s3.get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=bucket):
        to_delete = [
            {"Key": o["Key"], "VersionId": o["VersionId"]}
            for o in page.get("Versions", []) + page.get("DeleteMarkers", [])
        ]
        if to_delete:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete, "Quiet": True})
    print(f"  emptied bucket {bucket}")


def handler(event, context):
    print(json.dumps({"RequestType": event["RequestType"],
                      "ResourceProperties": event.get("ResourceProperties", {})}))
    props = event.get("ResourceProperties", {})
    bucket = props.get("BucketName")

    # Delete is ALWAYS idempotent SUCCESS. Best-effort empty the bucket, but never let a
    # Delete send FAILED or raise — otherwise the whole stack delete hangs ~1h on the CR
    # callback. (The bucket also has its own contents removed here so CFN can drop it.)
    if event["RequestType"] == "Delete":
        try:
            if bucket:
                _empty_bucket(bucket)
        except Exception as exc:
            print(f"WARN: delete cleanup best-effort failure (ignored): {exc}")
        _send(event, context, "SUCCESS", "Delete complete")
        return

    try:
        # Create / Update: upload corpora, then ingest each data source.
        for entry in props.get("Ingestions", []):
            kb_id, ds_id, prefix = entry.split("|")
            _upload_corpora(bucket, prefix)
            _ingest(kb_id, ds_id)

        _send(event, context, "SUCCESS", "Ingestion complete")
    except Exception as exc:  # surface failure back to CloudFormation
        print(f"ERROR: {exc}")
        _send(event, context, "FAILED", str(exc))
