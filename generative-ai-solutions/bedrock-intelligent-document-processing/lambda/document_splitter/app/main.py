# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import boto3
from datetime import datetime
import json
import textractmanifest as tm
import filetype
# from documentsplitter.documentsplitter import split_and_save_pages, split_s3_path_to_bucket_and_key
from typing import Tuple, Optional

from typing import Tuple, List
from pypdf import PdfReader, PdfWriter
from PIL import Image
import io
import sys

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

logger = logging.getLogger(__name__)
version = "0.0.14"

def split_and_save_pages(s3_path: str,
                         mime: str,
                         filename: str,
                         s3_output_bucket: str,
                         s3_output_prefix: str,
                         max_number_of_pages=1) -> List[str]:
    """takes a document ('application/pdf', 'image/tiff', 'image/png', 'image/jpeg') then stores single page files to s3_output_bucket under the s3_output_prefix with a _<page_number> and returns the list of file names """
    # object key is <start-page>-<end-page>.suffix
    output_file_list: List[str] = list()
    if mime == 'application/pdf':
        file_bytes = get_file_from_s3(s3_path=s3_path)
        with io.BytesIO(file_bytes) as input_pdf_file:
            pdf_reader = PdfReader(input_pdf_file)
            current_number_of_pages_collected = 0
            current_start_page = 1
            writer = PdfWriter()
            page_number = 1
            page_in_mem = io.BytesIO()
            for page_number in range(1, len(pdf_reader.pages) + 1):
                page_in_mem = io.BytesIO()
                writer.add_page(pdf_reader.pages[page_number - 1])
                writer.write(page_in_mem)
                logger.debug(f"len page_in_mem: {sys.getsizeof(page_in_mem)}")
                current_number_of_pages_collected += 1
                if current_number_of_pages_collected == max_number_of_pages:
                    file_name = f"{filename}-{current_start_page}-{page_number}.pdf"
                    output_bucket_key = os.path.join(s3_output_prefix,
                                                     file_name)
                    page_in_mem.seek(0)
                    s3_client.put_object(Body=page_in_mem,
                                  Bucket=s3_output_bucket,
                                  Key=output_bucket_key)
                    output_file_list.append(file_name)
                    # reset the counters
                    writer = PdfWriter()
                    current_start_page = page_number + 1
                    current_number_of_pages_collected = 0
                else:
                    if page_in_mem:
                        file_name = f"{current_start_page}-{page_number}.pdf"
                        output_bucket_key = os.path.join(s3_output_prefix,
                                                         file_name)
                        page_in_mem.seek(0)
                        s3_client.put_object(Body=page_in_mem,
                                      Bucket=s3_output_bucket,
                                      Key=output_bucket_key)
                        output_file_list.append(file_name)
            return output_file_list
    elif mime == 'image/tiff':
        file_bytes = get_file_from_s3(s3_path=s3_path)
        f = io.BytesIO(file_bytes)
        img = Image.open(f)
        page = 0
        current_start_page = 1
        #
        while True:
            images_for_chunk = []
            for _ in range(max_number_of_pages):
                try:
                    img.seek(page)
                    images_for_chunk.append(img.copy())
                    page += 1
                except EOFError:
                    # End of file, exit the loop
                    break

            # Upload the current chunk if it has any images
            if images_for_chunk:
                # Create an in-memory bytes buffer to store the chunk
                byte_io = io.BytesIO()
                images_for_chunk[0].save(byte_io,
                                         format='TIFF',
                                         save_all=True,
                                         append_images=images_for_chunk[1:])
                byte_io.seek(0)

                # Construct object key and upload to S3
                file_name = f"{current_start_page}-{page}.tiff"
                output_bucket_key = os.path.join(s3_output_prefix, file_name)
                output_file_list.append(file_name)
                s3_client.put_object(Body=byte_io,
                              Bucket=s3_output_bucket,
                              Key=output_bucket_key)
                current_start_page = page + 1
            else:
                # No more images left to process, exit the loop
                break
        #
    elif mime in ['image/png', 'image/jpeg']:
        source_s3_bucket, source_s3_key = split_s3_path_to_bucket_and_key(
            s3_path)
        suffix = mime.split('/')[1]
        file_name = f"1-1.{suffix}"
        output_bucket_key = os.path.join(s3_output_prefix, file_name)
        s3_resource.meta.client.copy(
            {
                'Bucket': source_s3_bucket,
                'Key': source_s3_key
            }, s3_output_bucket, output_bucket_key)
        output_file_list.append(file_name)
    else:
        raise ValueError(f"unsupported mime type: {mime}")
    return output_file_list
    
def split_s3_path_to_bucket_and_key(s3_path: str) -> Tuple[str, str]:
    if len(s3_path) > 7 and s3_path.lower().startswith("s3://"):
        s3_bucket, s3_key = s3_path.replace("s3://", "").split("/", 1)
        return (s3_bucket, s3_key)
    else:
        raise ValueError(
            f"s3_path: {s3_path} is no s3_path in the form of s3://bucket/key."
        )

def get_file_from_s3(s3_path: str, range=None) -> bytes:
    s3_bucket, s3_key = split_s3_path_to_bucket_and_key(s3_path)
    if range:
        o = s3_client.get_object(Bucket=s3_bucket, Key=s3_key, Range=range)
    else:
        o = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    return o.get('Body').read()


def get_mime_for_file(file_bytes: bytes) -> Optional[str]:
    """
    possible formats: image/tiff, image/jpeg, application/pdf, image/png or 
    """
    kind = filetype.guess(file_bytes)
    if kind is None:
        return None
    else:
        return kind.mime

def lambda_handler(event, _):
    # Accepts a manifest file, with an s3Path and will split the document into individual pages

    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logger.setLevel(log_level)
    logger.info(f"version: {version}")
    logger.info(f"amazon-textract-idp-cdk-manifest: {tm.__version__}")
    logger.info(json.dumps(event))

    s3_output_bucket = os.environ.get('S3_OUTPUT_BUCKET', None)
    s3_output_prefix="textract-split-documents"

    # if not s3_output_bucket:
    #     raise Exception("no S3_OUTPUT_BUCKET set")

    # s3_output_prefix = os.environ.get('S3_OUTPUT_PREFIX', None)
    # if not s3_output_prefix:
    #     raise Exception("no S3_OUTPUT_PREFIX set")
    
    # s3_output_bucket="bedrockidpclaude3workflow-bedrockidpclaude3bucket0-pgrdbpkwtsfg"
    # s3_output_prefix="textract-split-documents"

    max_number_of_pages_per_doc = int(
        os.environ.get('MAX_NUMBER_OF_PAGES_PER_DOC', "1"))
    
    logger.debug(f"S3_OUTPUT_BUCKET: {s3_output_bucket} \
     S3_OUTPUT_PREFIX: {s3_output_prefix} \
     MAX_NUMBER_OF_PAGES_PER_DOC: {max_number_of_pages_per_doc}")

    supported_mime_types = [
        'application/pdf', 'image/png', 'image/jpeg', 'image/tiff'
    ]

    if 'manifest' in event:
        manifest: tm.IDPManifest = tm.IDPManifestSchema().load(
            event['manifest'])  #type: ignore
    else:
        manifest: tm.IDPManifest = tm.IDPManifestSchema().load(
            event)  #type: ignore

    s3_path = manifest.s3_path

    if 'mime' in event:
        mime = event['mime']
    else:
        first_file_bytes = get_file_from_s3(s3_path=s3_path,
                                            range='bytes=0-2000')
        mime = get_mime_for_file(file_bytes=first_file_bytes)

    if mime and mime in supported_mime_types:
        timestamp = datetime.utcnow().isoformat()
        s3_filename, _ = os.path.splitext(os.path.basename(manifest.s3_path))
        full_output_prefix = os.path.join(s3_output_prefix, s3_filename,
                                          timestamp)
        output_file_list = split_and_save_pages(
            s3_path=s3_path,
            mime=mime,
            filename=s3_filename,
            s3_output_bucket=s3_output_bucket,
            s3_output_prefix=full_output_prefix,
            max_number_of_pages=max_number_of_pages_per_doc)
    else:
        raise Exception(f"not supported Mime type: {mime}")
    logger.info(f"return: {manifest}")

    result_value = {
        "documentSplitterS3OutputPath": full_output_prefix,
        "documentSplitterS3OutputBucket": s3_output_bucket,
        "pages": output_file_list,
        "mime": mime,
        "originFileURI": manifest.s3_path
    }

    return result_value