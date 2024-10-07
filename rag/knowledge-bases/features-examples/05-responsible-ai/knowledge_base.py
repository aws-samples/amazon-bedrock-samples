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
warnings.filterwarnings('ignore')

valid_embedding_models = ["cohere.embed-multilingual-v3", 
                          "cohere.embed-english-v3", 
                          "amazon.titan-embed-text-v1", 
                          "amazon.titan-embed-text-v2:0"]

# create a dictionary with model id as key and context length as value
embedding_context_dimensions = {
    "cohere.embed-multilingual-v3": 512,
    "cohere.embed-english-v3": 512,
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024
}
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


class BedrockKnowledgeBase:
    """
    Support class that allows for:
        - creation (or retrieval) of a Knowledge Base for Amazon Bedrock with all its pre-requisites
          (including OSS, IAM roles and Permissions and S3 bucket)
        - Ingestion of data into the Knowledge Base
        - Deletion of all resources created
    """
    account_number = boto3.client('sts').get_caller_identity().get('Account')
    region_name=boto3.session.Session().region_name
    suffix = f'{region_name}-{account_number}'
    kb_name = f"default-knowledge-base-{suffix}"
    kb_description = "Default Knowledge Base"
    bucket_name = f"{kb_name}-{suffix}"

    def __init__(
            self,
            kb_name=kb_name,
            kb_description=kb_description,
            data_bucket_name=bucket_name,
            intermediate_bucket_name=f"{kb_name}-intermediate-{suffix}",
            lambda_function_name=f"{kb_name}-intermediate-{suffix}",
            embedding_model="amazon.titan-embed-text-v2:0",
            chunking_strategy="FIXED_SIZE", 
            suffix=suffix,
    ):
        """
        Class initializer
        Args:
            kb_name(str): The name of the Knowledge Base.
            kb_description(str): The description of the Knowledge Base.
            data_bucket_name(str): The name of the S3 bucket to be used as the data source for the Knowledge Base.
            intermediate_bucket_name(str): The name of the intermediate S3 bucket to be used for custom chunking strategy.
            lambda_function_name(str): The name of the Lambda function to be used for custom chunking strategy.
            embedding_model(str): The embedding model to be used for the Knowledge Base.
            chunking_strategy(str): The chunking strategy to be used for the Knowledge Base.
            suffix(str): A suffix to be used for naming resources.
        """
        boto3_session = boto3.session.Session()
        self.region_name = boto3_session.region_name
        self.iam_client = boto3_session.client('iam')
        self.lambda_client = boto3.client('lambda')
        self.account_number = boto3.client('sts').get_caller_identity().get('Account')
        self.suffix = suffix
        self.identity = boto3.client('sts').get_caller_identity()['Arn']
        self.aoss_client = boto3_session.client('opensearchserverless')
        self.s3_client = boto3.client('s3')
        self.bedrock_agent_client = boto3.client('bedrock-agent')
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWSV4SignerAuth(credentials, self.region_name, 'aoss')
        self.bucket_name = data_bucket_name
        
        if chunking_strategy == "CUSTOM":
                self.intermediate_bucket_name = intermediate_bucket_name
                self.lambda_function_name = lambda_function_name
        else:
            self.intermediate_bucket_name = None
            self.lambda_function_name = None
        
        self.kb_name = kb_name
        self.kb_description = kb_description
        self.chunking_strategy = chunking_strategy
        if embedding_model not in valid_embedding_models:
            valid_embeddings_str = str(valid_embedding_models)
            raise ValueError(f"Invalid embedding model. Your embedding model should be one of {valid_embeddings_str}")
        self.embedding_model = embedding_model
        self.encryption_policy_name = f"bedrock-sample-rag-sp-{self.suffix}"
        self.network_policy_name = f"bedrock-sample-rag-np-{self.suffix}"
        self.access_policy_name = f'bedrock-sample-rag-ap-{self.suffix}'
        self.kb_execution_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_{self.suffix}'
        self.fm_policy_name = f'AmazonBedrockFoundationModelPolicyForKnowledgeBase_{self.suffix}'
        self.s3_policy_name = f'AmazonBedrockS3PolicyForKnowledgeBase_{self.suffix}'
        self.oss_policy_name = f'AmazonBedrockOSSPolicyForKnowledgeBase_{self.suffix}'
        self.lambda_policy_name = f'AmazonBedrockLambdaPolicyForKnowledgeBase_{self.suffix}'
        self.lambda_arn = None
        self.roles = []
        self.roles.append(self.kb_execution_role_name)

        self.vector_store_name = f'bedrock-sample-rag-{self.suffix}'
        self.index_name = f"bedrock-sample-rag-index-{self.suffix}"
        print("========================================================================================")
        print(f"Step 1 - Creating or retrieving S3 bucket(s) for Knowledge Base documents")
        self.create_s3_bucket()
        
        print("========================================================================================")
        print(f"Step 2 - Creating Knowledge Base Execution Role ({self.kb_execution_role_name}) and Policies")
        self.bedrock_kb_execution_role = self.create_bedrock_kb_execution_role()
        self.bedrock_kb_execution_role_name = self.bedrock_kb_execution_role['Role']['RoleName']
        print("========================================================================================")
        print(f"Step 3 - Creating OSS encryption, network and data access policies")
        self.encryption_policy, self.network_policy, self.access_policy = self.create_policies_in_oss()
        print("========================================================================================")
        print(f"Step 4 - Creating OSS Collection (this step takes a couple of minutes to complete)")
        self.host, self.collection, self.collection_id, self.collection_arn = self.create_oss()
        # Build the OpenSearch client
        self.oss_client = OpenSearch(
            hosts=[{'host': self.host, 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )
        print("========================================================================================")
        print(f"Step 5 - Creating OSS Vector Index")
        self.create_vector_index()
        print("========================================================================================")
        print(f"Step 6 - Will create Lambda Function if chunking strategy selected as CUSTOM")
        if self.chunking_strategy == "CUSTOM":
            print(f"Creating lambda function... as chunking strategy is {self.chunking_strategy}")
            response = self.create_lambda()
            self.lambda_arn = response['FunctionArn']
            print(response)
            print(f"Lambda function ARN: {self.lambda_arn}")
        else: 
            print(f"Not creating lambda function as chunking strategy is {self.chunking_strategy}")
        print("========================================================================================")
        print(f"Step 7 - Creating Knowledge Base")
        self.knowledge_base, self.data_source = self.create_knowledge_base()
        print("========================================================================================")

    
    def create_s3_bucket(self):
        """
        Check if buckets exist, and if not create S3 buckets for knowledge base data source
        """
        buckets_to_check = [self.bucket_name]
        if self.chunking_strategy == "CUSTOM":
            buckets_to_check.append(self.intermediate_bucket_name)

        existing_buckets = []
        for bucket_name in buckets_to_check:
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                existing_buckets.append(bucket_name)
                print(f'Bucket {bucket_name} already exists - retrieving it!')
            except ClientError:
                pass

        buckets_to_create = [b for b in buckets_to_check if b not in existing_buckets]
        print(buckets_to_create)

        for bucket_name in buckets_to_create:
            print(f'Creating bucket {bucket_name}')
            if self.region_name == "us-east-1":
                self.s3_client.create_bucket(
                    Bucket=bucket_name
                )
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region_name}
                )
            # bucket_config = {'LocationConstraint': self.region_name} if self.region_name != "us-east-1" else {}
            # self.s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=bucket_config)

    
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

    def create_bedrock_kb_execution_role(self):
        """
        Create Knowledge Base Execution IAM Role and its required policies.
        If role and/or policies already exist, retrieve them
        Returns:
            IAM role
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
                        f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.embedding_model}"
                    ]
                }
            ]
        }
        if self.chunking_strategy == "CUSTOM":
            s3_policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "S3ListBucketStatement",
                        "Effect": "Allow",
                        "Action": [
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{self.bucket_name}"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": [
                                    f"{self.account_number}"
                                ]
                            }
                        }
                    },
                    {
                        "Sid": "S3GetObjectStatement",
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{self.bucket_name}",
                            f"arn:aws:s3:::{self.intermediate_bucket_name}/*",
                            f"arn:aws:s3:::{self.bucket_name}/*"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": [
                                    f"{self.account_number}"
                                ]
                            }
                        }
                    },
                    {
                        "Sid": "S3PutObjectStatement",
                        "Effect": "Allow",
                        "Action": [
                            "s3:PutObject"
                        ],
                        "Resource": [
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
        else:
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
                            f"arn:aws:s3:::{self.bucket_name}",
                            f"arn:aws:s3:::{self.bucket_name}/*"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": f"{self.account_number}"
                            }
                        }
                    }
                ]
            }
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
        try:
            # create policies based on the policy documents
            fm_policy = self.iam_client.create_policy(
                PolicyName=self.fm_policy_name,
                PolicyDocument=json.dumps(foundation_model_policy_document),
                Description='Policy for accessing foundation model',
            )
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            fm_policy = self.iam_client.get_policy(
                PolicyArn=f"arn:aws:iam::{self.account_number}:policy/{self.fm_policy_name}"
            )

        try:
            s3_policy = self.iam_client.create_policy(
                PolicyName=self.s3_policy_name,
                PolicyDocument=json.dumps(s3_policy_document),
                Description='Policy for reading documents from s3')
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            s3_policy = self.iam_client.get_policy(
                PolicyArn=f"arn:aws:iam::{self.account_number}:policy/{self.s3_policy_name}"
            )
        
         # create bedrock execution role
        try:
            bedrock_kb_execution_role = self.iam_client.create_role(
                RoleName=self.kb_execution_role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
                Description='Amazon Bedrock Knowledge Base Execution Role for accessing OSS and S3',
                MaxSessionDuration=3600
            )
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            bedrock_kb_execution_role = self.iam_client.get_role(
                RoleName=self.kb_execution_role_name
            )
        
        # create lambda policy if chunking strategy is CUSTOM
        if self.chunking_strategy == "CUSTOM":
            try: 
                lambda_policy = self.iam_client.create_policy(
                    PolicyName=self.lambda_policy_name,
                    PolicyDocument=json.dumps(lambda_policy_document),
                    Description='Policy for invoking lambda function'
                )
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                lambda_policy = self.iam_client.get_policy(
                    PolicyArn=f"arn:aws:iam::{self.account_number}:policy/{self.lambda_policy_name}"
                )

            lambda_policy_arn = lambda_policy["Policy"]["Arn"]
            self.iam_client.attach_role_policy(
                RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
                PolicyArn=lambda_policy_arn
            )
               
       
        # fetch arn of the policies and role created above
        s3_policy_arn = s3_policy["Policy"]["Arn"]
        fm_policy_arn = fm_policy["Policy"]["Arn"]

        # attach policies to Amazon Bedrock execution role
        self.iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=fm_policy_arn
        )
        self.iam_client.attach_role_policy(
            RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=s3_policy_arn
        )
        return bedrock_kb_execution_role

    def create_oss_policy_attach_bedrock_execution_role(self, collection_id):
        """
        Create OpenSearch Serverless policy and attach it to the Knowledge Base Execution role.
        If policy already exists, attaches it
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

        oss_policy_arn = f"arn:aws:iam::{self.account_number}:policy/{self.oss_policy_name}"
        created = False
        try:
            self.iam_client.create_policy(
                PolicyName=self.oss_policy_name,
                PolicyDocument=json.dumps(oss_policy_document),
                Description='Policy for accessing opensearch serverless',
            )
            created = True
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            print(f"Policy {oss_policy_arn} already exists, skipping creation")
        print("Opensearch serverless arn: ", oss_policy_arn)

        self.iam_client.attach_role_policy(
            RoleName=self.bedrock_kb_execution_role["Role"]["RoleName"],
            PolicyArn=oss_policy_arn
        )
        return created

    def create_policies_in_oss(self):
        """
        Create OpenSearch Serverless encryption, network and data access policies.
        If policies already exist, retrieve them
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
            pp.pprint(collection)
            collection_id = collection['id']
            collection_arn = collection['arn']
        pp.pprint(collection)

        # Get the OpenSearch serverless collection URL
        host = collection_id + '.' + self.region_name + '.aoss.amazonaws.com'
        print(host)
        # wait for collection creation
        # This can take couple of minutes to finish
        response = self.aoss_client.batch_get_collection(names=[self.vector_store_name])
        # Periodically check collection status
        while (response['collectionDetails'][0]['status']) == 'CREATING':
            print('Creating collection...')
            interactive_sleep(30)
            response = self.aoss_client.batch_get_collection(names=[self.vector_store_name])
        print('\nCollection successfully created:')
        pp.pprint(response["collectionDetails"])
        # create opensearch serverless access policy and attach it to Bedrock execution role
        try:
            created = self.create_oss_policy_attach_bedrock_execution_role(collection_id)
            if created:
                # It can take up to a minute for data access rules to be enforced
                print("Sleeping for a minute to ensure data access rules have been enforced")
                interactive_sleep(60)
            return host, collection, collection_id, collection_arn
        except Exception as e:
            print("Policy already exists")
            pp.pprint(e)

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
                        "dimension": embedding_context_dimensions[self.embedding_model], # use dimension as per the context length of embeddings model selected.
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

        # Create index
        try:
            response = self.oss_client.indices.create(index=self.index_name, body=json.dumps(body_json))
            print('\nCreating index:')
            pp.pprint(response)

            # index creation can take up to a minute
            interactive_sleep(60)
        except RequestError as e:
            # you can delete the index if its already exists
            # oss_client.indices.delete(index=index_name)
            print(
                f'Error while trying to create the index, with error {e.error}\nyou may unmark the delete above to '
                f'delete, and recreate the index')
    
    def create_chunking_strategy_config(self, strategy):
        configs = {
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
    def create_knowledge_base(self):
        """
        Create Knowledge Base and its Data Source. If existent, retrieve
        """
        opensearch_serverless_configuration = {
            "collectionArn": self.collection_arn,
            "vectorIndexName": self.index_name,
            "fieldMapping": {
                "vectorField": "vector",
                "textField": "text",
                "metadataField": "text-metadata"
            }
        }

        chunking_strategy_configuration = {}
        # vectorIngestionConfiguration = {}

        print(f"Creating KB with chunking strategy - {self.chunking_strategy}")
        chunking_strategy_configuration = self.create_chunking_strategy_config(self.chunking_strategy)
        print("============Chunking config========\n", chunking_strategy_configuration)

        # The data source to ingest documents from, into the OpenSearch serverless knowledge base index
        s3_configuration = {
            "bucketArn": f"arn:aws:s3:::{self.bucket_name}",
            # "inclusionPrefixes":["*.*"] # you can use this if you want to create a KB using data within s3 prefixes.
        }

        # The embedding model used by Bedrock to embed ingested documents, and realtime prompts
        embedding_model_arn = f"arn:aws:bedrock:{self.region_name}::foundation-model/{self.embedding_model}"
        try:
            create_kb_response = self.bedrock_agent_client.create_knowledge_base(
                name=self.kb_name,
                description=self.kb_description,
                roleArn=self.bedrock_kb_execution_role['Role']['Arn'],
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
            pp.pprint(kb)
        except self.bedrock_agent_client.exceptions.ConflictException:
            kbs = self.bedrock_agent_client.list_knowledge_bases(
                maxResults=100
            )
            kb_id = None
            for kb in kbs['knowledgeBaseSummaries']:
                if kb['name'] == self.kb_name:
                    kb_id = kb['knowledgeBaseId']
            response = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
            kb = response['knowledgeBase']
            pp.pprint(kb)

        # Create a DataSource in KnowledgeBase
        try:
            print(self.kb_name)
            print(kb['knowledgeBaseId'])
            print(s3_configuration)
            create_ds_response = self.bedrock_agent_client.create_data_source(
                name=self.kb_name,
                description=self.kb_description,
                knowledgeBaseId=kb['knowledgeBaseId'],
                dataSourceConfiguration={
                    "type": "S3",
                    "s3Configuration": s3_configuration
                },
                vectorIngestionConfiguration = chunking_strategy_configuration, 
                dataDeletionPolicy='RETAIN'
            )
            ds = create_ds_response["dataSource"]
            pp.pprint(ds)
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
        return kb, ds

    def start_ingestion_job(self):
        """
        Start an ingestion job to synchronize data from an S3 bucket to the Knowledge Base
        """
        # Start an ingestion job
        start_job_response = self.bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=self.knowledge_base['knowledgeBaseId'],
            dataSourceId=self.data_source["dataSourceId"]
        )
        job = start_job_response["ingestionJob"]
        pp.pprint(job)
        # Get job
        while job['status'] != 'COMPLETE':
            get_job_response = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.knowledge_base['knowledgeBaseId'],
                dataSourceId=self.data_source["dataSourceId"],
                ingestionJobId=job["ingestionJobId"]
            )
            job = get_job_response["ingestionJob"]
        pp.pprint(job)
        interactive_sleep(40)

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
            # delete vector index and collection from vector store
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

            # delete knowledge base and vector store.
            
            try:
                self.bedrock_agent_client.delete_data_source(
                    dataSourceId=self.data_source["dataSourceId"],
                    knowledgeBaseId=self.knowledge_base['knowledgeBaseId']
                )
                self.bedrock_agent_client.delete_knowledge_base(
                    knowledgeBaseId=self.knowledge_base['knowledgeBaseId']
                )
                print("======== Knowledge base and data source deleted =========")
            except self.bedrock_agent_client.exceptions.ResourceNotFoundException as e:
                print("Resource not found", e)
                pass
            except Exception as e:
                print(e)

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
        try:
            objects = self.s3_client.list_objects(Bucket=self.bucket_name)
            if 'Contents' in objects:
                for obj in objects['Contents']:
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
            self.s3_client.delete_bucket(Bucket=self.bucket_name)
            print("======== S3 data bucket deleted =========")
        except Exception as e:
            print(e)

        if self.intermediate_bucket_name is not None:
            bucket = s3.Bucket(self.intermediate_bucket_name)
            print("intermediate bucket: ", bucket)
            if bucket in s3.buckets.all():
                print(f"Found intermediate bucket {self.intermediate_bucket_name}")
                try:
                    objects = self.s3_client.list_objects(Bucket=self.intermediate_bucket_name)
                    if 'Contents' in objects:
                        for obj in objects['Contents']:
                            print(f"Deleting {obj['Key']}")
                            self.s3_client.delete_object(Bucket=self.intermediate_bucket_name, Key=obj['Key'])
                        print("======== Intermediate S3 bucket emptied - will wait for 20s before deleting bucket =========")
                        interactive_sleep(20)
                    self.s3_client.delete_bucket(Bucket=self.intermediate_bucket_name)
                    print("======== Intermediate S3 bucket deleted =========")
                except Exception as e:
                    print(f"{self.intermediate_bucket_name} does not exist, therefore, will skip deleting")
        else:
            print("No intermediate bucket found")


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