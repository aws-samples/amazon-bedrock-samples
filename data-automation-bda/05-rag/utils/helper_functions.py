import time
import boto3
from urllib.parse import urlparse
import requests
import io
from PyPDF2 import PdfReader, PdfWriter


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

def create_sample_file(url, start_page_index, end_page_index, output_file_path):

    # Download the PDF
    response = requests.get(url)
    pdf_content = io.BytesIO(response.content)
    
    # Create a PDF reader object
    pdf_reader = PdfReader(pdf_content)
    
    # Create a PDF writer object
    pdf_writer = PdfWriter()

    start_page_index = max(start_page_index,0)
    end_page_index = min(end_page_index,len(pdf_reader.pages)-1)

    # Specify the pages you want to extract (0-indexed)
    pages_to_extract = list(range(start_page_index, end_page_index))
    
    # Add the specified pages to the writer
    for page_num in pages_to_extract:
        page = pdf_reader.pages[page_num]
        pdf_writer.add_page(page)

    # Save the extracted pages to a new PDF
    with open(output_file_path, "wb") as output_file:
        pdf_writer.write(output_file)
    