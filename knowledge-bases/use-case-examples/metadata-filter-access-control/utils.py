import re
import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

sts_client = boto3.client('sts')
cloudformation = boto3.client('cloudformation')
opensearch_client = boto3.client('opensearchserverless')



def create_base_infrastructure(solution_id):
    # Read the YAML template file
    with open('templates/1-base-infra.yaml', 'r') as f:
        template_body = f.read()

    # Define the stack parameters
    stack_parameters = [
        {
            'ParameterKey': 'SolutionId',
            'ParameterValue': solution_id
        }
    ]

    # Create the CloudFormation stack
    stack_name = "KB-E2E-Base-{}".format(solution_id)
    response = cloudformation.create_stack(
        StackName=stack_name,
        TemplateBody=template_body,
        Parameters=stack_parameters,
        Capabilities=['CAPABILITY_NAMED_IAM']  # Required if your template creates IAM resources
    )

    stack_id = response['StackId']
    print(f'Creating stack {stack_name} ({stack_id})')

    # Wait for the stack to be created
    waiter = cloudformation.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack_id)

    # Get the stack outputs
    stack_outputs = cloudformation.describe_stacks(StackName=stack_id)['Stacks'][0]['Outputs']

    # Extract the output values into variables
    user_pool_id = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'userpoolid'), None)
    user_pool_arn = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'userpoolarn'), None)
    cognito_arn = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'cognitoarn'), None)
    client_id = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'clientid'), None)
    client_secret = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'clientsecret'), None)
    dynamo_table = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'dynamotable'), None)
    s3_bucket = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 's3bucket'), None)
    lambda_function_arn = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'lambdafunctionarn'), None)
    collection_id = next((output['OutputValue'] for output in stack_outputs if output['OutputKey'] == 'OpenSearchCollectionId'), None)

    print('Stack outputs:')
    print(f'User Pool ID: {user_pool_id}')
    print(f'User Pool ARN: {user_pool_arn}')
    print(f'Cognito ARN: {cognito_arn}')
    print(f'Client ID: {client_id}')
    print(f'Client Secret: {client_secret}')
    print(f'DynamoDB Table: {dynamo_table}')
    print(f'S3 Bucket: {s3_bucket}')
    print(f'Lambda Arn: {lambda_function_arn}')
    print(f'OpenSearchCollectionId: {collection_id}')

    return user_pool_id, user_pool_arn, cognito_arn, client_id, client_secret, dynamo_table, s3_bucket, lambda_function_arn, collection_id


def create_kb_infrastructure(solution_id, s3_bucket, embeddingModelArn, indexName, region, account_id, collection_id):
    # Define the template parameters
    template_parameters = [
        {
            'ParameterKey': 'SolutionId',
            'ParameterValue': solution_id
        },
        {
            'ParameterKey': 'InputBucketName',
            'ParameterValue': s3_bucket
        },
        {
            'ParameterKey': 'EmbeddingModel',
            'ParameterValue': embeddingModelArn
        },
        {
            'ParameterKey': 'IndexName',
            'ParameterValue': indexName
        },
        {
            'ParameterKey': 'VectorFieldName',
            'ParameterValue': 'vector'
        },
        {
            'ParameterKey': 'MetaDataFieldName',
            'ParameterValue': 'text-metadata'
        },
        {
            'ParameterKey': 'TextFieldName',
            'ParameterValue': 'text'
        },
        {
            'ParameterKey': 'CollectionArn',
            'ParameterValue': "arn:aws:aoss:{}:{}:collection/{}".format(region, account_id, collection_id)
        }
    ]

    # Read the CloudFormation template from a file
    with open('templates/2-knowledgebase-infra.yaml', 'r') as template_file:
        template_body = template_file.read()

    # Create the CloudFormation stack
    stack_name = "KB-E2E-KB-{}".format(solution_id)
    response = cloudformation.create_stack(
        StackName=stack_name,
        TemplateBody=template_body,
        Parameters=template_parameters,
        Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND', 'CAPABILITY_NAMED_IAM']
    )

    stack_id = response['StackId']
    print(f'Stack creation initiated: {stack_id}')

    # Wait for the stack to be created
    waiter = cloudformation.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack_id)

    # Retrieve the stack outputs
    stack_description = cloudformation.describe_stacks(StackName=stack_id)['Stacks'][0]
    outputs = stack_description['Outputs']
    kb_id = next((output['OutputValue'] for output in outputs if output['OutputKey'] == 'KBID'), None)
    datasource_id = next((output['OutputValue'].split('|')[1] for output in outputs if output['OutputKey'] == 'DS'), None)

    # Print the output values
    for output in outputs:
        print(f"{output['OutputKey']}: {output['OutputValue']}")
    return kb_id, datasource_id


def updateDataAccessPolicy(solution_id):
    data_access_policy_name = "{}-kbcollection-access".format(solution_id)
    current_role_arn = sts_client.get_caller_identity()['Arn']
    response = opensearch_client.get_access_policy(
        name=data_access_policy_name,
        type='data'
    )
    policy_version = response["accessPolicyDetail"]["policyVersion"]
    existing_policy = response['accessPolicyDetail']['policy']
    updated_policy = existing_policy.copy()
    updated_policy[0]['Principal'].append(current_role_arn)
    updated_policy = str(updated_policy).replace("'", '"')

    response = opensearch_client.update_access_policy(
        description='dataAccessPolicy',
        name=data_access_policy_name,
        policy=updated_policy,
        policyVersion=policy_version,
        type='data'
    )
    print(response)

def createAOSSIndex(indexName, region, collection_id):
    # Set up AWS authentication
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    awsauth = AWSV4SignerAuth(credentials, region, service)

    # Define index settings and mappings
    index_settings = {
        "settings": {
            "index.knn": "true"
        },
        "mappings": {
            "properties": {
                "vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                     "method": {
                         "name": "hnsw",
                         "engine": "faiss",
                         "space_type": "innerproduct",
                         "parameters": {
                             "ef_construction": 512,
                             "m": 16
                         },
                     },
                 },
                "text": {
                    "type": "text"
                },
                "text-metadata": {
                    "type": "text"
                }
            }
        }
    }

    # Build the OpenSearch client
    host = f"{collection_id}.{region}.aoss.amazonaws.com"
    oss_client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )

    # Create index
    response = oss_client.indices.create(index=indexName, body=json.dumps(index_settings))
    print(response)
    
    
def replace_vars(file_path, user_pool_id, client_id, client_secret, kb_id, lambda_function_arn, dynamo_table):
    with open(file_path, 'r') as file:
        content = file.read()

    replacements = {
        "<<replace_pool_id>>": user_pool_id,
        "<<replace_app_client_id>>": client_id,
        "<<replace_app_client_secret>>": client_secret,
        "<<replace_kb_id>>": kb_id,
        "<<replace_lambda_function_arn>>": lambda_function_arn,
        "<<replace_dynamo_table_name>>": dynamo_table
    }

    for placeholder, value in replacements.items():
        content = re.sub(rf'{placeholder}', value, content)

    with open(file_path, 'w') as file:
        file.write(content)