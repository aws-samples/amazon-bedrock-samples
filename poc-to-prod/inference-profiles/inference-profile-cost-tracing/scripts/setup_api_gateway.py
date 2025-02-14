import boto3
import os
import json
from scripts.utils import get_s3_file_content
from scripts import s3_bucket_name, s3_config_file
from scripts.upload_to_s3 import upload_file_to_s3

ROOT_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_PATH, "config")
CONFIG_JSON = os.path.join(CONFIG_PATH, "config.json")

def main():
    # Load configuration
    config = json.loads(get_s3_file_content(s3_bucket_name, s3_config_file))

    apigateway_client = boto3.client('apigateway', region_name=config['aws_region'])
    lambda_client = boto3.client('lambda', region_name=config['aws_region'])

    # Create a new private REST API
    api_response = apigateway_client.create_rest_api(
        name=config['api_name'],
        description='API Gateway for Bedrock invokation through Lambda Function',
        endpointConfiguration={
            'types': ['PRIVATE']
        }
    )

    api_id = api_response['id']

    # Save the API ID to config file
    config['api_id'] = api_id
    with open(CONFIG_JSON, "w") as outfile:
        json.dump(config, outfile)
    upload_file_to_s3(CONFIG_JSON, s3_bucket_name, "config")

    # Get the root resource ID
    resources = apigateway_client.get_resources(restApiId=api_id)
    root_id = [resource['id'] for resource in resources['items'] if resource['path'] == '/'][0]

    # Create a new resource under the root
    resource_response = apigateway_client.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='invoke',
    )

    resource_id = resource_response['id']

    # Create a POST method for the resource
    apigateway_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        authorizationType='NONE',
    )

    # Get Lambda function ARN
    lambda_response = lambda_client.get_function(FunctionName=config['lambda_function_name'])
    lambda_arn = lambda_response['Configuration']['FunctionArn']

    # Grant API Gateway permission to invoke Lambda
    try:
        lambda_client.add_permission(
            FunctionName=config['lambda_function_name'],
            StatementId='APIGatewayInvokePermission',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{config["aws_region"]}:{lambda_arn.split(":")[4]}:{api_id}/*/POST/invoke',
        )
    except lambda_client.exceptions.ResourceConflictException:
        # Permission already exists
        pass

    # Integrate the method with the Lambda function
    lambda_uri = f'arn:aws:apigateway:{config["aws_region"]}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'

    apigateway_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=lambda_uri,
    )

    # Create resource policy for the API Gateway
    resource_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "*",
                "Resource": "*"
            }
        ]
    }

    # Update API Gateway with resource policy
    apigateway_client.update_rest_api(
        restApiId=api_id,
        patchOperations=[
            {
                'op': 'replace',
                'path': '/policy',
                'value': json.dumps(resource_policy)
            }
        ]
    )

    # Deploy the API
    deployment_response = apigateway_client.create_deployment(
        restApiId=api_id,
        stageName=config['api_stage'],
    )

    with open(CONFIG_JSON, "w") as outfile:
        json.dump(config, outfile)
    upload_file_to_s3(CONFIG_JSON, s3_bucket_name, "config")
    print('Private API Gateway created:')
    print(f'API ID: {api_id}')
    print('To access this API, you must connect through the VPC Endpoint.')

if __name__ == "__main__":
    main()
