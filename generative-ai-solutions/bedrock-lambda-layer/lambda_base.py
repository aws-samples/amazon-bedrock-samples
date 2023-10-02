import boto3
import base64
from botocore.exceptions import ClientError
from pathlib import Path
import logging
import json
import zipfile
import io

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


layer_arn = '<<arn from lambda layer>>' 
ROLE_arn = '<<role ARN>>'
REGION = 'us-west-2'
cur_dir = Path(__file__).parent.absolute()

lambda_client = boto3.client('lambda', region_name=REGION)

function_code ="""
import json
import boto3
import platform
import sys
import json

REGION = f'{REGION}'
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

"""
with open('lambda_function.py', 'w') as f:
  f.write(function_code)

# Create in-memory zip file 
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
  zip_file.write('lambda_function.py')
zip_buffer.seek(0)

# write function_code to a zip file
string_bytes = function_code.encode("ascii") 
base64_bytes = base64.b64encode(string_bytes) 

# with open(Path(cur_dir / 'function_code.zip'), 'wb') as f:
#     f.write(string_bytes)

def create_layer(region):
    lambda_client = boto3.client('lambda', region_name=region)
    try:
        response = lambda_client.publish_layer_version(
            LayerName='bedrock-1-28-57',
            Description='boto3 1.28.57 bedrock layer',
            Content={'ZipFile': open(Path(cur_dir / 'bedrock-1-28-57.zip'), 'rb').read()},
            CompatibleRuntimes=['python3.8','python3.9','python3.10','python3.11'],
            CompatibleArchitectures=['x86_64','arm64'],
            LicenseInfo='Apache-2.0'
        )
        logger.info(f"Created layer: {response}")
        response_body = json.loads(response['ResponseMetadata']['HTTPHeaders']['x-amzn-requestid'])
        return response['LayerVersionArn']
    except ClientError as e:
        logger.error(f"Error creating layer: {e}")

# aws lambda publish-layer-version --layer-name  my-layername  --zip-file fileb://my-layername.zip --compatible-runtimes "python3.7" "python3.8" "python3.9"

# created the functions
def create_functions(region, layer_arn):
    lambda_client = boto3.client('lambda', region_name=region)
    for version in [38, 39, 310, 311]:
        for arch in ['x86_64', 'arm64']:
            function_name = f'test-py{version}-{arch}'
            try:
                lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime=f'python{str(version)[0]+"."+str(version)[1:]}',
                    Role=ROLE_arn, 
                    Handler='lambda_function.lambda_handler',
                    # Code={'ZipFile': open(Path(cur_dir /'function_code.py'), 'rb').read()},
                    # Code={'ZipFile': open(Path(cur_dir /'function_code.zip'), 'rb').read()},
                    # Code={'ZipFile': open(Path(cur_dir /'lambda_function.py.zip'), 'rb').read()},
                    Code={'ZipFile': zip_buffer.read()},
                    # 'Code': {'ZipFile': open('./deploy.zip', 'rb').read()}
                    Architectures=[arch],
                    Layers=[layer_arn]
                )
                logger.info(f"Created function: {function_name}")
            except ClientError as e:
                logger.error(f"Error creating {function_name}: {e}")


def test_functions(region):
    for version in [38, 39, 310, 311]:
        for arch in ['x86_64', 'arm64']:
            function_name = f'test-py{version}-{arch}'
            response = lambda_client.invoke(FunctionName=function_name)
            if response['StatusCode'] != 200:
                logger.error(f"Error invoking {function_name}: {response}")
                break
            # response['Payload'].read()
            response_body = json.loads(response['Payload'].read()) # read the response

            if 'errorType' in response_body:
                logger.error(response_body['errorMessage'])
                logger.error(response_body['errorType'])
            else:
                for k,v in response_body.items():
                    logger.info(f"{k}: {v}")
                    print(f"{k}: {v}")
                print(f"{function_name} appears to have passed")

if __name__ == '__main__':
    # for r in ['us-west-2', 'us-east-1']:
    #     l_arn =create_functions(r)
    #     create_layer(r, l_arn)
    l_arn = create_layer('us-west-2')
    create_functions('us-west-2', l_arn)
    logger.info("Functions Created")
    test_functions()