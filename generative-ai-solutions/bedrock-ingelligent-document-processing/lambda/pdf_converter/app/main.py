"""
Converts single page PDFs to JPEGs
"""
import json
import logging
import os
import textractmanifest as tm
import boto3
from uuid import uuid4
from io import BytesIO

from typing import Tuple
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)

s3 = boto3.client("s3")

def split_s3_path_to_bucket_and_key(s3_path: str) -> Tuple[str, str]:
    if len(s3_path) > 7 and s3_path.lower().startswith("s3://"):
        s3_bucket, s3_key = s3_path.replace("s3://", "").split("/", 1)
        return (s3_bucket, s3_key)
    else:
        raise ValueError(
            f"s3_path: {s3_path} is no s3_path in the form of s3://bucket/key."
        )


def get_pdf_file_from_s3(s3_path: str, range=None) -> bytes:
    s3_bucket, s3_key = split_s3_path_to_bucket_and_key(s3_path)
    if range:
        o = s3.get_object(Bucket=s3_bucket, Key=s3_key, Range=range)
    else:
        o = s3.get_object(Bucket=s3_bucket, Key=s3_key)
    return o.get("Body").read()


class ThrottlingException(Exception):
    pass


class ServiceQuotaExceededException(Exception):
    pass


class ModelTimeoutException(Exception):
    pass


class ModelNotReadyException(Exception):
    pass

def lambda_handler(event, _):
    """
    Converts single page PDFs to PNGs
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logger.setLevel(log_level)
    logger.info(f"LOG_LEVEL: {log_level}")
    logger.info(json.dumps(event))
    bedrock_model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
    s3_output_bucket = os.environ.get('S3_OUTPUT_BUCKET')
    s3_output_prefix = os.environ.get('S3_OUTPUT_PREFIX')
    
    if not s3_output_bucket:
        raise Exception("no S3_OUTPUT_BUCKET set")
    if not s3_output_prefix:
        raise Exception("no S3_OUTPUT_PREFIX set")
    
    # Get manifest file from event context
    if "Payload" in event and "manifest" in event["Payload"]:
        manifest: tm.IDPManifest = tm.IDPManifestSchema().load(event["Payload"]["manifest"])  # type: ignore
    elif "manifest" in event:
        manifest: tm.IDPManifest = tm.IDPManifestSchema().load(event["manifest"])  # type: ignore else:
    else:
        manifest: tm.IDPManifest = tm.IDPManifestSchema().load(event)  # type: ignore
        
    # Load source image from S3
    if (
        "manifest" in event
        and "s3Path" in event["manifest"]
    ):
        image_path = event["manifest"]["s3Path"]
    else:
        raise ValueError(
            "no ['manifest']['s3Path'] to get the text file from "
        )
        
    source_pdf = get_pdf_file_from_s3(s3_path=image_path)
    transformed_images = convert_from_bytes(source_pdf)
   
    buf = BytesIO()
    transformed_images[0].save(buf, format='JPEG')
    byte_string = buf.getvalue()
    
    s3_filename, _ = os.path.splitext(os.path.basename(manifest.s3_path))
    output_bucket_key = s3_output_prefix + "/" + s3_filename + str(uuid4()) + ".jpeg"
    s3.put_object(Body=byte_string, Bucket=s3_output_bucket, Key=output_bucket_key)
    
    event['manifest']['s3Path'] = f"s3://{s3_output_bucket}/{output_bucket_key}"
    event['mime'] = "image/jpeg"
    return event