import json
import logging
import os
import pprint
import random
import time
import uuid
import zipfile
from io import BytesIO

import boto3

# setting logger
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# getting boto3 clients for required AWS services
sts_client = boto3.client("sts")
iam_client = boto3.client("iam")
s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")
aoss_client = boto3.client("opensearchserverless")
bedrock_agent_client = boto3.client("bedrock-agent")
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime")
s3 = boto3.client("s3")


session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
region, account_id


# assign variables
suffix = f"{region}-{account_id}"
agent_name = "fashion-agent"
agent_alias_name = "workshop-alias"
bucket_name = f"{agent_name}-{suffix}"
bucket_key = f"{agent_name}-schema.json"
schema_name = "FashionAgent_Schema.json"
schema_arn = f"arn:aws:s3:::{bucket_name}/{bucket_key}"
bedrock_agent_bedrock_allow_policy_name = f"{agent_name}-allow-{suffix}"
bedrock_agent_s3_allow_policy_name = f"{agent_name}-s3-allow-{suffix}"
lambda_role_name = f"{agent_name}-lambda-role-{suffix}"
agent_role_name = f"AmazonBedrockExecutionRoleForAgents_{suffix}"
lambda_code_path = "lambda_function.py"
lambda_name = f"{agent_name}-{suffix}"
s3_loc = "s3://" + bucket_name + "/" + bucket_key
s3_bucket = bucket_name
foundation_Model = "anthropic.claude-3-sonnet-20240229-v1:0"
idleSessionTTLInSeconds = 3600

# embedding size for Opensearch ingested data
# output vector size – one of 1024 (default), 384, 256
embeddingSize = 1024

# OSS setup
collection_name = "fashion-image-collection"
index_name = "images-index"
# Note: collection_id will be added by running the create_OSS_vectorstore.ipynb notebook
