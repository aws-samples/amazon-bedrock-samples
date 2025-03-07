import os
import time
import boto3
from urllib.parse import urlparse
import requests
import io
from PyPDF2 import PdfReader, PdfWriter
from botocore.exceptions import ClientError
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json
from botocore.config import Config
from typing import Optional
import pandas as pd
import ipywidgets as widgets

bda_client = boto3.client('bedrock-data-automation')
bda_runtime_client = boto3.client('bedrock-data-automation-runtime')

def get_bucket_and_key(s3_uri):
    parsed_uri = urlparse(s3_uri)
    bucket_name = parsed_uri.netloc
    object_key = parsed_uri.path.lstrip('/')
    return (bucket_name, object_key)

def wait_for_job_to_complete(invocationArn):
    get_status_response = bda_runtime_client.get_data_automation_status(
         invocationArn=invocationArn)
    status = get_status_response['status']
    job_id = invocationArn.split('/')[-1]
    max_iterations = 60
    iteration_count = 0
    while status not in ['Success', 'ServiceError', 'ClientError']:
        print(f'Waiting for Job to Complete. Current status is {status}')
        time.sleep(10)
        iteration_count += 1
        if iteration_count >= max_iterations:
            print(f"Maximum number of iterations ({max_iterations}) reached. Breaking the loop.")
            break
        get_status_response = bda_runtime_client.get_data_automation_status(
         invocationArn=invocationArn)
        status = get_status_response['status']
    if iteration_count >= max_iterations:
        raise Exception("Job did not complete within the expected time frame.")
    else:
        print(f"Invocation Job with id {job_id} completed. Status is {status}")
    return get_status_response


def read_s3_object(s3_uri):
    # Parse the S3 URI
    parsed_uri = urlparse(s3_uri)
    bucket_name = parsed_uri.netloc
    object_key = parsed_uri.path.lstrip('/')
    # Create an S3 client
    s3_client = boto3.client('s3')
    try:
        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        
        # Read the content of the object
        content = response['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        print(f"Error reading S3 object: {e}")
        return None

def download_document(url, start_page_index=None, end_page_index=None, output_file_path=None):

    if not output_file_path:
        filename = os.path.basename(url)
        output_file_path = filename
        
    # Download the PDF
    response = requests.get(url)
    print(response)
    pdf_content = io.BytesIO(response.content)
    
    # Create a PDF reader object
    pdf_reader = PdfReader(pdf_content)
    
    # Create a PDF writer object
    pdf_writer = PdfWriter()
    
    start_page_index = 0 if not start_page_index else max(start_page_index,0)
    end_page_index = len(pdf_reader.pages)-1 if not end_page_index else min(end_page_index,len(pdf_reader.pages)-1)

    # Specify the pages you want to extract (0-indexed)
    pages_to_extract = list(range(start_page_index, end_page_index))
    
    # Add the specified pages to the writer
    for page_num in pages_to_extract:
        page = pdf_reader.pages[page_num]
        pdf_writer.add_page(page)

    print(output_file_path)
    # Save the extracted pages to a new PDF
    with open(output_file_path, "wb") as output_file:
        pdf_writer.write(output_file)
    return output_file_path



def generate_presigned_url(s3_uri: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL for an S3 object with retry logic.
    
    Args:
        s3_uri (str): S3 URI in format 's3://bucket-name/key'
        expiration (int): URL expiration time in seconds
        
    Returns:
        Optional[str]: Presigned URL or None if generation fails
    """
    try:
        parsed = urlparse(s3_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )
        s3_client = boto3.client('s3', config=config)
        
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
    except Exception as e:
        print(f"Error generating presigned URL for {s3_uri}: {e}")
        return None

def create_image_html_column(row: pd.Series, image_col: str, width: str = '300px') -> str:
    """
    Create HTML embedded image from S3 URI using presigned URL for a DataFrame row.
    
    Args:
        row (pd.Series): DataFrame row
        image_col (str): Name of column containing S3 URI
        width (str): Fixed width for image
        
    Returns:
        str: HTML string for embedded image
    """
    s3_uri = row[image_col]
    if type(s3_uri)==list:
        s3_uri=s3_uri[0]    
    if pd.isna(s3_uri):
        return ''
    
    presigned_url = generate_presigned_url(s3_uri)
    if presigned_url:
        return f'<img src="{presigned_url}" style="width: {width}; object-fit: contain;">'
    return ''


# Example usage:
"""
# Add embedded images column
df['embedded_images'] = add_embedded_images(df, 'crop_images', width='300px')

# For Jupyter notebook display:
from IPython.display import HTML
HTML(df['embedded_images'].iloc[0])
"""



def wait_for_completion(
    client,
    get_status_function,
    status_kwargs,
    status_path_in_response,
    completion_states,
    error_states,
    max_iterations=60,
    delay=10
):
    for _ in range(max_iterations):
        try:
            response = get_status_function(**status_kwargs)
            status = get_nested_value(response, status_path_in_response)

            if status in completion_states:
                print(f"Operation completed successfully with status: {status}")
                return response

            if status in error_states:
                raise Exception(f"Operation failed with status: {status}")

            print(f"Current status: {status}. Waiting...")
            time.sleep(delay)

        except ClientError as e:
            raise Exception(f"Error checking status: {str(e)}")

    raise Exception(f"Operation timed out after {max_iterations} iterations")


def get_nested_value(data, path):
    """
    Retrieve a value from a nested dictionary using a dot-separated path.

    :param data: The dictionary to search
    :param path: A string representing the path to the value, e.g., "Job.Status"
    :return: The value at the specified path, or None if not found
    """
    keys = path.split('.')
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data


def send_request(region, url, method, credentials, payload=None, service='bedrock'):
    host = url.split("/")[2]
    request = AWSRequest(
            method,
            url,
            data=payload,
            headers={'Host': host, 'Content-Type':'application/json'}
    )    
    SigV4Auth(credentials, service, region).add_auth(request)
    response = requests.request(method, url, headers=dict(request.headers), data=payload, timeout=50)
    response.raise_for_status()
    content = response.content.decode("utf-8")
    data = json.loads(content)
    return data

def invoke_blueprint_recommendation_async(bda_client,region_name, payload):
    credentials = boto3.Session().get_credentials().get_frozen_credentials()
    url = f"{bda_client.meta.endpoint_url}/invokeBlueprintRecommendationAsync"
    print(f'Sending request to {url}')
    result = send_request(
        region = region_name,
        url = url,
        method = "POST", 
        credentials = credentials,
        payload=payload
    )
    return result


def get_blueprint_recommendation(bda_client, region_name, credentials, job_id):
    url = f"{bda_client.meta.endpoint_url}/getBlueprintRecommendation/{job_id}/"
    result = send_request(
        region = region_name,
        url = url,
        method = "POST",
        credentials = credentials        
    )
    return result

def create_or_update_blueprint(bda_client, blueprint_name, blueprint_description, blueprint_type, blueprint_stage, blueprint_schema):
    list_blueprints_response = bda_client.list_blueprints(
        blueprintStageFilter='ALL'
    )
    blueprint = next((blueprint for blueprint in
                      list_blueprints_response['blueprints']
                      if 'blueprintName' in blueprint and
                      blueprint['blueprintName'] == blueprint_name), None)

    if not blueprint:
        print(f'No existing blueprint found with name={blueprint_name}, creating custom blueprint')
        response = bda_client.create_blueprint(
            blueprintName=blueprint_name,
            type=blueprint_type,
            blueprintStage=blueprint_stage,
            schema=json.dumps(blueprint_schema)
        )
    else:
        print(f'Found existing blueprint with name={blueprint_name}, updating Stage and Schema')
        response = bda_client.update_blueprint(
            blueprintArn=blueprint['blueprintArn'],
            blueprintStage=blueprint_stage,
            schema=json.dumps(blueprint_schema)
        )

    return response['blueprint']['blueprintArn']


def transform_custom_output(input_json, explainability_info):
    result = {
        "forms": {},
        "tables": {}
    }

    def add_confidence(value, conf_info):
        return {"value": value, "confidence": conf_info["confidence"]} if isinstance(conf_info, dict) and "confidence" in conf_info else value
    
    def process_list_item(item, conf_info):
        return {k: add_confidence(v, conf_info.get(k, {})) for k, v in item.items() if isinstance(conf_info, dict)}    

    # Iterate through the input JSON
    for key, value in input_json.items():
        confidence_data = explainability_info.get(key, {})
        if isinstance(value, list):
            # Handle lists (tables)
            processed_list = []
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    # Process each item in the list using its corresponding confidence info
                    conf_info = confidence_data[idx] if isinstance(confidence_data, list) else confidence_data
                    processed_list.append(process_list_item(item, conf_info))
            result["tables"][key] = processed_list
        else:
            # Handle simple key-value pairs (forms)
            result["forms"][key] = add_confidence(value, confidence_data)
            
    return result


def get_summaries(custom_outputs):
    return [{
        'page_indices': output.get('split_document', {}).get('page_indices'),
        'matched_blueprint_name': output.get('matched_blueprint', {}).get('name'),
        'confidence': output.get('matched_blueprint', {}).get('confidence'),
        'document_class_type': output.get('document_class', {}).get('type')
    } if output else {} for output in custom_outputs]

