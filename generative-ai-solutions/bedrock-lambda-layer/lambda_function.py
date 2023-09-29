import boto3
import platform
import sys

REGION = 'us-east-1'
bedrock = boto3.client(
    service_name='bedrock',
    region_name=REGION, 
    endpoint_url=f'https://bedrock.{REGION}.amazonaws.com'
)

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=REGION, 
    endpoint_url=f'https://bedrock.{REGION}.amazonaws.com'
)

def lambda_handler(event, context):
    return {
            'first_model_bedrock': bedrock.list_foundation_models()['modelSummaries'][0]['modelId'],
            '58_methods': len(bedrock_runtime.__dir__()),
            'region': REGION,
            'python': str(sys.version),
            'boto3': boto3.__version__,
            'arch': platform.processor()}