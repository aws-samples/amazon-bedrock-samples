import boto3
from datetime import datetime
import cfnresponse
import os
import shutil
import subprocess
import sys
import zipfile

requirements = os.environ['REQUIREMENTS']
s3_bucket = os.environ['S3_BUCKET']


def upload_file_to_s3(file_path, bucket, key):
    s3 = boto3.client('s3')
    s3.upload_file(file_path, bucket, key)
    print(f"Upload successful. {file_path} uploaded to {bucket}/{key}")


def make_zip_filename():
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    filename = f'LambdaLayer_{timestamp}.zip'
    return filename


def zipdir(path, zipname):
    zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(path):
        for file in files:
            zipf.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))
    zipf.close()


def empty_bucket(bucket_name):
    s3_client = boto3.client('s3')
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        keys = [{'Key': obj['Key']} for obj in response['Contents']]
        s3_client.delete_objects(Bucket=bucket_name, Delete={'Objects': keys})
    return


def lambda_handler(event, context):
    print("Event: ", event)
    responseData = {}
    reason = ""
    status = cfnresponse.SUCCESS
    try:
        if event['RequestType'] != 'Delete':
            os.chdir('/tmp')
            # download Bedrock SDK
            requirements_list = requirements.split(" ")

            if os.path.exists("python"):
                shutil.rmtree("python")

            for requirement in requirements_list:
                subprocess.check_call([sys.executable, "-m", "pip", "install", requirement, "-t", "python"])

            boto3_zip_name = make_zip_filename()
            zipdir("python", boto3_zip_name)

            print(f"uploading {boto3_zip_name} to s3 bucket {s3_bucket}")
            upload_file_to_s3(boto3_zip_name, s3_bucket, boto3_zip_name)
            responseData = {"Bucket": s3_bucket, "Key": boto3_zip_name}
        else:
            # delete - empty the bucket so it can be deleted by the stack.
            empty_bucket(s3_bucket)
    except Exception as e:
        print(e)
        status = cfnresponse.FAILED
        reason = f"Exception thrown: {e}"
    cfnresponse.send(event, context, status, responseData, reason=reason)