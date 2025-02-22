import json

def read_json_on_s3(s3_uri, s3_client):
    # Parse s3 bucket and key from s3 uri
    s3_bucket = s3_uri.split('/')[2]
    s3_key = s3_uri.replace(f's3://{s3_bucket}/','')
    
    # Read BDA output_config file on S3
    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    file_content = response['Body'].read().decode('utf-8')  # Read the content and decode it to a string
    # Convert the content to JSON
    return json.loads(file_content)
