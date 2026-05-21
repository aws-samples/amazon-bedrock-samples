import boto3
import os
import botocore.exceptions
from botocore.exceptions import ClientError


# Initialize the S3 client
s3_client = boto3.client('s3')

ROOT_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_PATH, "config")
CONFIG_JSON = os.path.join(CONFIG_PATH, "config.json")
MODELS_JSON = os.path.join(CONFIG_PATH, "models.json")

def empty_bucket(bucket_name):
    try:
        objects = s3_client.list_objects_v2(Bucket=bucket_name).get('Contents', [])
        if objects:
            for obj in objects:
                s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
            print(f"Emptied bucket: {bucket_name}")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"Bucket {bucket_name} does not exist, proceeding to create it.")
        else:
            raise

def create_bucket(bucket_name, region=None):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists.")
        empty_bucket(bucket_name)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404' or 'NoSuchBucket':
            if region:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            else:
                s3_client.create_bucket(Bucket=bucket_name)
            print(f"Created bucket {bucket_name}.")
        else:
            raise

def upload_file_to_s3(file_path, bucket_name, s3_directory, object_name=None):
    """
    Upload a file to an S3 bucket in a specific directory

    :param file_path: File to upload
    :param bucket_name: Bucket to upload to
    :param s3_directory: Directory in S3 to upload to
    :param object_name: S3 object name. If not specified, file_path is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use the file_path
    if object_name is None:
        object_name = file_path.split('/')[-1]

    # Create the full S3 key (path + filename)
    s3_key = f"{s3_directory}/{object_name}"

    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
    except ClientError as e:
        print(f"Error uploading file to S3: {e}")
        return False
    return True

def main():
    bucket_name = 'inference-cost-tracing'
    region = "us-west-2"  # Specify your desired region
    create_bucket(bucket_name, region)
    upload_file_to_s3(CONFIG_JSON, bucket_name, "config")
    upload_file_to_s3(MODELS_JSON, bucket_name, "config")

if __name__ == "__main__":
    main()