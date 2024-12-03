import os
import json
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

def create_s3_bucket(bucket_name, region=None):
    try:
        s3_client = boto3.client('s3')
        
        # If region is not specified, use the default region of the AWS client
        if region is None:
            region = boto3.session.Session().region_name or 'us-east-1'
            
        # Configure bucket creation based on region
        if region == 'us-east-1':
            bucket_response = s3_client.create_bucket(
                Bucket=bucket_name
            )
        else:
            bucket_response = s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': region
                }
            )
                
        print(f"Successfully created bucket '{bucket_name}' in region '{region}'")
        print(f"Bucket ARN: arn:aws:s3:::{bucket_name}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"Bucket '{bucket_name}' already exists in your account")
        elif error_code == 'BucketAlreadyExists':
            print(f"Bucket '{bucket_name}' already exists in another account")
        elif error_code == 'InvalidBucketName':
            print(f"Invalid bucket name: {bucket_name}")
        else:
            print(f"Error creating bucket: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

def upload_training_data_to_s3(bucket_name, local_file_path, prefix="training-data", account_id=None):
    try:
        # Get AWS account ID if not provided
        if not account_id:
            sts = boto3.client('sts')
            account_id = sts.get_caller_identity()['Account']
        
        # Get file name from path
        file_name = os.path.basename(local_file_path)
        
        # Construct S3 key with prefix
        # Remove leading/trailing slashes from prefix and combine with filename
        prefix = prefix.strip('/')
        s3_key = f"{prefix}/{file_name}" if prefix else file_name
        
        # Initialize S3 client
        s3 = boto3.client('s3')
        
        print(f"Uploading {file_name} to bucket {bucket_name} with prefix {prefix}...")
        
        # Upload file
        s3.upload_file(
            local_file_path,
            bucket_name,
            s3_key
        )
        
        print(f"Successfully uploaded {file_name} to S3 bucket!")
        
        # Return the S3 URI for the uploaded file
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        print(f"File S3 URI: {s3_uri}")
        return s3_uri
        
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return None

def delete_s3_bucket_and_contents(bucket_name):
    try:
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket_name)
        
        # Delete all object versions
        print(f"Deleting all objects and versions from bucket '{bucket_name}'...")
        bucket.object_versions.all().delete()
        
        # Delete all objects
        print(f"Deleting any remaining objects from bucket '{bucket_name}'...")
        bucket.objects.all().delete()
        
        # Delete the bucket
        print(f"Deleting bucket '{bucket_name}'...")
        bucket.delete()
        
        print(f"Successfully deleted bucket '{bucket_name}' and all its contents")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"Bucket '{bucket_name}' does not exist")
        else:
            print(f"Error deleting bucket: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False
    
def delete_distillation_buckets(bucket):
    # Get current AWS account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
        
    print("Deleting input bucket...")
    message = delete_s3_bucket_and_contents(bucket)
    
    if message:
        print(f"\nBucket ({bucket}) has been deleted successfully!")
        return True
    else:
        print("\nThere were some issues deleting the buckets.")
        return False
    
def create_model_distillation_role_and_permissions(bucket_name, unique_id=None, account_id=None, prefix=None):
    # Initialize IAM client
    iam = boto3.client('iam')
    
    # Get AWS account ID
    if not account_id:
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
    
    if not unique_id:
        unique_id = str(datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
        role_name = f'custom_model_distilation_role_{unique_id}'
        
    # Define the trust policy (assume role policy)
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Define the permission policy
    permission_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                        f"arn:aws:s3:::{bucket_name}/*",
                        f"arn:aws:s3:::{bucket_name}"
                    ],
                "Condition": {
                    "StringEquals": {
                        "aws:PrincipalAccount": account_id
                    }
                }
            }
        ]
    }
    
    try:
        # Create IAM role
        print("Creating IAM role...")
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for Amazon Bedrock model distillation'
        )
        
        # Create IAM policy
        print("Creating IAM policy...")
        policy_response = iam.create_policy(
            PolicyName=f'custom_model_distilation_policy_{unique_id}',
            PolicyDocument=json.dumps(permission_policy),
            Description='Policy for Amazon Bedrock model distillation'
        )
        
        # Attach the policy to the role
        print("Attaching policy to role...")
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_response['Policy']['Arn']
        )
        
        print("Successfully created role and policy!")
        return role_response['Role']['RoleName'], role_response['Role']['Arn']
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def delete_role_and_attached_policies(role_name):
    try:
        iam = boto3.client('iam')
        
        # List all attached policies
        print(f"Retrieving attached policies for role '{role_name}'...")
        attached_policies = iam.list_attached_role_policies(RoleName=role_name)
        
        # Detach and delete each policy
        for policy in attached_policies['AttachedPolicies']:
            policy_arn = policy['PolicyArn']
            policy_name = policy['PolicyName']
            
            print(f"Detaching policy '{policy_name}' from role...")
            try:
                iam.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise e
            
            print(f"Deleting policy '{policy_name}'...")
            try:
                iam.delete_policy(PolicyArn=policy_arn)
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise e
        
        # Delete the role
        print(f"Deleting role '{role_name}'...")
        try:
            iam.delete_role(RoleName=role_name)
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                raise e
        
        print(f"Successfully deleted role '{role_name}' and its attached policies!")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"Role '{role_name}' does not exist")
        else:
            print(f"Error: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False