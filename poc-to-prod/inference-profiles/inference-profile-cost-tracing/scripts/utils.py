import boto3
import botocore
import subprocess
from botocore.exceptions import ClientError
import os



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


def get_current_username():
    """
    Get the current IAM username using boto3.

    Returns:
        str: The current IAM username or None if not an IAM user
    """
    try:
        sts_client = boto3.client('sts')
        caller_identity = sts_client.get_caller_identity()

        # Get the ARN from the response
        arn = caller_identity['Arn']

        # Check if this is an IAM user (ARN contains "user/")
        if ':user/' in arn:
            # Extract username from ARN (format: arn:aws:iam::account-id:user/username)
            username = arn.split(':user/')[1]
            return username
        else:
            # This might be a role or another identity type, not a user
            print("Current identity is not an IAM user.")
            return None

    except botocore.exceptions.ClientError as e:
        print(f"Error getting caller identity: {e}")
        return None


def ensure_api_gateway_permissions():
    """
    Ensures the current user has AmazonAPIGatewayAdministrator permissions
    via group membership rather than direct policy attachment
    """
    try:
        # Get current user identity
        sts_client = boto3.client('sts')
        caller_identity = sts_client.get_caller_identity()
        current_user_arn = caller_identity['Arn']

        # Extract username from ARN (format: arn:aws:iam::ACCOUNT_ID:user/USERNAME)
        username = current_user_arn.split('/')[-1]

        iam_client = boto3.client('iam')

        # Define group name and required policy
        group_name = "APIGatewayAdministrators"
        api_gateway_admin_arn = 'arn:aws:iam::aws:policy/AmazonAPIGatewayAdministrator'

        # Check if group exists, create if it doesn't
        try:
            iam_client.get_group(GroupName=group_name)
            print(f"Group {group_name} already exists")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"Creating group: {group_name}")
            iam_client.create_group(GroupName=group_name)

        # Check if policy is attached to the group
        attached_policies = iam_client.list_attached_group_policies(GroupName=group_name)
        existing_policies = [p['PolicyArn'] for p in attached_policies.get('AttachedPolicies', [])]

        # Attach policy to group if needed
        if api_gateway_admin_arn not in existing_policies:
            print(f"Attaching policy {api_gateway_admin_arn} to group {group_name}")
            iam_client.attach_group_policy(
                GroupName=group_name,
                PolicyArn=api_gateway_admin_arn
            )

        # Check if user is in the group
        user_groups = iam_client.list_groups_for_user(UserName=username)
        user_group_names = [g['GroupName'] for g in user_groups.get('Groups', [])]

        # Add user to group if needed
        if group_name not in user_group_names:
            print(f"Adding user {username} to group {group_name}")
            iam_client.add_user_to_group(
                GroupName=group_name,
                UserName=username
            )
            print("Added user to group. Note: It may take a few moments for permissions to propagate.")
            added_to_group = True
        else:
            print(f"User {username} is already in group {group_name}")
            added_to_group = False

        # Verify permissions have propagated
        if added_to_group or api_gateway_admin_arn not in existing_policies:
            print("Verifying permissions have propagated...")
            if verify_api_gateway_permissions():
                print("✓ Permission verification successful. You now have API Gateway Administrator access.")
            else:
                print("! Permissions verification failed or timed out.")
                return False
        else:
            print("No permission changes were made, user already had required permissions.")

        return True
    except Exception as e:
        print(f"Error ensuring API Gateway permissions: {str(e)}")
        print("Please ensure you have IAM permissions to manage groups and policies.")
        return False


def verify_api_gateway_permissions():
    """
    Verifies that API Gateway permissions have propagated by attempting to list API Gateways.
    Retries several times with increasing delays to account for permission propagation delay.
    """
    import time

    # Define retry parameters
    max_attempts = 5
    base_delay = 2  # seconds

    api_client = boto3.client('apigateway')

    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Verification attempt {attempt}/{max_attempts}...")
            # Try to list API Gateways - this will fail if permissions haven't propagated
            api_client.get_rest_apis(limit=1)
            print(f"Successfully listed API Gateways on attempt {attempt}")
            return True
        except Exception as e:
            if "AccessDenied" in str(e) or "not authorized" in str(e).lower():
                if attempt < max_attempts:
                    delay = base_delay * attempt
                    print(f"Permissions not yet propagated. Waiting {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Maximum verification attempts reached. Permissions may still be propagating.")
            else:
                print(f"Unexpected error during verification: {str(e)}")
                return False

    return False
