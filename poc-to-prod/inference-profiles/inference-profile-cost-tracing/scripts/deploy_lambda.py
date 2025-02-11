import boto3
import zipfile
import io
import json
import os
from scripts.utils import get_s3_file_content, deploy_layer
from scripts import s3_bucket_name, s3_config_file


ROOT_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
LAMBDA_PATH = os.path.join(ROOT_PATH, "lambda_function")

config = json.loads(get_s3_file_content(s3_bucket_name, s3_config_file))


def package_lambda_function(lambda_directory):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(lambda_directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=lambda_directory)
                    zip_file.write(file_path, arcname)
    zip_buffer.seek(0)
    return zip_buffer.read()


def main():
    print("####################SUBPROCESS: DEPLOY LAMBDA LAYER####################")
    _, lambda_arn= deploy_layer(config['aws_region'])

    lambda_client = boto3.client('lambda', region_name=config['aws_region'])
    # Package Lambda function
    zip_file_bytes = package_lambda_function(LAMBDA_PATH)

    try:
        # Try to create the Lambda function
        response = lambda_client.create_function(
            FunctionName=config['lambda_function_name'],
            Runtime='python3.12',
            Role=config['lambda_role_arn'],
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_file_bytes},
            Timeout=300,
            MemorySize=128,
            Publish=False,
            Layers=[lambda_arn]
        )
        print('Lambda function created:', response['FunctionArn'])
    except lambda_client.exceptions.ResourceConflictException:
        # If function already exists, update it
        response = lambda_client.update_function_code(
            FunctionName=config['lambda_function_name'],
            ZipFile=zip_file_bytes,
            Publish=False
        )
        print('Lambda function updated:', response['FunctionArn'])


if __name__ == '__main__':
    main()