---
tags:
    - Agents/ Function Calling
    - Agent/ RAG
    - RAG/ Knowledge-Bases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/04-create-agent-with-single-knowledge-base/04-create-agent-with-single-knowledge-base.ipynb){:target="_blank"}"

<h2>Create an Agent with a single Knowledge Base only</h2>

In this notebook you will learn how to create an Amazon Bedrock Agent that connects to a single Knowledge Bases for Amazon Bedrock to retrieve company data and complete tasks. 

The use case for this notebook is the Amazon Bedrock Documentation pages stored as PDFs. It will allow you to ask questions about Amazon Bedrock and get answers based on documents available in the Knowledge Base.

The steps to complete this notebook are:

1. Import the needed libraries
1. Create an S3 bucket and upload the data to it
1. Create the Knowledge Base for Amazon Bedrock and sync data to Knowledge Base
1. Create the Agent for Amazon Bedrock
1. Test the Agent
1. Clean up the resources created

<h2>1. Import the needed libraries</h2>


```python
!pip install --upgrade -q opensearch-py
!pip install --upgrade -q requests-aws4auth
!pip install --upgrade -q boto3
!pip install --upgrade -q botocore
!pip install --upgrade -q awscli
```


```python
import logging
import boto3
import time
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


```python
<h2>getting boto3 clients for required AWS services</h2>
sts_client = boto3.client('sts')
iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
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


```python
<h2>Generate random prefix for unique IAM roles, agent name and S3 Bucket and </h2>
<h2>assign variables</h2>
suffix = f"{region}-{account_id}"
agent_name = "bedrock-docs-kb-agents"
agent_alias_name = "bedrock-docs-alias"
bucket_name = f'{agent_name}-{suffix}'
bucket_arn = f"arn:aws:s3:::{bucket_name}"
bedrock_agent_bedrock_allow_policy_name = f"bda-bedrock-allow-{suffix}"
bedrock_agent_s3_allow_policy_name = f"bda-s3-allow-{suffix}"
bedrock_agent_kb_allow_policy_name = f"bda-kb-allow-{suffix}"
agent_role_name = f'AmazonBedrockExecutionRoleForAgents_bedrock_docs'
kb_name = f'bedrock-docs-kb-{suffix}'
data_source_name = f'bedrock-docs-kb-docs-{suffix}'
kb_files_path = 'kb_documents'
kb_key = 'kb_documents'
kb_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_bedrock_docs'
kb_bedrock_allow_policy_name = f"bd-kb-bedrock-allow-{suffix}"
kb_aoss_allow_policy_name = f"bd-kb-aoss-allow-{suffix}"
kb_s3_allow_policy_name = f"bd-kb-s3-allow-{suffix}"
kb_collection_name = f'bd-kbc-{suffix}'
<h2>Select Amazon titan as the embedding model</h2>
embedding_model_arn = f'arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v1'
kb_vector_index_name = "bedrock-knowledge-base-index"
kb_metadataField = 'bedrock-knowledge-base-metadata'
kb_textField = 'bedrock-knowledge-base-text'
kb_vectorField = 'bedrock-knowledge-base-vector'
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

<h2>agent configuration</h2>
agent_instruction = """
You are an agent that support users working with Amazon Bedrock. You have access to Bedrock's documentation in a Knowledge Base
and you can Answer questions from this documentation. Only answer questions based on the documentation and reply with 
"There is no information about your question on the Amazon Bedrock Documentation at the moment, sorry! Do you want to ask another question?" 
If the answer to the question is not available in the documentation
"""
```

<h2>2. Upload the dataset to Amazon S3</h2>
Knowledge Bases for Amazon Bedrock, currently require data to reside in an Amazon S3 bucket. In this section we will create an Amazon S3 bucket and the files.

<h3>2.1 Create the Amazon S3 bucket</h3>


```python
if region != 'us-east-1':
    s3_client.create_bucket(
        Bucket=bucket_name.lower(),
        CreateBucketConfiguration={'LocationConstraint': region}
    )
else:
    s3_client.create_bucket(Bucket=bucket_name)
```

<h3>2.2 Upload dataset to the Amazon S3 bucket</h3>


```python
<h2>Upload Knowledge Base files to this s3 bucket</h2>
for f in os.listdir(kb_files_path):
    if f.endswith(".pdf"):
        s3_client.upload_file(kb_files_path+'/'+f, bucket_name, kb_key+'/'+f)
```

<h2>3. Create a Knowledge Base for Amazon Bedrock</h2>

In this section we will go through all the steps to create and test a Knowledge Base. 

These are the steps to complete:
    
1. Create a Knowledge Base Role and its policies
1. Create a Vector Database
1. Create an OpenSearch Index
1. Create a Knowledge Base
1. Create a data source and attach to the recently created Knowledge Base
1. Ingest data to your knowledge Base

<h3>3.1 Create Knowledge Base Role and Policies</h3>

Let's first create IAM policies to allow our Knowledge Base to access Bedrock Titan Embedding Foundation model, Amazon OpenSearch Serverless and the S3 bucket with the Knowledge Base Files.

Once the policies are ready, we will create the Knowledge Base role


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

<h3>3.2 Create Vector Database</h3>

Firt of all we have to create a vector store. In this section we will use Amazon OpenSerach Serverless.

Amazon OpenSearch Serverless is a serverless option in Amazon OpenSearch Service. As a developer, you can use OpenSearch Serverless to run petabyte-scale workloads without configuring, managing, and scaling OpenSearch clusters. You get the same interactive millisecond response times as OpenSearch Service with the simplicity of a serverless environment. Pay only for what you use by automatically scaling resources to provide the right amount of capacity for your application—without impacting data ingestion.



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
        current_role
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

<h3>3.3 - Create OpenSearch Index</h3>

Let's now create a vector index to index our data



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
    "dimension": 1536,
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

<h3>3.5 - Create Knowledge Base</h3>
Now that we have the Vector database available in OpenSearch Serverless, let's create a Knowledge Base and associate it with the OpenSearch DB


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


```python
<h2>Creating the knowledge base</h2>
try:
    # ensure the index is created and available
    time.sleep(45)
    kb_obj = bedrock_agent_client.create_knowledge_base(
        name=kb_name, 
        description='KB that contains the bedrock documentation',
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
        description='DataSource for the bedrock documentation',
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

<h3>3.6 - Start ingestion job</h3>

Once the Knowledge Base and Data Source are created, we can start the ingestion job. During the ingestion job, Knowledge Base will fetch the documents in the data source, pre-process it to extract text, chunk it based on the chunking size provided, create embeddings of each chunk and then write it to the vector database, in this case Amazon OpenSource Serverless.



```python
<h2>Start an ingestion job</h2>
data_source_id = data_source_response["dataSource"]["dataSourceId"]
start_job_response = bedrock_agent_client.start_ingestion_job(
    knowledgeBaseId=knowledge_base_id, 
    dataSourceId=data_source_id
)

```

<h2>4. Create Agent</h2>

We will now create the Agent and associate the Knowledge Base to it. To do so we need to: 
1. Create Agent IAM role and policies
1. Create Agent
1. Associate Agent to Knowledge Base
1. Prepare Agent

<h3>4.1 - Create Agent IAM role and policies</h3>
First we need to create the agent policies that allow bedrock model invocation and Knowledge Base retrieval


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
                f"arn:aws:bedrock:{region}::foundation-model/{model_id}"
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
bedrock_agent_kb_retrival_policy_statement = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:Retrieve"
            ],
            "Resource": [
                knowledge_base_arn
            ]
        }
    ]
}
bedrock_agent_kb_json = json.dumps(bedrock_agent_kb_retrival_policy_statement)
agent_kb_schema_policy = iam_client.create_policy(
    PolicyName=bedrock_agent_kb_allow_policy_name,
    Description=f"Policy to allow agent to retrieve documents from knowledge base.",
    PolicyDocument=bedrock_agent_kb_json
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


iam_client.attach_role_policy(
    RoleName=agent_role_name,
    PolicyArn=agent_kb_schema_policy['Policy']['Arn']
)
```

<h3>4.2 - Create Agent</h3>
Once the needed IAM role is created, we can use the bedrock agent client to create a new agent. To do so we use the create_agent function. It requires an agent name, underline foundation model and instruction. You can also provide an agent description. Note that the agent created is not yet prepared. We will focus on preparing the agent and then using it to invoke actions and use other APIs


```python
<h2>Create Agent</h2>
response = bedrock_agent_client.create_agent(
    agentName=agent_name,
    agentResourceRoleArn=agent_role['Role']['Arn'],
    description="Agent supporting Amazon Bedrock Developers.",
    idleSessionTTLInSeconds=1800,
    foundationModel=model_id,
    instruction=agent_instruction,
)
```

Let's now store the agent id in a local variable to use it on the next steps


```python
agent_id = response['agent']['agentId']
agent_id
```

<h3>4.3 - Associate agent to the Knowledge Base</h3>
Next, we need to associate the agent created with the Knowledge Base for the Bedrock documentation


```python
agent_kb_description = bedrock_agent_client.associate_agent_knowledge_base(
    agentId=agent_id,
    agentVersion='DRAFT',
    description=f'Use the information in the {kb_name} knowledge base to provide accurate responses to the questions about Amazon Bedrock.',
    knowledgeBaseId=knowledge_base_id 
)
```

<h3>4.4 - Prepare Agent</h3>

Let's create a DRAFT version of the agent that can be used for internal testing.



```python
agent_prepare = bedrock_agent_client.prepare_agent(agentId=agent_id)
agent_prepare
```

<h2>5 - Testing Agent</h2>

Now that we have our agent, let's invoke it to test if it is providing correct information about Amazon Bedrock. To do so, let's first create an Agent Alias


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


```python
agent_alias
```

Now that we've created the agent, let's use the bedrock-agent-runtime client to invoke this agent and get the information from the Knowledge base


```python
<h2>Extract the agentAliasId from the response</h2>
agent_alias_id = agent_alias['agentAlias']['agentAliasId']

<h2>create a random id for session initiator id</h2>
session_id:str = str(uuid.uuid1())
enable_trace:bool = True
end_session:bool = False

<h2>invoke the agent API</h2>
agentResponse = bedrock_agent_runtime_client.invoke_agent(
    inputText="How can I evaluate models on Bedrock?",
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


```python
def simple_agent_invoke(input_text, agent_id, agent_alias_id, session_id=None, enable_trace=False, end_session=False):
    if session_id is None:
        session_id:str = str(uuid.uuid1())

    agentResponse = bedrock_agent_runtime_client.invoke_agent(
        inputText=input_text,
        agentId=agent_id,
        agentAliasId=agent_alias_id, 
        sessionId=session_id,
        enableTrace=enable_trace, 
        endSession= end_session
    )
    logger.info(pprint.pprint(agentResponse))
    
    agent_answer = ''
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
    return agent_answer
```


```python
simple_agent_invoke("what is bedrock provisioned throughput?", agent_id, agent_alias_id, session_id)
```


```python
simple_agent_invoke("what are the components of a Bedrock Guardrail?", agent_id, agent_alias_id, session_id)
```


```python
simple_agent_invoke("what are the components of a Bedrock Guardrail?", agent_id, agent_alias_id, session_id)
```

<h2>6 - Clean up (Optional)</h2>

The next steps are optional and demonstrate how to delete our agent. To delete the agent we need to:

1. delete agent alias
1. delete agent
1. delete the knowledge base
1. delete the OpenSearch Serverless vector store
1. empty created s3 bucket
1. delete s3 bucket



```python
agent_alias_deletion = bedrock_agent_client.delete_agent_alias(
    agentId=agent_id,
    agentAliasId=agent_alias['agentAlias']['agentAliasId']
)
```


```python
agent_deletion = bedrock_agent_client.delete_agent(
    agentId=agent_id
)
```


```python
<h2>Empty and delete S3 Bucket</h2>

objects = s3_client.list_objects(Bucket=bucket_name)  
if 'Contents' in objects:
    for obj in objects['Contents']:
        s3_client.delete_object(Bucket=bucket_name, Key=obj['Key']) 
s3_client.delete_bucket(Bucket=bucket_name)
```


```python
<h2>Delete IAM Roles and policies and Knowledge Base files</h2>
for policy in [
    agent_bedrock_policy, 
    agent_kb_schema_policy,
    kb_bedrock_policy,
    kb_aoss_policy,
    kb_s3_policy
]:
    response = iam_client.list_entities_for_policy(
        PolicyArn=policy['Policy']['Arn'],
        EntityFilter='Role'
    )

    for role in response['PolicyRoles']:
        iam_client.detach_role_policy(
            RoleName=role['RoleName'], 
            PolicyArn=policy['Policy']['Arn']
        )

    iam_client.delete_policy(
        PolicyArn=policy['Policy']['Arn']
    )

    

for role_name in [
    agent_role_name, 
    kb_role_name
]:
    try: 
        iam_client.delete_role(
            RoleName=role_name
        )
    except Exception as e:
        print(e)
        print("couldn't delete role", role_name)
        
    
try:

    open_search_serverless_client.delete_collection(
        id=opensearch_collection_response["createCollectionDetail"]["id"]
    )

    open_search_serverless_client.delete_access_policy(
          name=kb_collection_name,
          type='data'
    )    

    open_search_serverless_client.delete_security_policy(
          name=kb_collection_name,
          type='network'
    )   

    open_search_serverless_client.delete_security_policy(
          name=kb_collection_name,
          type='encryption'
    )    
    bedrock_agent_client.delete_knowledge_base(
        knowledgeBaseId=knowledge_base_id
    )
except Exception as e:
    print(e)
```

<h2>Conclusion</h2>

We have now experimented with using boto3 SDK to create, invoke and delete an agent having a single KB connected to it.
<h2>Take aways</h2>

Adapt this notebook to create new agents for your application

<h2>Thank You</h2>
