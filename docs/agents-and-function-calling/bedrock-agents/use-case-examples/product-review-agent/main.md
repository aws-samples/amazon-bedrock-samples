---
tags:
    - Use cases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/use-case-examples/product-review-agent/main.ipynb){:target="_blank"}"

```python
<h2>%pip install -r requirements.txt</h2>
```

<h3>Import libraries</h3>


```python
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
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
```


```python
<h2>setting logger</h2>
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
```

<h3>Setup AWS service clients</h3>


```python
<h2>getting boto3 clients for required AWS services</h2>
sts_client = boto3.client('sts')
iam_client = boto3.client('iam')
s3_client = boto3.client('s3',region_name='us-east-1')
lambda_client = boto3.client('lambda')
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
open_search_serverless_client = boto3.client('opensearchserverless')
```


```python
session = boto3.session.Session()
region = session.region_name
account_id = sts_client.get_caller_identity()["Account"]
region, account_id
```

<h3>Setup constants</h3>


```python
<h2>Generate random prefix for unique IAM roles, agent name and S3 Bucket and </h2>
<h2>assign variables</h2>
suffix = f"{region}-{account_id}"
agent_name = "product-reviews-agent-kb"
agent_alias_name = "agent-alias"
bucket_name = f'{agent_name}-{suffix}'
bucket_arn = f"arn:aws:s3:::{bucket_name}"
bedrock_agent_bedrock_allow_policy_name = f"pra-bedrock-allow-{suffix}"
bedrock_agent_s3_allow_policy_name = f"pra-s3-allow-{suffix}"
bedrock_agent_kb_allow_policy_name = f"pra-kb-allow-{suffix}"
lambda_role_name = f'{agent_name}-lambda-role-{suffix}'
agent_role_name = f'AmazonBedrockExecutionRoleForAgents_pra'
lambda_function_path = "lambda_function"
lambda_name = f'{agent_name}-{suffix}'
lambda_aoss_allow_policy_name = f'lambda-aoss-allow-{suffix}'
lambda_kb_allow_policy_name = f'lambda-kb-allow-{suffix}'
lambda_invoke_allow_policy_name = f'lambda-invoke-allow-{suffix}'
kb_name = f'product-reviews-kb-{suffix}'
data_source_name = f'product-reviews-kb-docs-{suffix}'
kb_files_path = 'kb_documents'
kb_key = 'kb_documents'
kb_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_prakb'
kb_bedrock_allow_policy_name = f"pra-kb-bedrock-allow-{suffix}"
kb_aoss_allow_policy_name = f"pra-kb-aoss-allow-{suffix}"
kb_s3_allow_policy_name = f"pra-kb-s3-allow-{suffix}"
kb_collection_name = f'pra-kbc-{suffix}'
llm_model_arn = f"arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
<h2>Select cohere as the embedding model</h2>
embedding_model_arn = f'arn:aws:bedrock:{region}::foundation-model/cohere.embed-english-v3'
kb_vector_index_name = "bedrock-knowledge-base-index"
kb_metadataField = 'bedrock-knowledge-base-metadata'
kb_textField = 'bedrock-knowledge-base-text'
kb_vectorField = 'bedrock-knowledge-base-vector'
```

<h3>Download dataset</h3>


```python
try:
    os.mkdir('data')
except:
    print('data exists')
```


```python
!curl -o 'data/All_Beauty_5.json.gz' 'https://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/All_Beauty_5.json.gz' --insecure
```


```python
!gzip -d 'data/All_Beauty_5.json.gz'
```


```python
try:
    os.mkdir(kb_files_path) 
except:
    print(f'{kb_files_path} exists')
```

<h3>Create documents with metadata</h3>


```python
import json
import pandas as pd
import numpy as np
reviewers = ['jokic','levert','lebron','curry','antman']
df = pd.read_json('data/All_Beauty_5.json',lines=True)
df = df.iloc[:100]
df['date'] = pd.to_datetime(df['reviewTime'])
df['timestamp'] = df['date'].astype(int)/10**6
for idx,row in df.iterrows():
    text = row['reviewText']
    metadata = {
        'metadataAttributes': {
            'rating': row['overall'],
            'timestamp':row['timestamp'],
            'reviewers': np.random.choice(reviewers,np.random.randint(1,6),replace=False).tolist()
        }
    }
    with open(f'{kb_files_path}/{idx}.txt','w') as f:
        f.write(text)
    with open(f'{kb_files_path}/{idx}.txt.metadata.json','w') as f:
        f.write(json.dumps(metadata))
```

<h3>Create S3 bucket and upload dataset to S3</h3>


```python
<h2>Create S3 bucket for dataset</h2>
if region == 'us-east-1':
    s3bucket = s3_client.create_bucket(
    Bucket=bucket_name)
else:
    s3bucket = s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={ 'LocationConstraint': region } 
    )
```


```python
<h2>Upload Knowledge Base files to this s3 bucket</h2>
for f in os.listdir(kb_files_path):
    s3_client.upload_file(kb_files_path+'/'+f, bucket_name, kb_key+'/'+f)
```

<h3>Allow Bedrock Knowledge Base to invoke OpenSearch Serverless and Bedrock LLM</h3>


```python
<h2>Create IAM policies for KB to invoke embedding model</h2>
bedrock_kb_allow_fm_model_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                embedding_model_arn
            ]
        }
    ]
}

kb_bedrock_policy_json = json.dumps(bedrock_kb_allow_fm_model_policy_statement)

kb_bedrock_policy = iam_client.create_policy(
    PolicyName=kb_bedrock_allow_policy_name,
    PolicyDocument=kb_bedrock_policy_json
)
```


```python
<h2>Create IAM policies for KB to access OpenSearch Serverless</h2>
bedrock_kb_allow_aoss_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "aoss:APIAccessAll",
            "Resource": [
                f"arn:aws:aoss:{region}:{account_id}:collection/*"
            ]
        }
    ]
}


kb_aoss_policy_json = json.dumps(bedrock_kb_allow_aoss_policy_statement)

kb_aoss_policy = iam_client.create_policy(
    PolicyName=kb_aoss_allow_policy_name,
    PolicyDocument=kb_aoss_policy_json
)
```


```python
kb_s3_allow_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowKBAccessDocuments",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                f"arn:aws:s3:::{bucket_name}/*",
                f"arn:aws:s3:::{bucket_name}"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:ResourceAccount": f"{account_id}"
                }
            }
        }
    ]
}


kb_s3_json = json.dumps(kb_s3_allow_policy_statement)
kb_s3_policy = iam_client.create_policy(
    PolicyName=kb_s3_allow_policy_name,
    PolicyDocument=kb_s3_json
)
```


```python
<h2>Create IAM Role for the agent and attach IAM policies</h2>
assume_role_policy_document = {
    "Version": "2012-10-17",
    "Statement": [{
          "Effect": "Allow",
          "Principal": {
            "Service": "bedrock.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
    }]
}

assume_role_policy_document_json = json.dumps(assume_role_policy_document)
kb_role = iam_client.create_role(
    RoleName=kb_role_name,
    AssumeRolePolicyDocument=assume_role_policy_document_json
)

<h2>Pause to make sure role is created</h2>
time.sleep(10)
    
iam_client.attach_role_policy(
    RoleName=kb_role_name,
    PolicyArn=kb_bedrock_policy['Policy']['Arn']
)

iam_client.attach_role_policy(
    RoleName=kb_role_name,
    PolicyArn=kb_aoss_policy['Policy']['Arn']
)

iam_client.attach_role_policy(
    RoleName=kb_role_name,
    PolicyArn=kb_s3_policy['Policy']['Arn']
)
```


```python
kb_role_arn = kb_role["Role"]["Arn"]
kb_role_arn
```

<h3>Create OpenSearch Serverless security and network policies</h3>


```python
<h2>Create OpenSearch Collection</h2>
security_policy_json = {
    "Rules": [
        {
            "ResourceType": "collection",
            "Resource":[
                f"collection/{kb_collection_name}"
            ]
        }
    ],
    "AWSOwnedKey": True
}
security_policy = open_search_serverless_client.create_security_policy(
    description='security policy of aoss collection',
    name=kb_collection_name,
    policy=json.dumps(security_policy_json),
    type='encryption'
)
```


```python
network_policy_json = [
  {
    "Rules": [
      {
        "Resource": [
          f"collection/{kb_collection_name}"
        ],
        "ResourceType": "dashboard"
      },
      {
        "Resource": [
          f"collection/{kb_collection_name}"
        ],
        "ResourceType": "collection"
      }
    ],
    "AllowFromPublic": True
  }
]

network_policy = open_search_serverless_client.create_security_policy(
    description='network policy of aoss collection',
    name=kb_collection_name,
    policy=json.dumps(network_policy_json),
    type='network'
)
```


```python
response = sts_client.get_caller_identity()
current_role = response['Arn']
current_role
```

<h3>Create OpensSearch Serverless Collection</h3>


```python
opensearch_collection_response = open_search_serverless_client.create_collection(
    description='OpenSearch collection for Amazon Bedrock Knowledge Base',
    name=kb_collection_name,
    standbyReplicas='DISABLED',
    type='VECTORSEARCH'
)
opensearch_collection_response
```


```python
collection_arn = opensearch_collection_response["createCollectionDetail"]["arn"]
collection_arn
```


```python
<h2>wait for collection creation</h2>
response = open_search_serverless_client.batch_get_collection(names=[kb_collection_name])
<h2>Periodically check collection status</h2>
while (response['collectionDetails'][0]['status']) == 'CREATING':
    print('Creating collection...')
    time.sleep(30)
    response = open_search_serverless_client.batch_get_collection(names=[kb_collection_name])
print('\nCollection successfully created:')
print(response["collectionDetails"])
<h2>Extract the collection endpoint from the response</h2>
host = (response['collectionDetails'][0]['collectionEndpoint'])
final_host = host.replace("https://", "")
final_host
```

<h3>Create lambda function zip</h3>


```python
try:
    os.mkdir('lambda_function') 
except:
    print(f'lambda_function exists')
```

    lambda_function exists



```python
%pip install --target 'lambda_function' boto3 opensearch-py
```


```python
%cp app.py lambda_function/
```


```python
def zipfolder(foldername, target_dir):            
    zipobj = zipfile.ZipFile(foldername + '.zip', 'w', zipfile.ZIP_DEFLATED)
    rootlen = len(target_dir) + 1
    for base, dirs, files in os.walk(target_dir):
        for file in files:
            fn = os.path.join(base, file)
            zipobj.write(fn, fn[rootlen:])
```


```python
zipfolder('lambda-package','lambda_function')
```

<h3>Allow Lambda function to invoke OpenSearch Serverless</h3>


```python
<h2>Create IAM Role for the Lambda function</h2>
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

    lambda_iam_role = iam_client.create_role(
        RoleName=lambda_role_name,
        AssumeRolePolicyDocument=assume_role_policy_document_json
    )

    # Pause to make sure role is created
    time.sleep(10)
except:
    lambda_iam_role = iam_client.get_role(RoleName=lambda_role_name)
```


```python
<h2>Create IAM policies for Lambda to access OpenSearch Serverless</h2>
lambda_allow_aoss_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "aoss:APIAccessAll",
            "Resource": [
                f"arn:aws:aoss:{region}:{account_id}:collection/*"
            ]
        }
    ]
}


lambda_aoss_policy_json = json.dumps(lambda_allow_aoss_policy_statement)

lambda_aoss_policy = iam_client.create_policy(
    PolicyName=lambda_aoss_allow_policy_name,
    PolicyDocument=lambda_aoss_policy_json
)

iam_client.attach_role_policy(
    RoleName=lambda_role_name,
    PolicyArn=lambda_aoss_policy['Policy']['Arn']
)

iam_client.attach_role_policy(
    RoleName=lambda_role_name,
    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
)
```

<h3>Create OpenSearch Serverless data access policies</h3>


```python
<h2>uncomment if running in sagemaker</h2>
<h2>import sagemaker</h2>
<h2>sagemaker_execution_role = sagemaker.sagemaker.get_execution_role()</h2>
```


```python
data_policy_json = [
  {
    "Rules": [
      {
        "Resource": [
          f"collection/{kb_collection_name}"
        ],
        "Permission": [
          "aoss:DescribeCollectionItems",
          "aoss:CreateCollectionItems",
          "aoss:UpdateCollectionItems",
          "aoss:DeleteCollectionItems"
        ],
        "ResourceType": "collection"
      },
      {
        "Resource": [
          f"index/{kb_collection_name}/*"
        ],
        "Permission": [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
        ],
        "ResourceType": "index"
      }
    ],
    "Principal": [
        kb_role_arn,
        f"arn:aws:sts::{account_id}:assumed-role/Admin/*",
        current_role,
        # uncomment if running in sagemaker
        # sagemaker_execution_role,
        lambda_iam_role['Role']['Arn']
    ],
    "Description": ""
  }
]

data_policy = open_search_serverless_client.create_access_policy(
    description='data access policy for aoss collection',
    name=kb_collection_name,
    policy=json.dumps(data_policy_json),
    type='data'
)
```

<h3>Create OpenSearch Serverless Index</h3>


```python
credentials = boto3.Session().get_credentials()
service = 'aoss'
awsauth = AWS4Auth(
    credentials.access_key, 
    credentials.secret_key,
    region, 
    service, 
    session_token=credentials.token
)

<h2>Build the OpenSearch client</h2>
open_search_client = OpenSearch(
    hosts=[{'host': final_host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)
<h2>It can take up to a minute for data access rules to be enforced</h2>
time.sleep(45)
index_body = {
    "settings": {
        "index.knn": True,
        "number_of_shards": 1,
        "knn.algo_param.ef_search": 512,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {}
    }
}

index_body["mappings"]["properties"][kb_vectorField] = {
    "type": "knn_vector",
    "dimension": 1024,
    "method": {
         "name": "hnsw",
         "engine": "faiss"
    },
}

index_body["mappings"]["properties"][kb_textField] = {
    "type": "text"
}

index_body["mappings"]["properties"][kb_metadataField] = {
    "type": "text"
}

<h2>Create index</h2>
response = open_search_client.indices.create(kb_vector_index_name, body=index_body)
print('\nCreating index:')
print(response)
```


```python
storage_configuration = {
    'opensearchServerlessConfiguration': {
        'collectionArn': collection_arn, 
        'fieldMapping': {
            'metadataField': kb_metadataField,
            'textField': kb_textField,
            'vectorField': kb_vectorField
        },
        'vectorIndexName': kb_vector_index_name
    },
    'type': 'OPENSEARCH_SERVERLESS'
}
```

<h3>Create Bedrock Knowledge Base</h3>


```python
<h2>Creating the knowledge base</h2>
try:
    # ensure the index is created and available
    time.sleep(45)
    kb_obj = bedrock_agent_client.create_knowledge_base(
        name=kb_name, 
        description='KB that contains product reviews',
        roleArn=kb_role_arn,
        knowledgeBaseConfiguration={
            'type': 'VECTOR',  # Corrected type
            'vectorKnowledgeBaseConfiguration': {
                'embeddingModelArn': embedding_model_arn
            }
        },
        storageConfiguration=storage_configuration
    )

    # Pretty print the response
    pprint.pprint(kb_obj)

except Exception as e:
    print(f"Error occurred: {e}")
```


```python
<h2>Define the S3 configuration for your data source</h2>
s3_configuration = {
    'bucketArn': bucket_arn,
    'inclusionPrefixes': [kb_key]  
}

<h2>Define the data source configuration</h2>
data_source_configuration = {
    's3Configuration': s3_configuration,
    'type': 'S3'
}

knowledge_base_id = kb_obj["knowledgeBase"]["knowledgeBaseId"]
knowledge_base_arn = kb_obj["knowledgeBase"]["knowledgeBaseArn"]

chunking_strategy_configuration = {
    "chunkingStrategy": "FIXED_SIZE",
    "fixedSizeChunkingConfiguration": {
        "maxTokens": 512,
        "overlapPercentage": 20
    }
}

<h2>Create the data source</h2>
try:
    # ensure that the KB is created and available
    time.sleep(45)
    data_source_response = bedrock_agent_client.create_data_source(
        knowledgeBaseId=knowledge_base_id,
        name=data_source_name,
        description='DataSource for the insurance claim documents requirements',
        dataSourceConfiguration=data_source_configuration,
        vectorIngestionConfiguration = {
            "chunkingConfiguration": chunking_strategy_configuration
        }
    )

    # Pretty print the response
    pprint.pprint(data_source_response)

except Exception as e:
    print(f"Error occurred: {e}")
```

<h3>Synchronise data to Bedrock Knowledge Base</h3>


```python
<h2>Start an ingestion job</h2>
data_source_id = data_source_response["dataSource"]["dataSourceId"]
start_job_response = bedrock_agent_client.start_ingestion_job(
    knowledgeBaseId=knowledge_base_id, 
    dataSourceId=data_source_id
)
```

<h3>Allow Lambda function to invoke Bedrock Knowledge Base and LLM</h3>


```python
<h2>Create IAM policies for Lambda to access Bedrock Knowledge base API</h2>
lambda_allow_kb_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
				"bedrock:RetrieveAndGenerate",
                "bedrock:Retrieve"
			],
            "Resource": knowledge_base_arn
        }
    ]
}

<h2>Create IAM policies for Lambda to invoke Bedrock model</h2>
lambda_allow_invoke_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                llm_model_arn
            ]
        }
    ]
}

lambda_kb_policy_json = json.dumps(lambda_allow_kb_policy_statement)

lambda_kb_policy = iam_client.create_policy(
    PolicyName=lambda_kb_allow_policy_name,
    PolicyDocument=lambda_kb_policy_json
)

iam_client.attach_role_policy(
    RoleName=lambda_role_name,
    PolicyArn=lambda_kb_policy['Policy']['Arn']
)

lambda_invoke_policy_json = json.dumps(lambda_allow_invoke_policy_statement)

lambda_invoke_policy = iam_client.create_policy(
    PolicyName=lambda_invoke_allow_policy_name,
    PolicyDocument=lambda_invoke_policy_json
)

iam_client.attach_role_policy(
    RoleName=lambda_role_name,
    PolicyArn=lambda_invoke_policy['Policy']['Arn']
)

```

<h3>Allow Bedrock Agent to invoke LLM</h3>


```python
<h2>Create IAM policies for agent</h2>
bedrock_agent_bedrock_allow_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AmazonBedrockAgentBedrockFoundationModelPolicy",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                llm_model_arn
            ]
        }
    ]
}

bedrock_policy_json = json.dumps(bedrock_agent_bedrock_allow_policy_statement)

agent_bedrock_policy = iam_client.create_policy(
    PolicyName=bedrock_agent_bedrock_allow_policy_name,
    PolicyDocument=bedrock_policy_json
)
```


```python
<h2>Create IAM Role for the agent and attach IAM policies</h2>
assume_role_policy_document = {
    "Version": "2012-10-17",
    "Statement": [{
          "Effect": "Allow",
          "Principal": {
            "Service": "bedrock.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
    }]
}

assume_role_policy_document_json = json.dumps(assume_role_policy_document)
agent_role = iam_client.create_role(
    RoleName=agent_role_name,
    AssumeRolePolicyDocument=assume_role_policy_document_json
)

<h2>Pause to make sure role is created</h2>
time.sleep(10)
    
iam_client.attach_role_policy(
    RoleName=agent_role_name,
    PolicyArn=agent_bedrock_policy['Policy']['Arn']
)

<h2>iam_client.attach_role_policy(</h2>
<h2>    RoleName=agent_role_name,</h2>
<h2>    PolicyArn=agent_kb_schema_policy['Policy']['Arn']</h2>
<h2>)</h2>
```

<h3>Create Lambda function</h3>


```python
import base64
<h2>Create Lambda Function</h2>
with open("lambda-package.zip","rb") as f:
    contents = f.read()
    # encoded = base64.b64encode(contents)
    lambda_function = lambda_client.create_function(
        FunctionName=lambda_name,
        Runtime='python3.12',
        Timeout=180,
        Role=lambda_iam_role['Role']['Arn'],
        Code={'ZipFile': contents},
        Handler='app.lambda_handler',
        Environment={
            'Variables': {
                'VECTOR_DB_INDEX':kb_vector_index_name,
                'AOSS_COLLECTION_ID':collection_arn.split('/')[1],
                'REGION':region,
                'KNOWLEDGE_BASE_ID': knowledge_base_id
            }
        }
    )
```

<h3>Creating Bedrock Agent</h3>


```python
<h2>Create Agent</h2>
agent_instruction = """
You are an agent that can look up product reviews. If an user asks about your functionality, provide guidance in natural language and do not include function names on the output."""

response = bedrock_agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_role['Role']['Arn'],
    description="Agent for searching through product reviews.",
    idleSessionTTLInSeconds=1800,
    foundationModel="anthropic.claude-3-haiku-20240307-v1:0",
    instruction=agent_instruction,
)
```


```python
agent_id = response['agent']['agentId']
```

<h4>Create Bedrock Agent Action Group</h4>


```python
agent_functions = [
            {
                "name": "retrieve-reviews-opensearch",
                "description": "Gets the list of top n reviews. Do not use this if any product is mentioned.",
                "parameters": {
                    "count":{
                        "description": "count of reviews to return",
                        "required": True,
                        "type": "integer"
                    },
                    "end_date":{
                        "description": "end date of range of reviews to query",
                        "required": True,
                        "type": "number"
                    },
                    "start_date":{
                        "description": "start date of range of reviews to query",
                        "required": True,
                        "type": "number"
                    }
                }
            },
            {
                "name": "retrieve-reviews-hybrid",
                "description": "Gets the list of top n reviews. Use this if any product is mentioned.",
                "parameters": {
                    "count":{
                        "description": "count of reviews to return",
                        "required": True,
                        "type": "integer"
                    },
                    "description":{
                        "description": "description of product",
                        "required": True,
                        "type": "string"
                    },
                    "end_date":{
                        "description": "end date of range of reviews to query",
                        "required": True,
                        "type": "number"
                    },
                    "reviewer":{
                        "description": "reviewer of product",
                        "required": True,
                        "type": "string"
                    },
                    "start_date":{
                        "description": "start date of range of reviews to query",
                        "required": True,
                        "type": "number"
                    }
                }
            }
        ]
```


```python
<h2>Pause to make sure agent is created</h2>
time.sleep(30)
<h2>Now, we can configure and create an action group here:</h2>
agent_action_group_response = bedrock_agent_client.create_agent_action_group(
    agentId=agent_id,
    agentVersion='DRAFT',
    actionGroupExecutor={
        'lambda': lambda_function['FunctionArn']
    },
    actionGroupName='GetReviewsActionGroup',
    functionSchema={
        'functions': agent_functions
    },
    description='Actions for listing product reviews'
)
```

<h3>Allow Bedrock Agent to invoke Lambda</h3>


```python
<h2>Create allow invoke permission on lambda</h2>
response = lambda_client.add_permission(
    FunctionName=lambda_name,
    StatementId='allow_bedrock',
    Action='lambda:InvokeFunction',
    Principal='bedrock.amazonaws.com',
    SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}",
)
```

<h3>Preparing Bedrock Agent</h3>


```python
agent_prepare = bedrock_agent_client.prepare_agent(agentId=agent_id)
agent_prepare
```

<h3>Create Bedrock Agent alias</h3>


```python
<h2>Pause to make sure agent is prepared</h2>
time.sleep(30)
agent_alias = bedrock_agent_client.create_agent_alias(
    agentId=agent_id,
    agentAliasName=agent_alias_name
)
<h2>Pause to make sure agent alias is ready</h2>
time.sleep(30)
```

<h3>Invoke Bedrock Agent</h3>


```python
<h2>Extract the agentAliasId from the response</h2>
agent_alias_id = agent_alias['agentAlias']['agentAliasId']

<h2>create a random id for session initiator id</h2>
session_id:str = str(uuid.uuid1())
enable_trace:bool = True
end_session:bool = False

<h2>invoke the agent API</h2>
agentResponse = bedrock_agent_runtime_client.invoke_agent(
    inputText="""
    The start date and end date are placed in <start_date></start_date> and <end_date></end_date> tags.
    Give me the last 2 reviews on hair conditioner from jokic.
    <start_date>1477808000000</start_date>
    <end_date>1609430400000</end_date>
    """,
    agentId=agent_id,
    agentAliasId=agent_alias_id, 
    sessionId=session_id,
    enableTrace=enable_trace, 
    endSession= end_session
)

logger.info(pprint.pprint(agentResponse))
```


```python
%%time
event_stream = agentResponse['completion']
try:
    for event in event_stream:        
        if 'chunk' in event:
            data = event['chunk']['bytes']
            logger.info(f"Final answer ->\n{data.decode('utf8')}")
            agent_answer = data.decode('utf8')
            end_event_received = True
            # End event indicates that the request finished successfully
        elif 'trace' in event:
            logger.info(json.dumps(event['trace'], indent=2))
        else:
            raise Exception("unexpected event.", event)
except Exception as e:
    raise Exception("unexpected event.", e)
```


```python
<h2>And here is the response if you just want to see agent's reply</h2>
print(agent_answer)
```
