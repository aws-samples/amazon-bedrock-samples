import boto3
import subprocess
from botocore.exceptions import ClientError
import os

os.environ['AWS_PROFILE'] = 'cost-tracing'


def deploy_layer(region):
    # Get the directory of this script and determine the parent directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(script_dir, ".."))  # One level above

    # Paths for the lambda layer
    layer_dir = os.path.join(parent_dir, "lambda-layer")
    python_dir = os.path.join(layer_dir, "python")
    layer_zip = os.path.join(parent_dir, "layer.zip")  # ZIP file also in the parent directory
    layer_name = "my-boto3-cip-layer"

    # 1. Create lambda-layer/python directories
    os.makedirs(python_dir, exist_ok=True)
    print(f"Created directories: {layer_dir}, {python_dir}")

    # 2. Install boto3==1.35.73 into lambda-layer/python
    print("Installing boto3==1.35.73 into lambda-layer/python ...")
    subprocess.run([
        "pip", "install", "boto3==1.35.73",
        "--target", python_dir
    ], check=True)

    # 3. Zip up the python folder
    print(f"Zipping {python_dir} into {layer_zip} ...")
    if os.path.exists(layer_zip):
        os.remove(layer_zip)  # remove old zip if exists

    # We zip *everything* inside `lambda-layer` (i.e., the `python` folder).
    subprocess.run([
        "zip", "-r", layer_zip,
        os.path.basename(python_dir)
    ], cwd=layer_dir, check=True)
    print(f"{layer_zip} created successfully.")

    # 4. Publish the Lambda layer using Boto3
    lambda_client = boto3.client("lambda", region_name=region)

    # Read the zip file contents
    with open(os.path.join(layer_dir, layer_zip), "rb") as f:
        zip_content = f.read()

    print("Publishing new Lambda layer version...")
    response = lambda_client.publish_layer_version(
        LayerName=layer_name,
        Content={"ZipFile": zip_content},
        CompatibleRuntimes=["python3.12", "python3.13"],  # adjust as needed
        Description="A custom layer containing Boto3 1.35.73"
    )

    # 5. Parse out the LayerVersionArn from the response
    layer_arn = response["LayerVersionArn"]
    print(f"Successfully published layer. ARN: {layer_arn}")
    return layer_name, layer_arn



def get_s3_file_content(bucket_name, object_key):
    """
    Retrieve the content of a file from an S3 bucket.

    Args:
    bucket_name (str): The name of the S3 bucket.
    object_key (str): The key of the object in the S3 bucket.
    profile_name (str): The AWS profile name to use. Defaults to 'cost-tracing'.

    Returns:
    str: The content of the file.

    Raises:
    Exception: If there's an error retrieving the file.
    """
    try:
        # Create an S3 client
        s3 = boto3.client('s3')

        # Get the object
        response = s3.get_object(Bucket=bucket_name, Key=object_key)

        # Read the file content
        file_content = response['Body'].read().decode('utf-8')

        return file_content

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise Exception(f"The object {object_key} does not exist in bucket {bucket_name}")
        elif e.response['Error']['Code'] == 'NoSuchBucket':
            raise Exception(f"The bucket {bucket_name} does not exist")
        else:
            raise Exception(f"An error occurred: {e}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")
