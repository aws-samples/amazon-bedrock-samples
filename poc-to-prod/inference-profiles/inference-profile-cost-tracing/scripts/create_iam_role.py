import boto3
import json
import botocore.exceptions
import os
from scripts.deploy_lambda import config
from scripts.utils import get_s3_file_content
from scripts.upload_to_s3 import upload_file_to_s3
from scripts import s3_bucket_name, s3_config_file



# Initialize the IAM client
iam_client = boto3.client('iam')

ROOT_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_PATH, "config")
CONFIG_JSON = os.path.join(CONFIG_PATH, "config.json")

# List of managed policies to attach to the role
MANAGED_POLICIES = [
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/AWSLambda_FullAccess",
    "arn:aws:iam::aws:policy/CloudWatchFullAccess"
]

def delete_iam_role_if_exists(role_name):
    try:
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in attached_policies['AttachedPolicies']:
            iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
            print(f"Detached managed policy: {policy['PolicyName']}")

        iam_client.delete_role(RoleName=role_name)
        print(f"Deleted existing IAM role: {role_name}")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"IAM role {role_name} does not exist, proceeding to create it.")
        else:
            raise

def create_iam_role(role_name):
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # Delete the existing role if it exists
    delete_iam_role_if_exists(role_name)

    # Create the IAM role
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy),
        Description="IAM Role for Lambda Cost Inference Execution"
    )
    role_arn = response['Role']['Arn']
    print(f"Created IAM role: {role_name} with ARN: {role_arn}")

    # Attach managed policies to the role
    for policy_arn in MANAGED_POLICIES:
        iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        print(f"Attached policy {policy_arn} to role {role_name}.")

    return role_arn

def update_json_with_arn(role_arn, _config):
    _config['lambda_role_arn'] = role_arn
    with open(CONFIG_JSON, "w") as outfile:
        json.dump(config, outfile)
    upload_file_to_s3(CONFIG_JSON, 'inference-cost-tracing', "config")
    print(f"Updated {config} with Lambda Role ARN.")


def main():
    role_name = "LambdaCostInferenceInvocationRole"
    role_arn = create_iam_role(role_name)
    config_ = json.loads(get_s3_file_content(s3_bucket_name, s3_config_file))
    update_json_with_arn(role_arn, config_)

if __name__ == "__main__":
    main()