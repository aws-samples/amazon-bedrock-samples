import botocore
import os
import time
import boto3
import logging
import pprint
import json
from knowledge_base import BedrockKnowledgeBase
from generate_policy import create_kb_documents
from botocore.exceptions import ClientError

region = "us-east-1"
s3_client = boto3.client('s3', region_name=region)
sts_client = boto3.client('sts', region_name=region)
bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=region)

logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def create_knowledge_base(region, bucket_name, kb_name, data_path):
    # create policy docs
    print("Generating sythetic HR policies")
    data_path = os.path.join(os.getcwd(), 'policy_documents')
    create_kb_documents(data_path)
    time.sleep(10)
    
    # KB process
    current_time = time.time()
    timestamp_str = time.strftime("%Y%m%d%H%M%S", time.localtime(current_time))[-7:]
    suffix = f"{timestamp_str}"
    
    knowledge_base_description = "This knowledge base stores data about companies HR policy"
    foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

    print("creating kb")
    knowledge_base_metadata = BedrockKnowledgeBase(
        kb_name=f'{kb_name}-{suffix}',
        kb_description=knowledge_base_description,
        data_bucket_name=bucket_name, 
        chunking_strategy="FIXED_SIZE", 
        suffix=suffix
    )
    kb_id_metadata = knowledge_base_metadata.get_knowledge_base_id()
    
    print("uploading docs to S3")
    def upload_file(file_name, bucket, object_name=None):
        if object_name is None:
            object_name = os.path.basename(file_name)
        try:
            response = s3_client.upload_file(file_name, bucket, 'data/'+object_name)
            print(f"Successfully uploaded {file_name} to {bucket}/{object_name}")
            return True
        except ClientError as e:
            logging.error(e)
            return False

    for root, dirs, files in os.walk(data_path):
        for file in files:
            if not file.startswith('.DS_Store'):
                file_path = os.path.join(root, file)
                print(file_path, bucket_name)
                if not upload_file(file_path, bucket_name):
                    print(f"Failed to upload {file_path}")

    time.sleep(60)
    print("starting ingestion job")
    knowledge_base_metadata.start_ingestion_job()
    time.sleep(30)
    
    return kb_id_metadata, bucket_name, knowledge_base_metadata