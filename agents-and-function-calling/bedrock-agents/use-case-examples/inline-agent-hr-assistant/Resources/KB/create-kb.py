import botocore
import os
import time
import boto3
import logging
from knowledge_base import BedrockKnowledgeBase

# Setup logging
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_clients(region="us-east-1"):
    """Initialize AWS clients"""
    return {
        's3': boto3.client('s3', region_name=region),
        'sts': boto3.client('sts', region_name=region),
        'bedrock_agent': boto3.client('bedrock-agent', region_name=region)
    }

def generate_suffix():
    """Generate timestamp-based suffix"""
    current_time = time.time()
    return time.strftime("%Y%m%d%H%M%S", time.localtime(current_time))[-7:]

def create_knowledge_base(kb_name, kb_description, suffix):
    """Create a knowledge base"""
    bucket_name = f'{kb_name}-{suffix}'
    knowledge_base_metadata = BedrockKnowledgeBase(
        kb_name=f'{kb_name}-{suffix}',
        kb_description=kb_description,
        data_bucket_name=bucket_name,
        chunking_strategy="FIXED_SIZE",
        suffix=suffix
    )
    return knowledge_base_metadata, bucket_name

def upload_directory(path, bucket_name, s3_client):
    """Upload directory contents to S3"""
    for root, dirs, files in os.walk(path):
        for file in files:
            if not file.startswith('.DS_Store'):
                file_to_upload = os.path.join(root, file)
                logger.info(f"uploading file {file_to_upload} to {bucket_name}")
                s3_client.upload_file(file_to_upload, bucket_name, file)

def setup_knowledge_base(
    kb_name='inline-agent-kb',
    kb_description="This knowledge base stores data about companies HR policy",
    docs_path="policydocs",
    region=""
):
    """Main function to setup knowledge base"""
    clients = initialize_clients(region)
    suffix = generate_suffix()
    
    # Create knowledge base
    logger.info("Creating knowledge base...")
    kb_metadata, bucket_name = create_knowledge_base(kb_name, kb_description, suffix)
    kb_id = kb_metadata.get_knowledge_base_id()
    data_source_id = kb_metadata.get_data_source_id()
    
    # Upload documents
    logger.info("Uploading documents to S3...")
    upload_directory(docs_path, bucket_name, clients['s3'])
    
    # Wait for KB to be available and start ingestion
    logger.info("Waiting for knowledge base to be available...")
    time.sleep(30)
    
    # Start ingestion job
    logger.info("Starting ingestion job...")
    kb_metadata.start_ingestion_job()
    time.sleep(30)
    
    logger.info(f"Knowledge base setup complete. KB ID: {kb_id}")
    return {
        'knowledge_base_id': kb_id,
        'bucket_name': bucket_name,
        'kb_metadata': kb_metadata,
        'data_source_id': data_source_id
    }