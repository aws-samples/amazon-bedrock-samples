This notebook demonstrates how to create a knowledge base with a custom data source and then uses the KnowledgeBaseDocuments API to ingest documents directly into the knowledge base without the need for syncing.  We test the KB with a query and then show how to clean up the resources we just created.

## Setup Vars


```python
import time

# Get the current timestamp
current_time = time.time()
# Format the timestamp as a string
timestamp_str = time.strftime("%Y%m%d%H%M%S", time.localtime(current_time))[-7:]
# Create the suffix using the timestamp
suffix = f"{timestamp_str}"
```


```python
import boto3
import json 

boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
iam_client = boto3_session.client('iam')
aoss_client = boto3_session.client('opensearchserverless')
sts_client = boto3_session.client('sts')
bedrock_agent_client = boto3_session.client('bedrock-agent')
bedrock_agent_runtime_client = boto3_session.client('bedrock-agent-runtime') 
bedrock_client = boto3_session.client('bedrock')
account_number = sts_client.get_caller_identity().get('Account')
identity = sts_client.get_caller_identity()['Arn']
credentials = boto3_session.get_credentials()

```

## Create Role


```python
# create bedrock execution role

kb_execution_role_name = f'AmazonBedrockExecutionRoleForKnowledgeBase_{suffix}'

assume_role_policy_document = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Principal': {
                'Service': 'bedrock.amazonaws.com'
            },
            'Action': 'sts:AssumeRole'
        }
    ]
}

bedrock_kb_execution_role = None

try:
    bedrock_kb_execution_role = iam_client.create_role(
        RoleName=kb_execution_role_name,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
        Description='Amazon Bedrock Knowledge Base Execution Role for accessing OSS and S3',
        MaxSessionDuration=3600
    )
except iam_client.exceptions.EntityAlreadyExistsException:
    print("Role already exists")
    bedrock_kb_execution_role = iam_client.get_role(
        RoleName=kb_execution_role_name
    )

print("Amazon Bedrock Execution Role ARN: ", bedrock_kb_execution_role["Role"]["Arn"])
```

## Create FM Policy and attach to role



```python
fm_policy_name = f'AmazonBedrockFoundationModelPolicyForKnowledgeBase_{suffix}'

foundation_model_policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0",
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                "arn:aws:bedrock:us-east-1::foundation-model/cohere.rerank-v3-5:0"
            ]
        }
    ]
}

try:
    # create policies based on the policy documents
    fm_policy = iam_client.create_policy(
        PolicyName=fm_policy_name,
        PolicyDocument=json.dumps(foundation_model_policy_document),
        Description='Policy for accessing foundation model',
    )
except iam_client.exceptions.EntityAlreadyExistsException:
    print(f"Policy {fm_policy_name} already exists.")
    fm_policy = iam_client.get_policy(
        PolicyArn=f"arn:aws:iam::{account_number}:policy/{fm_policy_name}"
    )

fm_policy_arn = fm_policy["Policy"]["Arn"]
print("Foundation model policy arn: ", fm_policy_arn)

# attach policies to Amazon Bedrock execution role
iam_client.attach_role_policy(
    RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
    PolicyArn=fm_policy_arn
)

```

## Create Encryption Policy


```python
encryption_policy_name = f"bedrock-sample-rag-sp-{suffix}"
vector_store_name = f'bedrock-sample-rag-{suffix}'

try:
    encryption_policy = aoss_client.create_security_policy(
        name= encryption_policy_name,
        policy=json.dumps(
            {
                'Rules': [{'Resource': ['collection/' + vector_store_name],
                            'ResourceType': 'collection'}],
                'AWSOwnedKey': True
            }),
        type='encryption'
    )
except aoss_client.exceptions.ConflictException:
    print(f"Security policy {encryption_policy_name} already exists")
    encryption_policy = aoss_client.get_security_policy(
        name=encryption_policy_name,
        type='encryption'
    )

```

## Create OSS Collection



```python
import pprint
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


try:
    collection = aoss_client.create_collection(name=vector_store_name, type='VECTORSEARCH')
    collection_id = collection['createCollectionDetail']['id']
    collection_arn = collection['createCollectionDetail']['arn']
except aoss_client.exceptions.ConflictException:
    print("Collection already exists")
    collection = aoss_client.batch_get_collection(names=[vector_store_name])['collectionDetails'][0]
    pp.pprint(collection)
    collection_id = collection['id']
    collection_arn = collection['arn']
pp.pprint(collection)

# Get the OpenSearch serverless collection URL
host = collection_id + '.' + region_name + '.aoss.amazonaws.com'
print(host)
# wait for collection creation
# This can take couple of minutes to finish
response = aoss_client.batch_get_collection(names=[vector_store_name])
# Periodically check collection status
while (response['collectionDetails'][0]['status']) == 'CREATING':
    print('Creating collection...')
    interactive_sleep(30)
    response = aoss_client.batch_get_collection(names=[vector_store_name])
print('\nCollection successfully created:')
pp.pprint(response["collectionDetails"])

```

## Create OSS Policy and attach to role


```python
oss_policy_name = f'AmazonBedrockOSSPolicyForKnowledgeBase_{suffix}'

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
                f"arn:aws:aoss:{region_name}:{account_number}:collection/{collection_id}"
            ]
        }
    ]
}

oss_policy_arn = f"arn:aws:iam::{account_number}:policy/{oss_policy_name}"
created = False
try:
    iam_client.create_policy(
        PolicyName=oss_policy_name,
        PolicyDocument=json.dumps(oss_policy_document),
        Description='Policy for accessing opensearch serverless',
    )
    created = True
except iam_client.exceptions.EntityAlreadyExistsException:
    print(f"Policy {oss_policy_arn} already exists, skipping creation")
print("Opensearch serverless arn: ", oss_policy_arn)

iam_client.attach_role_policy(
    RoleName=bedrock_kb_execution_role["Role"]["RoleName"],
    PolicyArn=oss_policy_arn
)
```

## Create Network Policy


```python
network_policy_name = f"bedrock-sample-rag-np-{suffix}"
try:
    network_policy = aoss_client.create_security_policy(
        name=network_policy_name,
        policy=json.dumps(
            [
                {'Rules': [{'Resource': ['collection/' + vector_store_name],
                            'ResourceType': 'collection'}],
                    'AllowFromPublic': True}
            ]),
        type='network'
    )
except aoss_client.exceptions.ConflictException:
    print("Policy already exists")
    network_policy = aoss_client.get_security_policy(
        name= network_policy_name,
        type='network'
    )
```

## Create access policy for vector index


```python
access_policy_name = f'bedrock-sample-rag-ap-{suffix}'
try:
    access_policy = aoss_client.create_access_policy(
        name= access_policy_name,
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
                    'Principal': [identity, bedrock_kb_execution_role['Role']['Arn']],
                    'Description': 'Easy data policy'}
            ]),
        type='data'
    )
except aoss_client.exceptions.ConflictException:
    print("Policy already exists")
    access_policy = aoss_client.get_access_policy(
        name=access_policy_name,
        type='data'
    )
```

## Create the vector index


```python
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, RequestError
awsauth = AWSV4SignerAuth(credentials, region_name, 'aoss')
# Build the OpenSearch client
oss_client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth= awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)


# create a dictionary with model id as key and context length as value
embedding_context_dimensions = {
    "cohere.embed-multilingual-v3": 512,
    "cohere.embed-english-v3": 512,
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024
}
embedding_model = "amazon.titan-embed-text-v2:0"

index_name = f"bedrock-sample-rag-index-{suffix}"

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
                "dimension": embedding_context_dimensions[embedding_model], # use dimension as per the context length of embeddings model selected.
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
    response = oss_client.indices.create(index=index_name, body=json.dumps(body_json))
    print('\nCreating index:')
    pp.pprint(response)

    # index creation can take up to a minute
    interactive_sleep(60)
except RequestError as e:
    # you can delete the index if its already exists
    # oss_client.indices.delete(index=index_name)
    print(e)
    print(
        f'Error while trying to create the index, with error {e.error}\nyou may unmark the delete above to '
        f'delete, and recreate the index')
```

## Create the knowledge base


```python
chunking_strategy = "FIXED_SIZE"

kb_name = f"bedrock-sample-knowledge-base-{suffix}"
kb_description = "Multi data source knowledge base."

opensearch_serverless_configuration = {
    "collectionArn": collection_arn,
    "vectorIndexName": index_name,
    "fieldMapping": {
        "vectorField": "vector",
        "textField": "text",
        "metadataField": "text-metadata"
    }
}

chunking_strategy_configuration = {}
# vectorIngestionConfiguration = {}

print(f"Creating KB with chunking strategy - {chunking_strategy}")
chunking_strategy_configuration = {
                "chunkingConfiguration": {"chunkingStrategy": "NONE"}
            }
print("============Chunking config========\n", chunking_strategy_configuration)


custom_datasource_name = f'bedrock-sample-rag-customds-{suffix}'

# The embedding model used by Bedrock to embed ingested documents, and realtime prompts
embedding_model_arn = f"arn:aws:bedrock:{region_name}::foundation-model/{embedding_model}"
try:
    create_kb_response = bedrock_agent_client.create_knowledge_base(
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
    pp.pprint(kb)
except bedrock_agent_client.exceptions.ConflictException:
    print("Knowledge Base already exists")
    kbs = bedrock_agent_client.list_knowledge_bases(
        maxResults=100
    )
    kb_id = None
    for kb in kbs['knowledgeBaseSummaries']:
        if kb['name'] == kb_name:
            kb_id = kb['knowledgeBaseId']
    response = bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
    kb = response['knowledgeBase']
    pp.pprint(kb)

# Create a DataSource in KnowledgeBase
try:
    print(kb_name)
    print(kb['knowledgeBaseId'])
    create_ds_response = bedrock_agent_client.create_data_source(
        name=kb_name,
        description=kb_description,
        knowledgeBaseId=kb['knowledgeBaseId'],
        dataSourceConfiguration={
            "type": "CUSTOM"
        },
        vectorIngestionConfiguration = chunking_strategy_configuration, 
        dataDeletionPolicy='RETAIN'
    )
    ds = create_ds_response["dataSource"]
    pp.pprint(ds)
except bedrock_agent_client.exceptions.ConflictException as ce:
    print(ce)
    print("Datasource already exists")
    ds_id = bedrock_agent_client.list_data_sources(
        knowledgeBaseId=kb['knowledgeBaseId'],
        maxResults=100
    )['dataSourceSummaries'][0]['dataSourceId']
    get_ds_response = bedrock_agent_client.get_data_source(
        dataSourceId=ds_id,
        knowledgeBaseId=kb['knowledgeBaseId']
    )
    ds = get_ds_response["dataSource"]
    pp.pprint(ds)

knowledgeBaseId = kb['knowledgeBaseId']
dsId = ds['dataSourceId']
print("Knowledge Base ID: ", knowledgeBaseId)
print("Data Source ID: ", ds['dataSourceId'])
```

## Add documents to the custom data source using the KnowledgeBaseDocuments API.

At this point you have a working knowledge base.  We will demonstrate how to load a document directly to the knowledge base.  There is no need to sync.  See: https://docs.aws.amazon.com/bedrock/latest/userguide/kb-direct-ingestion-add.html


```python
def ingest_documents(knowledge_base_id, data_source_id, documents):
    
    try:
        formatted_documents = []
        for doc in documents:
            document = { 
                "content": { 
                    "dataSourceType": "CUSTOM",
                    "custom": { 
                        "customDocumentIdentifier": { 
                            "id": f"{doc['source']}_{suffix}"
                        },
                        "inlineContent": { 
                            "textContent": { 
                                "data": doc['text']
                            },
                            "type": "TEXT"
                        },
                        "sourceType": "IN_LINE"
                    }
                }
            }
            formatted_documents.append(document)

        #https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_IngestKnowledgeBaseDocuments.html
        response = bedrock_agent_client.ingest_knowledge_base_documents(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            documents=formatted_documents
        )
        
        print(f"Response: {response}")

        return response['documentDetails'] 
        
    except Exception as e:
        print(f"Error ingesting documents: {str(e)}")
        raise


# Sample documents to ingest
documents = [
    {
        'text': """
        Amazon Bedrock is a fully managed service that makes FMs from leading AI companies 
        accessible via an API, making it easy to build generative AI applications.
        """,
        'source': 'AWS Documentation',
        'author': 'AWS',
        'source_uri': 'https://docs.aws.amazon.com/bedrock'
    },
    {
        'text': """
        George Washington was born in Virginia in 1732. He served as Commander and Chief of the Army. He was the first president of the United States.  He died in Mount Vernon, Virginia in 1799,
        """,
        'source': 'Wikipedia',
        'author': 'Wikipedia',
        'source_uri': 'https://en.wikipedia.org/wiki/George_Washington'
    }

]

try:
    # Replace with your actual knowledge base ID
    kb_id = knowledgeBaseId
    data_source_id = dsId
    
    # Ingest documents with retry logic
    document_details = ingest_documents(kb_id, data_source_id, documents)
    
    print(f"\nSuccessfully completed ingestion: {document_details}")
    
except Exception as e:
    print(f"Final error: {e}")


```

## Check the status of the documents we just uploaded.


```python
# aws bedrock-agent list-knowledge-base-documents --knowledge-base-id SNNQJ2YY5G --data-source-id MXBOGUPBGT


import boto3
from botocore.exceptions import ClientError

def list_knowledge_base_documents(knowledge_base_id, data_source_id):
    try:
        response = bedrock_agent_client.list_knowledge_base_documents(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id
        )
        
        return response['documentDetails']
        
    except ClientError as e:
        print(f"Error listing documents: {e.response['Error']['Message']}")
        raise   

list_knowledge_base_documents(kb_id, ds_id)
```

## Query the knowledge base


```python
# find the ARN of a model from the cli as follows
# e.g., aws bedrock list-foundation-models | grep -i haiku 

model_arn = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
response = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": "When was George Washington born? "
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id,
            "modelArn": model_arn,
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5
                } 
            }
        }
    }
)
print(response)
print(response['output']['text'],end='\n'*2)

```

## Cleanup Data Source and KB


```python
try:
    bedrock_agent_client.delete_data_source(
        dataSourceId=ds_id,
        knowledgeBaseId=kb_id
    )
    bedrock_agent_client.delete_knowledge_base(
        knowledgeBaseId=kb_id
    )
except bedrock_agent_client.exceptions.ResourceNotFoundException as e:
    print("Resource not found", e)
    pass
except Exception as e:
    print(e)

```

## Cleanup Policies


```python
attached_policies = iam_client.list_attached_role_policies(RoleName=kb_execution_role_name)["AttachedPolicies"]
print(f"======Attached policies with role {kb_execution_role_name}========\n", attached_policies)
for attached_policy in attached_policies:
    policy_arn = attached_policy["PolicyArn"]
    policy_name = attached_policy["PolicyName"]
    iam_client.detach_role_policy(RoleName=kb_execution_role_name, PolicyArn=policy_arn)
    print(f"Detached policy {policy_name} from role {kb_execution_role_name}")
    iam_client.delete_policy(PolicyArn=policy_arn)
    print(f"Deleted policy {policy_name} from role {kb_execution_role_name}")            

```

## Cleanup Role
If this fails, wait a moment for the policy deletions to propogate and try again.


```python
iam_client.delete_role(RoleName=kb_execution_role_name)
print(f"Deleted role {kb_execution_role_name}")
print("======== All IAM roles and policies deleted =========")
 
```
