# Copyright 2024 Amazon.com and its affiliates; all rights reserved.
# This file is AWS Content and may not be duplicated or distributed without permission

"""
This module contains a helper class for building and using Knowledge Bases for Amazon Bedrock.
The KnowledgeBasesForAmazonBedrock class provides a convenient interface for working with Knowledge Bases.
It includes methods for creating, updating, and invoking Knowledge Bases, as well as managing
IAM roles and OpenSearch Serverless. Here is a quick example of using
the class:

    >>> from knowledge_base import KnowledgeBasesForAmazonBedrock
    >>> kb = KnowledgeBasesForAmazonBedrock()
    >>> kb_name = "my-knowledge-base-test"
    >>> kb_description = "my knowledge base description"
    >>> data_bucket_name = "<s3_bucket_with_kb_dataset>"
    >>> kb_id, ds_id = kb.create_or_retrieve_knowledge_base(kb_name, kb_description, data_bucket_name)
    >>> kb.synchronize_data(kb_id, ds_id)

Here is a summary of the most important methods:

- create_or_retrieve_knowledge_base: Creates a new Knowledge Base or retrieves an existent one.
- synchronize_data: Syncronize the Knowledge Base with the
"""
import json
import boto3
import time
import logging
from botocore.exceptions import ClientError, BotoCoreError
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, RequestError
import pprint
from retrying import retry
import random
import requests
from requests_aws4auth import AWS4Auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

valid_embedding_models = [
    "cohere.embed-multilingual-v3", "cohere.embed-english-v3", "amazon.titan-embed-text-v1",
    "amazon.titan-embed-text-v2:0"
]
pp = pprint.PrettyPrinter(indent=2)


def interactive_sleep(seconds: int):
    """
    Support functionality to induce an artificial 'sleep' to the code in order to wait for resources to be available
    Args:
        seconds (int): number of seconds to sleep for
    """
    dots = ''
    for i in range(seconds):
        dots += '.'
        print(dots, end='\r')
        time.sleep(1)


def retry_with_iam_propagation(max_retries=3, base_wait_time=30):
    """
    Decorator to retry operations that may fail due to IAM permission propagation delays
    Args:
        max_retries: Maximum number of retry attempts
        base_wait_time: Base wait time in seconds between retries
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ClientError, BotoCoreError) as e:
                    last_exception = e
                    error_code = getattr(e.response.get('Error', {}), 'Code', 'Unknown') if hasattr(e, 'response') else 'Unknown'
                    
                    # Check if this is an IAM-related error that might benefit from retry
                    iam_related_errors = [
                        'AccessDeniedException', 
                        'UnauthorizedOperation',
                        'InvalidUserID.NotFound',
                        'ValidationException'  # Sometimes IAM propagation causes validation errors
                    ]
                    
                    if attempt < max_retries and error_code in iam_related_errors:
                        wait_time = base_wait_time * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"IAM-related error detected (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        logger.info(f"Waiting {wait_time} seconds for IAM permission propagation before retry...")
                        interactive_sleep(wait_time)
                        continue
                    else:
                        raise
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = base_wait_time * (2 ** attempt)
                        logger.warning(f"Unexpected error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        interactive_sleep(wait_time)
                        continue
                    else:
                        raise
            
            # If we get here, all retries failed
            raise last_exception
        return wrapper
    return decorator


class KnowledgeBasesForAmazonBedrock:
    """
    Support class that allows for:
        - creation (or retrieval) of a Knowledge Base for Amazon Bedrock with all its pre-requisites
          (including OSS, IAM roles and Permissions and S3 bucket)
        - Ingestion of data into the Knowledge Base
        - Deletion of all resources created
    """

    def __init__(self, suffix=None):
        """
        Class initializer
        """
        boto3_session = boto3.session.Session(region_name="us-west-2")
        self.region_name = boto3_session.region_name
        self.iam_client = boto3_session.client('iam')
        self.account_number = boto3_session.client('sts').get_caller_identity().get('Account')
        self.suffix = random.randrange(200, 900)
        self.identity = boto3_session.client('sts').get_caller_identity()['Arn']
        self.aoss_client = boto3_session.client('opensearchserverless', region_name="us-west-2")
        self.s3_client = boto3_session.client('s3', region_name="us-west-2")
        self.bedrock_agent_client = boto3_session.client('bedrock-agent', region_name="us-west-2")
        self.bedrock_agent_client = boto3_session.client(
            'bedrock-agent',
            region_name=self.region_name
        )
        credentials = boto3_session.get_credentials()
        self.awsauth = AWSV4SignerAuth(credentials, self.region_name, 'aoss')
        self.oss_client = None

    def create_or_retrieve_knowledge_base(
            self,
            kb_name: str,
            kb_description: str = None,
            data_bucket_name: str = None,
            embedding_model: str = "amazon.titan-embed-text-v2:0",
            use_native_vector_store: bool = False
    ):
        """
        Function used to create a new Knowledge Base or retrieve an existent one.
        
        Args:
            kb_name: Knowledge Base Name
            kb_description: Knowledge Base Description
            data_bucket_name: Name of s3 Bucket containing Knowledge Base Data
            embedding_model: Name of Embedding model to be used on Knowledge Base creation
            use_native_vector_store: If True, uses Bedrock's built-in vector store instead of OpenSearch

        Returns:
            kb_id: str - Knowledge base id
            ds_id: str - Data Source id
        """
        """
        Function used to create a new Knowledge Base or retrieve an existent one

        Args:
            kb_name: Knowledge Base Name
            kb_description: Knowledge Base Description
            data_bucket_name: Name of s3 Bucket containing Knowledge Base Data
            embedding_model: Name of Embedding model to be used on Knowledge Base creation

        Returns:
            kb_id: str - Knowledge base id
            ds_id: str - Data Source id
        """
        kb_id = None
        ds_id = None
        kbs_available = self.bedrock_agent_client.list_knowledge_bases(
            maxResults=100,
        )
        for kb in kbs_available["knowledgeBaseSummaries"]:
            if kb_name == kb["name"]:
                kb_id = kb["knowledgeBaseId"]
        if kb_id is not None:
            ds_available = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=kb_id,
                maxResults=100,
            )
            for ds in ds_available["dataSourceSummaries"]:
                if kb_id == ds["knowledgeBaseId"]:
                    ds_id = ds["dataSourceId"]
            print(f"Knowledge Base {kb_name} already exists.")
            print(f"Retrieved Knowledge Base Id: {kb_id}")
            print(f"Retrieved Data Source Id: {ds_id}")
        else:
            print(f"Creating KB {kb_name}")
            
            # Check if we should use Bedrock's native vector store
            if use_native_vector_store:
                print("Using Bedrock's native vector store instead of OpenSearch Serverless")
                return self.create_knowledge_base_with_native_vector_store(
                    kb_name, kb_description, data_bucket_name, embedding_model
                )
            # self.kb_name = kb_name
            # self.kb_description = kb_description
            if data_bucket_name is None:
                kb_name_temp = kb_name.replace("_", "-")
                data_bucket_name = f"{kb_name_temp}-{self.suffix}"
                print(f"KB bucket name not provided, creating a new one called: {data_bucket_name}")
            if embedding_model not in valid_embedding_models:
                valid_embeddings_str = str(valid_embedding_models)
                raise ValueError(f"Invalid embedding model. Your embedding model should be one of {valid_embeddings_str}")
            # self.embedding_model = embedding_model
            encryption_policy_name = f"{kb_name}-sp-{self.suffix}"
            network_policy_name = f"{kb_name}-np-{self.suffix}"
            access_policy_name = f'{kb_name}-ap-{self.suffix}'
            kb_execution_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_{self.suffix}'
            fm_policy_name = f'AmazonBedrockFoundationModelPolicyForKnowledgeBase_{self.suffix}'
            s3_policy_name = f'AmazonBedrockS3PolicyForKnowledgeBase_{self.suffix}'
            oss_policy_name = f'AmazonBedrockOSSPolicyForKnowledgeBase_{self.suffix}'
            vector_store_name = f'{kb_name}-{self.suffix}'
            index_name = f"{kb_name}-index-{self.suffix}"
            print("========================================================================================")
            print(f"Step 1 - Creating or retrieving {data_bucket_name} S3 bucket for Knowledge Base documents")
            self.create_s3_bucket(data_bucket_name)
            print("========================================================================================")
            print(f"Step 2 - Creating Knowledge Base Execution Role ({kb_execution_role_name}) and Policies")
            bedrock_kb_execution_role = self.create_bedrock_kb_execution_role(
                embedding_model, data_bucket_name, fm_policy_name, s3_policy_name, kb_execution_role_name
            )
            print("========================================================================================")
            print(f"Step 3 - Creating OSS encryption, network and data access policies")
            encryption_policy, network_policy, access_policy = self.create_policies_in_oss(
                encryption_policy_name, vector_store_name, network_policy_name,
                bedrock_kb_execution_role, access_policy_name
            )
            print("========================================================================================")
            print(f"Step 4 - Creating OSS Collection (this step takes a couple of minutes to complete)")
            host, collection, collection_id, collection_arn = self.create_oss(
                vector_store_name, oss_policy_name, bedrock_kb_execution_role
            )
            # Wait for the collection and permissions to fully propagate
            logger.info("Waiting for OpenSearch collection and permissions to propagate (180 seconds)...")
            print("Waiting for OpenSearch collection and permissions to propagate...")
            print("This includes collection creation, data access policies, and IAM role permissions...")
            interactive_sleep(180)  # Increased wait time for better propagation
            logger.info("✓ OpenSearch permission propagation wait completed")
            
            # Build the OpenSearch client with fresh credentials
            credentials = boto3.session.Session(region_name="us-west-2").get_credentials()
            self.awsauth = AWSV4SignerAuth(credentials, self.region_name, 'aoss')
            self.oss_client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=self.awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=300
            )

            print("========================================================================================")
            print(f"Step 5 - Creating OSS Vector Index")
            self.create_vector_index(index_name, embedding_model)
            
            # Additional wait to ensure index is fully ready before creating knowledge base
            print("Waiting for index to be fully ready before creating knowledge base...")
            interactive_sleep(60)
            
            print("========================================================================================")
            print(f"Step 6 - Creating Knowledge Base")
            knowledge_base, data_source = self.create_knowledge_base(
                collection_arn, index_name, data_bucket_name, embedding_model,
                kb_name, kb_description, bedrock_kb_execution_role
            )
            interactive_sleep(60)
            print("========================================================================================")
            kb_id = knowledge_base['knowledgeBaseId']
            ds_id = data_source["dataSourceId"]
        return kb_id, ds_id

    def create_s3_bucket(self, bucket_name: str):
        """
        Check if bucket exists, and if not create S3 bucket for knowledge base data source
        Args:
            bucket_name: s3 bucket name
        """
        logger.info(f"Checking if S3 bucket '{bucket_name}' exists...")
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f'✓ S3 bucket {bucket_name} already exists - retrieving it!')
            print(f'Bucket {bucket_name} already exists - retrieving it!')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.info(f"S3 bucket '{bucket_name}' does not exist, creating it...")
                print(f'Creating bucket {bucket_name}')
                try:
                    if self.region_name == "us-east-1":
                        self.s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region_name}
                        )
                    logger.info(f"✓ Successfully created S3 bucket '{bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"✗ Failed to create S3 bucket '{bucket_name}': {create_error}")
                    raise Exception(f"Failed to create S3 bucket: {create_error}")
                except Exception as create_error:
                    logger.error(f"✗ Unexpected error creating S3 bucket '{bucket_name}': {create_error}")
                    raise
            elif error_code == '403':
                logger.error(f"✗ Access denied to S3 bucket '{bucket_name}'. Check IAM permissions.")
                raise Exception(f"Access denied to S3 bucket '{bucket_name}'. Check IAM permissions.")
            else:
                logger.error(f"✗ Error checking S3 bucket '{bucket_name}': {e}")
                raise Exception(f"Error checking S3 bucket: {e}")
        except BotoCoreError as e:
            logger.error(f"✗ AWS service error while checking S3 bucket '{bucket_name}': {e}")
            raise Exception(f"AWS service error: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error while checking S3 bucket '{bucket_name}': {e}")
            raise

    def create_bedrock_kb_execution_role(
            self,
            embedding_model: str,
            bucket_name: str,
            fm_policy_name: str,
            s3_policy_name: str,
            kb_execution_role_name: str
    ):
        """
        Create Knowledge Base Execution IAM Role and its required policies.
        If role and/or policies already exist, retrieve them
        Args:
            embedding_model: the embedding model used by the knowledge base
            bucket_name: the bucket name used by the knowledge base
            fm_policy_name: the name of the foundation model access policy
            s3_policy_name: the name of the s3 access policy
            kb_execution_role_name: the name of the knowledge base execution role

        Returns:
            IAM role created
        """
        foundation_model_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/{embedding_model}"
                    ]
                }
            ]
        }

        s3_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "aws:ResourceAccount": f"{self.account_number}"
                        }
                    }
                }
            ]
        }

        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "preprod.bedrock.aws.internal"
                    },
                    "Action": "sts:AssumeRole"
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "beta.bedrock.aws.internal"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        logger.info("Creating IAM policies for Knowledge Base execution role...")
        
        # Create foundation model policy
        try:
            logger.info(f"Creating foundation model policy: {fm_policy_name}")
            fm_policy = self.iam_client.create_policy(
                PolicyName=fm_policy_name,
                PolicyDocument=json.dumps(foundation_model_policy_document),
                Description='Policy for accessing foundation model',
            )
            logger.info(f"✓ Successfully created foundation model policy: {fm_policy_name}")
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"Foundation model policy {fm_policy_name} already exists, retrieving it")
            print(f"{fm_policy_name} already exists, retrieving it!")
            try:
                fm_policy = self.iam_client.get_policy(
                    PolicyArn=f"arn:aws:iam::{self.account_number}:policy/{fm_policy_name}"
                )
                logger.info(f"✓ Retrieved existing foundation model policy: {fm_policy_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve foundation model policy {fm_policy_name}: {e}")
                raise Exception(f"Failed to retrieve foundation model policy: {e}")
        except ClientError as e:
            logger.error(f"✗ Failed to create foundation model policy {fm_policy_name}: {e}")
            raise Exception(f"Failed to create foundation model policy: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating foundation model policy {fm_policy_name}: {e}")
            raise

        # Create S3 policy
        try:
            logger.info(f"Creating S3 access policy: {s3_policy_name}")
            s3_policy = self.iam_client.create_policy(
                PolicyName=s3_policy_name,
                PolicyDocument=json.dumps(s3_policy_document),
                Description='Policy for reading documents from s3')
            logger.info(f"✓ Successfully created S3 access policy: {s3_policy_name}")
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"S3 access policy {s3_policy_name} already exists, retrieving it")
            print(f"{s3_policy_name} already exists, retrieving it!")
            try:
                s3_policy = self.iam_client.get_policy(
                    PolicyArn=f"arn:aws:iam::{self.account_number}:policy/{s3_policy_name}"
                )
                logger.info(f"✓ Retrieved existing S3 access policy: {s3_policy_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve S3 access policy {s3_policy_name}: {e}")
                raise Exception(f"Failed to retrieve S3 access policy: {e}")
        except ClientError as e:
            logger.error(f"✗ Failed to create S3 access policy {s3_policy_name}: {e}")
            raise Exception(f"Failed to create S3 access policy: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating S3 access policy {s3_policy_name}: {e}")
            raise
            
        # Create bedrock execution role
        try:
            logger.info(f"Creating Bedrock execution role: {kb_execution_role_name}")
            bedrock_kb_execution_role = self.iam_client.create_role(
                RoleName=kb_execution_role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
                Description='Amazon Bedrock Knowledge Base Execution Role for accessing OSS and S3',
                MaxSessionDuration=3600
            )
            logger.info(f"✓ Successfully created Bedrock execution role: {kb_execution_role_name}")
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            logger.info(f"Bedrock execution role {kb_execution_role_name} already exists, retrieving it")
            print(f"{kb_execution_role_name} already exists, retrieving it!")
            try:
                bedrock_kb_execution_role = self.iam_client.get_role(
                    RoleName=kb_execution_role_name
                )
                logger.info(f"✓ Retrieved existing Bedrock execution role: {kb_execution_role_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve Bedrock execution role {kb_execution_role_name}: {e}")
                raise Exception(f"Failed to retrieve Bedrock execution role: {e}")
        except ClientError as e:
            logger.error(f"✗ Failed to create Bedrock execution role {kb_execution_role_name}: {e}")
            raise Exception(f"Failed to create Bedrock execution role: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating Bedrock execution role {kb_execution_role_name}: {e}")
            raise
            
        # Fetch ARNs of the policies and role created above
        try:
            s3_policy_arn = s3_policy["Policy"]["Arn"]
            fm_policy_arn = fm_policy["Policy"]["Arn"]
            logger.info(f"Policy ARNs retrieved - FM: {fm_policy_arn}, S3: {s3_policy_arn}")
        except KeyError as e:
            logger.error(f"✗ Failed to extract policy ARNs: {e}")
            raise Exception(f"Failed to extract policy ARNs: {e}")

        # Attach policies to Amazon Bedrock execution role
        try:
            logger.info("Attaching foundation model policy to execution role...")
            self.iam_client.attach_role_policy(
                RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
                PolicyArn=fm_policy_arn
            )
            logger.info("✓ Foundation model policy attached successfully")
            
            logger.info("Attaching S3 access policy to execution role...")
            self.iam_client.attach_role_policy(
                RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
                PolicyArn=s3_policy_arn
            )
            logger.info("✓ S3 access policy attached successfully")
            
            # Wait for IAM permission propagation
            logger.info("Waiting for IAM permission propagation (30 seconds)...")
            interactive_sleep(30)
            logger.info("✓ IAM permission propagation wait completed")
            
        except ClientError as e:
            logger.error(f"✗ Failed to attach policies to execution role: {e}")
            raise Exception(f"Failed to attach policies to execution role: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error attaching policies to execution role: {e}")
            raise
        return bedrock_kb_execution_role

    def create_oss_policy_attach_bedrock_execution_role(
            self,
            collection_id: str, oss_policy_name: str,
            bedrock_kb_execution_role: str
    ):
        """
        Create OpenSearch Serverless policy and attach it to the Knowledge Base Execution role.
        If policy already exists, attaches it
        Args:
            collection_id: collection id
            oss_policy_name: opensearch serverless policy name
            bedrock_kb_execution_role: knowledge base execution role

        Returns:
            created: bool - boolean to indicate if role was created
        """
        # define oss policy document
        oss_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "aoss:APIAccessAll"
                    ],
                    "Resource": [
                        f"arn:aws:aoss:{self.region_name}:{self.account_number}:collection/{collection_id}"
                    ]
                }
            ]
        }

        oss_policy_arn = f"arn:aws:iam::{self.account_number}:policy/{oss_policy_name}"
        created = False
        try:
            self.iam_client.create_policy(
                PolicyName=oss_policy_name,
                PolicyDocument=json.dumps(oss_policy_document),
                Description='Policy for accessing opensearch serverless',
            )
            created = True
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            print(f"Policy {oss_policy_arn} already exists, updating it")
        print("Opensearch serverless arn: ", oss_policy_arn)

        # Attach our custom policy
        self.iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=oss_policy_arn
        )
        
        # Attach AWS managed policies for full access
        opensearch_managed_policy = "arn:aws:iam::aws:policy/AmazonOpenSearchServiceFullAccess"
        print(f"Attaching AWS managed policy: {opensearch_managed_policy}")
        self.iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=opensearch_managed_policy
        )
        
        # Attach AdministratorAccess policy as suggested by user
        admin_policy = "arn:aws:iam::aws:policy/AdministratorAccess"
        print(f"Attaching AWS managed policy: {admin_policy}")
        self.iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=admin_policy
        )
        return created

    def create_policies_in_oss(
            self, encryption_policy_name: str, vector_store_name: str, network_policy_name: str,
            bedrock_kb_execution_role: str, access_policy_name: str
    ):
        """
        Create comprehensive OpenSearch Serverless encryption, network and data access policies.
        If policies already exist, retrieve them with enhanced error handling.
        Args:
            encryption_policy_name: name of the data encryption policy
            vector_store_name: name of the vector store
            network_policy_name: name of the network policy
            bedrock_kb_execution_role: name of the knowledge base execution role
            access_policy_name: name of the data access policy

        Returns:
            encryption_policy, network_policy, access_policy
        """
        logger.info(f"Creating OpenSearch Serverless policies for collection: {vector_store_name}")
        print(f"Creating OpenSearch Serverless policies for collection: {vector_store_name}")
        
        # Create encryption policy with AWS managed keys
        try:
            logger.info(f"Creating encryption policy: {encryption_policy_name}")
            print(f"Creating encryption policy: {encryption_policy_name}")
            encryption_policy = self.aoss_client.create_security_policy(
                name=encryption_policy_name,
                policy=json.dumps(
                    {
                        'Rules': [{'Resource': ['collection/' + vector_store_name],
                                   'ResourceType': 'collection'}],
                        'AWSOwnedKey': True
                    }),
                type='encryption'
            )
            logger.info(f"✓ Successfully created encryption policy: {encryption_policy_name}")
            print(f"✓ Successfully created encryption policy: {encryption_policy_name}")
        except self.aoss_client.exceptions.ConflictException:
            logger.info(f"Encryption policy {encryption_policy_name} already exists, retrieving it")
            print(f"Encryption policy {encryption_policy_name} already exists, retrieving it")
            try:
                encryption_policy = self.aoss_client.get_security_policy(
                    name=encryption_policy_name,
                    type='encryption'
                )
                logger.info(f"✓ Retrieved existing encryption policy: {encryption_policy_name}")
                print(f"✓ Retrieved existing encryption policy: {encryption_policy_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve encryption policy {encryption_policy_name}: {e}")
                raise Exception(f"Failed to retrieve encryption policy: {e}")
        except ClientError as e:
            logger.error(f"✗ Failed to create encryption policy {encryption_policy_name}: {e}")
            print(f"✗ Error creating encryption policy: {e}")
            raise Exception(f"Failed to create encryption policy: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating encryption policy {encryption_policy_name}: {e}")
            print(f"✗ Error creating encryption policy: {e}")
            raise

        # Create network policy with public access
        try:
            logger.info(f"Creating network policy: {network_policy_name}")
            print(f"Creating network policy: {network_policy_name}")
            network_policy = self.aoss_client.create_security_policy(
                name=network_policy_name,
                policy=json.dumps(
                    [
                        {'Rules': [{'Resource': ['collection/' + vector_store_name],
                                    'ResourceType': 'collection'}],
                         'AllowFromPublic': True}
                    ]),
                type='network'
            )
            logger.info(f"✓ Successfully created network policy: {network_policy_name}")
            print(f"✓ Successfully created network policy: {network_policy_name}")
        except self.aoss_client.exceptions.ConflictException:
            logger.info(f"Network policy {network_policy_name} already exists, retrieving it")
            print(f"Network policy {network_policy_name} already exists, retrieving it")
            try:
                network_policy = self.aoss_client.get_security_policy(
                    name=network_policy_name,
                    type='network'
                )
                logger.info(f"✓ Retrieved existing network policy: {network_policy_name}")
                print(f"✓ Retrieved existing network policy: {network_policy_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve network policy {network_policy_name}: {e}")
                raise Exception(f"Failed to retrieve network policy: {e}")
        except ClientError as e:
            logger.error(f"✗ Failed to create network policy {network_policy_name}: {e}")
            print(f"✗ Error creating network policy: {e}")
            raise Exception(f"Failed to create network policy: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating network policy {network_policy_name}: {e}")
            print(f"✗ Error creating network policy: {e}")
            raise

        # Create comprehensive data access policy
        try:
            logger.info(f"Creating data access policy: {access_policy_name}")
            print(f"Creating data access policy: {access_policy_name}")
            
            # Include both the Bedrock execution role and the current user identity
            principals = [bedrock_kb_execution_role['Role']['Arn']]
            
            # Add current user identity to allow index creation
            if self.identity:
                principals.append(self.identity)
                logger.info(f"Adding current user identity to access policy: {self.identity}")
                print(f"Adding current user identity to access policy: {self.identity}")
            
            access_policy = self.aoss_client.create_access_policy(
                name=access_policy_name,
                policy=json.dumps(
                    [
                        {
                            'Rules': [
                                {
                                    'Resource': ['collection/' + vector_store_name],
                                    'Permission': [
                                        'aoss:CreateCollectionItems',
                                        'aoss:DeleteCollectionItems',
                                        'aoss:UpdateCollectionItems',
                                        'aoss:DescribeCollectionItems'],
                                    'ResourceType': 'collection'
                                },
                                {
                                    'Resource': ['index/' + vector_store_name + '/*'],
                                    'Permission': [
                                        'aoss:CreateIndex',
                                        'aoss:DeleteIndex',
                                        'aoss:UpdateIndex',
                                        'aoss:DescribeIndex',
                                        'aoss:ReadDocument',
                                        'aoss:WriteDocument'],
                                    'ResourceType': 'index'
                                }],
                            'Principal': principals,
                            'Description': 'Comprehensive data access policy for Bedrock Knowledge Base and current user'}
                    ]),
                type='data'
            )
            logger.info(f"✓ Successfully created data access policy: {access_policy_name}")
            print(f"✓ Successfully created data access policy: {access_policy_name}")
        except self.aoss_client.exceptions.ConflictException:
            logger.info(f"Data access policy {access_policy_name} already exists, retrieving it")
            print(f"Data access policy {access_policy_name} already exists, retrieving it")
            try:
                access_policy = self.aoss_client.get_access_policy(
                    name=access_policy_name,
                    type='data'
                )
                logger.info(f"✓ Retrieved existing data access policy: {access_policy_name}")
                print(f"✓ Retrieved existing data access policy: {access_policy_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve data access policy {access_policy_name}: {e}")
                raise Exception(f"Failed to retrieve data access policy: {e}")
        except ClientError as e:
            logger.error(f"✗ Failed to create data access policy {access_policy_name}: {e}")
            print(f"✗ Error creating data access policy: {e}")
            raise Exception(f"Failed to create data access policy: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating data access policy {access_policy_name}: {e}")
            print(f"✗ Error creating data access policy: {e}")
            raise
            
        logger.info("✓ All OpenSearch Serverless policies created/retrieved successfully")
        print("✓ All OpenSearch Serverless policies created/retrieved successfully")
        return encryption_policy, network_policy, access_policy

    def create_oss(self, vector_store_name: str, oss_policy_name: str, bedrock_kb_execution_role: str):
        """
        Create comprehensive OpenSearch Serverless Collection with proper VECTORSEARCH type configuration.
        If already existent, retrieve with enhanced error handling.
        Args:
            vector_store_name: name of the vector store
            oss_policy_name: name of the opensearch serverless access policy
            bedrock_kb_execution_role: name of the knowledge base execution role
        """
        logger.info(f"Creating OpenSearch Serverless collection: {vector_store_name}")
        print(f"Creating OpenSearch Serverless collection: {vector_store_name}")
        
        try:
            logger.info(f"Creating collection with VECTORSEARCH type: {vector_store_name}")
            print(f"Creating collection with VECTORSEARCH type: {vector_store_name}")
            collection = self.aoss_client.create_collection(
                name=vector_store_name, 
                type='VECTORSEARCH',
                description=f'Vector search collection for knowledge base {vector_store_name}'
            )
            collection_id = collection['createCollectionDetail']['id']
            collection_arn = collection['createCollectionDetail']['arn']
            logger.info(f"✓ Collection creation initiated - ID: {collection_id}, ARN: {collection_arn}")
            print(f"✓ Collection creation initiated - ID: {collection_id}")
            print(f"✓ Collection ARN: {collection_arn}")
        except self.aoss_client.exceptions.ConflictException:
            logger.info(f"Collection {vector_store_name} already exists, retrieving it")
            print(f"Collection {vector_store_name} already exists, retrieving it")
            try:
                collection = self.aoss_client.batch_get_collection(
                    names=[vector_store_name]
                )['collectionDetails'][0]
                collection_id = collection['id']
                collection_arn = collection['arn']
                logger.info(f"✓ Retrieved existing collection - ID: {collection_id}, ARN: {collection_arn}")
                print(f"✓ Retrieved existing collection - ID: {collection_id}")
                print(f"✓ Collection ARN: {collection_arn}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve existing collection {vector_store_name}: {e}")
                raise Exception(f"Failed to retrieve existing collection: {e}")
            except Exception as e:
                logger.error(f"✗ Unexpected error retrieving collection {vector_store_name}: {e}")
                raise
        except ClientError as e:
            logger.error(f"✗ Failed to create OpenSearch Serverless collection {vector_store_name}: {e}")
            print(f"✗ Error creating OpenSearch Serverless collection: {e}")
            raise Exception(f"Failed to create OpenSearch Serverless collection: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating OpenSearch Serverless collection {vector_store_name}: {e}")
            print(f"✗ Error creating OpenSearch Serverless collection: {e}")
            raise

        # Get the OpenSearch serverless collection URL
        host = collection_id + '.' + self.region_name + '.aoss.amazonaws.com'
        logger.info(f"Collection endpoint: {host}")
        print(f"Collection endpoint: {host}")
        
        # Wait for collection creation with enhanced status monitoring
        logger.info("Waiting for collection to become active...")
        print("Waiting for collection to become active...")
        
        try:
            response = self.aoss_client.batch_get_collection(names=[vector_store_name])
            
            # Periodically check collection status with better logging
            status_check_count = 0
            max_status_checks = 20  # Maximum 10 minutes (20 * 30 seconds)
            
            while (response['collectionDetails'][0]['status']) == 'CREATING':
                status_check_count += 1
                logger.info(f'Collection status: CREATING (check #{status_check_count}/{max_status_checks})')
                print(f'Collection status: CREATING (check #{status_check_count})')
                
                if status_check_count >= max_status_checks:
                    logger.error(f"✗ Collection creation timeout after {max_status_checks} checks")
                    raise Exception(f"Collection creation timeout - status still CREATING after {max_status_checks * 30} seconds")
                
                interactive_sleep(30)
                response = self.aoss_client.batch_get_collection(names=[vector_store_name])
                
            final_status = response['collectionDetails'][0]['status']
            if final_status == 'ACTIVE':
                logger.info(f'✓ Collection successfully created and is now ACTIVE')
                print(f'✓ Collection successfully created and is now ACTIVE')
            elif final_status == 'FAILED':
                logger.error(f'✗ Collection creation failed with status: {final_status}')
                raise Exception(f"Collection creation failed with status: {final_status}")
            else:
                logger.warning(f'⚠ Collection status: {final_status}')
                print(f'⚠ Collection status: {final_status}')
                
            logger.info("Collection details:")
            print("Collection details:")
            pp.pprint(response["collectionDetails"])
            
        except ClientError as e:
            logger.error(f"✗ Error checking collection status: {e}")
            raise Exception(f"Error checking collection status: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error during collection status monitoring: {e}")
            raise
        
        # Create opensearch serverless access policy and attach it to Bedrock execution role
        try:
            logger.info("Creating and attaching OpenSearch Serverless access policy to execution role...")
            print("Creating and attaching OpenSearch Serverless access policy to execution role...")
            created = self.create_oss_policy_attach_bedrock_execution_role(
                collection_id, oss_policy_name, bedrock_kb_execution_role
            )
            if created:
                # It can take up to a minute for data access rules to be enforced
                logger.info("Waiting for data access rules to be enforced (60 seconds)...")
                print("Waiting for data access rules to be enforced...")
                interactive_sleep(60)
            logger.info("✓ OpenSearch Serverless access policy configured successfully")
            print("✓ OpenSearch Serverless access policy configured successfully")
            return host, collection, collection_id, collection_arn
        except Exception as e:
            logger.warning(f"⚠ Warning: Issue with policy attachment: {e}")
            print(f"⚠ Warning: Issue with policy attachment: {e}")
            print("Continuing with collection creation - policy may already exist")
            # Still return the values even if there was an error attaching the policy
            return host, collection, collection_id, collection_arn

    def create_vector_index(self, index_name: str, embedding_model: str = "amazon.titan-embed-text-v2:0"):
        """
        Create comprehensive OpenSearch Serverless vector index with correct dimensions 
        based on embedding model and proper field mapping for Bedrock Knowledge Base.
        Args:
            index_name: name of the vector index
            embedding_model: embedding model to determine vector dimensions
        """
        # Validate embedding model and determine vector field dimensions
        print(f"Configuring vector index for embedding model: {embedding_model}")
        
        if embedding_model not in valid_embedding_models:
            raise ValueError(f"Invalid embedding model: {embedding_model}. Must be one of: {valid_embedding_models}")
        
        # Determine vector field dimensions based on embedding model
        if "cohere" in embedding_model:
            vector_dimension = 1536
            print(f"✓ Using Cohere embedding model - vector dimension: {vector_dimension}")
        else:  # Titan models
            vector_dimension = 1024
            print(f"✓ Using Titan embedding model - vector dimension: {vector_dimension}")
            
        print(f"Creating vector index '{index_name}' with dimension {vector_dimension}")
        
        # Wait for permissions to be fully effective
        print("Waiting for OpenSearch permissions to propagate...")
        interactive_sleep(60)
        
        # Create index configuration compatible with Bedrock Knowledge Base (requires FAISS)
        body_json = {
            "settings": {
                "index.knn": True,
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "vector": {
                        "type": "knn_vector",
                        "dimension": vector_dimension,
                        "method": {
                            "name": "hnsw",
                            "engine": "faiss",
                            "space_type": "l2",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24
                            }
                        }
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

        # Create the index with comprehensive error handling
        try:
            print(f'Creating vector index: {index_name}')
            print(f'Index configuration:')
            print(f'  - Vector dimension: {vector_dimension}')
            print(f'  - Engine: faiss with HNSW algorithm (required by Bedrock)')
            print(f'  - Space type: l2')
            print(f'  - Number of shards: 1')
            print(f'  - Number of replicas: 0')
            print(f'  - Field mapping: vector, text, text-metadata')
            print(f'  - Bedrock Knowledge Base compatible configuration')
            
            # Check if index already exists and verify it has the correct engine type
            try:
                existing_index = self.oss_client.indices.get(index=index_name)
                print(f"Index {index_name} already exists - checking engine type...")
                
                # Check if the existing index has the correct engine type (FAISS)
                index_mapping = existing_index[index_name]['mappings']['properties']
                if 'vector' in index_mapping:
                    vector_config = index_mapping['vector']
                    if 'method' in vector_config:
                        engine_type = vector_config['method'].get('engine', 'unknown')
                        print(f"Existing index engine type: {engine_type}")
                        
                        if engine_type != 'faiss':
                            print(f"⚠ Index has wrong engine type ({engine_type}). Bedrock requires FAISS.")
                            print(f"Deleting existing index to recreate with correct configuration...")
                            
                            # Delete the existing index
                            self.oss_client.indices.delete(index=index_name)
                            print(f"✓ Deleted existing index {index_name}")
                            
                            # Wait a bit for deletion to propagate
                            interactive_sleep(10)
                        else:
                            print(f"✓ Index {index_name} already has correct FAISS engine - skipping creation")
                            return True
                    else:
                        print("⚠ Could not determine engine type, recreating index...")
                        self.oss_client.indices.delete(index=index_name)
                        interactive_sleep(10)
                else:
                    print("⚠ Index missing vector field, recreating...")
                    self.oss_client.indices.delete(index=index_name)
                    interactive_sleep(10)
                    
            except Exception as e:
                # Index doesn't exist or error checking it, proceed with creation
                print(f"Index doesn't exist or error checking it: {str(e)}")
                pass
            
            response = self.oss_client.indices.create(index=index_name, body=json.dumps(body_json))
            print('✓ Vector index creation successful')
            pp.pprint(response)
            
            # Wait for index to be fully ready
            print("Waiting for index to be fully ready...")
            interactive_sleep(30)
            
            # Verify index was created successfully
            try:
                index_info = self.oss_client.indices.get(index=index_name)
                print("✓ Index verification successful")
                print(f"✓ Index '{index_name}' is ready for use")
                return True
            except Exception as verify_error:
                print(f"⚠ Warning: Could not verify index creation: {verify_error}")
                print("Continuing anyway - index may still be functional")
                return True
                
        except RequestError as e:
            # If index already exists, this is actually OK - continue
            if "resource_already_exists_exception" in str(e):
                print(f"✓ Index {index_name} already exists - verifying configuration")
                try:
                    # Verify existing index has correct configuration
                    index_info = self.oss_client.indices.get(index=index_name)
                    print("✓ Existing index verified successfully")
                    return True
                except Exception as verify_error:
                    print(f"⚠ Warning: Could not verify existing index: {verify_error}")
                    print("Continuing anyway - existing index may still be functional")
                    return True
            else:
                print(f'✗ Error creating vector index: {e.error}')
                raise Exception(f"Failed to create vector index: {e.error}")
        except Exception as e:
            print(f'✗ Unexpected error during index creation: {str(e)}')
            raise Exception(f"Failed to create vector index: {str(e)}")

    @retry(wait_random_min=1000, wait_random_max=2000, stop_max_attempt_number=7)
    def create_knowledge_base(
            self, collection_arn: str, index_name: str, bucket_name: str, embedding_model: str,
            kb_name: str, kb_description: str, bedrock_kb_execution_role: str
    ):
        """
        Create Knowledge Base and its Data Source. If existent, retrieve
        Args:
            collection_arn: ARN of the opensearch serverless collection
            index_name: name of the opensearch serverless index
            bucket_name: name of the s3 bucket containing the knowledge base data
            embedding_model: id of the embedding model used
            kb_name: knowledge base name
            kb_description: knowledge base description
            bedrock_kb_execution_role: knowledge base execution role

        Returns:
            knowledge base object,
            data source object
        """
        # First, attempt to ensure the index exists with proper synchronization
        try:
            # Extract collection ID from collection ARN instead of index name
            collection_id = collection_arn.split('/')[-1]
            host = collection_id + '.' + self.region_name + '.aoss.amazonaws.com'
            
            # Use a direct approach with requests
            import requests
            from requests_aws4auth import AWS4Auth
            
            # Get fresh credentials
            boto3_session = boto3.session.Session(region_name="us-west-2")
            credentials = boto3_session.get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region_name,
                'aoss',
                session_token=credentials.token
            )
            
            # First check if index exists
            url = f"https://{host}/{index_name}"
            print(f"Checking if index exists: {url}")
            
            # Try multiple times to check index existence due to eventual consistency
            index_exists = False
            for attempt in range(3):
                response = requests.head(url, auth=awsauth, timeout=30)
                if response.status_code == 200:
                    index_exists = True
                    print(f"Index {index_name} already exists")
                    break
                elif response.status_code == 404:
                    print(f"Index {index_name} not found (attempt {attempt + 1}/3)")
                    if attempt < 2:
                        time.sleep(10)  # Wait before retry
                else:
                    print(f"Unexpected response checking index: {response.status_code}")
                    if attempt < 2:
                        time.sleep(10)
            
            if not index_exists:
                print(f"Creating index {index_name}...")
                
                # Create the index with Bedrock Knowledge Base compatible configuration (FAISS required)
                body_json = {
                    "settings": {
                        "index.knn": True,
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    },
                    "mappings": {
                        "properties": {
                            "vector": {
                                "type": "knn_vector",
                                "dimension": 1024,
                                "method": {
                                    "name": "hnsw",
                                    "engine": "faiss",
                                    "space_type": "l2",
                                    "parameters": {
                                        "ef_construction": 128,
                                        "m": 24
                                    }
                                }
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
                
                # Try direct request to create index
                create_response = requests.put(
                    url,
                    auth=awsauth,
                    json=body_json,
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )
                
                if create_response.status_code >= 200 and create_response.status_code < 300:
                    print(f"Successfully created index {index_name}")
                    # Wait for index to be fully ready
                    print("Waiting for index to be fully ready...")
                    time.sleep(30)
                    
                    # Verify index was created
                    verify_response = requests.head(url, auth=awsauth, timeout=30)
                    if verify_response.status_code == 200:
                        print(f"✓ Index {index_name} verified and ready")
                    else:
                        print(f"⚠ Warning: Index creation may not be complete (status: {verify_response.status_code})")
                else:
                    print(f"Failed to create index: {create_response.status_code}")
                    print(f"Response: {create_response.text}")
                    raise Exception(f"Failed to create index {index_name}: {create_response.text}")
                
        except Exception as e:
            print(f"Error while trying to verify/create index: {str(e)}")
            raise Exception(f"Index creation/verification failed: {str(e)}")
        """
        Create Knowledge Base and its Data Source. If existent, retrieve
        Args:
            collection_arn: ARN of the opensearch serverless collection
            index_name: name of the opensearch serverless index
            bucket_name: name of the s3 bucket containing the knowledge base data
            embedding_model: id of the embedding model used
            kb_name: knowledge base name
            kb_description: knowledge base description
            bedrock_kb_execution_role: knowledge base execution role

        Returns:
            knowledge base object,
            data source object
        """
        opensearch_serverless_configuration = {
            "collectionArn": collection_arn,
            "vectorIndexName": index_name,
            "fieldMapping": {
                "vectorField": "vector",
                "textField": "text",
                "metadataField": "text-metadata"
            }
        }

        # Ingest strategy - How to ingest data from the data source
        chunking_strategy_configuration = {
            "chunkingStrategy": "FIXED_SIZE",
            "fixedSizeChunkingConfiguration": {
                "maxTokens": 150,
                "overlapPercentage": 20
            }
        }

        # The data source to ingest documents from, into the OpenSearch serverless knowledge base index
        s3_configuration = {
            "bucketArn": f"arn:aws:s3:::{bucket_name}",
            # "inclusionPrefixes":["*.*"] # you can use this if you want to create a KB using data within s3 prefixes.
        }

        # The embedding model used by Bedrock to embed ingested documents, and realtime prompts
        embedding_model_arn = f"arn:aws:bedrock:{self.region_name}::foundation-model/{embedding_model}"
        print(str({
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": embedding_model_arn
            }
        }))
        logger.info(f"Creating knowledge base: {kb_name}")
        logger.info(f"Configuration - Embedding model: {embedding_model}, Collection ARN: {collection_arn}")
        
        try:
            logger.info("Attempting to create knowledge base...")
            create_kb_response = self.bedrock_agent_client.create_knowledge_base(
                name=kb_name,
                description=kb_description,
                roleArn=bedrock_kb_execution_role['Role']['Arn'],
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": embedding_model_arn
                    }
                },
                storageConfiguration={
                    "type": "OPENSEARCH_SERVERLESS",
                    "opensearchServerlessConfiguration": opensearch_serverless_configuration
                }
            )
            kb = create_kb_response["knowledgeBase"]
            logger.info(f"✓ Successfully created knowledge base with ID: {kb['knowledgeBaseId']}")
            pp.pprint(kb)
        except self.bedrock_agent_client.exceptions.ConflictException:
            logger.info(f"Knowledge base {kb_name} already exists, retrieving it")
            try:
                kbs = self.bedrock_agent_client.list_knowledge_bases(maxResults=100)
                kb_id = None
                for existing_kb in kbs['knowledgeBaseSummaries']:
                    if existing_kb['name'] == kb_name:
                        kb_id = existing_kb['knowledgeBaseId']
                        break
                
                if kb_id:
                    response = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
                    kb = response['knowledgeBase']
                    logger.info(f"✓ Retrieved existing knowledge base with ID: {kb_id}")
                    pp.pprint(kb)
                else:
                    logger.error(f"✗ Could not find existing knowledge base with name {kb_name}")
                    raise Exception(f"Could not find existing knowledge base with name {kb_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve existing knowledge base {kb_name}: {e}")
                raise Exception(f"Failed to retrieve existing knowledge base: {e}")
        except self.bedrock_agent_client.exceptions.ValidationException as e:
            logger.error(f"✗ Validation error creating knowledge base {kb_name}: {e}")
            error_message = str(e)
            if "storageConfiguration.type" in error_message:
                logger.error("This appears to be a storage configuration validation error")
                logger.error("Supported storage types: [RDS, OPENSEARCH_SERVERLESS, PINECONE, MONGO_DB_ATLAS, NEPTUNE_ANALYTICS, REDIS_ENTERPRISE_CLOUD]")
            raise Exception(f"Knowledge base validation error: {e}")
        except ClientError as e:
            logger.error(f"✗ AWS client error creating knowledge base {kb_name}: {e}")
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDeniedException':
                logger.error("Access denied - check IAM permissions for Bedrock and OpenSearch Serverless")
            elif error_code == 'ResourceNotFoundException':
                logger.error("Resource not found - check if collection ARN and index exist")
            raise Exception(f"AWS client error creating knowledge base: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating knowledge base {kb_name}: {e}")
            raise

        # Create a DataSource in KnowledgeBase
        logger.info(f"Creating data source for knowledge base: {kb['knowledgeBaseId']}")
        try:
            logger.info("Attempting to create data source...")
            create_ds_response = self.bedrock_agent_client.create_data_source(
                name=kb_name,
                description=kb_description,
                knowledgeBaseId=kb['knowledgeBaseId'],
                dataDeletionPolicy='RETAIN',
                dataSourceConfiguration={
                    "type": "S3",
                    "s3Configuration": s3_configuration
                },
                vectorIngestionConfiguration={
                    "chunkingConfiguration": chunking_strategy_configuration
                }
            )
            ds = create_ds_response["dataSource"]
            logger.info(f"✓ Successfully created data source with ID: {ds['dataSourceId']}")
            pp.pprint(ds)
        except self.bedrock_agent_client.exceptions.ConflictException:
            logger.info(f"Data source for knowledge base {kb['knowledgeBaseId']} already exists, retrieving it")
            try:
                ds_list = self.bedrock_agent_client.list_data_sources(
                    knowledgeBaseId=kb['knowledgeBaseId'],
                    maxResults=100
                )
                
                if ds_list['dataSourceSummaries']:
                    ds_id = ds_list['dataSourceSummaries'][0]['dataSourceId']
                    get_ds_response = self.bedrock_agent_client.get_data_source(
                        dataSourceId=ds_id,
                        knowledgeBaseId=kb['knowledgeBaseId']
                    )
                    ds = get_ds_response["dataSource"]
                    logger.info(f"✓ Retrieved existing data source with ID: {ds_id}")
                    pp.pprint(ds)
                else:
                    logger.error(f"✗ No data sources found for knowledge base {kb['knowledgeBaseId']}")
                    raise Exception(f"No data sources found for knowledge base {kb['knowledgeBaseId']}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve existing data source: {e}")
                raise Exception(f"Failed to retrieve existing data source: {e}")
        except self.bedrock_agent_client.exceptions.ValidationException as e:
            logger.error(f"✗ Validation error creating data source: {e}")
            raise Exception(f"Data source validation error: {e}")
        except ClientError as e:
            logger.error(f"✗ AWS client error creating data source: {e}")
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDeniedException':
                logger.error("Access denied - check IAM permissions for S3 bucket access")
            elif error_code == 'ResourceNotFoundException':
                logger.error("Resource not found - check if knowledge base exists and S3 bucket is accessible")
            raise Exception(f"AWS client error creating data source: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating data source: {e}")
            raise
        return kb, ds

    def synchronize_data(self, kb_id, ds_id):
        """
        Start an ingestion job to synchronize data from an S3 bucket to the Knowledge Base
        and waits for the job to be completed
        Args:
            kb_id: knowledge base id
            ds_id: data source id
        """
        logger.info(f"Starting data synchronization for knowledge base: {kb_id}, data source: {ds_id}")
        
        # Ensure that the knowledge base is available
        logger.info("Waiting for knowledge base to be available...")
        i_status = ['CREATING', 'DELETING', 'UPDATING']
        status_check_count = 0
        max_status_checks = 60  # Maximum 10 minutes (60 * 10 seconds)
        
        try:
            while True:
                kb_response = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
                kb_status = kb_response['knowledgeBase']['status']
                
                if kb_status not in i_status:
                    if kb_status == 'AVAILABLE':
                        logger.info(f"✓ Knowledge base is now available (status: {kb_status})")
                        break
                    elif kb_status == 'FAILED':
                        logger.error(f"✗ Knowledge base is in FAILED state")
                        raise Exception(f"Knowledge base is in FAILED state")
                    else:
                        logger.info(f"✓ Knowledge base status: {kb_status}")
                        break
                
                status_check_count += 1
                if status_check_count >= max_status_checks:
                    logger.error(f"✗ Timeout waiting for knowledge base to be available after {max_status_checks * 10} seconds")
                    raise Exception(f"Timeout waiting for knowledge base to be available")
                
                logger.info(f"Knowledge base status: {kb_status} (check #{status_check_count}/{max_status_checks})")
                time.sleep(10)
                
        except ClientError as e:
            logger.error(f"✗ Error checking knowledge base status: {e}")
            raise Exception(f"Error checking knowledge base status: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error waiting for knowledge base: {e}")
            raise
        
        # Start an ingestion job
        try:
            logger.info("Starting ingestion job...")
            start_job_response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=ds_id
            )
            job = start_job_response["ingestionJob"]
            job_id = job["ingestionJobId"]
            logger.info(f"✓ Ingestion job started with ID: {job_id}")
            pp.pprint(job)
        except ClientError as e:
            logger.error(f"✗ Failed to start ingestion job: {e}")
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ConflictException':
                logger.error("Another ingestion job may already be running")
            elif error_code == 'ResourceNotFoundException':
                logger.error("Knowledge base or data source not found")
            raise Exception(f"Failed to start ingestion job: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error starting ingestion job: {e}")
            raise
        
        # Monitor job progress
        logger.info("Monitoring ingestion job progress...")
        job_check_count = 0
        max_job_checks = 120  # Maximum 20 minutes (120 * 10 seconds)
        
        try:
            while job['status'] not in ['COMPLETE', 'FAILED']:
                job_check_count += 1
                if job_check_count >= max_job_checks:
                    logger.error(f"✗ Ingestion job timeout after {max_job_checks * 10} seconds")
                    raise Exception(f"Ingestion job timeout")
                
                logger.info(f"Ingestion job status: {job['status']} (check #{job_check_count}/{max_job_checks})")
                time.sleep(10)
                
                get_job_response = self.bedrock_agent_client.get_ingestion_job(
                    knowledgeBaseId=kb_id,
                    dataSourceId=ds_id,
                    ingestionJobId=job["ingestionJobId"]
                )
                job = get_job_response["ingestionJob"]
            
            if job['status'] == 'COMPLETE':
                logger.info(f"✓ Ingestion job completed successfully")
                if 'statistics' in job:
                    stats = job['statistics']
                    logger.info(f"Ingestion statistics: {stats}")
            elif job['status'] == 'FAILED':
                logger.error(f"✗ Ingestion job failed")
                if 'failureReasons' in job:
                    logger.error(f"Failure reasons: {job['failureReasons']}")
                raise Exception(f"Ingestion job failed: {job.get('failureReasons', 'Unknown reason')}")
            
            pp.pprint(job)
            
        except ClientError as e:
            logger.error(f"✗ Error monitoring ingestion job: {e}")
            raise Exception(f"Error monitoring ingestion job: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error during ingestion job monitoring: {e}")
            raise
        
        logger.info("Waiting for final synchronization to complete...")
        interactive_sleep(40)

    def delete_kb(self, kb_name: str, delete_s3_bucket: bool = True, delete_iam_roles_and_policies: bool = True,
                  delete_aoss: bool = True):
        """
        Delete the Knowledge Base resources
        Args:
            kb_name: name of the knowledge base to delete
            delete_s3_bucket (bool): boolean to indicate if s3 bucket should also be deleted
            delete_iam_roles_and_policies (bool): boolean to indicate if IAM roles and Policies should also be deleted
            delete_aoss: boolean to indicate if amazon opensearch serverless resources should also be deleted
        """
        kbs_available = self.bedrock_agent_client.list_knowledge_bases(
            maxResults=100,
        )
        kb_id = None
        ds_id = None
        for kb in kbs_available["knowledgeBaseSummaries"]:
            if kb_name == kb["name"]:
                kb_id = kb["knowledgeBaseId"]
        kb_details = self.bedrock_agent_client.get_knowledge_base(
            knowledgeBaseId=kb_id
        )
        kb_role = kb_details['knowledgeBase']['roleArn'].split("/")[1]
        collection_id = kb_details['knowledgeBase']['storageConfiguration']['opensearchServerlessConfiguration']['collectionArn'].split(
            '/')[1]
        index_name = kb_details['knowledgeBase']['storageConfiguration']['opensearchServerlessConfiguration'][
            'vectorIndexName']

        encryption_policies = self.aoss_client.list_security_policies(
            maxResults=100,
            type='encryption'
        )
        encryption_policy_name = None
        for ep in encryption_policies['securityPolicySummaries']:
            if ep['name'].startswith(kb_name):
                encryption_policy_name = ep['name']

        network_policies = self.aoss_client.list_security_policies(
            maxResults=100,
            type='network'
        )
        network_policy_name = None
        for np in network_policies['securityPolicySummaries']:
            if np['name'].startswith(kb_name):
                network_policy_name = np['name']

        data_policies = self.aoss_client.list_access_policies(
            maxResults=100,
            type='data'
        )
        access_policy_name = None
        for dp in data_policies['accessPolicySummaries']:
            if dp['name'].startswith(kb_name):
                access_policy_name = dp['name']

        ds_available = self.bedrock_agent_client.list_data_sources(
            knowledgeBaseId=kb_id,
            maxResults=100,
        )
        for ds in ds_available["dataSourceSummaries"]:
            if kb_id == ds["knowledgeBaseId"]:
                ds_id = ds["dataSourceId"]
        ds_details = self.bedrock_agent_client.get_data_source(
            dataSourceId=ds_id,
            knowledgeBaseId=kb_id,
        )
        bucket_name = ds_details['dataSource']['dataSourceConfiguration']['s3Configuration']['bucketArn'].replace(
            "arn:aws:s3:::", "")
        try:
            self.bedrock_agent_client.delete_data_source(
                dataSourceId=ds_id,
                knowledgeBaseId=kb_id
            )
            print("Data Source deleted successfully!")
        except Exception as e:
            print(e)
        try:
            self.bedrock_agent_client.delete_knowledge_base(
                knowledgeBaseId=kb_id
            )
            print("Knowledge Base deleted successfully!")
        except Exception as e:
            print(e)
        if delete_aoss:
            try:
                self.oss_client.indices.delete(index=index_name)
                print("OpenSource Serveless Index deleted successfully!")
            except Exception as e:
                print(e)
            try:
                self.aoss_client.delete_collection(id=collection_id)
                print("OpenSource Collection Index deleted successfully!")
            except Exception as e:
                print(e)
            try:
                self.aoss_client.delete_access_policy(
                    type="data",
                    name=access_policy_name
                )
                print("OpenSource Serveless access policy deleted successfully!")
            except Exception as e:
                print(e)
            try:
                self.aoss_client.delete_security_policy(
                    type="network",
                    name=network_policy_name
                )
                print("OpenSource Serveless network policy deleted successfully!")
            except Exception as e:
                print(e)
            try:
                self.aoss_client.delete_security_policy(
                    type="encryption",
                    name=encryption_policy_name
                )
                print("OpenSource Serveless encryption policy deleted successfully!")
            except Exception as e:
                print(e)
        if delete_s3_bucket:
            try:
                self.delete_s3(bucket_name)
                print("Knowledge Base S3 bucket deleted successfully!")
            except Exception as e:
                print(e)
        if delete_iam_roles_and_policies:
            try:
                self.delete_iam_roles_and_policies(kb_role)
                print("Knowledge Base Roles and Policies deleted successfully!")
            except Exception as e:
                print(e)
        print("Resources deleted successfully!")

    def delete_iam_roles_and_policies(self, kb_execution_role_name: str):
        """
        Delete IAM Roles and policies used by the Knowledge Base
        Args:
            kb_execution_role_name: knowledge base execution role
        """
        attached_policies = self.iam_client.list_attached_role_policies(
            RoleName=kb_execution_role_name,
            MaxItems=100
        )
        policies_arns = []
        for policy in attached_policies['AttachedPolicies']:
            policies_arns.append(policy['PolicyArn'])
        for policy in policies_arns:
            self.iam_client.detach_role_policy(
                RoleName=kb_execution_role_name,
                PolicyArn=policy
            )
            self.iam_client.delete_policy(PolicyArn=policy)
        self.iam_client.delete_role(RoleName=kb_execution_role_name)
        return 0

    def create_knowledge_base_with_native_vector_store(
            self, kb_name: str, kb_description: str, data_bucket_name: str, embedding_model: str
    ):
        """
        Create a knowledge base using OpenSearch Serverless configuration.
        This method creates all required OpenSearch Serverless infrastructure components.
        
        Args:
            kb_name: Knowledge Base Name
            kb_description: Knowledge Base Description
            data_bucket_name: Name of s3 Bucket containing Knowledge Base Data
            embedding_model: Name of Embedding model to be used

        Returns:
            kb_id: str - Knowledge base id
            ds_id: str - Data Source id
        """
        print("========================================================================================")
        print(f"Step 1 - Creating or retrieving {data_bucket_name} S3 bucket for Knowledge Base documents")
        if data_bucket_name is None:
            kb_name_temp = kb_name.replace("_", "-")
            data_bucket_name = f"{kb_name_temp}-{self.suffix}"
            print(f"KB bucket name not provided, creating a new one called: {data_bucket_name}")
        
        self.create_s3_bucket(data_bucket_name)
        
        print("========================================================================================")
        print(f"Step 2 - Creating Knowledge Base Execution Role and Policies")
        
        kb_execution_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_{self.suffix}'
        fm_policy_name = f'AmazonBedrockFoundationModelPolicyForKnowledgeBase_{self.suffix}'
        s3_policy_name = f'AmazonBedrockS3PolicyForKnowledgeBase_{self.suffix}'
        oss_policy_name = f'AmazonBedrockOSSPolicyForKnowledgeBase_{self.suffix}'
        
        bedrock_kb_execution_role = self.create_bedrock_kb_execution_role(
            embedding_model, data_bucket_name, fm_policy_name, s3_policy_name, kb_execution_role_name
        )
        
        print("========================================================================================")
        print(f"Step 3 - Creating comprehensive OpenSearch Serverless policies")
        
        # Create policy names for OpenSearch Serverless
        encryption_policy_name = f"{kb_name}-sp-{self.suffix}"
        network_policy_name = f"{kb_name}-np-{self.suffix}"
        access_policy_name = f'{kb_name}-ap-{self.suffix}'
        vector_store_name = f'{kb_name}-{self.suffix}'
        index_name = f"bedrock-knowledge-base-default-index"
        
        print(f"Policy configuration:")
        print(f"  - Encryption policy: {encryption_policy_name}")
        print(f"  - Network policy: {network_policy_name}")
        print(f"  - Access policy: {access_policy_name}")
        print(f"  - Vector store name: {vector_store_name}")
        
        # Create comprehensive OpenSearch Serverless policies
        encryption_policy, network_policy, access_policy = self.create_policies_in_oss(
            encryption_policy_name, vector_store_name, network_policy_name,
            bedrock_kb_execution_role, access_policy_name
        )
        
        print("========================================================================================")
        print(f"Step 4 - Creating OpenSearch Serverless Collection with VECTORSEARCH type")
        
        print(f"Collection configuration:")
        print(f"  - Collection name: {vector_store_name}")
        print(f"  - Collection type: VECTORSEARCH")
        print(f"  - Region: {self.region_name}")
        
        # Create comprehensive OpenSearch Serverless collection
        host, collection, collection_id, collection_arn = self.create_oss(
            vector_store_name, oss_policy_name, bedrock_kb_execution_role
        )
        
        # Wait for collection and permissions to propagate
        print("Waiting for OpenSearch permissions to propagate...")
        interactive_sleep(120)
        
        # Build the OpenSearch client with fresh credentials
        credentials = boto3.session.Session(region_name="us-west-2").get_credentials()
        self.awsauth = AWSV4SignerAuth(credentials, self.region_name, 'aoss')
        self.oss_client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )
        
        print("========================================================================================")
        print(f"Step 5 - Creating OpenSearch Serverless Vector Index with proper engine settings")
        
        print(f"Vector index configuration:")
        print(f"  - Index name: {index_name}")
        print(f"  - Embedding model: {embedding_model}")
        print(f"  - Collection endpoint: {host}")
        
        # Create comprehensive vector index with proper dimensions and engine settings
        index_created = self.create_vector_index(index_name, embedding_model)
        
        if not index_created:
            print("⚠ WARNING: Vector index creation failed - this may cause issues")
            print("Attempting to continue with knowledge base creation...")
        else:
            print("✓ Vector index created successfully")
        
        print("========================================================================================")
        print(f"Step 6 - Creating Knowledge Base with OpenSearch Serverless")
        
        # The embedding model used by Bedrock to embed ingested documents, and realtime prompts
        embedding_model_arn = f"arn:aws:bedrock:{self.region_name}::foundation-model/{embedding_model}"
        
        # Determine vector field dimensions based on embedding model
        if "cohere" in embedding_model:
            vector_field_dimension = 1536
        else:  # Titan models
            vector_field_dimension = 1024
        
        # OpenSearch Serverless configuration
        opensearch_serverless_configuration = {
            "collectionArn": collection_arn,
            "vectorIndexName": index_name,
            "fieldMapping": {
                "vectorField": "bedrock-knowledge-base-default-vector",
                "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                "metadataField": "AMAZON_BEDROCK_METADATA"
            }
        }
        
        # Ingest strategy - How to ingest data from the data source
        chunking_strategy_configuration = {
            "chunkingStrategy": "FIXED_SIZE",
            "fixedSizeChunkingConfiguration": {
                "maxTokens": 150,
                "overlapPercentage": 20
            }
        }
        
        # The data source to ingest documents from
        s3_configuration = {
            "bucketArn": f"arn:aws:s3:::{data_bucket_name}",
        }
        
        logger.info(f"Creating knowledge base with OpenSearch Serverless configuration...")
        logger.info(f"Knowledge base name: {kb_name}")
        logger.info(f"Embedding model: {embedding_model}")
        logger.info(f"Collection ARN: {collection_arn}")
        logger.info(f"Index name: {index_name}")
        
        try:
            logger.info("Attempting to create knowledge base with OpenSearch Serverless...")
            create_kb_response = self.bedrock_agent_client.create_knowledge_base(
                name=kb_name,
                description=kb_description if kb_description else f"Knowledge base for {kb_name}",
                roleArn=bedrock_kb_execution_role['Role']['Arn'],
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": embedding_model_arn
                    }
                },
                storageConfiguration={
                    "type": "OPENSEARCH_SERVERLESS",
                    "opensearchServerlessConfiguration": opensearch_serverless_configuration
                }
            )
            kb = create_kb_response["knowledgeBase"]
            logger.info(f"✓ Successfully created knowledge base with ID: {kb['knowledgeBaseId']}")
            print(f"Created knowledge base with ID: {kb['knowledgeBaseId']}")
        except self.bedrock_agent_client.exceptions.ConflictException:
            logger.info(f"Knowledge base {kb_name} already exists, retrieving it")
            print(f"Knowledge base {kb_name} already exists, retrieving it")
            try:
                kbs = self.bedrock_agent_client.list_knowledge_bases(maxResults=100)
                kb_id = None
                for existing_kb in kbs['knowledgeBaseSummaries']:
                    if existing_kb['name'] == kb_name:
                        kb_id = existing_kb['knowledgeBaseId']
                        break
                
                if kb_id:
                    response = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
                    kb = response['knowledgeBase']
                    logger.info(f"✓ Retrieved existing knowledge base with ID: {kb['knowledgeBaseId']}")
                    print(f"Retrieved existing knowledge base with ID: {kb['knowledgeBaseId']}")
                else:
                    logger.error(f"✗ Could not find existing knowledge base with name {kb_name}")
                    raise Exception(f"Could not find existing knowledge base with name {kb_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve existing knowledge base: {e}")
                raise Exception(f"Failed to retrieve existing knowledge base: {e}")
        except self.bedrock_agent_client.exceptions.ValidationException as e:
            logger.error(f"✗ Validation error creating knowledge base: {e}")
            error_message = str(e)
            if "storageConfiguration.type" in error_message:
                logger.error("Storage configuration validation error detected")
                logger.error("Supported storage types: [RDS, OPENSEARCH_SERVERLESS, PINECONE, MONGO_DB_ATLAS, NEPTUNE_ANALYTICS, REDIS_ENTERPRISE_CLOUD]")
                logger.error("Current configuration uses: OPENSEARCH_SERVERLESS")
            elif "opensearchServerlessConfiguration" in error_message:
                logger.error("OpenSearch Serverless configuration error detected")
                logger.error(f"Collection ARN: {collection_arn}")
                logger.error(f"Index name: {index_name}")
            print(f"✗ Validation error: {e}")
            raise Exception(f"Knowledge base validation error: {e}")
        except ClientError as e:
            logger.error(f"✗ AWS client error creating knowledge base: {e}")
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDeniedException':
                logger.error("Access denied - check IAM permissions for Bedrock and OpenSearch Serverless")
                logger.error("Required permissions: bedrock:CreateKnowledgeBase, aoss:APIAccessAll")
            elif error_code == 'ResourceNotFoundException':
                logger.error("Resource not found - check if collection ARN exists and is accessible")
                logger.error(f"Collection ARN: {collection_arn}")
            print(f"✗ AWS client error: {e}")
            raise Exception(f"AWS client error creating knowledge base: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating knowledge base: {e}")
            print(f"Error creating knowledge base: {e}")
            raise
        
        # Wait for the knowledge base to be available
        kb_id = kb['knowledgeBaseId']
        logger.info(f"Waiting for knowledge base {kb_id} to be available...")
        print("Waiting for knowledge base to be available...")
        
        status_check_count = 0
        max_status_checks = 60  # Maximum 10 minutes (60 * 10 seconds)
        
        try:
            while True:
                response = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
                status = response["knowledgeBase"]["status"]
                
                status_check_count += 1
                logger.info(f"Knowledge base status: {status} (check #{status_check_count}/{max_status_checks})")
                print(f"Knowledge base status: {status}")
                
                if status == "AVAILABLE":
                    logger.info(f"✓ Knowledge base is now available")
                    break
                elif status == "FAILED":
                    logger.error(f"✗ Knowledge base creation failed")
                    raise Exception(f"Knowledge base creation failed")
                elif status_check_count >= max_status_checks:
                    logger.error(f"✗ Timeout waiting for knowledge base to be available after {max_status_checks * 10} seconds")
                    raise Exception(f"Timeout waiting for knowledge base to be available")
                
                interactive_sleep(10)
                
        except ClientError as e:
            logger.error(f"✗ Error checking knowledge base status: {e}")
            raise Exception(f"Error checking knowledge base status: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error waiting for knowledge base: {e}")
            raise
        
        print("========================================================================================")
        print(f"Step 7 - Creating Data Source for Knowledge Base")
        
        # Create the data source
        logger.info(f"Creating data source for knowledge base: {kb_id}")
        logger.info(f"S3 bucket ARN: {s3_configuration['bucketArn']}")
        
        try:
            logger.info("Attempting to create data source...")
            create_ds_response = self.bedrock_agent_client.create_data_source(
                name=f"{kb_name}-source",
                description=f"Data source for {kb_name}",
                knowledgeBaseId=kb_id,
                dataDeletionPolicy="RETAIN",
                dataSourceConfiguration={
                    "type": "S3",
                    "s3Configuration": s3_configuration
                },
                vectorIngestionConfiguration={
                    "chunkingConfiguration": chunking_strategy_configuration
                }
            )
            ds = create_ds_response["dataSource"]
            logger.info(f"✓ Successfully created data source with ID: {ds['dataSourceId']}")
            print(f"Created data source with ID: {ds['dataSourceId']}")
        except self.bedrock_agent_client.exceptions.ConflictException:
            logger.info(f"Data source for knowledge base {kb_id} already exists, retrieving it")
            print(f"Data source for {kb_name} already exists, retrieving it")
            try:
                ds_available = self.bedrock_agent_client.list_data_sources(
                    knowledgeBaseId=kb_id,
                    maxResults=100
                )
                
                if ds_available['dataSourceSummaries']:
                    ds_id = ds_available['dataSourceSummaries'][0]['dataSourceId']
                    get_ds_response = self.bedrock_agent_client.get_data_source(
                        dataSourceId=ds_id,
                        knowledgeBaseId=kb_id
                    )
                    ds = get_ds_response["dataSource"]
                    logger.info(f"✓ Retrieved existing data source with ID: {ds['dataSourceId']}")
                    print(f"Retrieved existing data source with ID: {ds['dataSourceId']}")
                else:
                    logger.error(f"✗ No data sources found for knowledge base {kb_id}")
                    raise Exception(f"Could not find existing data source for knowledge base {kb_name}")
            except ClientError as e:
                logger.error(f"✗ Failed to retrieve existing data source: {e}")
                raise Exception(f"Failed to retrieve existing data source: {e}")
        except self.bedrock_agent_client.exceptions.ValidationException as e:
            logger.error(f"✗ Validation error creating data source: {e}")
            error_message = str(e)
            if "s3Configuration" in error_message:
                logger.error("S3 configuration validation error detected")
                logger.error(f"S3 bucket ARN: {s3_configuration['bucketArn']}")
            print(f"✗ Validation error: {e}")
            raise Exception(f"Data source validation error: {e}")
        except ClientError as e:
            logger.error(f"✗ AWS client error creating data source: {e}")
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDeniedException':
                logger.error("Access denied - check IAM permissions for S3 bucket access")
                logger.error(f"Required permissions for bucket: {data_bucket_name}")
            elif error_code == 'ResourceNotFoundException':
                logger.error("Resource not found - check if knowledge base exists and S3 bucket is accessible")
                logger.error(f"Knowledge base ID: {kb_id}")
                logger.error(f"S3 bucket: {data_bucket_name}")
            print(f"✗ AWS client error: {e}")
            raise Exception(f"AWS client error creating data source: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error creating data source: {e}")
            print(f"Error creating data source: {e}")
            raise
        
        print("========================================================================================")
        
        return kb["knowledgeBaseId"], ds["dataSourceId"]

    def delete_s3(self, bucket_name: str):
        """
        Delete the objects contained in the Knowledge Base S3 bucket.
        Once the bucket is empty, delete the bucket
        Args:
            bucket_name: bucket name

        """
        objects = self.s3_client.list_objects(Bucket=bucket_name)
        if 'Contents' in objects:
            for obj in objects['Contents']:
                self.s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
        self.s3_client.delete_bucket(Bucket=bucket_name)
