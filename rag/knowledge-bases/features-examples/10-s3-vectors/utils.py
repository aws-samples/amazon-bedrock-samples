import uuid
import boto3
import json
from botocore.exceptions import ClientError

iam_client = boto3.client("iam")
sts_client = boto3.client('sts')
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
account_id = sts_client.get_caller_identity()['Account']

def create_s3_bucket(bucket_name, region=None):
    """
    Create an S3 bucket
    
    Args:
        bucket_name: Name of the bucket to create
        region: AWS region where the bucket will be created
        
    Returns:
        bool: True if bucket was created, False otherwise
    """
    try:
        s3_client = boto3.client('s3', region_name=region if region else 'us-east-1')
        
        # For us-east-1, no LocationConstraint should be provided
        if region is None or region == 'us-east-1':
            response = s3_client.create_bucket(Bucket=bucket_name)
        else:
            response = s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': region
                }
            )
            
        print(f"✅ S3 bucket '{bucket_name}' created successfully")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
        print(f"❌ Error creating bucket '{bucket_name}': {error_code} - {error_message}")
        return False

def generate_short_code():
    # Create a random UUID
    random_uuid = uuid.uuid4()
    
    # Convert to string and take the first 4 characters
    short_code = str(random_uuid)[:4]
    
    return short_code

def empty_and_delete_bucket(bucket_name):
    """
    Empty and delete an S3 bucket, including all objects and versions
    """
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    
    # Delete all objects
    bucket.objects.all().delete()
    
    # Delete all object versions if versioning is enabled
    bucket_versioning = boto3.client('s3').get_bucket_versioning(Bucket=bucket_name)
    if 'Status' in bucket_versioning and bucket_versioning['Status'] == 'Enabled':
        bucket.object_versions.all().delete()
    
    # Now delete the empty bucket
    boto3.client('s3').delete_bucket(Bucket=bucket_name)
    print(f"Bucket {bucket_name} has been emptied and deleted.")

def create_bedrock_execution_role(unique_id, region_name, bucket_name, vector_store_name,vector_index_name, account_id):
        """
        Create Knowledge Base Execution IAM Role and its required policies.
        If role and/or policies already exist, retrieve them
        Returns:
            IAM role
        """

        foundation_model_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:{region_name}::foundation-model/amazon.titan-embed-text-v2:0",
                        f"arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                        f"arn:aws:bedrock:{region_name}::foundation-model/cohere.rerank-v3-5:0"             
                    ]
                }
            ]
        }

        s3_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket",
                            "s3:PutObject",
                            "s3:DeleteObject"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{bucket_name}",
                            f"arn:aws:s3:::{bucket_name}/*"
                        ]
                    }
                ]
            }

        cw_log_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ],
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock/invokemodel:*"
                }
            ]
        }

        s3_vector_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3vectors:*"
                    ],
                    "Resource": f"arn:aws:s3vectors:{region_name}:{account_id}:bucket/{vector_store_name}/index/{vector_index_name}"
                }
            ]
        }

        assume_role_policy_document = {
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

        # combine all policies into one list from policy documents
        policies = [
            (f"foundation-model-policy_{unique_id}", foundation_model_policy_document, 'Policy for accessing foundation model'),
            (f"cloudwatch-logs-policy_{unique_id}", cw_log_policy_document, 'Policy for writing logs to CloudWatch Logs'),
            (f"s3-bucket_{unique_id}", s3_policy_document, 'Policy for s3 buckets'),
            (f"s3vector_{unique_id}", s3_vector_policy, 'Policy for s3 Vector')]
        
            
        # create bedrock execution role
        bedrock_kb_execution_role = iam_client.create_role(
            RoleName=f"kb_execution_role_s3_vector_{unique_id}",
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
            Description='Amazon Bedrock Knowledge Base Execution Role',
            MaxSessionDuration=3600
        )

        # create and attach the policies to the bedrock execution role
        for policy_name, policy_document, description in policies:
            policy = iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
                Description=description,
            )
            iam_client.attach_role_policy(
                RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
                PolicyArn=policy["Policy"]["Arn"]
            )

        return bedrock_kb_execution_role