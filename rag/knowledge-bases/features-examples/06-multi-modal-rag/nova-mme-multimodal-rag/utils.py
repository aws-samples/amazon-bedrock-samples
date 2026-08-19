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


    """
    Download images from Amazon Berkeley Objects S3 bucket.
    
    Downloads one or more product images from the public ABO dataset bucket.
    Supports concurrent downloads for better performance with multiple images.
    
    Args:
        image_ids (str or list): Single image ID (str) or list of image IDs to download
        output_dir (str, optional): Directory where images will be saved. 
                                   Defaults to "downloaded_images"
        max_workers (int, optional): Maximum number of concurrent downloads. 
                                    Defaults to 5
        bucket_name (str, optional): S3 bucket name. 
                                    Defaults to "amazon-berkeley-objects"
        subfolder (str, optional): Image size subfolder in S3. 
                                  Options: "small", "medium", "large", "original"
                                  Defaults to "small"
    
    Returns:
        tuple: (successful_downloads, failed_downloads) - counts of each
        
    Raises:
        ValueError: If image_ids is empty or invalid type
        
    Example:
        >>> # Download a single image
        >>> download_abo_images("6d00d6b4")
        ✅ Successfully downloaded 6d00d6b4.jpg
        (1, 0)
        
        >>> # Download multiple images concurrently
        >>> image_list = ["6d00d6b4", "6d00dc87", "6d00e3f2"]
        >>> success, failed = download_abo_images(image_list, output_dir="my_images")
        ✅ Download complete: 3 successful, 0 failed
        (3, 0)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    
    # Validate and normalize input
    if isinstance(image_ids, str):
        image_ids = [image_ids]
    elif not isinstance(image_ids, list):
        raise ValueError("image_ids must be a string or list of strings")
    
    if not image_ids:
        raise ValueError("image_ids cannot be empty")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Initialize S3 client (no credentials needed for public bucket)
    s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='UNSIGNED'))
    
    def _download_single_image(image_id):
        """Internal helper function to download a single image"""
        # Construct the S3 key based on the ABO dataset structure
        s3_key = f"images/{subfolder}/{image_id}.jpg"
        local_path = output_path / f"{image_id}.jpg"
        
        try:
            s3_client.download_file(bucket_name, s3_key, str(local_path))
            print(f"✅ Successfully downloaded {image_id}.jpg")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            print(f"❌ Failed to download {image_id}.jpg: {error_code}")
            return False
        except Exception as e:
            print(f"❌ Failed to download {image_id}.jpg: {str(e)}")
            return False
    
    # Download images
    successful_downloads = 0
    failed_downloads = 0
    
    if len(image_ids) == 1:
        # Single image - no need for threading
        success = _download_single_image(image_ids[0])
        successful_downloads = 1 if success else 0
        failed_downloads = 0 if success else 1
    else:
        # Multiple images - use concurrent downloads
        print(f"Downloading {len(image_ids)} images with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_id = {
                executor.submit(_download_single_image, image_id): image_id 
                for image_id in image_ids
            }
            
            # Process completed downloads
            for future in as_completed(future_to_id):
                image_id = future_to_id[future]
                try:
                    success = future.result()
                    if success:
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                except Exception as e:
                    print(f"❌ Exception occurred for {image_id}: {str(e)}")
                    failed_downloads += 1
        
        print(f"✅ Download complete: {successful_downloads} successful, {failed_downloads} failed")
    
    return successful_downloads, failed_download

def download_abo_images(image_ids, output_dir="downloaded_images", max_workers=5, bucket_name="amazon-berkeley-objects", subfolder="small"):
    """
    Download images from Amazon Berkeley Objects S3 bucket.
    
    Downloads one or more product images from the public ABO dataset bucket.
    Supports concurrent downloads for better performance with multiple images.
    
    Args:
        image_ids (str or list): Single image ID (str) or list of image IDs to download
        output_dir (str, optional): Directory where images will be saved. 
                                   Defaults to "downloaded_images"
        max_workers (int, optional): Maximum number of concurrent downloads. 
                                    Defaults to 5
        bucket_name (str, optional): S3 bucket name. 
                                    Defaults to "amazon-berkeley-objects"
        subfolder (str, optional): Image size subfolder in S3. 
                                  Options: "small", "medium", "large", "original"
                                  Defaults to "small"
    
    Returns:
        tuple: (successful_downloads, failed_downloads, not_found_count) - counts of each
        
    Example:
        >>> download_abo_images("6d00d6b4")
        ✅ Successfully downloaded 6d00d6b4.jpg
        (1, 0, 0)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pathlib import Path
    from botocore.config import Config
    from botocore import UNSIGNED
    
    # Validate and normalize input
    if isinstance(image_ids, str):
        image_ids = [image_ids]
    elif not isinstance(image_ids, list):
        raise ValueError("image_ids must be a string or list of strings")
    
    if not image_ids:
        raise ValueError("image_ids cannot be empty")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Initialize S3 client (no credentials needed for public bucket)
    s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    
    def _download_single_image(image_id):
        """Internal helper function to download a single image"""
        # Extract first 2 characters for partitioning folder
        partition = image_id[:2]
        
        # Construct the S3 key with partition: images/small/6d/6d0f65cf.jpg
        s3_key = f"images/{subfolder}/{partition}/{image_id}.jpg"
        local_path = output_path / f"{image_id}.jpg"
        
        try:
            s3_client.download_file(bucket_name, s3_key, str(local_path))
            print(f"✅ Successfully downloaded {image_id}.jpg")
            return 'success'
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404' or error_code == 'NoSuchKey':
                print(f"⚠️  Image not found: {image_id}.jpg (skipped)")
                return 'not_found'
            else:
                print(f"❌ Failed to download {image_id}.jpg: {error_code}")
                return 'failed'
        except Exception as e:
            print(f"❌ Failed to download {image_id}.jpg: {str(e)}")
            return 'failed'
    
    # Download images
    successful_downloads = 0
    failed_downloads = 0
    not_found_count = 0
    
    if len(image_ids) == 1:
        # Single image - no need for threading
        result = _download_single_image(image_ids[0])
        if result == 'success':
            successful_downloads = 1
        elif result == 'not_found':
            not_found_count = 1
        else:
            failed_downloads = 1
    else:
        # Multiple images - use concurrent downloads
        print(f"Downloading {len(image_ids)} images with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_id = {
                executor.submit(_download_single_image, image_id): image_id 
                for image_id in image_ids
            }
            
            # Process completed downloads
            for future in as_completed(future_to_id):
                image_id = future_to_id[future]
                try:
                    result = future.result()
                    if result == 'success':
                        successful_downloads += 1
                    elif result == 'not_found':
                        not_found_count += 1
                    else:
                        failed_downloads += 1
                except Exception as e:
                    print(f"❌ Exception occurred for {image_id}: {str(e)}")
                    failed_downloads += 1
        
        print(f"✅ Download complete: {successful_downloads} successful, {not_found_count} not found, {failed_downloads} failed")
    
    return successful_downloads, failed_downloads, not_found_count

def download_abo_images_from_file(file_path, output_dir="downloaded_images", max_workers=5):
    """
    Download ABO images from a list in a text file.
    
    Reads image IDs from a text file (one ID per line) and downloads them
    from the Amazon Berkeley Objects S3 bucket.
    
    Args:
        file_path (str): Path to text file containing image IDs (one per line)
        output_dir (str, optional): Directory where images will be saved.
                                   Defaults to "downloaded_images"
        max_workers (int, optional): Maximum number of concurrent downloads.
                                    Defaults to 5
    
    Returns:
        tuple: (successful_downloads, failed_downloads) - counts of each
        
    Example:
        >>> # Create a file with image IDs
        >>> with open("image_list.txt", "w") as f:
        ...     f.write("6d00d6b4\\n6d00dc87\\n6d00e3f2\\n")
        
        >>> # Download all images from the file
        >>> download_abo_images_from_file("image_list.txt", output_dir="products")
        Found 3 image IDs in image_list.txt
        ✅ Download complete: 3 successful, 0 failed
        (3, 0)
    """
    try:
        with open(file_path, 'r') as f:
            image_ids = [line.strip() for line in f if line.strip()]
        
        if not image_ids:
            print(f"⚠️  No image IDs found in {file_path}")
            return 0, 0
        
        print(f"Found {len(image_ids)} image IDs in {file_path}")
        return download_abo_images(image_ids, output_dir, max_workers)
    
    except FileNotFoundError:
        print(f"❌ File {file_path} not found")
        return 0, 0
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {str(e)}")
        return 0, 0

def download_product_catalog_data(image_list_file="file_list.txt", max_workers=5):
    """
    Download complete product catalog data including ABO images, videos, and test image.
    
    This function downloads:
    1. Product images from ABO dataset (from file_list.txt) → product-catalog/
    2. Two demonstration videos → product-catalog/
    3. A test phone image → test-image/
    
    Args:
        image_list_file (str, optional): Path to text file containing ABO image IDs.
                                        Defaults to "file_list.txt"
        max_workers (int, optional): Maximum concurrent downloads for images.
                                    Defaults to 5
    
    Returns:
        dict: Summary of downloads with counts and status
    """
    import urllib.request
    from pathlib import Path
    
    print("📦 Downloading Product Catalog Data")
    print("=" * 50)
    
    summary = {
        'images': {'success': 0, 'failed': 0},
        'videos': 0,
        'test_image': 0,
        'status': 'complete'
    }
    
    # Create directories
    catalog_dir = Path("product-catalog")
    test_dir = Path("test-image")
    catalog_dir.mkdir(exist_ok=True)
    test_dir.mkdir(exist_ok=True)
    
    # 1. Download ABO images from file_list.txt
    print("\n📸 Step 1: Downloading ABO product images...")
    print("-" * 50)
    try:
        success, failed = download_abo_images_from_file(
            image_list_file, 
            output_dir=str(catalog_dir),
            max_workers=max_workers
        )
        summary['images']['success'] = success
        summary['images']['failed'] = failed
        print(f"✅ Downloaded {success} images to product-catalog/")
        if failed > 0:
            print(f"⚠️  {failed} images failed to download")
    except Exception as e:
        print(f"❌ Error downloading images: {str(e)}")
        summary['status'] = 'partial'
    
    # 2. Download videos
    print("\n🎥 Step 2: Downloading demonstration videos...")
    print("-" * 50)
    videos = [
        ("https://d2908q01vomqb2.cloudfront.net/artifacts/DBSBlogs/ML-20078/ML-20078-video-1.mp4", "cellphone-1.mp4"),
        ("https://d2908q01vomqb2.cloudfront.net/artifacts/DBSBlogs/ML-20078/ML-20078-video-2.mp4", "cellphone-2.mp4")
    ]
    
    for url, filename in videos:
        try:
            output_path = catalog_dir / filename
            print(f"Downloading {filename}...")
            urllib.request.urlretrieve(url, output_path)
            print(f"✅ Downloaded {filename} to product-catalog/")
            summary['videos'] += 1
        except Exception as e:
            print(f"❌ Failed to download {filename}: {str(e)}")
            summary['status'] = 'partial'
    
    # 3. Download test image
    print("\n🖼️  Step 3: Downloading test image...")
    print("-" * 50)
    try:
        test_image_url = "https://d2908q01vomqb2.cloudfront.net/artifacts/DBSBlogs/ML-20078/phone.png"
        test_image_path = test_dir / "phone.png"
        print(f"Downloading phone.png...")
        urllib.request.urlretrieve(test_image_url, test_image_path)
        print(f"✅ Downloaded phone.png to test-image/")
        summary['test_image'] = 1
    except Exception as e:
        print(f"❌ Failed to download test image: {str(e)}")
        summary['status'] = 'partial'
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Download Summary")
    print("=" * 50)
    print(f"Product Images:  {summary['images']['success']} successful, {summary['images']['failed']} failed")
    print(f"Videos:          {summary['videos']} downloaded")
    print(f"Test Image:      {summary['test_image']} downloaded")
    print(f"Status:          {summary['status'].upper()}")
    print("=" * 50)
    
    return summary