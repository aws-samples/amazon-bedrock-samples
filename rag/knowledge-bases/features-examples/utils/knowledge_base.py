import json
import boto3
import time
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, RequestError
import pprint
from retrying import retry
import zipfile
from io import BytesIO
import warnings
import random
warnings.filterwarnings('ignore')

valid_generation_models = ["anthropic.claude-3-5-sonnet-20240620-v1:0", 
                          "anthropic.claude-3-5-haiku-20241022-v1:0", 
                          "anthropic.claude-3-sonnet-20240229-v1:0",
                          "anthropic.claude-3-haiku-20240307-v1:0",
                          "amazon.nova-micro-v1:0"] 

valid_reranking_models = ["cohere.rerank-v3-5:0",
                          "amazon.rerank-v1:0"] 

valid_embedding_models = ["cohere.embed-multilingual-v3", 
                          "cohere.embed-english-v3", 
                          "amazon.titan-embed-text-v1", 
                          "amazon.titan-embed-text-v2:0"]

embedding_context_dimensions = {
    "cohere.embed-multilingual-v3": 512,
    "cohere.embed-english-v3": 512,
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024
}

pp = pprint.PrettyPrinter(indent=2)

def interactive_sleep(seconds: int):
    dots = ''
    for i in range(seconds):
        dots += '.'
        print(dots, end='\r')
        time.sleep(1)

class BedrockKnowledgeBase:
    """
    Support class that allows for:
        - creation (or retrieval) of a Knowledge Base for Amazon Bedrock with all its pre-requisites
          (including OSS, IAM roles and Permissions and S3 bucket)
        - Ingestion of data into the Knowledge Base
        - Deletion of all resources created
    """
    def __init__(
            self,
            kb_name=None,
            kb_description=None,
            data_sources=None,
            multi_modal=None,
            parser=None,
            intermediate_bucket_name=None,
            lambda_function_name=None,
            embedding_model="amazon.titan-embed-text-v2:0",
            generation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            reranking_model="cohere.rerank-v3-5:0",
            graph_model="anthropic.claude-3-haiku-20240307-v1:0",
            chunking_strategy="FIXED_SIZE",
            suffix=None,
            vector_store="OPENSEARCH_SERVERLESS" # can be OPENSEARCH_SERVERLESS or NEPTUNE_ANALYTICS
    ):
        """
        Class initializer
        Args:
            kb_name(str): The name of the Knowledge Base.
            kb_description(str): The description of the Knowledge Base.
            data_sources(list): The list of data source used for the Knowledge Base.
            multi_modal(bool): Whether the Knowledge Base supports multi-modal data.
            parser(str): The parser to be used for the Knowledge Base.
            intermediate_bucket_name(str): The name of the intermediate S3 bucket to be used for custom chunking strategy.
            lambda_function_name(str): The name of the Lambda function to be used for custom chunking strategy.
            embedding_model(str): The embedding model to be used for the Knowledge Base.
            generation_model(str): The generation model to be used for the Knowledge Base.
            reranking_model(str): The reranking model to be used for the Knowledge Base.
            chunking_strategy(str): The chunking strategy to be used for the Knowledge Base.
            suffix(str): A suffix to be used for naming resources.
        """

        boto3_session = boto3.session.Session()
        self.region_name = boto3_session.region_name
        self.iam_client = boto3_session.client('iam')
        self.lambda_client = boto3.client('lambda')
        self.account_number = boto3.client('sts').get_caller_identity().get('Account')
        self.suffix = suffix or f'{self.region_name}-{self.account_number}'
        self.identity = boto3.client('sts').get_caller_identity()['Arn']
        self.aoss_client = boto3_session.client('opensearchserverless')
        self.neptune_client = boto3.client('neptune-graph')
        self.s3_client = boto3.client('s3')
        self.bedrock_agent_client = boto3.client('bedrock-agent')
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWSV4SignerAuth(credentials, self.region_name, 'aoss')

        self.kb_name = kb_name or f"default-knowledge-base-{self.suffix}"
        self.vector_store = vector_store
        self.graph_name = self.kb_name
        self.kb_description = kb_description or "Default Knowledge Base"
        
        self.data_sources = data_sources
        self.bucket_names=[d["bucket_name"] for d in self.data_sources if d['type']== 'S3']
        self.secrets_arns = [d["credentialsSecretArn"] for d in self.data_sources if d['type']== 'CONFLUENCE'or d['type']=='SHAREPOINT' or d['type']=='SALESFORCE']
        self.chunking_strategy = chunking_strategy
        self.multi_modal = multi_modal
        self.parser = parser
        
        if multi_modal or chunking_strategy == "CUSTOM" :
            self.intermediate_bucket_name = intermediate_bucket_name or f"{self.kb_name}-intermediate-{self.suffix}"
            self.lambda_function_name = lambda_function_name or f"{self.kb_name}-lambda-{self.suffix}"
        else:
            self.intermediate_bucket_name = None
            self.lambda_function_name = None
        
        self.embedding_model = embedding_model
        self.generation_model = generation_model
        self.reranking_model = reranking_model
        self.graph_model = graph_model
        
        self._validate_models()
        
        self.encryption_policy_name = f"bedrock-sample-rag-sp-{self.suffix}"
        self.network_policy_name = f"bedrock-sample-rag-np-{self.suffix}"
        self.access_policy_name = f'bedrock-sample-rag-ap-{self.suffix}'
        self.kb_execution_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_{self.suffix}'
        self.fm_policy_name = f'AmazonBedrockFoundationModelPolicyForKnowledgeBase_{self.suffix}'
        self.s3_policy_name = f'AmazonBedrockS3PolicyForKnowledgeBase_{self.suffix}'
        self.sm_policy_name = f'AmazonBedrockSecretPolicyForKnowledgeBase_{self.suffix}'
        self.cw_log_policy_name = f'AmazonBedrockCloudWatchPolicyForKnowledgeBase_{self.suffix}'
        self.oss_policy_name = f'AmazonBedrockOSSPolicyForKnowledgeBase_{self.suffix}'
        self.lambda_policy_name = f'AmazonBedrockLambdaPolicyForKnowledgeBase_{self.suffix}'
        self.bda_policy_name = f'AmazonBedrockBDAPolicyForKnowledgeBase_{self.suffix}'
        self.neptune_policy_name = f'AmazonBedrockNeptunePolicyForKnowledgeBase_{self.suffix}'
        self.lambda_arn = None
        self.roles = [self.kb_execution_role_name]

        self.vector_store_name = f'bedrock-sample-rag-{self.suffix}'
        self.index_name = f"bedrock-sample-rag-index-{self.suffix}"
        self.graph_id = None

        self._setup_resources()

    def _validate_models(self):
        if self.embedding_model not in valid_embedding_models:
            raise ValueError(f"Invalid embedding model. Your embedding model should be one of {valid_embedding_models}")
        if self.generation_model not in valid_generation_models:
            raise ValueError(f"Invalid Generation model. Your generation model should be one of {valid_generation_models}")
        if self.reranking_model not in valid_reranking_models:
            raise ValueError(f"Invalid Reranking model. Your reranking model should be one of {valid_reranking_models}")

    def _setup_resources(self):
        print("========================================================================================")
        print(f"Step 1 - Creating or retrieving S3 bucket(s) for Knowledge Base documents")
        self.create_s3_bucket()
        
        print("========================================================================================")
        print(f"Step 2 - Creating Knowledge Base Execution Role ({self.kb_execution_role_name}) and Policies")
        self.bedrock_kb_execution_role = self.create_bedrock_execution_role_multi_ds(self.bucket_names, self.secrets_arns)
        self.bedrock_kb_execution_role_name = self.bedrock_kb_execution_role['Role']['RoleName']

        if self.vector_store == "OPENSEARCH_SERVERLESS":
            print("========================================================================================")
            print(f"Step 3a - Creating OSS encryption, network and data access policies")
            self.encryption_policy, self.network_policy, self.access_policy = self.create_policies_in_oss()
            
            print("========================================================================================")
            print(f"Step 3b - Creating OSS Collection (this step takes a couple of minutes to complete)")
            self.host, self.collection, self.collection_id, self.collection_arn = self.create_oss()
            self.oss_client = OpenSearch(
                hosts=[{'host': self.host, 'port': 443}],
                http_auth=self.awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=300
            )
            
            print("========================================================================================")
            print(f"Step 3c - Creating OSS Vector Index")
            self.create_vector_index()
        else:
            print("========================================================================================")
            print(f"Step 3 - Creating Neptune Analytics Graph Index: might take upto 5-7 minutes")
            self.graph_id = self.create_neptune()
            
            
            
        print("========================================================================================")
        print(f"Step 4 - Will create Lambda Function if chunking strategy selected as CUSTOM")
        if self.chunking_strategy == "CUSTOM":
            print(f"Creating lambda function... as chunking strategy is {self.chunking_strategy}")
            response = self.create_lambda()
            self.lambda_arn = response['FunctionArn']
            print(response)
            print(f"Lambda function ARN: {self.lambda_arn}")
        else: 
            print(f"Not creating lambda function as chunking strategy is {self.chunking_strategy}")
        
        print("========================================================================================")
        print(f"Step 5 - Creating Knowledge Base")
        self.knowledge_base, self.data_source = self.create_knowledge_base(self.data_sources)
        print("========================================================================================")
        
    def create_s3_bucket(self, multi_modal=False):

        buckets_to_check = self.bucket_names.copy()
        # if multi_modal:
        #     buckets_to_check.append(buckets_to_check[0] + '-multi-modal-storage')

        if self.multi_modal or self.chunking_strategy == "CUSTOM":
            buckets_to_check.append(self.intermediate_bucket_name)

        print(buckets_to_check)
        print('buckets_to_check: ', buckets_to_check)

        existing_buckets = []
        for bucket_name in buckets_to_check:
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                existing_buckets.append(bucket_name)
                print(f'Bucket {bucket_name} already exists - retrieving it!')
            except ClientError:
                pass

        buckets_to_create = [b for b in buckets_to_check if b not in existing_buckets]

        for bucket_name in buckets_to_create:
            print(f'Creating bucket {bucket_name}')
            if self.region_name == "us-east-1":
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region_name}
                )

    def create_lambda(self):
        # add to function
        lambda_iam_role = self.create_lambda_role()
        self.lambda_iam_role_name = lambda_iam_role['Role']['RoleName']
        self.roles.append(self.lambda_iam_role_name)
        # Package up the lambda function code
        s = BytesIO()
        z = zipfile.ZipFile(s, 'w')
        z.write("lambda_function.py")
        z.close()
        zip_content = s.getvalue()

        # Create Lambda Function
        lambda_function = self.lambda_client.create_function(
            FunctionName=self.lambda_function_name,
            Runtime='python3.12',
            Timeout=60,
            Role=lambda_iam_role['Role']['Arn'],
            Code={'ZipFile': zip_content},
            Handler='lambda_function.lambda_handler'
        )
        return lambda_function

    def create_lambda_role(self):
        lambda_function_role = f'{self.kb_name}-lambda-role-{self.suffix}'
        s3_access_policy_name = f'{self.kb_name}-s3-policy'
        # Create IAM Role for the Lambda function
        try:
            assume_role_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }

            assume_role_policy_document_json = json.dumps(assume_role_policy_document)

            lambda_iam_role = self.iam_client.create_role(
                RoleName=lambda_function_role,
                AssumeRolePolicyDocument=assume_role_policy_document_json
            )

            # Pause to make sure role is created
            time.sleep(10)
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            lambda_iam_role = self.iam_client.get_role(RoleName=lambda_function_role)

        # Attach the AWSLambdaBasicExecutionRole policy
        self.iam_client.attach_role_policy(
            RoleName=lambda_function_role,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )

        # Create a policy to grant access to the intermediate S3 bucket
        s3_access_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket", 
                        "s3:PutObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self.intermediate_bucket_name}",
                        f"arn:aws:s3:::{self.intermediate_bucket_name}/*"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "aws:ResourceAccount": f"{self.account_number}"
                        }
                    }
                }
            ]
        }

        # Create the policy
        s3_access_policy_json = json.dumps(s3_access_policy)
        s3_access_policy_response = self.iam_client.create_policy(
            PolicyName=s3_access_policy_name,
            PolicyDocument= s3_access_policy_json
        )

        # Attach the policy to the Lambda function's role
        self.iam_client.attach_role_policy(
            RoleName=lambda_function_role,
            PolicyArn=s3_access_policy_response['Policy']['Arn']
        )
        return lambda_iam_role

    def create_bedrock_execution_role_multi_ds(self, bucket_names=None, secrets_arns=None):
        """
        Create Knowledge Base Execution IAM Role and its required policies.
        If role and/or policies already exist, retrieve them
        Returns:
            IAM role
        """
      
        bucket_names = self.bucket_names.copy()
        if self.intermediate_bucket_name:
            bucket_names.append(self.intermediate_bucket_name)

        # 1. Create and attach policy for foundation models
        foundation_model_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.embedding_model}",
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.generation_model}",
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.reranking_model}",
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.graph_model}"
                    ]
                }
            ]
        }

        # 2. Define policy documents for s3 bucket
        if bucket_names:
            s3_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket",
                            "s3:PutObject",
                            "s3:DeleteObject"
                        ],
                        "Resource": [item for sublist in [[f'arn:aws:s3:::{bucket}', f'arn:aws:s3:::{bucket}/*'] for bucket in bucket_names] for item in sublist],
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": f"{self.account_number}"
                            }
                        }
                    } 
                ]
            }   
        if self.vector_store == "NEPTUNE_ANALYTICS":
            neptune_policy_name = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "NeptuneAnalyticsAccess",
            "Effect": "Allow",
            "Action": [
                "*"
            ],
            "Resource": f"arn:aws:neptune-graph:{self.region_name}:{self.account_number}:graph/*"
            }
                     ]
            }
            
            
        # 3. Define policy documents for secrets manager
        if secrets_arns:
            secrets_manager_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:GetSecretValue",
                            "secretsmanager:PutSecretValue"
                        ],
                        "Resource": secrets_arns
                    }
                ]
            } 

        # 4. Define policy documents for BDA
        bda_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "BDAGetStatement",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:GetDataAutomationStatus"
                    ],
                    "Resource": f"arn:aws:bedrock:{self.region_name}:{self.account_number}:data-automation-invocation/*"
                },
                {
                    "Sid": "BDAInvokeStatement",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeDataAutomationAsync"
                    ],
                    "Resource": f"arn:aws:bedrock:{self.region_name}:aws:data-automation-project/public-rag-default"
                }
            ]
        }
        
        
        # 5. Define policy documents for lambda
        if self.chunking_strategy == "CUSTOM":
            lambda_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "LambdaInvokeFunctionStatement",
                        "Effect": "Allow",
                        "Action": [
                            "lambda:InvokeFunction"
                        ],
                        "Resource": [
                            f"arn:aws:lambda:{self.region_name}:{self.account_number}:function:{self.lambda_function_name}:*"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": f"{self.account_number}"
                            }
                        }
                    }
                ]
            }
        
        cw_log_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ],
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock/invokemodel:*"
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
            }
            ]
        }

        # combine all policies into one list from policy documents
        policies = [
            (self.fm_policy_name, foundation_model_policy_document, 'Policy for accessing foundation model'),
            (self.cw_log_policy_name, cw_log_policy_document, 'Policy for writing logs to CloudWatch Logs'),
        ]
        if self.bucket_names:
            policies.append((self.s3_policy_name, s3_policy_document, 'Policy for reading documents from s3'))
        if self.secrets_arns:
            policies.append((self.sm_policy_name, secrets_manager_policy_document, 'Policy for accessing secret manager'))
        if self.chunking_strategy == 'CUSTOM':
            policies.append((self.lambda_policy_name, lambda_policy_document, 'Policy for invoking lambda function'))
        if self.multi_modal:
            policies.append((self.bda_policy_name, bda_policy_document, 'Policy for accessing BDA'))
        if self.vector_store == "NEPTUNE_ANALYTICS":
            policies.append((self.neptune_policy_name, neptune_policy_name, 'Policy for Neptune Vector Store'))
            
        # create bedrock execution role
        bedrock_kb_execution_role = self.iam_client.create_role(
            RoleName=self.kb_execution_role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
            Description='Amazon Bedrock Knowledge Base Execution Role for accessing OSS, secrets manager and S3',
            MaxSessionDuration=3600
        )

        # create and attach the policies to the bedrock execution role
        for policy_name, policy_document, description in policies:
            policy = self.iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
                Description=description,
            )
            self.iam_client.attach_role_policy(
                RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
                PolicyArn=policy["Policy"]["Arn"]
            )

        return bedrock_kb_execution_role

    def create_neptune(self):
        response = self.neptune_client.create_graph(
                graphName=self.graph_name,
                tags={
                    'usecase': 'graphRAG'
                },
                publicConnectivity=True,
                vectorSearchConfiguration={
                    'dimension': embedding_context_dimensions[self.embedding_model]
                },
                replicaCount=1,
                deletionProtection=True,
                provisionedMemory=16
            )
        graph_id = response["id"]

        self.neptune_client.get_graph(graphIdentifier=graph_id)["status"]
        try:
            while self.neptune_client.get_graph(graphIdentifier=graph_id)["status"] == "CREATING":
                print("Graph is getting creating...")
                time.sleep(90)
                if response["status"] == "CREATED":
                    print("Graph created successfully")
        except KeyError as e:
            print(f"Error: 'status' key not found in response dictionary: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return graph_id

    def create_policies_in_oss(self):
        """
        Create OpenSearch Serverless policy and attach it to the Knowledge Base Execution role.
        If policy already exists, attaches it
        """
        try:
            encryption_policy = self.aoss_client.create_security_policy(
                name=self.encryption_policy_name,
                policy=json.dumps(
                    {
                        'Rules': [{'Resource': ['collection/' + self.vector_store_name],
                                   'ResourceType': 'collection'}],
                        'AWSOwnedKey': True
                    }),
                type='encryption'
            )
        except self.aoss_client.exceptions.ConflictException:
            encryption_policy = self.aoss_client.get_security_policy(
                name=self.encryption_policy_name,
                type='encryption'
            )

        try:
            network_policy = self.aoss_client.create_security_policy(
                name=self.network_policy_name,
                policy=json.dumps(
                    [
                        {'Rules': [{'Resource': ['collection/' + self.vector_store_name],
                                    'ResourceType': 'collection'}],
                         'AllowFromPublic': True}
                    ]),
                type='network'
            )
        except self.aoss_client.exceptions.ConflictException:
            network_policy = self.aoss_client.get_security_policy(
                name=self.network_policy_name,
                type='network'
            )

        try:
            access_policy = self.aoss_client.create_access_policy(
                name=self.access_policy_name,
                policy=json.dumps(
                    [
                        {
                            'Rules': [
                                {
                                    'Resource': ['collection/' + self.vector_store_name],
                                    'Permission': [
                                        'aoss:CreateCollectionItems',
                                        'aoss:DeleteCollectionItems',
                                        'aoss:UpdateCollectionItems',
                                        'aoss:DescribeCollectionItems'],
                                    'ResourceType': 'collection'
                                },
                                {
                                    'Resource': ['index/' + self.vector_store_name + '/*'],
                                    'Permission': [
                                        'aoss:CreateIndex',
                                        'aoss:DeleteIndex',
                                        'aoss:UpdateIndex',
                                        'aoss:DescribeIndex',
                                        'aoss:ReadDocument',
                                        'aoss:WriteDocument'],
                                    'ResourceType': 'index'
                                }],
                            'Principal': [self.identity, self.bedrock_kb_execution_role['Role']['Arn']],
                            'Description': 'Easy data policy'}
                    ]),
                type='data'
            )
        except self.aoss_client.exceptions.ConflictException:
            access_policy = self.aoss_client.get_access_policy(
                name=self.access_policy_name,
                type='data'
            )

        return encryption_policy, network_policy, access_policy

    def create_oss(self):
        """
        Create OpenSearch Serverless Collection. If already existent, retrieve
        """
        try:
            collection = self.aoss_client.create_collection(name=self.vector_store_name, type='VECTORSEARCH')
            collection_id = collection['createCollectionDetail']['id']
            collection_arn = collection['createCollectionDetail']['arn']
        except self.aoss_client.exceptions.ConflictException:
            collection = self.aoss_client.batch_get_collection(names=[self.vector_store_name])['collectionDetails'][0]
            collection_id = collection['id']
            collection_arn = collection['arn']
        pp.pprint(collection)

        host = collection_id + '.' + self.region_name + '.aoss.amazonaws.com'
        print(host)

        response = self.aoss_client.batch_get_collection(names=[self.vector_store_name])
        while (response['collectionDetails'][0]['status']) == 'CREATING':
            print('Creating collection...')
            interactive_sleep(30)
            response = self.aoss_client.batch_get_collection(names=[self.vector_store_name])
        print('\nCollection successfully created:')
        pp.pprint(response["collectionDetails"])

        try:
            self.create_oss_policy_attach_bedrock_execution_role(collection_id)
            print("Sleeping for a minute to ensure data access rules have been enforced")
            interactive_sleep(60)
        except Exception as e:
            print("Policy already exists")
            pp.pprint(e)

        return host, collection, collection_id, collection_arn

    def create_oss_policy_attach_bedrock_execution_role(self, collection_id):
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
        try:
            oss_policy = self.iam_client.create_policy(
                PolicyName=self.oss_policy_name,
                PolicyDocument=json.dumps(oss_policy_document),
                Description='Policy for accessing opensearch serverless',
            )
            oss_policy_arn = oss_policy["Policy"]["Arn"]
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            oss_policy_arn = f"arn:aws:iam::{self.account_number}:policy/{self.oss_policy_name}"
        
        print("Opensearch serverless arn: ", oss_policy_arn)

        self.iam_client.attach_role_policy(
            RoleName=self.bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=oss_policy_arn
        )

    def create_vector_index(self):
        """
        Create OpenSearch Serverless vector index. If existent, ignore
        """
        body_json = {
            "settings": {
                "index.knn": "true",
                "number_of_shards": 1,
                "knn.algo_param.ef_search": 512,
                "number_of_replicas": 0,
            },
            "mappings": {
                "properties": {
                    "vector": {
                        "type": "knn_vector",
                        "dimension": embedding_context_dimensions[self.embedding_model],
                        "method": {
                            "name": "hnsw",
                            "engine": "faiss",
                            "space_type": "l2"
                        },
                    },
                    "text": {
                        "type": "text"
                    },
                    "text-metadata": {
                        "type": "text"}
                }
            }
        }

        try:
            response = self.oss_client.indices.create(index=self.index_name, body=json.dumps(body_json))
            print('\nCreating index:')
            pp.pprint(response)
            interactive_sleep(60)
        except RequestError as e:
            print(f'Error while trying to create the index, with error {e.error}')

    def create_chunking_strategy_config(self, strategy):
        configs = {
           
            "GRAPH": {
                "contextEnrichmentConfiguration": { 
                        "bedrockFoundationModelConfiguration": { 
                            "enrichmentStrategyConfiguration": { 
                                "method": "CHUNK_ENTITY_EXTRACTION"
                            },
                            "modelArn": f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.graph_model}"
                        },
                        "type": "BEDROCK_FOUNDATION_MODEL"
                }
            },
                    
            "NONE": {
                "chunkingConfiguration": {"chunkingStrategy": "NONE"}
            },
            "FIXED_SIZE": {
                "chunkingConfiguration": {
                "chunkingStrategy": "FIXED_SIZE",
                "fixedSizeChunkingConfiguration": {
                    "maxTokens": 300,
                    "overlapPercentage": 20
                    }
                }
            },
            "HIERARCHICAL": {
                "chunkingConfiguration": {
                "chunkingStrategy": "HIERARCHICAL",
                "hierarchicalChunkingConfiguration": {
                    "levelConfigurations": [{"maxTokens": 1500}, {"maxTokens": 300}],
                    "overlapTokens": 60
                    }
                }
            },
            "SEMANTIC": {
                "chunkingConfiguration": {
                "chunkingStrategy": "SEMANTIC",
                "semanticChunkingConfiguration": {
                    "maxTokens": 300,
                    "bufferSize": 1,
                    "breakpointPercentileThreshold": 95}
                }
            },
            "CUSTOM": {
                "customTransformationConfiguration": {
                    "intermediateStorage": {
                        "s3Location": {
                            "uri": f"s3://{self.intermediate_bucket_name}/"
                        }
                    },
                    "transformations": [
                        {
                            "transformationFunction": {
                                "transformationLambdaConfiguration": {
                                    "lambdaArn": self.lambda_arn
                                }
                            },
                            "stepToApply": "POST_CHUNKING"
                        }
                    ]
                }, 
                "chunkingConfiguration": {"chunkingStrategy": "NONE"}
            }
        }
        return configs.get(strategy, configs["NONE"])

    @retry(wait_random_min=1000, wait_random_max=2000, stop_max_attempt_number=7)
    def create_knowledge_base(self, data_sources):
        """
        Create Knowledge Base and its Data Source. If existent, retrieve
        """
        if self.graph_id: 
            storage_configuration = {
            "type": "NEPTUNE_ANALYTICS",
            "neptuneAnalyticsConfiguration": {
                "graphArn": f"arn:aws:neptune-graph:{self.region_name}:{self.account_number}:graph/{self.graph_id}",
                "fieldMapping": {
                    "textField": "text",
                    "metadataField": "text-metadata"
                }
            }
        }
        else:
            storage_configuration = {
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": self.collection_arn,
                "vectorIndexName": self.index_name,
                "fieldMapping": {
                    "vectorField": "vector",
                    "textField": "text",
                    "metadataField": "text-metadata"
                }
            }
            }

        # create Knowledge Bases
        embedding_model_arn = f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.embedding_model}"
        knowledgebase_configuration = { "type": "VECTOR", "vectorKnowledgeBaseConfiguration": { "embeddingModelArn": embedding_model_arn}}
            
        if self.multi_modal:
            supplemental_storageLocation={"storageLocations": [{ "s3Location": { "uri": f"s3://{self.intermediate_bucket_name}"},"type": "S3"}]}
            knowledgebase_configuration['vectorKnowledgeBaseConfiguration']['supplementalDataStorageConfiguration'] = supplemental_storageLocation
        
        try:
            create_kb_response = self.bedrock_agent_client.create_knowledge_base(
                name=self.kb_name,
                description=self.kb_description,
                roleArn=self.bedrock_kb_execution_role['Role']['Arn'],
                knowledgeBaseConfiguration=knowledgebase_configuration,
                storageConfiguration=storage_configuration,
            )
            kb = create_kb_response["knowledgeBase"]
            pp.pprint(kb)
        except self.bedrock_agent_client.exceptions.ConflictException:
            kbs = self.bedrock_agent_client.list_knowledge_bases(maxResults=100)
            kb_id = next((kb['knowledgeBaseId'] for kb in kbs['knowledgeBaseSummaries'] if kb['name'] == self.kb_name), None)
            response = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
            kb = response['knowledgeBase']
            pp.pprint(kb)
          
        # create Data Sources
        print("Creating Data Sources")
        try:
            ds_list = self.create_data_sources(kb_id, self.data_sources)
            pp.pprint(ds_list)
        except self.bedrock_agent_client.exceptions.ConflictException:
            ds_id = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=kb['knowledgeBaseId'],
                maxResults=100
            )['dataSourceSummaries'][0]['dataSourceId']
            get_ds_response = self.bedrock_agent_client.get_data_source(
                dataSourceId=ds_id,
                knowledgeBaseId=kb['knowledgeBaseId']
            )
            ds = get_ds_response["dataSource"]
            pp.pprint(ds)
        return kb, ds_list
    
    def create_data_sources(self, kb_id, data_sources):
        """
        Create Data Sources for the Knowledge Base. 
        """
        ds_list=[]

        # create data source for each data source type in list data_sources
        for idx, ds in enumerate(data_sources):

            # The data source to ingest documents from, into the OpenSearch serverless knowledge base index
            s3_data_source_congiguration = {
                    "type": "S3",
                    "s3Configuration":{
                        "bucketArn": "",
                        # "inclusionPrefixes":["*.*"] # you can use this if you want to create a KB using data within s3 prefixes.
                        }
                }
            
            confluence_data_source_congiguration = {
                "confluenceConfiguration": {
                    "sourceConfiguration": {
                        "hostUrl": "",
                        "hostType": "SAAS",
                        "authType": "", # BASIC | OAUTH2_CLIENT_CREDENTIALS
                        "credentialsSecretArn": ""
                        
                    },
                    "crawlerConfiguration": {
                        "filterConfiguration": {
                            "type": "PATTERN",
                            "patternObjectFilter": {
                                "filters": [
                                    {
                                        "objectType": "Attachment",
                                        "inclusionFilters": [
                                            ".*\\.pdf"
                                        ],
                                        "exclusionFilters": [
                                            ".*private.*\\.pdf"
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                },
                "type": "CONFLUENCE"
            }

            sharepoint_data_source_congiguration = {
                "sharePointConfiguration": {
                    "sourceConfiguration": {
                        "tenantId": "",
                        "hostType": "ONLINE",
                        "domain": "domain",
                        "siteUrls": [],
                        "authType": "", # BASIC | OAUTH2_CLIENT_CREDENTIALS
                        "credentialsSecretArn": ""
                        
                    },
                    "crawlerConfiguration": {
                        "filterConfiguration": {
                            "type": "PATTERN",
                            "patternObjectFilter": {
                                "filters": [
                                    {
                                        "objectType": "Attachment",
                                        "inclusionFilters": [
                                            ".*\\.pdf"
                                        ],
                                        "exclusionFilters": [
                                            ".*private.*\\.pdf"
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                },
                "type": "SHAREPOINT"
            }


            salesforce_data_source_congiguration = {
                "salesforceConfiguration": {
                    "sourceConfiguration": {
                        "hostUrl": "",
                        "authType": "", # BASIC | OAUTH2_CLIENT_CREDENTIALS
                        "credentialsSecretArn": ""
                    },
                    "crawlerConfiguration": {
                        "filterConfiguration": {
                            "type": "PATTERN",
                            "patternObjectFilter": {
                                "filters": [
                                    {
                                        "objectType": "Attachment",
                                        "inclusionFilters": [
                                            ".*\\.pdf"
                                        ],
                                        "exclusionFilters": [
                                            ".*private.*\\.pdf"
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                },
                "type": "SALESFORCE"
            }

            webcrawler_data_source_congiguration = {
                "webConfiguration": {
                    "sourceConfiguration": {
                        "urlConfiguration": {
                            "seedUrls": []
                        }
                    },
                    "crawlerConfiguration": {
                        "crawlerLimits": {
                            "rateLimit": 50
                        },
                        "scope": "HOST_ONLY",
                        "inclusionFilters": [],
                        "exclusionFilters": []
                    }
                },
                "type": "WEB"
            }

            # Set the data source configuration based on the Data source type

            if ds['type'] == "S3":
                print(f'{idx +1 } data source: S3')
                ds_name = f'{kb_id}-s3'
                s3_data_source_congiguration["s3Configuration"]["bucketArn"] = f'arn:aws:s3:::{ds["bucket_name"]}'
                # print(s3_data_source_congiguration)
                data_source_configuration = s3_data_source_congiguration
            
            if ds['type'] == "CONFLUENCE":
                print(f'{idx +1 } data source: CONFLUENCE')
                ds_name = f'{kb_id}-confluence'
                confluence_data_source_congiguration['confluenceConfiguration']['sourceConfiguration']['hostUrl'] = ds['hostUrl']
                confluence_data_source_congiguration['confluenceConfiguration']['sourceConfiguration']['authType'] = ds['authType']
                confluence_data_source_congiguration['confluenceConfiguration']['sourceConfiguration']['credentialsSecretArn'] = ds['credentialsSecretArn']
                # print(confluence_data_source_congiguration)
                data_source_configuration = confluence_data_source_congiguration

            if ds['type'] == "SHAREPOINT":
                print(f'{idx +1 } data source: SHAREPOINT')
                ds_name = f'{kb_id}-sharepoint'
                sharepoint_data_source_congiguration['sharePointConfiguration']['sourceConfiguration']['tenantId'] = ds['tenantId']
                sharepoint_data_source_congiguration['sharePointConfiguration']['sourceConfiguration']['domain'] = ds['domain']
                sharepoint_data_source_congiguration['sharePointConfiguration']['sourceConfiguration']['authType'] = ds['authType']
                sharepoint_data_source_congiguration['sharePointConfiguration']['sourceConfiguration']['siteUrls'] = ds["siteUrls"]
                sharepoint_data_source_congiguration['sharePointConfiguration']['sourceConfiguration']['credentialsSecretArn'] = ds['credentialsSecretArn']
                # print(sharepoint_data_source_congiguration)
                data_source_configuration = sharepoint_data_source_congiguration


            if ds['type'] == "SALESFORCE":
                print(f'{idx +1 } data source: SALESFORCE')
                ds_name = f'{kb_id}-salesforce'
                salesforce_data_source_congiguration['salesforceConfiguration']['sourceConfiguration']['hostUrl'] = ds['hostUrl']
                salesforce_data_source_congiguration['salesforceConfiguration']['sourceConfiguration']['authType'] = ds['authType']
                salesforce_data_source_congiguration['salesforceConfiguration']['sourceConfiguration']['credentialsSecretArn'] = ds['credentialsSecretArn']
                # print(salesforce_data_source_congiguration)
                data_source_configuration = salesforce_data_source_congiguration

            if ds['type'] == "WEB":
                print(f'{idx +1 } data source: WEB')
                ds_name = f'{kb_id}-web'
                webcrawler_data_source_congiguration['webConfiguration']['sourceConfiguration']['urlConfiguration']['seedUrls'] = ds['seedUrls']
                webcrawler_data_source_congiguration['webConfiguration']['crawlerConfiguration']['inclusionFilters'] = ds['inclusionFilters']
                webcrawler_data_source_congiguration['webConfiguration']['crawlerConfiguration']['exclusionFilters'] = ds['exclusionFilters']
                # print(webcrawler_data_source_congiguration)
                data_source_configuration = webcrawler_data_source_congiguration
                

            # Create a DataSource in KnowledgeBase 
            chunking_strategy_configuration = self.create_chunking_strategy_config(self.chunking_strategy)
            print("============Chunking config========\n", chunking_strategy_configuration)
            vector_ingestion_configuration = chunking_strategy_configuration

            if self.multi_modal:
                if self.parser == "BEDROCK_FOUNDATION_MODEL":
                    parsing_configuration = {"bedrockFoundationModelConfiguration": 
                                             {"parsingModality": "MULTIMODAL", "modelArn": f"arn:aws:bedrock:{self.region_name}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"}, 
                                             "parsingStrategy": "BEDROCK_FOUNDATION_MODEL"}
                    
                if self.parser == 'BEDROCK_DATA_AUTOMATION':
                    parsing_configuration = {"bedrockDataAutomationConfiguration": {"parsingModality": "MULTIMODAL"}, "parsingStrategy": "BEDROCK_DATA_AUTOMATION"}    

                vector_ingestion_configuration["parsingConfiguration"] = parsing_configuration

            create_ds_response = self.bedrock_agent_client.create_data_source(
                name = ds_name,
                description = self.kb_description,
                knowledgeBaseId = kb_id,
                dataSourceConfiguration = data_source_configuration,
                vectorIngestionConfiguration = vector_ingestion_configuration
            )
            ds = create_ds_response["dataSource"]
            pp.pprint(ds)
            # self.data_sources[idx]['dataSourceId'].append(ds['dataSourceId'])
            ds_list.append(ds)
        return ds_list
        

    def start_ingestion_job(self):
        """
        Start an ingestion job to synchronize data from an S3 bucket to the Knowledge Base
        """

        for idx, ds in enumerate(self.data_sources):
            try:
                start_job_response = self.bedrock_agent_client.start_ingestion_job(
                    knowledgeBaseId=self.knowledge_base['knowledgeBaseId'],
                    dataSourceId=self.data_source[idx]["dataSourceId"]
                )
                job = start_job_response["ingestionJob"]
                print(f"job {idx+1} started successfully\n")
                # pp.pprint(job)
                while job['status'] not in ["COMPLETE", "FAILED", "STOPPED"]:
                    get_job_response = self.bedrock_agent_client.get_ingestion_job(
                        knowledgeBaseId=self.knowledge_base['knowledgeBaseId'],
                        dataSourceId=self.data_source[idx]["dataSourceId"],
                        ingestionJobId=job["ingestionJobId"]
                    )
                    job = get_job_response["ingestionJob"]
                pp.pprint(job)
                interactive_sleep(40)

            except Exception as e:
                print(f"Couldn't start {idx} job.\n")
                print(e)
            

    def get_knowledge_base_id(self):
        """
        Get Knowledge Base Id
        """
        pp.pprint(self.knowledge_base["knowledgeBaseId"])
        return self.knowledge_base["knowledgeBaseId"]

    def get_bucket_name(self):
        """
        Get the name of the bucket connected with the Knowledge Base Data Source
        """
        pp.pprint(f"Bucket connected with KB: {self.bucket_name}")
        return self.bucket_name

    def delete_kb(self, delete_s3_bucket=False, delete_iam_roles_and_policies=True, delete_lambda_function=False):
        """
        Delete the Knowledge Base resources
        Args:
            delete_s3_bucket (bool): boolean to indicate if s3 bucket should also be deleted
            delete_iam_roles_and_policies (bool): boolean to indicate if IAM roles and Policies should also be deleted
            delete_lambda_function (bool): boolean to indicate if Lambda function should also be deleted
        """
        
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")

            # delete knowledge base and data source.
            
            # Delete knowledge base and data sources
            try:
                # First delete all data sources
                for ds in self.data_source:
                    try:
                        self.bedrock_agent_client.delete_data_source(
                            dataSourceId=ds["dataSourceId"],
                            knowledgeBaseId=self.knowledge_base['knowledgeBaseId']
                        )
                        print(f"Deleted data source {ds['dataSourceId']}")
                    except self.bedrock_agent_client.exceptions.ResourceNotFoundException:
                        print(f"Data source {ds['dataSourceId']} not found")
                    except Exception as e:
                        print(f"Error deleting data source {ds['dataSourceId']}: {str(e)}")

                # Then delete the knowledge base
                self.bedrock_agent_client.delete_knowledge_base(
                    knowledgeBaseId=self.knowledge_base['knowledgeBaseId']
                )
                print("======== Knowledge base and all data sources deleted =========")
            
            except self.bedrock_agent_client.exceptions.ResourceNotFoundException as e:
                print("Knowledge base not found:", e)
            except Exception as e:
                print(f"Error during knowledge base deletion: {str(e)}")

            # delete s3 bucket
            if delete_s3_bucket==True:
                    self.delete_s3()
                    
            # delete IAM role and policies
            if delete_iam_roles_and_policies:
                self.delete_iam_roles_and_policies()
            
            if delete_lambda_function:
                try:
                    self.delete_lambda_function()
                    print(f"Deleted Lambda function {self.lambda_function_name}")
                except self.lambda_client.exceptions.ResourceNotFoundException:
                    print(f"Lambda function {self.lambda_function_name} not found.")

            # delete vector index and collection from vector store
            if self.vector_store=="OPENSEARCH_SERVERLESS":
                try:
                    self.aoss_client.delete_collection(id=self.collection_id)
                    self.aoss_client.delete_access_policy(
                        type="data",
                        name=self.access_policy_name
                    )
                    self.aoss_client.delete_security_policy(
                        type="network",
                        name=self.network_policy_name
                    )
                    self.aoss_client.delete_security_policy(
                        type="encryption",
                        name=self.encryption_policy_name
                    )
                    print("======== Vector Index, collection and associated policies deleted =========")
                except Exception as e:
                    print(e)
            else: 
                try: 
                    # disable delete protection
                    response = self.neptune_client.update_graph(
                        graphIdentifier=self.graph_id,
                        deletionProtection=False)
                    print("======= Delete protection disabled before deleting the graph: ", response['deletionProtection'])

                    # delete the graph
                    self.neptune_client.delete_graph(
                        graphIdentifier=self.graph_id,
                        skipSnapshot=True)
                    print("========= Neptune Analytics Graph Deleted =================================")
                except Exception as e:
                    print(e)

            
    def delete_iam_roles_and_policies(self):
        for role_name in self.roles:
            print(f"Found role {role_name}")
            try:
                self.iam_client.get_role(RoleName=role_name)
            except self.iam_client.exceptions.NoSuchEntityException:
                print(f"Role {role_name} does not exist") 
                continue
            attached_policies = self.iam_client.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]
            print(f"======Attached policies with role {role_name}========\n", attached_policies)
            for attached_policy in attached_policies:
                policy_arn = attached_policy["PolicyArn"]
                policy_name = attached_policy["PolicyName"]
                self.iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                print(f"Detached policy {policy_name} from role {role_name}")
                if str(policy_arn.split("/")[1]) == "service-role":
                    print(f"Skipping deletion of service-linked role policy {policy_name}")
                else: 
                    self.iam_client.delete_policy(PolicyArn=policy_arn)
                    print(f"Deleted policy {policy_name} from role {role_name}")
                
            self.iam_client.delete_role(RoleName=role_name)
            print(f"Deleted role {role_name}")
        print("======== All IAM roles and policies deleted =========")

    def bucket_exists(bucket):
        s3 = boto3.resource('s3')
        return s3.Bucket(bucket) in s3.buckets.all()

    def delete_s3(self):
        """
        Delete the objects contained in the Knowledge Base S3 bucket.
        Once the bucket is empty, delete the bucket
        """
        s3 = boto3.resource('s3')
        bucket_names = self.bucket_names.copy()
        if self.intermediate_bucket_name:
            bucket_names.append(self.intermediate_bucket_name)

        for bucket_name in bucket_names:
            try:
                bucket = s3.Bucket(bucket_name)
                if bucket in s3.buckets.all():
                    print(f"Found bucket {bucket_name}")
                    # Delete all objects including versions (if versioning enabled)
                    bucket.object_versions.delete()
                    bucket.objects.all().delete()
                    print(f"Deleted all objects in bucket {bucket_name}")
                    
                    # Delete the bucket
                    bucket.delete()
                    print(f"Deleted bucket {bucket_name}")
                else:
                    print(f"Bucket {bucket_name} does not exist, skipping deletion")
            except Exception as e:
                print(f"Error deleting bucket {bucket_name}: {str(e)}")

        print("======== S3 bucket deletion process completed =========")


    def delete_lambda_function(self):
        """
        Delete the Knowledge Base Lambda function
        Delete the IAM role used by the Knowledge Base Lambda function
        """
        # delete lambda function
        try:
            self.lambda_client.delete_function(FunctionName=self.lambda_function_name)
            print(f"======== Lambda function {self.lambda_function_name} deleted =========")
        except Exception as e:
            print(e)