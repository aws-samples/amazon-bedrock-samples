import os
import logging
import time
import sys
from typing import Dict, Tuple
import boto3
import json
import argparse

# Add Resources directory to Python path
RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(RESOURCES_DIR)

# Configure logging
logging.basicConfig(
    format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Create AWS resources')
    parser.add_argument('--account-id', type=str, required=True, help='AWS Account ID')
    parser.add_argument('--region', type=str, required=True, help='AWS Region')  # Add this line
    return parser.parse_args()

def create_lambda_resources(
    account_id: str = '',
    region: str = '',
    lambda_info_file: str = os.path.join(RESOURCES_DIR, "ActionGroups", "lambda_functions_info.json")
) -> Dict:
    """Create Lambda functions and save their information."""
    try:
        # Try different import approaches
        try:
            from ActionGroups.create_action_group import create_all_lambda_functions
        except ImportError:
            logger.error("Could not import create_action_group module")
            raise
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(lambda_info_file), exist_ok=True)
        
        logger.info("Starting Lambda functions creation...")
        lambda_functions = create_all_lambda_functions(
            region=region,
            account_id=account_id,
            output_file=lambda_info_file
        )
        logger.info("Successfully created Lambda functions")
        return lambda_functions
    except Exception as e:
        logger.error(f"Error creating Lambda resources: {str(e)}")
        raise

def create_knowledge_base(region) -> Tuple[str, str]:
    """Create Knowledge Base and upload documents."""
    try:
        # Import here to avoid circular imports
        sys.path.append(os.path.join(RESOURCES_DIR, "KB"))
        from KB.knowledge_base import BedrockKnowledgeBase
                
        # Initialize clients
        s3_client = boto3.client('s3', region_name=region)
        
        # Get the current timestamp
        timestamp_str = time.strftime("%m%d%H", time.localtime())
        
        knowledge_base_name = f'inline-agent-kb-{timestamp_str}'
        knowledge_base_description = "This knowledge base stores data about companies HR policy"
        bucket_name = f'{knowledge_base_name}-{timestamp_str}'
        
        logger.info("Creating Knowledge Base...")
        knowledge_base_metadata = BedrockKnowledgeBase(
            kb_name=knowledge_base_name,
            kb_description=knowledge_base_description,
            data_bucket_name=bucket_name,
            chunking_strategy="FIXED_SIZE",
            suffix=timestamp_str
        )
        
        kb_id = knowledge_base_metadata.get_knowledge_base_id()
        logger.info(f"Created Knowledge Base with ID: {kb_id}")

        data_source_id = knowledge_base_metadata.get_data_source_id()
        logger.info(f"Created data source ID: {data_source_id}")
        
        # Get policy docs path
        policy_docs_path = os.path.join(RESOURCES_DIR, "KB", "policydocs")
        logger.info(f"Looking for policy documents in: {policy_docs_path}")
        
        # Wait for bucket to be fully created
        time.sleep(60)
        
        # Upload files
        logger.info(f"Starting upload from {policy_docs_path} to S3 bucket {bucket_name}")
        
        for root, dirs, files in os.walk(policy_docs_path):
            for file in files:
                if not file.startswith('.DS_Store'):
                    file_path = os.path.join(root, file)
                    try:
                        s3_client.upload_file(
                            file_path,
                            bucket_name,
                            f"data/{file}"
                        )
                        logger.info(f"Successfully uploaded {file_path}")
                    except Exception as upload_error:
                        logger.error(f"Failed to upload {file_path}: {str(upload_error)}")
        
        logger.info("Completed uploading files to S3")
        
        # Wait for KB to be available and start ingestion
        logger.info("Waiting for Knowledge Base to be available...")
        time.sleep(60)
        
        logger.info("Starting ingestion job...")
        knowledge_base_metadata.start_ingestion_job()
        time.sleep(30)
        
        logger.info("Successfully created Knowledge Base and started ingestion")
        return kb_id, data_source_id, bucket_name
        
    except Exception as e:
        logger.error(f"Error creating Knowledge Base: {str(e)}")
        raise

def create_all_resources(
    account_id: str,
    region: str = "us-east-1"
) -> Dict:
    """Create all required resources for the application."""
    try:
        resources = {}
        
        # Create Lambda functions
        logger.info("Creating Lambda functions...")
        lambda_resources = create_lambda_resources(
            region=region,
            account_id=account_id
        )
        resources['lambda'] = lambda_resources
        logger.info(f"Lambda resources created: {len(lambda_resources)} functions")
        
        # Create Knowledge Base
        logger.info("Creating Knowledge Base...")
        kb_id, data_source_id, bucket_name = create_knowledge_base(region=region)
        resources['knowledge_base'] = {
            'kb_id': kb_id,
            'data_source_id': data_source_id,
            'bucket_name': bucket_name
        }
        logger.info(f"Knowledge base created with ID: {kb_id}")
        
        # Save resources information to a file in the current directory
        output_file = "resources_info.json"
        logger.info(f"Attempting to save resources info to: {output_file}")
        
        try:
            with open(output_file, 'w') as f:
                json.dump(resources, f, indent=2, default=str)
            logger.info(f"Successfully saved resources information to {output_file}")
            
            # Verify file was created and contains data
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    saved_content = json.load(f)
                logger.info(f"Verified file contents: {json.dumps(saved_content, indent=2)}")
            else:
                logger.error(f"File was not created: {output_file}")
        except Exception as file_error:
            logger.error(f"Error saving resources file: {str(file_error)}")
            raise
        
        return resources
        
    except Exception as e:
        logger.error(f"Error creating resources: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Error creating resources: {str(e)}")
        raise

if __name__ == "__main__":
    args = parse_arguments()
    
    # Set your AWS configuration
    REGION = args.region
    ACCOUNT_ID = args.account_id

    print(REGION, ACCOUNT_ID)
    
    # Create all resources
    resources = create_all_resources(ACCOUNT_ID, REGION)
    
    # Print summary
    print("\nResources Created:")
    print("=================")
    print(f"Lambda Functions: {len(resources['lambda'])} functions created")
    print(f"Knowledge Base ID: {resources['knowledge_base']['kb_id']}")
    print(f"S3 Bucket: {resources['knowledge_base']['bucket_name']}")
    
    # Verify resources_info.json
    resources_file = "resources_info.json"
    if os.path.exists(resources_file):
        print(f"\nResources file created successfully at: {resources_file}")
        with open(resources_file, 'r') as f:
            saved_resources = json.load(f)
        print("Contents:")
        print(json.dumps(saved_resources, indent=2))
    else:
        print(f"\nWARNING: Resources file was not created at: {resources_file}")