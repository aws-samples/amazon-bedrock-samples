import json
import boto3
from botocore.exceptions import ClientError
import os

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


def profile_lookup(payload_tags):
    bucket_name = 'inference-cost-tracing'
    cost_file = 'config/config.json'
    config = json.loads(get_s3_file_content(bucket_name, cost_file))
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
    if not inference_profile_id:
        tags_for_lookup = headers.get('tags', {})
        if not tags_for_lookup:
            inference_profile_id = None
        else:
            inference_profile_id = profile_lookup(tags_for_lookup)

    bucket_name = 'inference-cost-tracing'
    cost_file = 'config/models.json'
    cost = get_s3_file_content(bucket_name, cost_file)
    message = event.get('body', [])  # extract the input data from the request body
    if not message:
        raise Exception("No message")

    bedrock_client = boto3.client('bedrock', region_name=region)
    inference_client = boto3.client("bedrock-runtime", region_name=region)
    cloudwatch = boto3.client('cloudwatch', region_name=region)
    cost_mapping = json.loads(cost)
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
        model_id = event['model_id']
        response = inference_client.converse(
            modelId=model_id,
            messages=message
        )
        # Return successful response
        return {
            'statusCode': 200,
            'body': json.dumps(response['output'])
        }
