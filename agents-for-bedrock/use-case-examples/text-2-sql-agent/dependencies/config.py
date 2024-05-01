import logging
import boto3
import random
import time
import zipfile
from io import BytesIO
import json
import uuid
import pprint
import os





# setting logger
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# getting boto3 clients for required AWS services
sts_client = boto3.client('sts')
iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
s3 = boto3.client('s3')
glue = boto3.client('glue')
athena = boto3.client('athena')
sts = boto3.client('sts')
iam_client = boto3.client('iam')



session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
region, account_id

# assign variables
suffix = f"{region}-{account_id}"
agent_name = "text-2-sql-agent"
agent_alias_name = "workshop-alias"
bucket_name = f'{agent_name}-{suffix}'
bucket_key = f'{agent_name}-schema.json'
schema_name = 'text_to_sql_openapi_schema.json'
schema_arn = f'arn:aws:s3:::{bucket_name}/{bucket_key}'
bedrock_agent_bedrock_allow_policy_name = f"{agent_name}-allow-{suffix}"
bedrock_agent_s3_allow_policy_name = f"{agent_name}-s3-allow-{suffix}"
lambda_role_name = f'{agent_name}-lambda-role-{suffix}'
agent_role_name = f'AmazonBedrockExecutionRoleForAgents_{suffix}'
lambda_code_path = "lambda_function.py"
lambda_name = f'{agent_name}-{suffix}'
glue_database_name = 'thehistoryofbaseball'
glue_crawler_name = 'TheHistoryOfBaseball'
glue_role_name="AWSGlueServiceRole"
athena_result_loc = "s3://" + bucket_name + "/athena_result/" 
s3_loc = "s3://" + bucket_name + "/" + bucket_key
s3_bucket=bucket_name
db_loc = "s3://" + s3_bucket + "/db/"
athena_result_loc = "s3://" + s3_bucket + "/athena_result/" 
#foundation_Model='anthropic.claude-v2:1'
foundation_Model='anthropic.claude-3-sonnet-20240229-v1:0'
idleSessionTTLInSeconds=3600
#print(db_loc)
#glue_crawler_name='TheHistoryOfBaseball'

zip_data = "./data/TheHistoryofBaseball.zip"
ext_data = "./data/extracted/"

s3_prefix = "data"
s3_path = "s3://" + s3_bucket + "/" +s3_prefix
s3_target = s3_path + "/TheHistoryofBaseball/"

print(glue_crawler_name)