
import json
import logging
import boto3
import base64
from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urlparse
from pypdf import PdfReader
from io import BytesIO
from botocore.exceptions import ClientError
from PIL import Image


# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Abstract class for chunking text
class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str) -> List[str]:
        pass

# Simple implementation of the Chunker that splits text into chunks of 10 words
class SimpleChunker(Chunker):
    def chunk(self, text: str) -> List[str]:
        words = text.split()
        return [' '.join(words[i:i + 1000]) for i in range(0, len(words), 1000)]

# Lambda function entry point
def lambda_handler(event, context):
    logger.debug('Starting lambda_handler')
    logger.debug(f'Input event: {json.dumps(event, indent=2)}')
    
    # Initialize the S3 and Bedrock clients
    s3 = boto3.client('s3')
    bedrock_client = boto3.client('bedrock-runtime')
    chunker = SimpleChunker()
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    # Extract relevant information from the input event
    input_files = event.get('inputFiles')
    input_bucket = event.get('bucketName')

    if not all([input_files, input_bucket]):
        raise ValueError("Missing required input parameters")

    output_files = []

    # Iterate over each input file
    for input_file in input_files:
        content_batches = input_file.get('contentBatches', [])
        file_metadata = input_file.get('fileMetadata', {})
        original_file_location = input_file.get('originalFileLocation', {})
        logger.debug(f"Processing input file from: {original_file_location}")

        # original_file_location = input_file['originalFileLocation']['s3_location']['uri']
        s3_uri = original_file_location['s3_location']['uri']
        # bucket, key = original_file_location.replace("s3://", "").split('/', 1)
        # Use the extract_bucket_and_key function to get the bucket and key
        bucket, key = extract_bucket_and_key(s3_uri)
        logger.info(f"Reading PDF from S3: bucket={bucket}, key={key}")

        # Read the PDF from S3 and extract images
        pdf_content = read_pdf_from_s3(bucket, key)
        images_with_metadata = extract_images_from_pdf(pdf_content)
        
        # Generate summaries for the extracted images
        # prompt = "Summarize all the details in the image, focus on statistics such as bar charts and graphs."
        prompt = "Provide a comprehensive description of the image, highlighting all the key details. " \
                 "If the image includes charts or any other visual data representations, focus also on summarizing the " \
                 "statistical information, including trends, comparisons, and any relavant numerical data present in bar charts, line graphs, or other graphical elements."
        
        # Generate image summaries and add base64 representations as metadata
        processed_images = process_images_with_metadata(bedrock_client, model_id, prompt, images_with_metadata)

        processed_batches = []

        # Iterate over content batches and process text
        for batch in content_batches:
            input_key = batch.get('key')

            if not input_key:
                raise ValueError("Missing uri in content batch")

            file_content = read_s3_file(s3, input_bucket, input_key)

            # # Update content metadata with page numbers and chunk the content
            # for page_number, page_content in enumerate(file_content['fileContents'], start=1):
            #     page_content['contentMetadata']['pageNumber'] = page_number


            # Create chunks using the SimpleChunker
            chunked_content = process_content(file_content, chunker)
            chunked_content['fileContents'].extend(processed_images)  # Combine the chunked content with image summaries
            logger.debug(f'Chunked content: {json.dumps(chunked_content, indent=2)}')


            # Define the output key and write the final content to S3
            # final_key = f"OutputLocal/{input_key}"
            output_key = f"Output/{input_key}"

            write_to_s3(s3, input_bucket, output_key, chunked_content)
            logger.info(f"Final output written to S3 with key: {output_key}")

            # Add processed batch information
            processed_batches.append({
                'key': output_key
            })


        # Prepare output file information
        output_file = {
            'originalFileLocation': original_file_location,
            'fileMetadata': file_metadata,
            'contentBatches': processed_batches
        }

        logger.info(f"Processed file: {output_file}")
        output_files.append(output_file)

    # Prepare the result with the output files
    result = {'outputFiles': output_files}
    logger.debug(f'lambda_handler result: {result}')

    logger.debug(f'Final result before returning: {json.dumps(result, indent=2)}')

    return result

# Helper function to read content from S3
def read_s3_file(s3_client, bucket: str, key: str) -> dict:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read().decode('utf-8'))

# Helper function to write content to S3
def write_to_s3(s3_client, bucket: str, key: str, content: dict):
    s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(content))


def process_content(file_content: dict, chunker: Chunker) -> dict:
    chunked_content = {
        'fileContents': []
    }
    
    for content in file_content.get('fileContents', []):
        content_body = content.get('contentBody', '')
        content_type = content.get('contentType', '')
        content_metadata = content.get('contentMetadata', {})
        
        words = content['contentBody']
        chunks = chunker.chunk(words)
        
        for chunk in chunks:
            chunked_content['fileContents'].append({
                'contentType': content_type,
                'contentMetadata': content_metadata,
                'contentBody': chunk
            })
    
    return chunked_content

# Reads a PDF from S3 and returns its content as bytes
def read_pdf_from_s3(bucket: str, key: str) -> bytes:
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()

# Encodes image data to a base64 string
def encode_image(image_data: bytes) -> str:
    return base64.b64encode(image_data).decode('utf-8')
    
def extract_images_from_pdf(pdf_content: bytes) -> List[dict]:
    pdf_reader = PdfReader(BytesIO(pdf_content))
    images = []
    for page_num, page in enumerate(pdf_reader.pages):
        for image in page.images:
            image_bytes = image.data
            try:
                img = Image.open(BytesIO(image_bytes))
                width, height = img.size
                logger.info(f"Extracted image on page {page_num + 1} with width {width}px and height {height}px")
            except Exception as e:
                logger.error(f"Failed to get image size: {e}")
                width, height = None, None
            images.append({
                'image_data': image_bytes,
                'contentMetadata': {
                    'base64Image': encode_image(image_bytes),
                    'width': width,
                    'height': height
                }
            })
    return images


# Sends image data to the Bedrock model and returns the generated summary
def generate_image_summaries(bedrock_client, model_id: str, input_text: str, image_data: bytes) -> dict:
    message = {
        "role": "user",
        "content": [
            {"text": input_text},
            {"image": {"format": 'png', "source": {"bytes": image_data}}}
        ]
    }

    response = bedrock_client.converse(modelId=model_id, messages=[message])
    return response

# Processes images by generating summaries and appending metadata
def process_images_with_metadata(bedrock_client, model_id: str, input_text: str, images_with_metadata: List[dict]) -> List[dict]:
    results = []

    for image_metadata in images_with_metadata:
        # try:
            response = generate_image_summaries(bedrock_client, model_id, input_text, image_metadata['image_data'])
            summary = " ".join([content['text'] for content in response['output']['message']['content'] if 'text' in content])
            logger.info(f"Generated summary for image: {summary}")

            results.append({
                "contentType": "PDF",
                "contentMetadata": {
                    # "pageNumber": image_metadata['contentMetadata']['pageNumber'],
                    "base64Image": image_metadata['contentMetadata']['base64Image']
                },
                "contentBody": summary,
                
            })

    return results

def extract_bucket_and_key(s3_uri: str):
    parsed_url = urlparse(s3_uri)
    bucket = parsed_url.netloc
    key = parsed_url.path.lstrip('/')
    return bucket, key
