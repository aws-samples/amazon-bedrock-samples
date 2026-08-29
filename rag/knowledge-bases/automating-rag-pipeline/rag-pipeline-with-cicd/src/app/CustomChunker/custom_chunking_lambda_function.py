import json
import logging
from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urlparse
import boto3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Abstract class for chunking text
class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        raise NotImplementedError()

# Simple chunker implementation with 1000-word chunks
class SimpleChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        words = text.split()
        return [' '.join(words[i:i + 1000]) for i in range(0, len(words), 1000)]

def lambda_handler(event, context):
    logger.debug(f'Input event to custom chunker lambda: {json.dumps(event)}')

    # Initialize S3 client
    s3 = boto3.client('s3')

    # Extract input parameters from the event
    input_files = event.get('inputFiles')
    input_bucket = event.get('bucketName')

    if not all([input_files, input_bucket]):
        raise ValueError("Missing required input parameters")

    chunker = SimpleChunker()
    output_files = []

    # Process each input file
    for input_file in input_files:
        content_batches = input_file.get('contentBatches', [])
        file_metadata = input_file.get('fileMetadata', {})
        original_file_location = input_file.get('originalFileLocation', {})

        processed_batches = []

        # Process each content batch
        for batch in content_batches:
            input_key = batch.get('key')

            if not input_key:
                raise ValueError("Missing 'key' in content batch")

            # Read the file from S3
            file_content = read_s3_file(s3, input_bucket, input_key)

            # Chunk the content using SimpleChunker
            chunked_content = process_content(file_content, chunker)

            # Define the output key and write the chunked content back to S3
            output_key = f"Output/{input_key}"
            write_to_s3(s3, input_bucket, output_key, chunked_content)

            # Add batch information for tracking
            processed_batches.append({'key': output_key})

        # Prepare the output file information
        output_file = {
            'originalFileLocation': original_file_location,
            'fileMetadata': file_metadata,
            'contentBatches': processed_batches
        }
        output_files.append(output_file)

    # Return the result with all output files
    result = {'outputFiles': output_files}
    logger.debug(f'Result: {json.dumps(result)}')

    return result

# Helper function to read content from S3
def read_s3_file(s3_client, bucket: str, key: str) -> dict:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read().decode('utf-8'))

# Helper function to write content to S3
def write_to_s3(s3_client, bucket: str, key: str, content: dict):
    s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(content))

# Process file content by chunking it
def process_content(file_content: dict, chunker: Chunker) -> dict:
    chunked_content = {'fileContents': []}

    for content in file_content.get('fileContents', []):
        content_body = content.get('contentBody', '')
        content_type = content.get('contentType', '')
        content_metadata = content.get('contentMetadata', {})

        # Create chunks using the chunker
        chunks = chunker.chunk(content_body)

        # Store each chunk as a separate content item
        for chunk in chunks:
            chunked_content['fileContents'].append({
                'contentType': content_type,
                'contentMetadata': content_metadata,
                'contentBody': chunk
            })

    return chunked_content

# Helper function to extract bucket and key from S3 URI
def extract_bucket_and_key(s3_uri: str):
    parsed_url = urlparse(s3_uri)
    bucket = parsed_url.netloc
    key = parsed_url.path.lstrip('/')
    return bucket, key
