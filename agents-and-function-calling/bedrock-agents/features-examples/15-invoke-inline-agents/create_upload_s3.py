import boto3
from botocore.exceptions import ClientError
import logging

def create_bucket(bucket_name, region='us-east-1'):
    try:
        s3_client = boto3.client('s3', region_name=region)
        location = {'LocationConstraint': region}
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration=location)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def upload_file(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def main():
    # Specify your bucket name and region
    bucket_name = 'my-unique-bucket-name'
    region = 'us-east-1'

    # Create the bucket
    if create_bucket(bucket_name, region):
        print(f"Successfully created bucket {bucket_name}")
    else:
        print(f"Failed to create bucket {bucket_name}")
        return

    # Upload file
    if upload_file('hrpolicy.txt', bucket_name):
        print(f"Successfully uploaded example.txt to {bucket_name}")
    else:
        print(f"Failed to upload example.txt to {bucket_name}")

if __name__ == '__main__':
    main()