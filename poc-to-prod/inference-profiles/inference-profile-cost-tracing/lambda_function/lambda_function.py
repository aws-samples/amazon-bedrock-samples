import json
import boto3
from botocore.exceptions import ClientError
import os

import boto3
import re
from datetime import datetime

# Global variables to store the cached data
CONFIG_MAPPING = None
COST_MAPPING = None
CACHE_FILE = "/tmp/config.json"
CACHE_TIMESTAMP_FILE = "/tmp/config_timestamp.txt"
COST_CACHE_FILE = "/tmp/config.json"
COST_CACHE_TIMESTAMP_FILE = "/tmp/cost_timestamp.txt"
CACHE_TTL = 3600  # Cache TTL in seconds (1 hour)

def should_refresh_cache(timestamp_file):
    """
    Check if the cache needs to be refreshed based on TTL
    """
    try:
        if not os.path.exists(timestamp_file):
            return True
            
        with open(timestamp_file, 'r') as f:
            timestamp = float(f.read().strip())
            
            
        # Check if cache has expired
        current_time = datetime.now().timestamp()
        return (current_time - timestamp) > CACHE_TTL
            
    except Exception:
        return True

def load_config_mapping():
    """
    Load cost mapping from cache or S3, updating cache if necessary
    """
    global CONFIG_MAPPING
    
    
    # If we have cached data and it's not expired, use it
    if CONFIG_MAPPING and not should_refresh_cache(CACHE_TIMESTAMP_FILE):
        return CONFIG_MAPPING
    
    try:
        # If cache exists but needs refresh, or first load
        bucket_name = find_latest_inference_cost_tracing_bucket()
        config_file = 'config/config.json'
        
        # Get fresh data from S3
        file_content = get_s3_file_content(bucket_name, config_file)
        
        # Save to tmp storage
        with open(CACHE_FILE, 'w') as f:
            f.write(file_content)
            
        # Update timestamp
        with open(CACHE_TIMESTAMP_FILE, 'w') as f:
            f.write(str(datetime.now().timestamp()))
            
        CONFIG_MAPPING = json.loads(file_content)
        return CONFIG_MAPPING
        
    except Exception as e:
        # If there's an error getting from S3, try to load from cache if it exists
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                CONFIG_MAPPING = json.loads(f.read())
            return CONFIG_MAPPING
        raise Exception(f"Failed to load config mapping: {str(e)}")

def load_cost_mapping():
    """
    Load cost mapping from cache or S3, updating cache if necessary
    """
    global COST_MAPPING
    
    
    # If we have cached data and it's not expired, use it
    if COST_MAPPING and not should_refresh_cache(COST_CACHE_TIMESTAMP_FILE):
        return COST_MAPPING
    
    try:
        # If cache exists but needs refresh, or first load
        bucket_name = find_latest_inference_cost_tracing_bucket()
        cost_file = 'config/models.json'
        
        # Get fresh data from S3
        file_content = get_s3_file_content(bucket_name, cost_file)
        
        # Save to tmp storage
        with open(COST_CACHE_FILE, 'w') as f:
            f.write(file_content)
            
        # Update timestamp
        with open(COST_CACHE_TIMESTAMP_FILE, 'w') as f:
            f.write(str(datetime.now().timestamp()))
            
        COST_MAPPING = json.loads(file_content)
        return COST_MAPPING
        
    except Exception as e:
        # If there's an error getting from S3, try to load from cache if it exists
        if os.path.exists(COST_CACHE_FILE):
            with open(COST_CACHE_FILE, 'r') as f:
                COST_MAPPING = json.loads(f.read())
            return COST_MAPPING
        raise Exception(f"Failed to load cost mapping: {str(e)}")


def find_latest_inference_cost_tracing_bucket():
    """
    Searches for S3 buckets that start with 'inference-cost-tracing-' followed by a UUID-like string
    and returns the most recently created one.

    Returns:
        str or None: The name of the latest matching bucket, or None if no match is found
    """
    # Initialize S3 client
    s3_client = boto3.client('s3')

    try:
        # Get all buckets
        response = s3_client.list_buckets()

        # Define the pattern to match
        prefix = "inference-cost-tracing-"

        # UUID pattern (roughly)
        _pattern = r'^inference-cost-tracing'

        matching_buckets = []

        # Check each bucket and store matching ones with their creation dates
        for bucket in response['Buckets']:
            bucket_name = bucket['Name']
            creation_date = bucket['CreationDate']

            # Check if bucket name matches our pattern
            if bucket_name.startswith(prefix) and re.match(_pattern, bucket_name):
                matching_buckets.append({
                    'name': bucket_name,
                    'creation_date': creation_date
                })

        if not matching_buckets:
            print("No matching buckets found")
            return None

        # Sort buckets by creation date (newest first)
        sorted_buckets = sorted(
            matching_buckets,
            key=lambda x: x['creation_date'],
            reverse=True
        )

        latest_bucket = sorted_buckets[0]['name']
        return latest_bucket

    except Exception as e:
        print(f"Error searching for bucket: {str(e)}")
        return None


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


def has_matching_keys(original_list, comparison_list):
    """
    Check if all dictionaries in comparison_list have the same key-value elements as original_list.

    Parameters:
    - original_list (list of dict): The reference list of dictionaries.
    - comparison_list (list of dict): The list to compare against the original list.

    Returns:
    - bool: True if all dictionaries in comparison_list match original_list, False otherwise.
    """
    pairs = zip(original_list, comparison_list)
    return any(x != y for x, y in pairs)


def profile_lookup(config,payload_tags):
    bucket_name = find_latest_inference_cost_tracing_bucket()
    for profile in config['profiles']:
        if has_matching_keys(profile['tags'], payload_tags):
            for _id in config['profile_ids']:
                if profile['name'] == list(_id.keys()).pop():
                    return _id[profile['name']]


def lambda_handler(event, context):

    headers = event.get('headers', {}) # extract headers from the API Gateway call
    if not headers:
        raise Exception("No message")

    inference_profile_id = headers.get('inference-profile-id', None)
    region = headers.get('region', None)

    config = load_config_mapping()
    model_id = config['default_model_id']

    if not inference_profile_id:
        tags_for_lookup = headers.get('tags', {})
        if not tags_for_lookup:
            inference_profile_id = None
        else:
            inference_profile_id = profile_lookup(config, tags_for_lookup)

    cost_mapping = load_cost_mapping()

    message = event.get('body', [])  # extract the input data from the request body
    if not message:
        raise Exception("No message")

    bedrock_client = boto3.client('bedrock', region_name=region)
    inference_client = boto3.client("bedrock-runtime", region_name=region)
    cloudwatch = boto3.client('cloudwatch', region_name=region)
  
    region_cost_mapping = cost_mapping[region]
    if inference_profile_id:
        # Get model ID from the inference profile tags
        inference_profile = bedrock_client.get_inference_profile(
            inferenceProfileIdentifier=inference_profile_id
        )
        profile_name = inference_profile.get('inferenceProfileName', '')
        profile_arn = inference_profile.get('inferenceProfileArn', '')
        try:
            model_arn = inference_profile.get('models', [])
            model_id_tag = model_arn[0].get('modelArn', []).split('/')[-1]
        except:
            raise Exception(f"ModelName tag not found in Inference Profile '{profile_name}'.")

        try:
            tags_list = bedrock_client.list_tags_for_resource(resourceARN=profile_arn).get('tags', [])
            tags = {d['key']: d['value'] for d in tags_list}

            model_token_cost = region_cost_mapping['text'].get(model_id_tag, {})

            model_id = model_id_tag  # Use the ModelName tag value as model ID

            # Invoke the model using invoke_model
            response = inference_client.converse(
                modelId=model_id,
                messages=message
            )
            # Read the AI response
            result = response['output']
            input_token_cost = model_token_cost['input_cost'] * (response['usage']['inputTokens'] / 1000000)
            output_token_cost = model_token_cost['output_cost'] * (response['usage']['outputTokens'] / 1000000)

            # Publish counts to CloudWatch
            cloudwatch.put_metric_data(
                Namespace='BedrockInvocationTracing',
                MetricData=[
                    ### invocation data
                    {
                        'MetricName': 'InputTokens',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': response['usage']['inputTokens'],
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'OutputTokens',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': response['usage']['outputTokens'],
                        'Unit': 'Count'
                    },
                    #### cost
                    {
                        'MetricName': 'InputTokensCost',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': input_token_cost,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'OutputTokensCost',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': output_token_cost,
                        'Unit': 'Count'
                    },
                    ####
                    {
                        'MetricName': 'InvocationSuccess',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    ### Inference Profile data
                    {
                        'MetricName': tags['ModelName'],
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': tags['TenantID'],
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': tags['CreatedBy'],
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': tags['ModelProvider'],
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': tags['CustomerAccountID'],
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': tags['Environment'],
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': tags['ApplicationID'],
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    #####
                ]
            )
            # Return successful response
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        except Exception as e:
            error_message = str(e)
            status_code = 500
            # Set token counts to zero on error
            input_token_count = 0
            output_token_count = 0
            print(error_message)
            # Publish failure metric and token counts to CloudWatch
            cloudwatch.put_metric_data(
                Namespace='BedrockInvocationTracing',
                MetricData=[
                    {
                        'MetricName': 'InvocationFailure',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'InputTokens',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': input_token_count,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'OutputTokens',
                        'Dimensions': [
                            {'Name': 'InferenceProfile', 'Value': profile_name},
                        ],
                        'Value': output_token_count,
                        'Unit': 'Count'
                    },
                ]
            )

            # If error return error response
            return {
                'statusCode': status_code,
                'body': json.dumps({'error': error_message})
            }
    else:
            
        response = inference_client.converse(
            modelId=model_id,
            messages=message
        )
        # Return successful response
        return {
            'statusCode': 200,
            'body': json.dumps(response['output'])
        }
