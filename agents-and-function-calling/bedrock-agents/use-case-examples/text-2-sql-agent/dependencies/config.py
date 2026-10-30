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

# Resolve the Region before constructing clients, ARNs, or resource names.
from security_config import require_aws_region

session = boto3.session.Session()
region = require_aws_region(session.region_name)


def aws_client(service_name):
    """Create a regional AWS client through the configured session."""
    return session.client(service_name, region_name=region)


# getting boto3 clients for required AWS services
sts_client = aws_client('sts')
iam_client = aws_client('iam')
s3_client = aws_client('s3')
lambda_client = aws_client('lambda')
bedrock_agent_client = aws_client('bedrock-agent')
bedrock_agent_runtime_client = aws_client('bedrock-agent-runtime')
s3 = s3_client
glue = aws_client('glue')
athena = aws_client('athena')
sts = sts_client
account_id = sts_client.get_caller_identity()["Account"]

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
lambda_query_policy_name = f'{agent_name}-lambda-query-{suffix}'
glue_data_policy_name = f'{agent_name}-glue-data-{suffix}'
lambda_code_path = "lambda_function.py"
query_guard_path = "query_guard.py"
lambda_name = f'{agent_name}-{suffix}'
glue_database_name = 'thehistoryofbaseball'
glue_crawler_name = 'TheHistoryOfBaseball'
glue_role_name = f'{agent_name}-glue-role-{suffix}'
athena_workgroup_name = f'{agent_name}-workgroup-{suffix}'
athena_bytes_scanned_cutoff = 100_000_000
query_timeout_seconds = 120
max_result_rows = 100
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