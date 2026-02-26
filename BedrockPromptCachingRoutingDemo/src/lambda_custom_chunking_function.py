import json
import boto3
import os
import logging
import traceback
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Constants for chunking
MAX_TOKENS = 1000
OVERLAP_PERCENTAGE = 0.20

def estimate_tokens(text):
    """
    Rough estimation of tokens (approximation: 1 token ≈ 0.75 words)
    """
    words = text.split()
    return int(len(words) * 0.75)

def chunk_text(text, max_tokens=MAX_TOKENS, overlap_percentage=OVERLAP_PERCENTAGE):
    """
    Chunk text based on words with specified max tokens and overlap
    """
    if not text:
        return []

    # Split text into words
    words = text.split()
    if not words:
        return []

    # Estimate words per chunk based on token limit
    # Assuming average of 0.75 tokens per word
    words_per_chunk = int(max_tokens * 1.33)  # Convert tokens to approximate words
    overlap_words = int(words_per_chunk * overlap_percentage)

    chunks = []
    current_position = 0
    total_words = len(words)

    while current_position < total_words:
        # Calculate end position for current chunk
        chunk_end = min(current_position + words_per_chunk, total_words)
        
        # Get current chunk words
        chunk_words = words[current_position:chunk_end]
        
        # If this isn't the last chunk, try to find a good break point
        if chunk_end < total_words:
            # Look for sentence-ending punctuation in the last few words
            for i in range(len(chunk_words) - 1, max(len(chunk_words) - 10, 0), -1):
                if chunk_words[i].endswith(('.', '!', '?')):
                    chunk_end = current_position + i + 1
                    chunk_words = chunk_words[:i + 1]
                    break

        # Join words back into text
        chunk_text = ' '.join(chunk_words)
        chunks.append(chunk_text.strip())
        
        # Move position considering overlap
        current_position = chunk_end - overlap_words if chunk_end < total_words else chunk_end

    return chunks

def write_output_to_s3(s3_client, bucket_name, file_name, json_data):
    """
    Write JSON data to S3 bucket
    """
    try:
        json_string = json.dumps(json_data)
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json_string,
            ContentType='application/json'
        )

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"Successfully uploaded {file_name} to {bucket_name}")
            return True
        else:
            print(f"Failed to upload {file_name} to {bucket_name}")
            return False

    except ClientError as e:
        print(f"Error occurred: {e}")
        return False

def read_from_s3(s3_client, bucket_name, file_name):
    """
    Read JSON data from S3 bucket
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        print(f"Error reading file from S3: {str(e)}")

def parse_s3_path(s3_path):
    """
    Parse S3 path into bucket and key
    """
    s3_path = s3_path.replace('s3://', '')
    parts = s3_path.split('/', 1)
    if len(parts) != 2:
        raise ValueError("Invalid S3 path format")
    return parts[0], parts[1]

def invoke_model_with_response_stream(bedrock_runtime, prompt, max_tokens=1000):
    """
    Invoke Bedrock model with streaming response
    """
    model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.0,
    })

    try:
        response = bedrock_runtime.invoke_model_with_response_stream(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=request_body
        )

        for event in response.get('body'):
            chunk = json.loads(event['chunk']['bytes'].decode())
            if chunk['type'] == 'content_block_delta':
                yield chunk['delta']['text']
            elif chunk['type'] == 'message_delta':
                if 'stop_reason' in chunk['delta']:
                    break

    except ClientError as e:
        print(f"An error occurred: {e}")
        yield None

# Define the contextual retrieval prompt
contextual_retrieval_prompt = """
    <document>
    {doc_content}
    </document>

    Here is the chunk we want to situate within the whole document
    <chunk>
    {chunk_content}
    </chunk>

    Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
    Answer only with the succinct context and nothing else.
    """

def lambda_handler(event, context):
    """
    Lambda handler function
    """
    logger.debug('input={}'.format(json.dumps(event)))

    s3_client = boto3.client('s3')
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-1'
    )

    input_files = event.get('inputFiles')
    input_bucket = event.get('bucketName')

    if not all([input_files, input_bucket]):
        raise ValueError("Missing required input parameters")

    output_files = []
    for input_file in input_files:
        processed_batches = []
        for batch in input_file.get('contentBatches'):
            input_key = batch.get('key')

            if not input_key:
                raise ValueError("Missing uri in content batch")

            file_content = read_from_s3(s3_client, bucket_name=input_bucket, file_name=input_key)
            print(file_content.get('fileContents'))

            original_document_content = ''.join(
                content.get('contentBody') 
                for content in file_content.get('fileContents') 
                if content
            )

            chunked_content = {
                'fileContents': []
            }
            
            for content in file_content.get('fileContents'):
                content_body = content.get('contentBody', '')
                content_type = content.get('contentType', '')
                content_metadata = content.get('contentMetadata', {})

                # Apply chunking strategy
                chunks = chunk_text(content_body)
                
                for chunk in chunks:
                    prompt = contextual_retrieval_prompt.format(
                        doc_content=original_document_content, 
                        chunk_content=chunk
                    )
                    response_stream = invoke_model_with_response_stream(bedrock_runtime, prompt)
                    chunk_context = ''.join(chunk_text for chunk_text in response_stream if chunk_text)

                    chunked_content['fileContents'].append({
                        "contentBody": chunk_context + "\n\n" + chunk,
                        "contentType": content_type,
                        "contentMetadata": content_metadata,
                    })

            output_key = f"Output/{input_key}"
            write_output_to_s3(s3_client, input_bucket, output_key, chunked_content)
            processed_batches.append({"key": output_key})
            
        output_files.append({
            "originalFileLocation": input_file.get('originalFileLocation'),
            "fileMetadata": {},
            "contentBatches": processed_batches
        })

    return {
        "outputFiles": output_files
    }