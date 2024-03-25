# to create IAM role for Bedrock fine-tuning
import json
import boto3

import pandas as pd
from botocore.exceptions import ClientError

iam = boto3.client('iam')
s3 = boto3.client('s3')
sts = boto3.client('sts')

def get_aws_account_id():
    return sts.get_caller_identity()['Account']

def check_if_bucket_exists(bucket_name):
  try:
    s3.head_bucket(Bucket=bucket_name)
    print("Bucket %s exists" % bucket_name)
    return True
  except ClientError as e:
    print(f"client error: {e}")
    return False
  except s3.exceptions.NoSuchBucket:
    print("Bucket %s does not exist" % bucket_name)
    return False

def create_bucket(bucket_name, region):
    """
    Create a bucket in a specific region
    """
    if check_if_bucket_exists(bucket_name):
        return
    
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name, 
                CreateBucketConfiguration={
                    'LocationConstraint': region
                }
            )
    except Exception as e:
        print(e)

def check_if_role_exists(role_name):
    try:
        response = iam.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"Role {role_name} exists")
        return role_arn
    except iam.exceptions.NoSuchEntityException:
        print(f"Role {role_name} does not exist")
        return None


def create_bedrock_fine_tuning_role(role_name:str, bucket_name:str) -> str:
    """
    Create bedrock fine-tuning IAM role if it doesn't exist.
    """
    
    role_arn = check_if_role_exists(role_name)
    if role_arn:
        print(f"{role_name} exists, hence, no role creation.")
        return role_arn

    policy_doc = {
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
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ]
            }
        ]
    }

    response = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps({
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
        })
    )

    role_arn = response['Role']['Arn']

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="S3AccessPolicy",
        PolicyDocument=json.dumps(policy_doc)
    )
    return role_arn

# reading S3 data using boto3 instead of s3fs to avoid issue - https://github.com/pandas-dev/pandas/issues/54070
def read_s3_file_as_dataframe(s3_object_uri:str) -> pd.DataFrame:
    """
    Read a s3 file as a dataframe.
    """
    uri_path_elements = s3_object_uri.split("//")[1].split("/")
    bucket_name = uri_path_elements[0]
    key = "/".join(uri_path_elements[1:])

    s3_object = s3.get_object(
        Bucket=bucket_name,
        Key=key
    )
    df = pd.read_csv(s3_object['Body'])

    return df

def upload_data_to_s3(dataframe, folder, file_name, bucket_name, prefix):
    """
    Save the dataframe to file and upload it to target S3 location.
    """
    file = folder / file_name
    dataframe.to_json(file, orient="records", lines=True, index=False)
    object_key = f"{prefix}/data/{file_name}"
    s3.upload_file(file, bucket_name, object_key)
    return f"s3://{bucket_name}/{object_key}"
