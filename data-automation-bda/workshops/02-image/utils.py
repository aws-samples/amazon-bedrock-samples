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

def delete_s3_folder(bucket_name, folder_prefix, s3_client):
    """
    Delete all objects within an S3 folder.

    :param bucket_name: Name of the S3 bucket
    :param folder_prefix: Folder path (prefix) to delete (must end with '/')
    """
    
    # List all objects with the given prefix (folder)
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_prefix)
    
    if 'Contents' in response:
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        
        # Delete all objects in the folder
        s3_client.delete_objects(Bucket=bucket_name, Delete={'Objects': objects_to_delete})
        print(f"Deleted folder: {folder_prefix} in bucket: {bucket_name}")
    else:
        print(f"No objects found in folder: {folder_prefix}")