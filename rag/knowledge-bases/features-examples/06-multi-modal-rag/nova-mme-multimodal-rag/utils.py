"""
Utility functions for Amazon Bedrock Knowledge Bases with S3 Vectors
This module provides helper functions for creating and managing AWS resources
needed for multimodal knowledge bases.
"""

import uuid
import boto3
import json
from botocore.exceptions import ClientError

# Initialize AWS clients
iam_client = boto3.client("iam")
sts_client = boto3.client('sts')
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
account_id = sts_client.get_caller_identity()['Account']


def generate_short_code():
    """
    Generate a short unique identifier for resource naming.
    
    Creates a 4-character unique code from a UUID to append to resource names,
    ensuring no conflicts with existing resources.
    
    Returns:
        str: A 4-character unique identifier
        
    Example:
        >>> generate_short_code()
        'a3f9'
    """
    # Create a random UUID
    random_uuid = uuid.uuid4()
    
    # Convert to string and take the first 4 characters
    short_code = str(random_uuid)[:4]
    
    return short_code


def create_s3_bucket(bucket_name, region=None):
    """
    Create an S3 bucket in the specified region.
    
    Handles region-specific bucket creation requirements, particularly for us-east-1
    which doesn't require a LocationConstraint.
    
    Args:
        bucket_name (str): Name of the bucket to create. Must be globally unique.
        region (str, optional): AWS region where the bucket will be created.
                               Defaults to 'us-east-1' if not specified.
        
    Returns:
        bool: True if bucket was created successfully, False otherwise
        
    Raises:
        ClientError: If bucket creation fails (e.g., name already exists)
        
    Example:
        >>> create_s3_bucket("my-product-catalog-bucket", "us-east-1")
        ✅ S3 bucket 'my-product-catalog-bucket' created successfully
        True
    """
    try:
        s3_client = boto3.client('s3', region_name=region if region else 'us-east-1')
        
        # For us-east-1, no LocationConstraint should be provided
        # Other regions require the LocationConstraint parameter
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


def empty_and_delete_bucket(bucket_name):
    """
    Empty and delete an S3 bucket, including all objects and versions.
    
    This function safely removes all contents from a bucket before deleting it:
    1. Deletes all current object versions
    2. Deletes all non-current object versions (if versioning is enabled)
    3. Deletes the empty bucket
    
    Args:
        bucket_name (str): Name of the bucket to empty and delete
        
    Returns:
        None
        
    Note:
        This operation cannot be undone. All data in the bucket will be permanently deleted.
        
    Example:
        >>> empty_and_delete_bucket("my-old-bucket")
        Bucket my-old-bucket has been emptied and deleted.
    """
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    
    print(f"Emptying bucket {bucket_name}...")
    
    # Step 1: Delete all current object versions
    bucket.objects.all().delete()
    
    # Step 2: Delete all object versions if versioning is enabled
    bucket_versioning = boto3.client('s3').get_bucket_versioning(Bucket=bucket_name)
    if 'Status' in bucket_versioning and bucket_versioning['Status'] == 'Enabled':
        bucket.object_versions.all().delete()
    
    # Step 3: Delete the empty bucket
    boto3.client('s3').delete_bucket(Bucket=bucket_name)
    print(f"✅ Bucket {bucket_name} has been emptied and deleted.")


def create_bedrock_execution_role(unique_id, region_name, bucket_name, multimodal_storage_bucket_name, vector_store_name, vector_index_name, account_id):
    """
    Create an IAM execution role for Amazon Bedrock Knowledge Base with required policies.
    
    This function creates a comprehensive IAM role that allows Bedrock Knowledge Base to:
    - Access foundation models for embedding and generation
    - Read/write data from/to S3 buckets
    - Write logs to CloudWatch Logs
    - Access S3 Vector Store for vector operations
    
    The role is created with the following policies:
    1. Foundation Model Policy: Access to embedding and generation models
    2. S3 Policy: Read/write access to the data source bucket
    3. CloudWatch Logs Policy: Write logs for monitoring and debugging
    4. S3 Vectors Policy: Full access to the vector store and index
    
    Args:
        unique_id (str): Unique identifier to append to role and policy names
        region_name (str): AWS region where resources are located
        bucket_name (str): Name of the S3 bucket containing source data
        multimodal_storage_bucket_name (str): Name of the S3 bucket for multimodal storage
        vector_store_name (str): Name of the S3 Vector Store bucket
        vector_index_name (str): Name of the vector index within the vector store
        account_id (str): AWS account ID
        
    Returns:
        dict: IAM role object containing role ARN and other metadata
        
    Example:
        >>> role = create_bedrock_execution_role(
        ...     "a3f9", 
        ...     "us-east-1", 
        ...     "my-data-bucket",
        ...     "my-multimodal-storage-bucket",
        ...     "my-vector-store",
        ...     "my-index",
        ...     "123456789012"
        ... )
        >>> print(role["Role"]["Arn"])
        arn:aws:iam::123456789012:role/kb_execution_role_s3_vector_a3f9
    """
    
    # Policy 1: Foundation Model Access
    # Allows the Knowledge Base to invoke embedding and generation models
    foundation_model_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockInvokeModelStatement",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": [
                    # Amazon Nova Multimodal Embeddings for encoding images/videos/text
                    f"arn:aws:bedrock:{region_name}::foundation-model/amazon.nova-2-multimodal-embeddings-v1:0",
                    # Async invoke resources
                    f"arn:aws:bedrock:{region_name}:{account_id}:async-invoke/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    }
                }
            },
            {
                "Sid": "BedrockGetAsyncInvokeStatement",
                "Effect": "Allow",
                "Action": [
                    "bedrock:GetAsyncInvoke"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{region_name}:{account_id}:async-invoke/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    }
                }
            },
            {
                "Sid": "MarketplaceOperationsFromBedrockFor3pModels",
                "Effect": "Allow",
                "Action": [
                    "aws-marketplace:Subscribe",
                    "aws-marketplace:ViewSubscriptions",
                    "aws-marketplace:Unsubscribe"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "aws:CalledViaLast": "bedrock.amazonaws.com"
                    }
                }
            }
        ]
    }

    # Policy 2: S3 Bucket Access
    # Allows reading source documents and writing multimodal storage outputs
    s3_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ListBucketStatement",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{multimodal_storage_bucket_name}"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": [
                            account_id
                        ]
                    }
                }
            },
            {
                "Sid": "S3GetObjectStatement",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{multimodal_storage_bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*",
                    f"arn:aws:s3:::{multimodal_storage_bucket_name}/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": [
                            account_id
                        ]
                    }
                }
            },
            {
                "Sid": "S3PutObjectStatement",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::{multimodal_storage_bucket_name}/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    }
                }
            },
            {
                "Sid": "S3DeleteObjectStatement",
                "Effect": "Allow",
                "Action": [
                    "s3:DeleteObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::{multimodal_storage_bucket_name}/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    }
                }
            }
        ]
    }

    # Policy 3: CloudWatch Logs Access
    # Enables logging for debugging and monitoring
    cw_log_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "CloudWatchLogsStatement",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams"
                ],
                "Resource": f"arn:aws:logs:{region_name}:{account_id}:log-group:/aws/bedrock/*",
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    }
                }
            }
        ]
    }

    # Policy 4: S3 Vector Store Access
    # Allows full access to the vector store for storing and querying embeddings
    s3_vector_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3VectorsPermissions",
                "Effect": "Allow",
                "Action": [
                    "s3vectors:GetIndex",
                    "s3vectors:QueryVectors",
                    "s3vectors:PutVectors",
                    "s3vectors:GetVectors",
                    "s3vectors:DeleteVectors"
                ],
                "Resource": f"arn:aws:s3vectors:{region_name}:{account_id}:bucket/{vector_store_name}/index/{vector_index_name}",
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    }
                }
            }
        ]
    }

    # Trust Policy: Allow Bedrock service to assume this role
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockAssumeRoleStatement",
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{region_name}:{account_id}:knowledge-base/*"
                    }
                }
            }
        ]
    }

    # Combine all policies into a list with metadata
    policies = [
        (f"foundation-model-policy_{unique_id}", foundation_model_policy_document, 'Policy for accessing foundation models'),
        (f"cloudwatch-logs-policy_{unique_id}", cw_log_policy_document, 'Policy for writing logs to CloudWatch Logs'),
        (f"s3-bucket_{unique_id}", s3_policy_document, 'Policy for S3 bucket access'),
        (f"s3vector_{unique_id}", s3_vector_policy, 'Policy for S3 Vector Store access')
    ]
    
    # Step 1: Create the IAM role
    print(f"Creating IAM role: kb_execution_role_s3_vector_{unique_id}")
    bedrock_kb_execution_role = iam_client.create_role(
        RoleName=f"kb_execution_role_s3_vector_{unique_id}",
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        Description='Amazon Bedrock Knowledge Base Execution Role for Multimodal RAG with S3 Vectors',
        MaxSessionDuration=3600
    )

    # Step 2: Create and attach each policy to the role
    print(f"Creating and attaching {len(policies)} policies...")
    for policy_name, policy_document, description in policies:
        # Create the policy
        policy = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document),
            Description=description,
        )
        
        # Attach the policy to the role
        iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=policy["Policy"]["Arn"]
        )
        print(f"  ✅ Attached policy: {policy_name}")

    print(f"✅ IAM role created successfully: {bedrock_kb_execution_role['Role']['RoleName']}")
    return bedrock_kb_execution_role