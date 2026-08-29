import os
import sys
import time
import boto3
import logging
import pprint
import json
import zipfile
import io
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from botocore.client import Config

class LambdaManager:
    """
    A class to manage AWS Lambda functions for custom chunking strategies.
    """
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize the LambdaManager with AWS clients.
        
        Args:
            region: AWS region to use. If None, uses the default from session.
        """
        self.session = boto3.session.Session()
        self.region = region or self.session.region_name
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.iam_client = boto3.client('iam', region_name=self.region)
        self.sts_client = boto3.client('sts', region_name=self.region)
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
    
    def create_or_update_lambda(self, function_name: str, role_arn: str, source_file: str) -> str:
        """
        Create or update a Lambda function from a local Python file.
        
        Args:
            function_name: Name of the Lambda function
            role_arn: ARN of the IAM role for the Lambda function
            source_file: Path to the Lambda function source file
            
        Returns:
            The ARN of the Lambda function
        """
        # Read the Lambda function code
        try:
            with open(source_file, 'rb') as f:
                code_content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading Lambda source file {source_file}: {str(e)}")
            raise
        
        # Create a ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', code_content)
        
        zip_buffer.seek(0)
        zip_content = zip_buffer.read()
        
        # Check if the Lambda function already exists
        try:
            self.lambda_client.get_function(FunctionName=function_name)
            
            # Update the existing function
            self.logger.info(f"Updating existing Lambda function: {function_name}")
            response = self.lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
        except self.lambda_client.exceptions.ResourceNotFoundException:
            # Create a new function
            self.logger.info(f"Creating new Lambda function: {function_name}")
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={
                    'ZipFile': zip_content
                },
                Timeout=900, # 15 minutes
                MemorySize=1024
            )
        
        # Wait for the function to be active
        waiter = self.lambda_client.get_waiter('function_active')
        waiter.wait(FunctionName=function_name)
        
        return response['FunctionArn']
    
    def create_lambda_role(self, role_name: str) -> str:
        """
        Create an IAM role for the Lambda function with necessary permissions.
        
        Args:
            role_name: Name of the IAM role
            
        Returns:
            The ARN of the created role
        """
        # Define the trust policy for Lambda
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Create the role
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy)
            )
            role_arn = response['Role']['Arn']
            
            # Attach basic Lambda execution policy
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            # Attach S3 access policy
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
            )
            
            # Wait for the role to be available
            time.sleep(10)
            
            return role_arn
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            # If role already exists, get its ARN
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except Exception as e:
            self.logger.error(f"Error creating Lambda role {role_name}: {str(e)}")
            raise
    
    def update_lambda_timeout(self, function_name: str, timeout_seconds: int = 900) -> None:
        """
        Update the timeout configuration for a Lambda function.
        
        Args:
            function_name: Name of the Lambda function
            timeout_seconds: Timeout value in seconds (default: 900 seconds / 15 minutes)
        """
        try:
            response = self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Timeout=timeout_seconds
            )
            self.logger.info(f"Successfully updated Lambda timeout to {timeout_seconds} seconds for {function_name}")
        except Exception as e:
            self.logger.error(f"Error updating Lambda timeout for {function_name}: {str(e)}")
            raise
    
    def get_lambda_role(self, function_name: str) -> str:
        """
        Get the IAM role associated with a Lambda function.
        
        Args:
            function_name: Name of the Lambda function
            
        Returns:
            The name of the IAM role
        """
        try:
            response = self.lambda_client.get_function_configuration(
                FunctionName=function_name
            )
            role_arn = response['Role']
            role_name = role_arn.split('/')[-1]
            
            self.logger.info(f"Lambda Role ARN: {role_arn}")
            self.logger.info(f"Lambda Role Name: {role_name}")
            
            return role_name
        except Exception as e:
            self.logger.error(f"Error getting Lambda role for {function_name}: {str(e)}")
            raise
    
    def create_bedrock_policy(self, role_name: str) -> None:
        """
        Create and attach a policy for Bedrock access to a Lambda role.
        
        Args:
            role_name: Name of the IAM role
        """
        # Define the policy document for Bedrock access
        bedrock_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    "Resource": [
                        "*"
                    ]
                }
            ]
        }
        
        policy_name = 'BedrockClaudeAccess'
        
        try:
            # Create the policy
            try:
                response = self.iam_client.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(bedrock_policy)
                )
                policy_arn = response['Policy']['Arn']
                self.logger.info(f"Created policy {policy_name} with ARN: {policy_arn}")
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                # If policy already exists, get its ARN
                account_id = self.sts_client.get_caller_identity()['Account']
                policy_arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
                self.logger.info(f"Policy {policy_name} already exists with ARN: {policy_arn}")
            
            # Attach the policy to the role
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            self.logger.info(f"Successfully attached Bedrock policy to role {role_name}")
        except Exception as e:
            self.logger.error(f"Error creating or attaching Bedrock policy: {str(e)}")
            raise

class BedrockKnowledgeBaseManager:
    """
    A class to manage AWS Bedrock Knowledge Base operations including creation,
    data ingestion, and querying.
    """
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize the BedrockKnowledgeBaseManager with AWS clients and configuration.
        
        Args:
            region: AWS region to use. If None, uses the default from session.
        """
        # Configure logging
        logging.basicConfig(
            format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        
        # Set up AWS session and clients
        self.session = boto3.session.Session()
        self.region = region or self.session.region_name
        self.s3_client = boto3.client('s3')
        self.sts_client = boto3.client('sts')
        self.bedrock_agent_client = boto3.client('bedrock-agent')
        self.bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
        
        # Get account ID
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        
        # Add parent directory to path for imports
        self._setup_import_paths()
        
        # Import the BedrockKnowledgeBase class after path setup
        from knowledge_base import BedrockKnowledgeBase
        self.BedrockKnowledgeBase = BedrockKnowledgeBase
        
        # Generate timestamp suffix for resource naming
        self.timestamp_suffix = self._generate_timestamp_suffix()
        
        # Default foundation model
        self.foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"
        
        # Knowledge base instances
        self.kb_instances = {}
        
        # Lambda manager for custom chunking
        self.lambda_manager = LambdaManager(region)

    def _setup_import_paths(self) -> None:
        """Set up Python import paths to include parent directory."""
        current_path = Path().resolve().parent
        if str(current_path) not in sys.path:
            sys.path.append(str(current_path))
            
    def _generate_timestamp_suffix(self) -> str:
        """Generate a timestamp suffix for unique resource naming."""
        current_time = time.time()
        return time.strftime("%Y%m%d%H%M%S", time.localtime(current_time))[-7:]
    
    def _create_s3_bucket(self, bucket_name: str) -> None:
        """
        Create an S3 bucket if it doesn't exist.
        
        Args:
            bucket_name: Name of the bucket to create
        """
        try:
            self.s3_client.create_bucket(Bucket=bucket_name)
            self.logger.info(f"Created bucket: {bucket_name}")
        except self.s3_client.exceptions.BucketAlreadyExists:
            self.logger.info(f"Bucket already exists: {bucket_name}")
        except Exception as e:
            self.logger.error(f"Error creating bucket {bucket_name}: {e}")
            raise
    
    def setup_custom_chunking_lambda(self, lambda_name: str) -> str:
        """
        Set up the Lambda function for custom chunking.
        
        Args:
            lambda_name: Base name for the Lambda function
            
        Returns:
            The name of the created Lambda function
        """
        # Create a unique name for the Lambda function
        function_name = f"{lambda_name}-{self.timestamp_suffix}"
        
        # Create IAM role for the Lambda function
        role_name = f"{function_name}-role"
        role_arn = self.lambda_manager.create_lambda_role(role_name)
        
        # Create or update the Lambda function
        lambda_source_file = "lambda_custom_chunking_function.py"
        self.lambda_manager.create_or_update_lambda(function_name, role_arn, lambda_source_file)
        
        # Configure the Lambda function
        self.lambda_manager.update_lambda_timeout(function_name)
        
        # Attach Bedrock policy to the role
        self.lambda_manager.create_bedrock_policy(role_name)
        
        return function_name
    
    def create_knowledge_base(self, 
                             kb_name: str,
                             kb_description: str,
                             chunking_strategy: str = "FIXED_SIZE",
                             suffix_override: Optional[str] = None,
                             lambda_function_name: Optional[str] = None,
                             intermediate_bucket_name: Optional[str] = None) -> str:
        """
        Create a knowledge base with the specified configuration.
        
        Args:
            kb_name: Base name for the knowledge base
            kb_description: Description of the knowledge base
            chunking_strategy: Strategy for chunking documents (FIXED_SIZE or CUSTOM)
            suffix_override: Optional override for the timestamp suffix
            lambda_function_name: Name of the Lambda function for custom chunking
            intermediate_bucket_name: Name of the intermediate S3 bucket for custom chunking
            
        Returns:
            The knowledge base ID
        """
        suffix = suffix_override or self.timestamp_suffix
        full_kb_name = f"{kb_name}-{suffix}"
        bucket_name = full_kb_name
        
        # Create S3 bucket for the knowledge base
        self._create_s3_bucket(bucket_name)
        
        # Define data sources
        data_source = [{"type": "S3", "bucket_name": bucket_name}]
        
        # Create the knowledge base instance based on chunking strategy
        if chunking_strategy == "CUSTOM":
            # If intermediate bucket name is not provided, create one
            if not intermediate_bucket_name:
                intermediate_bucket_name = f"{full_kb_name}-intermediate"
            
            # Create the intermediate bucket
            self._create_s3_bucket(intermediate_bucket_name)
            
            # If lambda function name is not provided, create one
            if not lambda_function_name:
                lambda_function_name = self.setup_custom_chunking_lambda(f"{kb_name}-lambda")
            
            kb_instance = self.BedrockKnowledgeBase(
                kb_name=full_kb_name,
                kb_description=kb_description,
                data_sources=data_source,
                lambda_function_name=lambda_function_name,
                intermediate_bucket_name=intermediate_bucket_name,
                chunking_strategy=chunking_strategy,
                suffix=f"{suffix}-c"
            )
        else:
            kb_instance = self.BedrockKnowledgeBase(
                kb_name=full_kb_name,
                kb_description=kb_description,
                data_sources=data_source,
                chunking_strategy=chunking_strategy,
                suffix=f"{suffix}-f"
            )
        
        # Store the instance for later use
        self.kb_instances[full_kb_name] = kb_instance
        
        return kb_instance.get_knowledge_base_id()
    
    def upload_directory_to_s3(self, local_path: str, bucket_name: str, 
                              skip_files: List[str] = ["LICENSE", "NOTICE", "README.md"]) -> None:
        """
        Upload all files from a local directory to an S3 bucket.
        
        Args:
            local_path: Path to the local directory
            bucket_name: Name of the target S3 bucket
            skip_files: List of filenames to skip
        """
        for root, _, files in os.walk(local_path):
            for file in files:
                file_to_upload = os.path.join(root, file)
                if file not in skip_files:
                    self.logger.info(f"Uploading file {file_to_upload} to {bucket_name}")
                    self.s3_client.upload_file(file_to_upload, bucket_name, file)
                else:
                    self.logger.info(f"Skipping file {file_to_upload}")
    
    def start_ingestion_job(self, kb_name: str) -> None:
        """
        Start the ingestion job for a knowledge base.
        
        Args:
            kb_name: Name of the knowledge base
        """
        full_kb_name = f"{kb_name}-{self.timestamp_suffix}"
        if full_kb_name in self.kb_instances:
            self.kb_instances[full_kb_name].start_ingestion_job()
            # Wait for ingestion to complete
            self.logger.info("Waiting for ingestion to complete...")
            time.sleep(30)
        else:
            self.logger.error(f"Knowledge base {full_kb_name} not found")
            raise ValueError(f"Knowledge base {full_kb_name} not found")
    
    def retrieve_and_generate(self, kb_id: str, query: str, 
                             num_results: int = 5) -> Dict[str, Any]:
        """
        Perform a retrieve and generate operation using the knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            query: Query text
            num_results: Number of results to retrieve
            
        Returns:
            Response from the retrieve and generate operation
        """
        response = self.bedrock_agent_runtime_client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    'knowledgeBaseId': kb_id,
                    "modelArn": f"arn:aws:bedrock:{self.region}::foundation-model/{self.foundation_model}",
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "numberOfResults": num_results
                        } 
                    }
                }
            }
        )
        return response
    
    def retrieve(self, kb_id: str, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Perform a retrieve operation using the knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            query: Query text
            num_results: Number of results to retrieve
            
        Returns:
            Response from the retrieve operation
        """
        response = self.bedrock_agent_runtime_client.retrieve(
            knowledgeBaseId=kb_id,
            nextToken='string',
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": num_results,
                } 
            },
            retrievalQuery={
                'text': query
            }
        )
        return response
    
    def delete_knowledge_base(self, kb_name: str, 
                             delete_s3_bucket: bool = False,
                             delete_iam_roles_and_policies: bool = True,
                             delete_lambda_function: bool = False) -> None:
        """
        Delete a knowledge base and optionally its associated resources.
        
        Args:
            kb_name: Name of the knowledge base
            delete_s3_bucket: Whether to delete the associated S3 bucket
            delete_iam_roles_and_policies: Whether to delete IAM roles and policies
            delete_lambda_function: Whether to delete the Lambda function
        """
        full_kb_name = f"{kb_name}-{self.timestamp_suffix}"
        if full_kb_name in self.kb_instances:
            self.logger.info(f"Deleting knowledge base: {full_kb_name}")
            self.kb_instances[full_kb_name].delete_kb(
                delete_s3_bucket=delete_s3_bucket,
                delete_iam_roles_and_policies=delete_iam_roles_and_policies,
                delete_lambda_function=delete_lambda_function
            )
            # Remove from instances dictionary
            del self.kb_instances[full_kb_name]
        else:
            self.logger.warning(f"Knowledge base {full_kb_name} not found for deletion")

class ResponseFormatter:
    """
    A utility class to format and print responses from Bedrock operations.
    """
    
    @staticmethod
    def print_citations(response_citations: List[Dict[str, Any]]) -> None:
        """
        Print citation information from a response.
        
        Args:
            response_citations: List of citation references
        """
        print(f"# of citations or chunks used to generate the response: {len(response_citations)}")
        for num, chunk in enumerate(response_citations, 1):
            print(f'Chunk {num}: {chunk["content"]["text"]}\n')
            print(f'Chunk {num} Location: {chunk["location"]}\n')
            print(f'Chunk {num} Metadata: {chunk["metadata"]}\n')
    
    @staticmethod
    def print_retrieval_results(response: Dict[str, Any]) -> None:
        """
        Print retrieval results from a response.
        
        Args:
            response: Response containing retrieval results
        """
        results = response.get('retrievalResults', [])
        print(f"# of retrieved results: {len(results)}")
        for num, chunk in enumerate(results, 1):
            print(f'Chunk {num}: {chunk["content"]["text"]}\n')
            print(f'Chunk {num} Location: {chunk["location"]}\n')
            print(f'Chunk {num} Score: {chunk["score"]}\n')
            print(f'Chunk {num} Metadata: {chunk["metadata"]}\n')

class ChunkingStrategySelector:
    """
    A class to handle user selection of chunking strategies.
    """
    
    STRATEGIES = {
        "1": {"name": "FIXED_SIZE", "description": "Standard fixed-size chunking"},
        "2": {"name": "CUSTOM", "description": "Custom chunking using Lambda function"},
        "3": {"name": "BOTH", "description": "Run both fixed-size and custom chunking for comparison"}
    }
    
    @classmethod
    def get_user_selection(cls) -> Dict[str, Any]:
        """
        Get the user's selection of chunking strategy.
        
        Returns:
            Dictionary with strategy information
        """
        print("\n=== Chunking Strategy Selection ===")
        print("Select a chunking strategy for your knowledge base:")
        
        for key, strategy in cls.STRATEGIES.items():
            print(f"{key}. {strategy['name']}: {strategy['description']}")
        
        while True:
            selection = input("\nEnter your selection (1-3): ")
            if selection in cls.STRATEGIES:
                strategy_info = cls.STRATEGIES[selection]
                print(f"Selected: {strategy_info['name']} - {strategy_info['description']}")
                return {"strategy": strategy_info['name']}
            else:
                print("Invalid selection. Please try again.")

def main():
    """Main function to demonstrate the usage of the classes."""
    try:
        # Initialize the manager
        kb_manager = BedrockKnowledgeBaseManager()
        formatter = ResponseFormatter()
        
        # Check if lambda function file exists and create a copy with the expected name
        lambda_source_file = "lambda_custom_chunking_function.py"
        lambda_target_file = "lambda_function.py"
        
        # Create a copy of the lambda file with the expected name
        if os.path.exists(lambda_source_file) and not os.path.exists(lambda_target_file):
            print(f"Creating a copy of {lambda_source_file} as {lambda_target_file}")
            with open(lambda_source_file, 'r') as source:
                content = source.read()
                with open(lambda_target_file, 'w') as target:
                    target.write(content)
        elif not os.path.exists(lambda_source_file):
            print(f"Error: Lambda source file {lambda_source_file} not found.")
            print("Please create this file with your custom chunking code.")
            return
        
        # Get user selection for chunking strategy
        strategy_selection = ChunkingStrategySelector.get_user_selection()
        chunking_strategy = strategy_selection["strategy"]
        
        # Base names for resources
        kb_base_name = 'kb'
        kb_description = "Knowledge Base containing complex PDF."
        
        # Create knowledge bases with different chunking strategies
        kb_ids = {}
        kb_names = {}
        
        # Create standard knowledge base if selected
        if chunking_strategy in ["FIXED_SIZE", "BOTH"]:
            kb_name_standard = f"standard-{kb_base_name}"
            print(f"\nCreating knowledge base with FIXED_SIZE chunking strategy...")
            kb_id_standard = kb_manager.create_knowledge_base(
                kb_name=kb_name_standard,
                kb_description=kb_description,
                chunking_strategy="FIXED_SIZE"
            )
            kb_ids["standard"] = kb_id_standard
            kb_names["standard"] = kb_name_standard
            
            # Upload data to the S3 bucket
            bucket_name = f'{kb_name_standard}-{kb_manager.timestamp_suffix}'
            print(f"Uploading data to bucket: {bucket_name}")
            kb_manager.upload_directory_to_s3("synthetic_dataset", bucket_name)
            
            # Start ingestion job
            print("Starting ingestion job...")
            kb_manager.start_ingestion_job(kb_name_standard)
            
        # Create custom chunking knowledge base if selected
        if chunking_strategy in ["CUSTOM", "BOTH"]:
            kb_name_custom = f"custom-{kb_base_name}"
            print(f"\nCreating knowledge base with CUSTOM chunking strategy...")
            
            # Create intermediate bucket name
            intermediate_bucket_name = f"{kb_name_custom}-intermediate-{kb_manager.timestamp_suffix}"
            
            # Set up Lambda function for custom chunking
            lambda_function_name = f"{kb_name_custom}-lambda-{kb_manager.timestamp_suffix}"
            
            kb_id_custom = kb_manager.create_knowledge_base(
                kb_name=kb_name_custom,
                kb_description=kb_description,
                chunking_strategy="CUSTOM",
                lambda_function_name=lambda_function_name,
                intermediate_bucket_name=intermediate_bucket_name
            )
            kb_ids["custom"] = kb_id_custom
            kb_names["custom"] = kb_name_custom
            
            # Upload data to the S3 bucket
            bucket_name = f'{kb_name_custom}-{kb_manager.timestamp_suffix}'
            print(f"Uploading data to bucket: {bucket_name}")
            kb_manager.upload_directory_to_s3("synthetic_dataset", bucket_name)
            
            # Start ingestion job
            print("Starting ingestion job...")
            kb_manager.start_ingestion_job(kb_name_custom)
        
        # Define a query
        query = "Provide a summary of consolidated statements of cash flows of Octank Financial for the fiscal years ended December 31, 2019."
        
        # Wait for knowledge base to be ready
        print("\nWaiting for knowledge base to be ready...")
        time.sleep(20)
        
        # Process query with each knowledge base
        for kb_type, kb_id in kb_ids.items():
            print(f"\n=== Results from {kb_type.upper()} knowledge base ===")
            print(f"Knowledge Base ID: {kb_id}")
            
            # Perform retrieve and generate
            print("\nPerforming retrieve and generate operation...")
            response = kb_manager.retrieve_and_generate(kb_id, query)
            print(response['output']['text'], end='\n'*2)
            
            # Format and print citations
            print("\nCitation information:")
            response_refs = response['citations'][0]['retrievedReferences']
            formatter.print_citations(response_refs)
            
            # Perform retrieve operation
            print("\nPerforming retrieve operation...")
            response_ret = kb_manager.retrieve(kb_id, query)
            formatter.print_retrieval_results(response_ret)
        
        # Print summary of knowledge base IDs
        print("\n=== Knowledge Base Summary ===")
        for kb_type, kb_id in kb_ids.items():
            print(f"{kb_type.capitalize()}: {kb_id}")
        
        # Run RAGAS evaluation if multiple knowledge bases are created
        if len(kb_ids) > 1 and "standard" in kb_ids and "custom" in kb_ids:
            print("\n=== Running RAGAS Evaluation ===")
            input("Press Enter to Run the RAGAS Evaluation...")
            
            # Import the RAG evaluator
            from rag_evaluator import RAGEvaluator
            
            # Create a Bedrock runtime client with appropriate configuration
            bedrock_runtime_client = boto3.client(
                'bedrock-runtime',
                region_name=kb_manager.region,
                config=Config(
                    read_timeout=900,  # 15 minutes
                    connect_timeout=60,
                    retries={'max_attempts': 3}
                )
            )
            
            # Initialize the RAG evaluator
            evaluator = RAGEvaluator(
                bedrock_runtime_client=bedrock_runtime_client,
                bedrock_agent_runtime_client=kb_manager.bedrock_agent_runtime_client
            )
            
            # Define evaluation questions and ground truths
            questions = [
                "What was the primary reason for the increase in net cash provided by operating activities for Octank Financial in 2021?",
                "In which year did Octank Financial have the highest net cash used in investing activities, and what was the primary reason for this?",
                "What was the primary source of cash inflows from financing activities for Octank Financial in 2021?",
                "Based on the information provided, what can you infer about Octank Financial's overall financial health and growth prospects?"
            ]
            ground_truths = [
                "The increase in net cash provided by operating activities was primarily due to an increase in net income and favorable changes in operating assets and liabilities.",
                "Octank Financial had the highest net cash used in investing activities in 2021, at $360 million. The primary reason for this was an increase in purchases of property, plant, and equipment and marketable securities",
                "The primary source of cash inflows from financing activities for Octank Financial in 2021 was an increase in proceeds from the issuance of common stock and long-term debt.",
                "Based on the information provided, Octank Financial appears to be in a healthy financial position and has good growth prospects. The company has consistently increased its net cash provided by operating activities, indicating strong profitability and efficient management of working capital. Additionally, Octank Financial has been investing in long-term assets, such as property, plant, and equipment, and marketable securities, which suggests plans for future growth and expansion. The company has also been able to finance its growth through the issuance of common stock and long-term debt, indicating confidence from investors and lenders. Overall, Octank Financial's steady increase in cash and cash equivalents over the past three years provides a strong foundation for future growth and investment opportunities."
            ]
            
            # Compare knowledge base strategies
            kb_strategy_map = {
                "Default Chunking": kb_ids["standard"],
                "Contextual Chunking": kb_ids["custom"]
            }
            
            comparison_df = evaluator.compare_kb_strategies(kb_strategy_map, questions, ground_truths)
            
            # Format and display the comparison
            styled_df = evaluator.format_comparison(comparison_df)
            print("\n=== RAGAS Evaluation Results ===")
            print(styled_df.to_string())
            
            # Save the results to a CSV file
            comparison_df.to_csv("ragas_evaluation_results.csv")
            print("\nEvaluation results saved to ragas_evaluation_results.csv")
        
    finally:
        # Clean up resources before exiting
        print("\nCleaning up resources...")
        input("Press Enter to Delete the Resources...")
        try:
            # Delete the knowledge bases and associated resources
            for kb_type, kb_name in kb_names.items():
                print(f"Cleaning up {kb_type} knowledge base: {kb_name}")
                kb_manager.delete_knowledge_base(
                    kb_name,
                    delete_s3_bucket=True,
                    delete_iam_roles_and_policies=True,
                    delete_lambda_function=False if kb_type == "standard" else True
                )
                print(f"Knowledge base {kb_name} cleanup completed successfully.")
                
            # Clean up the temporary lambda function file
            if os.path.exists(lambda_target_file):
                print(f"Removing temporary file: {lambda_target_file}")
                os.remove(lambda_target_file)
                
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    main()


