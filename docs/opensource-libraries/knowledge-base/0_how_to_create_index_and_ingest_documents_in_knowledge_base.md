<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>


<h2>How to create index and ingest documents in Amazon Bedrock Knowledge Base</h2>

<a href="https://github.com/aws-samples/amazon-bedrock-samples/opensource-libraries/knowledge-base/0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb">Open in Github</a>

<h2>Overview</h2>

This notebook provides sample code for building an empty OpenSearch Serverless (OSS) index in Amazon Bedrock Knowledge Base and then ingest documents into it.


In this notebook we create a data pipeline that ingests documents (typically stored in Amazon S3) into a knowledge base i.e. a vector database such as Amazon OpenSearch Service Serverless (AOSS) so that it is available for lookup when a question is received.

<ul>
<li>Load the documents into the knowledge base by connecting your s3 bucket (data source). </li>
<li>Ingestion - Knowledge base will split them into smaller chunks (based on the strategy selected), generate embeddings and store it in the associated vectore store.</li>
</ul>


<img src="./assets/images/data_ingestion.png" alt="Data Ingestion in Index of Knowledge Base" style="margin:auto">

<h2>Steps followed in the Notebook</h2>

<ul>
<li>Create Amazon Bedrock Knowledge Base execution role with necessary policies for accessing data from S3 and writing embeddings into OSS.</li>
<li>Create an empty OpenSearch serverless index.</li>
<li>Download documents</li>
<li>Create Amazon Bedrock knowledge base</li>
<li>Create a data source within knowledge base which will connect to Amazon S3</li>
<li>Start an ingestion job using KB APIs which will read data from s3, chunk it, convert chunks into embeddings using Amazon Titan Embeddings model and then store these embeddings in AOSS. All of this without having to build, deploy and manage the data pipeline.</li>
</ul>

Once the data is available in the Amazon Bedrock Knowledge Base then a question answering application can be built using the Knowledge Base APIs provided by Amazon Bedrock as demonstrated by other notebooks in the same folder.

<div class="alert alert-block alert-info">
<b>Note:</b> This notebook has been tested in <strong>Mumbai (ap-south-1)</strong> in <strong>Python 3.10.14</strong>
</div>

<h2>Prerequisites</h2>

This notebook requires permissions to:
<ul>
<li>create and delete Amazon IAM roles</li>
<li>create, update and delete Amazon S3 buckets</li>
<li>access Amazon Bedrock</li>
<li>access to Amazon OpenSearch Serverless</li>
</ul>

If running on SageMaker Studio, you should add the following managed policies to your role:
<ul>
<li>IAMFullAccess</li>
<li>AWSLambda_FullAccess</li>
<li>AmazonS3FullAccess</li>
<li>AmazonBedrockFullAccess</li>
<li>Custom policy for Amazon OpenSearch Serverless such as:
<code>
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "aoss:*",
            "Resource": "*"
        }
    ]
}
</code></li>
</ul>

<div class="alert alert-block alert-info">
<b>Note:</b> Please make sure to enable `Cohere Embed Multilingual`, `Anthropic Claude 3 Sonnet`  and `Anthropic Claude 3 Haiku` model access in Amazon Bedrock Console, as the notebook will use Cohere Embed Multilingual for creating the embeddings & Anthropic Claude 3 Sonnet and Claude 3 Haiku models for testing the knowledge base once its created.
</div>


Next we install the required python libraries.


```python
%pip install -U opensearch-py==2.7.1
%pip install -U boto3==1.34.162
%pip install -U retrying==1.3.4
```

    Collecting opensearch-py==2.7.1
      Using cached opensearch_py-2.7.1-py3-none-any.whl.metadata (6.9 kB)
    Requirement already satisfied: requests<3.0.0,>=2.32.0 in /opt/conda/lib/python3.10/site-packages (from opensearch-py==2.7.1) (2.32.3)
    Requirement already satisfied: python-dateutil in /opt/conda/lib/python3.10/site-packages (from opensearch-py==2.7.1) (2.9.0)
    Requirement already satisfied: certifi>=2024.07.04 in /opt/conda/lib/python3.10/site-packages (from opensearch-py==2.7.1) (2024.7.4)
    Collecting Events (from opensearch-py==2.7.1)
      Using cached Events-0.5-py3-none-any.whl.metadata (3.9 kB)
    Requirement already satisfied: urllib3!=2.2.0,!=2.2.1,<3,>=1.26.19 in /opt/conda/lib/python3.10/site-packages (from opensearch-py==2.7.1) (1.26.19)
    Requirement already satisfied: charset-normalizer<4,>=2 in /opt/conda/lib/python3.10/site-packages (from requests<3.0.0,>=2.32.0->opensearch-py==2.7.1) (3.3.2)
    Requirement already satisfied: idna<4,>=2.5 in /opt/conda/lib/python3.10/site-packages (from requests<3.0.0,>=2.32.0->opensearch-py==2.7.1) (3.7)
    Requirement already satisfied: six>=1.5 in /opt/conda/lib/python3.10/site-packages (from python-dateutil->opensearch-py==2.7.1) (1.16.0)
    Using cached opensearch_py-2.7.1-py3-none-any.whl (325 kB)
    Using cached Events-0.5-py3-none-any.whl (6.8 kB)
    Installing collected packages: Events, opensearch-py
    Successfully installed Events-0.5 opensearch-py-2.7.1
    Note: you may need to restart the kernel to use updated packages.
    Collecting boto3==1.34.162
      Using cached boto3-1.34.162-py3-none-any.whl.metadata (6.6 kB)
    Collecting botocore<1.35.0,>=1.34.162 (from boto3==1.34.162)
      Using cached botocore-1.34.162-py3-none-any.whl.metadata (5.7 kB)
    Requirement already satisfied: jmespath<2.0.0,>=0.7.1 in /opt/conda/lib/python3.10/site-packages (from boto3==1.34.162) (1.0.1)
    Requirement already satisfied: s3transfer<0.11.0,>=0.10.0 in /opt/conda/lib/python3.10/site-packages (from boto3==1.34.162) (0.10.2)
    Requirement already satisfied: python-dateutil<3.0.0,>=2.1 in /opt/conda/lib/python3.10/site-packages (from botocore<1.35.0,>=1.34.162->boto3==1.34.162) (2.9.0)
    Requirement already satisfied: urllib3!=2.2.0,<3,>=1.25.4 in /opt/conda/lib/python3.10/site-packages (from botocore<1.35.0,>=1.34.162->boto3==1.34.162) (1.26.19)
    Requirement already satisfied: six>=1.5 in /opt/conda/lib/python3.10/site-packages (from python-dateutil<3.0.0,>=2.1->botocore<1.35.0,>=1.34.162->boto3==1.34.162) (1.16.0)
    Using cached boto3-1.34.162-py3-none-any.whl (139 kB)
    Using cached botocore-1.34.162-py3-none-any.whl (12.5 MB)
    Installing collected packages: botocore, boto3
      Attempting uninstall: botocore
        Found existing installation: botocore 1.35.12
        Uninstalling botocore-1.35.12:
          Successfully uninstalled botocore-1.35.12
      Attempting uninstall: boto3
        Found existing installation: boto3 1.35.12
        Uninstalling boto3-1.35.12:
          Successfully uninstalled boto3-1.35.12
    [31mERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
    aiobotocore 2.13.1 requires botocore<1.34.132,>=1.34.70, but you have botocore 1.34.162 which is incompatible.
    amazon-sagemaker-sql-magic 0.1.3 requires sqlparse==0.5.0, but you have sqlparse 0.5.1 which is incompatible.
    autogluon-common 0.8.3 requires pandas<1.6,>=1.4.1, but you have pandas 2.1.4 which is incompatible.
    autogluon-core 0.8.3 requires pandas<1.6,>=1.4.1, but you have pandas 2.1.4 which is incompatible.
    autogluon-core 0.8.3 requires scikit-learn<1.4.1,>=1.1, but you have scikit-learn 1.4.2 which is incompatible.
    autogluon-features 0.8.3 requires pandas<1.6,>=1.4.1, but you have pandas 2.1.4 which is incompatible.
    autogluon-features 0.8.3 requires scikit-learn<1.4.1,>=1.1, but you have scikit-learn 1.4.2 which is incompatible.
    autogluon-multimodal 0.8.3 requires pandas<1.6,>=1.4.1, but you have pandas 2.1.4 which is incompatible.
    autogluon-multimodal 0.8.3 requires pytorch-lightning<1.10.0,>=1.9.0, but you have pytorch-lightning 2.0.9 which is incompatible.
    autogluon-multimodal 0.8.3 requires scikit-learn<1.4.1,>=1.1, but you have scikit-learn 1.4.2 which is incompatible.
    autogluon-multimodal 0.8.3 requires torch<1.14,>=1.9, but you have torch 2.0.0.post104 which is incompatible.
    autogluon-multimodal 0.8.3 requires torchmetrics<0.12.0,>=0.11.0, but you have torchmetrics 1.0.3 which is incompatible.
    autogluon-multimodal 0.8.3 requires torchvision<0.15.0, but you have torchvision 0.15.2a0+ab7b3e6 which is incompatible.
    autogluon-tabular 0.8.3 requires pandas<1.6,>=1.4.1, but you have pandas 2.1.4 which is incompatible.
    autogluon-tabular 0.8.3 requires scikit-learn<1.4.1,>=1.1, but you have scikit-learn 1.4.2 which is incompatible.
    autogluon-timeseries 0.8.3 requires pandas<1.6,>=1.4.1, but you have pandas 2.1.4 which is incompatible.
    autogluon-timeseries 0.8.3 requires pytorch-lightning<1.10.0,>=1.7.4, but you have pytorch-lightning 2.0.9 which is incompatible.
    autogluon-timeseries 0.8.3 requires torch<1.14,>=1.9, but you have torch 2.0.0.post104 which is incompatible.[0m[31m
    [0mSuccessfully installed boto3-1.34.162 botocore-1.34.162
    Note: you may need to restart the kernel to use updated packages.
    Collecting retrying==1.3.4
      Using cached retrying-1.3.4-py3-none-any.whl.metadata (6.9 kB)
    Requirement already satisfied: six>=1.7.0 in /opt/conda/lib/python3.10/site-packages (from retrying==1.3.4) (1.16.0)
    Using cached retrying-1.3.4-py3-none-any.whl (11 kB)
    Installing collected packages: retrying
      Attempting uninstall: retrying
        Found existing installation: retrying 1.3.3
        Uninstalling retrying-1.3.3:
          Successfully uninstalled retrying-1.3.3
    [31mERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
    dash 2.17.1 requires dash-core-components==2.0.0, which is not installed.
    dash 2.17.1 requires dash-html-components==2.0.0, which is not installed.
    dash 2.17.1 requires dash-table==5.0.0, which is not installed.[0m[31m
    [0mSuccessfully installed retrying-1.3.4
    Note: you may need to restart the kernel to use updated packages.


<h2>Setup</h2>

Before running the rest of this notebook, you'll need to run the cell below to restart the kernel. If it does not work please manually restar the kernel. 


```python
# restart kernel
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```




<script>Jupyter.notebook.kernel.restart()</script>



We import the required libraries and initialize the required variables.


```python
import warnings
warnings.filterwarnings('ignore')
```


```python
import json
import os
import boto3
from botocore.exceptions import ClientError
import pprint
from utility import create_bedrock_execution_role, create_oss_policy_attach_bedrock_execution_role, create_policies_in_oss, interactive_sleep
import random
from retrying import retry

```


```python
suffix = random.randrange(200, 900)

sts_client = boto3.client('sts')
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
bedrock_agent_client = boto3_session.client('bedrock-agent', region_name=region_name)
service = 'aoss'
s3_client = boto3.client('s3')
account_id = sts_client.get_caller_identity()["Account"]
s3_suffix = f"{region_name}-{account_id}"
bucket_name = f'bedrock-kb-{s3_suffix}' # replace it with your bucket name.
pp = pprint.PrettyPrinter(indent=2)
```


```python
# Check if bucket exists, and if not create S3 bucket for knowledge base data source
try:
    s3_client.head_bucket(Bucket=bucket_name)
    print(f'Bucket {bucket_name} Exists')
except ClientError as e:
    print(f'Creating bucket {bucket_name}')
    if region_name == "us-east-1":
        s3bucket = s3_client.create_bucket(
            Bucket=bucket_name)
    else:
        s3bucket = s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={ 'LocationConstraint': region_name }
    )
```

    Creating bucket bedrock-kb-ap-south-1-874163252636



```python
%store bucket_name
```

    Stored 'bucket_name' (str)


<h2>Code</h2>


<h3>Create a Vector Store - OpenSearch Serverless index</h3>

<h4>Step 1 - Create OSS policies and collection</h4>
First of all we have to create a vector store. In this section we will use <strong>Amazon OpenSerach serverless</strong>.

Amazon OpenSearch Serverless is a serverless option in Amazon OpenSearch Service. As a developer, you can use OpenSearch Serverless to run petabyte-scale workloads without configuring, managing, and scaling OpenSearch clusters. You get the same interactive millisecond response times as OpenSearch Service with the simplicity of a serverless environment. Pay only for what you use by automatically scaling resources to provide the right amount of capacity for your application—without impacting data ingestion.


```python
import boto3
import time
vector_store_name = f'bedrock-sample-rag-{suffix}'
index_name = f"bedrock-sample-rag-index-{suffix}"
aoss_client = boto3_session.client('opensearchserverless')
bedrock_kb_execution_role = create_bedrock_execution_role(bucket_name=bucket_name)
bedrock_kb_execution_role_arn = bedrock_kb_execution_role['Role']['Arn']
```


```python
# create security, network and data access policies within OSS
encryption_policy, network_policy, access_policy = create_policies_in_oss(vector_store_name=vector_store_name,
                       aoss_client=aoss_client,
                       bedrock_kb_execution_role_arn=bedrock_kb_execution_role_arn)
collection = aoss_client.create_collection(name=vector_store_name,type='VECTORSEARCH')
```


```python
pp.pprint(collection)
```

    { 'ResponseMetadata': { 'HTTPHeaders': { 'connection': 'keep-alive',
                                             'content-length': '315',
                                             'content-type': 'application/x-amz-json-1.0',
                                             'date': 'Thu, 05 Sep 2024 15:19:34 '
                                                     'GMT',
                                             'x-amzn-requestid': '01ad6cd7-e0d6-431d-b8dc-68a75228dd78'},
                            'HTTPStatusCode': 200,
                            'RequestId': '01ad6cd7-e0d6-431d-b8dc-68a75228dd78',
                            'RetryAttempts': 0},
      'createCollectionDetail': { 'arn': 'arn:aws:aoss:ap-south-1:874163252636:collection/qucjcmpe10mr2kv6jaf2',
                                  'createdDate': 1725549573961,
                                  'id': 'qucjcmpe10mr2kv6jaf2',
                                  'kmsKeyArn': 'auto',
                                  'lastModifiedDate': 1725549573961,
                                  'name': 'bedrock-sample-rag-416',
                                  'standbyReplicas': 'ENABLED',
                                  'status': 'CREATING',
                                  'type': 'VECTORSEARCH'}}



```python
%store encryption_policy network_policy access_policy collection
```

    Stored 'encryption_policy' (dict)
    Stored 'network_policy' (dict)
    Stored 'access_policy' (dict)
    Stored 'collection' (dict)



```python
# Get the OpenSearch serverless collection URL
collection_id = collection['createCollectionDetail']['id']
host = collection_id + '.' + region_name + '.aoss.amazonaws.com'
print(host)
```

    qucjcmpe10mr2kv6jaf2.ap-south-1.aoss.amazonaws.com



```python
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

    Creating collection...
    Creating collection...........
    Creating collection...........
    Creating collection...........
    Creating collection...........
    Creating collection...........
    Creating collection...........
    Creating collection...........
    Creating collection...........
    Creating collection...........
    ..............................
    Collection successfully created:
    [ { 'arn': 'arn:aws:aoss:ap-south-1:874163252636:collection/qucjcmpe10mr2kv6jaf2',
        'collectionEndpoint': 'https://qucjcmpe10mr2kv6jaf2.ap-south-1.aoss.amazonaws.com',
        'createdDate': 1725549573961,
        'dashboardEndpoint': 'https://qucjcmpe10mr2kv6jaf2.ap-south-1.aoss.amazonaws.com/_dashboards',
        'id': 'qucjcmpe10mr2kv6jaf2',
        'kmsKeyArn': 'auto',
        'lastModifiedDate': 1725549870683,
        'name': 'bedrock-sample-rag-416',
        'standbyReplicas': 'ENABLED',
        'status': 'ACTIVE',
        'type': 'VECTORSEARCH'}]



```python
# create opensearch serverless access policy and attach it to Bedrock execution role
try:
    create_oss_policy_attach_bedrock_execution_role(collection_id=collection_id,
                                                    bedrock_kb_execution_role=bedrock_kb_execution_role)
    # It can take up to a minute for data access rules to be enforced
    interactive_sleep(60)
except Exception as e:
    print("Policy already exists")
    pp.pprint(e)
```

    Opensearch serverless arn:  arn:aws:iam::874163252636:policy/AmazonBedrockOSSPolicyForKnowledgeBase_653
    ............................................................

<h4>Step 2 - Create vector index</h4>


```python
# Create the vector index in Opensearch serverless, with the knn_vector field index mapping, specifying the dimension size, name and engine.
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, RequestError
credentials = boto3.Session().get_credentials()
awsauth = AWSV4SignerAuth(credentials, region_name, service)

index_name = f"bedrock-sample-index-{suffix}"
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
            "dimension": 1024,
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
            "type": "text"         
         }
      }
   }
}

# Build the OpenSearch client
oss_client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)

```


```python
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
    print(f'Error while trying to create the index, with error {e.error}\nyou may unmark the delete above to delete, and recreate the index')
    
```

    
    Creating index:
    { 'acknowledged': True,
      'index': 'bedrock-sample-index-416',
      'shards_acknowledged': True}
    ............................................................

<h3>Download data to ingest into our knowledge base</h3>

<h4>Download and Prepare dataset</h4>


```python

!mkdir -p ./assets/data

from urllib.request import urlretrieve
urls = [
    'https://s2.q4cdn.com/299287126/files/doc_financials/2023/ar/2022-Shareholder-Letter.pdf',
    'https://s2.q4cdn.com/299287126/files/doc_financials/2022/ar/2021-Shareholder-Letter.pdf',
    'https://s2.q4cdn.com/299287126/files/doc_financials/2021/ar/Amazon-2020-Shareholder-Letter-and-1997-Shareholder-Letter.pdf',
    'https://s2.q4cdn.com/299287126/files/doc_financials/2020/ar/2019-Shareholder-Letter.pdf'
]

filenames = [
    'AMZN-2022-Shareholder-Letter.pdf',
    'AMZN-2021-Shareholder-Letter.pdf',
    'AMZN-2020-Shareholder-Letter.pdf',
    'AMZN-2019-Shareholder-Letter.pdf'
]

data_root = "./assets/data/"

for idx, url in enumerate(urls):
    file_path = data_root + filenames[idx]
    urlretrieve(url, file_path)

```

<h4>Upload data to S3 Bucket data source</h4>


```python
# Upload data to s3 to the bucket that was configured as a data source to the knowledge base
s3_client = boto3.client("s3")
def uploadDirectory(path,bucket_name):
        for root,dirs,files in os.walk(path):
            for file in files:
                s3_client.upload_file(os.path.join(root,file),bucket_name,file)

uploadDirectory(data_root, bucket_name)
```

<h3>Create Knowledge Base</h3>

Steps:
<ul>
<li>initialize Open search serverless configuration which will include collection ARN, index name, vector field, text field and metadata field.</li>
<li>initialize chunking strategy, based on which KB will split the documents into pieces of size equal to the chunk size mentioned in the <strong>chunkingStrategyConfiguration</strong>.</li>
<li>initialize the s3 configuration, which will be used to create the data source object later.</li>
<li>initialize the Cohere Embed Multilingual embeddings model ARN, as this will be used to create the embeddings for each of the text chunks.</li>
</ul>


```python
opensearchServerlessConfiguration = {
            "collectionArn": collection["createCollectionDetail"]['arn'],
            "vectorIndexName": index_name,
            "fieldMapping": {
                "vectorField": "vector",
                "textField": "text",
                "metadataField": "text-metadata"
            }
        }

# Ingest strategy - How to ingest data from the data source
chunkingStrategyConfiguration = {
    "chunkingStrategy": "FIXED_SIZE",
    "fixedSizeChunkingConfiguration": {
        "maxTokens": 512,
        "overlapPercentage": 20
    }
}

# The data source to ingest documents from, into the OpenSearch serverless knowledge base index
s3Configuration = {
    "bucketArn": f"arn:aws:s3:::{bucket_name}",
    # "inclusionPrefixes":["*.*"] # you can use this if you want to create a KB using data within s3 prefixes.
}

# The embedding model used by Bedrock to embed ingested documents, and realtime prompts
embeddingModelArn = f"arn:aws:bedrock:{region_name}::foundation-model/cohere.embed-multilingual-v3"

name = f"bedrock-sample-knowledge-base-{suffix}"
description = "Amazon shareholder letter knowledge base."
roleArn = bedrock_kb_execution_role_arn

```

Provide the above configurations as input to the `create_knowledge_base` method, which will create the Knowledge base.


```python
# Create a KnowledgeBase
from retrying import retry

@retry(wait_random_min=1000, wait_random_max=2000,stop_max_attempt_number=7)
def create_knowledge_base_func():
    create_kb_response = bedrock_agent_client.create_knowledge_base(
        name = name,
        description = description,
        roleArn = roleArn,
        knowledgeBaseConfiguration = {
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": embeddingModelArn
            }
        },
        storageConfiguration = {
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration":opensearchServerlessConfiguration
        }
    )
    return create_kb_response["knowledgeBase"]
```


```python
try:
    kb = create_knowledge_base_func()
except Exception as err:
    print(f"{err=}, {type(err)=}")
```


```python
pp.pprint(kb)
```

    { 'createdAt': datetime.datetime(2024, 9, 5, 15, 26, 39, 640513, tzinfo=tzlocal()),
      'description': 'Amazon shareholder letter knowledge base.',
      'knowledgeBaseArn': 'arn:aws:bedrock:ap-south-1:874163252636:knowledge-base/KV0AYQHWPO',
      'knowledgeBaseConfiguration': { 'type': 'VECTOR',
                                      'vectorKnowledgeBaseConfiguration': { 'embeddingModelArn': 'arn:aws:bedrock:ap-south-1::foundation-model/cohere.embed-multilingual-v3'}},
      'knowledgeBaseId': 'KV0AYQHWPO',
      'name': 'bedrock-sample-knowledge-base-416',
      'roleArn': 'arn:aws:iam::874163252636:role/AmazonBedrockExecutionRoleForKnowledgeBase_653',
      'status': 'CREATING',
      'storageConfiguration': { 'opensearchServerlessConfiguration': { 'collectionArn': 'arn:aws:aoss:ap-south-1:874163252636:collection/qucjcmpe10mr2kv6jaf2',
                                                                       'fieldMapping': { 'metadataField': 'text-metadata',
                                                                                         'textField': 'text',
                                                                                         'vectorField': 'vector'},
                                                                       'vectorIndexName': 'bedrock-sample-index-416'},
                                'type': 'OPENSEARCH_SERVERLESS'},
      'updatedAt': datetime.datetime(2024, 9, 5, 15, 26, 39, 640513, tzinfo=tzlocal())}



```python
# Get KnowledgeBase 
get_kb_response = bedrock_agent_client.get_knowledge_base(knowledgeBaseId = kb['knowledgeBaseId'])
```

Next we need to create a data source, which will be associated with the knowledge base created above. Once the data source is ready, we can then start to ingest the documents.


```python
# Create a DataSource in KnowledgeBase 
create_ds_response = bedrock_agent_client.create_data_source(
    name = name,
    description = description,
    knowledgeBaseId = kb['knowledgeBaseId'],
    dataSourceConfiguration = {
        "type": "S3",
        "s3Configuration":s3Configuration
    },
    vectorIngestionConfiguration = {
        "chunkingConfiguration": chunkingStrategyConfiguration
    }
)
ds = create_ds_response["dataSource"]
pp.pprint(ds)
```

    { 'createdAt': datetime.datetime(2024, 9, 5, 15, 26, 40, 575472, tzinfo=tzlocal()),
      'dataDeletionPolicy': 'DELETE',
      'dataSourceConfiguration': { 's3Configuration': { 'bucketArn': 'arn:aws:s3:::bedrock-kb-ap-south-1-874163252636'},
                                   'type': 'S3'},
      'dataSourceId': 'QSPUTYFUTO',
      'description': 'Amazon shareholder letter knowledge base.',
      'knowledgeBaseId': 'KV0AYQHWPO',
      'name': 'bedrock-sample-knowledge-base-416',
      'status': 'AVAILABLE',
      'updatedAt': datetime.datetime(2024, 9, 5, 15, 26, 40, 575472, tzinfo=tzlocal()),
      'vectorIngestionConfiguration': { 'chunkingConfiguration': { 'chunkingStrategy': 'FIXED_SIZE',
                                                                   'fixedSizeChunkingConfiguration': { 'maxTokens': 512,
                                                                                                       'overlapPercentage': 20}}}}



```python
# Get DataSource 
bedrock_agent_client.get_data_source(knowledgeBaseId = kb['knowledgeBaseId'], dataSourceId = ds["dataSourceId"])
```




    {'ResponseMetadata': {'RequestId': '347bc56b-54dc-4f44-91dd-2d6a0ae59f84',
      'HTTPStatusCode': 200,
      'HTTPHeaders': {'date': 'Thu, 05 Sep 2024 15:26:40 GMT',
       'content-type': 'application/json',
       'content-length': '604',
       'connection': 'keep-alive',
       'x-amzn-requestid': '347bc56b-54dc-4f44-91dd-2d6a0ae59f84',
       'x-amz-apigw-id': 'do0ToEJnhcwEKDQ=',
       'x-amzn-trace-id': 'Root=1-66d9cdb0-246bf56070b1f22904afba54'},
      'RetryAttempts': 0},
     'dataSource': {'createdAt': datetime.datetime(2024, 9, 5, 15, 26, 40, 575472, tzinfo=tzlocal()),
      'dataDeletionPolicy': 'DELETE',
      'dataSourceConfiguration': {'s3Configuration': {'bucketArn': 'arn:aws:s3:::bedrock-kb-ap-south-1-874163252636'},
       'type': 'S3'},
      'dataSourceId': 'QSPUTYFUTO',
      'description': 'Amazon shareholder letter knowledge base.',
      'knowledgeBaseId': 'KV0AYQHWPO',
      'name': 'bedrock-sample-knowledge-base-416',
      'status': 'AVAILABLE',
      'updatedAt': datetime.datetime(2024, 9, 5, 15, 26, 40, 575472, tzinfo=tzlocal()),
      'vectorIngestionConfiguration': {'chunkingConfiguration': {'chunkingStrategy': 'FIXED_SIZE',
        'fixedSizeChunkingConfiguration': {'maxTokens': 512,
         'overlapPercentage': 20}}}}}



<h3>Start ingestion job</h3>

Once the KB and data source is created, we can start the ingestion job.

During the ingestion job, KB will fetch the documents in the data source, pre-process it to extract text, chunk it based on the chunking size provided, create embeddings of each chunk and then write it to the vector database, in this case OSS.


```python
# Start an ingestion job
start_job_response = bedrock_agent_client.start_ingestion_job(knowledgeBaseId = kb['knowledgeBaseId'], dataSourceId = ds["dataSourceId"])
```


```python
job = start_job_response["ingestionJob"]
pp.pprint(job)
```

    { 'dataSourceId': 'QSPUTYFUTO',
      'ingestionJobId': 'GGKHXD6XUE',
      'knowledgeBaseId': 'KV0AYQHWPO',
      'startedAt': datetime.datetime(2024, 9, 5, 15, 30, 24, 145767, tzinfo=tzlocal()),
      'statistics': { 'numberOfDocumentsDeleted': 0,
                      'numberOfDocumentsFailed': 0,
                      'numberOfDocumentsScanned': 0,
                      'numberOfMetadataDocumentsModified': 0,
                      'numberOfMetadataDocumentsScanned': 0,
                      'numberOfModifiedDocumentsIndexed': 0,
                      'numberOfNewDocumentsIndexed': 0},
      'status': 'STARTING',
      'updatedAt': datetime.datetime(2024, 9, 5, 15, 30, 24, 145767, tzinfo=tzlocal())}



```python
# Get job 
while(job['status']!='COMPLETE' ):
    get_job_response = bedrock_agent_client.get_ingestion_job(
      knowledgeBaseId = kb['knowledgeBaseId'],
        dataSourceId = ds["dataSourceId"],
        ingestionJobId = job["ingestionJobId"]
  )
    job = get_job_response["ingestionJob"]
    
    interactive_sleep(30)

pp.pprint(job)
```

    { 'dataSourceId': 'QSPUTYFUTO',
      'ingestionJobId': 'GGKHXD6XUE',
      'knowledgeBaseId': 'KV0AYQHWPO',
      'startedAt': datetime.datetime(2024, 9, 5, 15, 30, 24, 145767, tzinfo=tzlocal()),
      'statistics': { 'numberOfDocumentsDeleted': 0,
                      'numberOfDocumentsFailed': 0,
                      'numberOfDocumentsScanned': 4,
                      'numberOfMetadataDocumentsModified': 0,
                      'numberOfMetadataDocumentsScanned': 0,
                      'numberOfModifiedDocumentsIndexed': 0,
                      'numberOfNewDocumentsIndexed': 4},
      'status': 'COMPLETE',
      'updatedAt': datetime.datetime(2024, 9, 5, 15, 30, 40, 332743, tzinfo=tzlocal())}



```python
# Print the knowledge base Id in bedrock, that corresponds to the Opensearch index in the collection we created before, we will use it for the invocation later
kb_id = kb["knowledgeBaseId"]
pp.pprint(kb_id)
```

    'KV0AYQHWPO'



```python
# keep the kb_id for invocation later in the invoke request
%store kb_id
```

    Stored 'kb_id' (str)


<h3>Test the knowledge base</h3>

<b>Note: If you plan to run any of the notebooks in the current folder then, you can skip this section</b>

<h4>RetrieveAndGenerate API</h4>

Behind the scenes, RetrieveAndGenerate API converts queries into embeddings, searches the knowledge base, and then augments the foundation model prompt with the search results as context information and returns the FM-generated response to the question. For multi-turn conversations, Knowledge Bases manage short-term memory of the conversation to provide more contextual results.

The output of the RetrieveAndGenerate API includes the generated response, source attribution as well as the retrieved text chunks.


```python
# try out KB using RetrieveAndGenerate API
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=region_name)
# Lets see how different Anthropic Claude 3 models responds to the input text we provide
claude_model_ids = [ ["Claude 3 Sonnet", "anthropic.claude-3-sonnet-20240229-v1:0"], ["Claude 3 Haiku", "anthropic.claude-3-haiku-20240307-v1:0"]]
```


```python
def ask_bedrock_llm_with_knowledge_base(query: str, model_arn: str, kb_id: str) -> str:
    response = bedrock_agent_runtime_client.retrieve_and_generate(
        input={
            'text': query
        },
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': kb_id,
                'modelArn': model_arn
            }
        },
    )

    return response
```


```python
query = "What is Amazon's doing in the field of generative AI?"

for model_id in claude_model_ids:
    model_arn = f'arn:aws:bedrock:{region_name}::foundation-model/{model_id[1]}'
    response = ask_bedrock_llm_with_knowledge_base(query, model_arn, kb_id)
    generated_text = response['output']['text']
    citations = response["citations"]
    contexts = []
    for citation in citations:
        retrievedReferences = citation["retrievedReferences"]
        for reference in retrievedReferences:
            contexts.append(reference["content"]["text"])
    print(f"---------- Generated using {model_id[0]}:")
    pp.pprint(generated_text )
    print(f'---------- The citations for the response generated by {model_id[0]}:')
    pp.pprint(contexts)
    print()
```

    ---------- Generated using Claude 3 Sonnet:
    ('Amazon has been investing heavily in large language models (LLMs) and '
     'generative AI, which it believes will transform and improve virtually every '
     'customer experience across its consumer, seller, brand, and creator '
     'offerings. Amazon has been working on its own LLMs for a while and plans to '
     'continue investing substantially in these models. For its cloud computing '
     'service AWS, Amazon is offering machine learning chips like Trainium and '
     'Inferentia that provide cost-effective training and inference for LLMs, '
     'allowing companies of all sizes to leverage generative AI. AWS is also '
     'delivering applications like CodeWhisperer that use generative AI to improve '
     'developer productivity by generating code suggestions in real time.')
    ---------- The citations for the response generated by Claude 3 Sonnet:
    [ 'The customer reaction to what we’ve shared thus far about Kuiper has been '
      'very positive, and we believe Kuiper represents a very large potential '
      'opportunity for Amazon. It also shares several similarities to AWS in that '
      'it’s capital intensive at the start, but has a large prospective consumer, '
      'enterprise, and government customer base, significant revenue and operating '
      'profit potential, and relatively few companies with the technical and '
      'inventive aptitude, as well as the investment hypothesis to go after it.   '
      'One final investment area that I’ll mention, that’s core to setting Amazon '
      'up to invent in every area of our business for many decades to come, and '
      'where we’re investing heavily is Large Language Models (“LLMs”) and '
      'Generative AI. Machine learning has been a technology with high promise for '
      'several decades, but it’s only been the last five to ten years that it’s '
      'started to be used more pervasively by companies. This shift was driven by '
      'several factors, including access to higher volumes of compute capacity at '
      'lower prices than was ever available. Amazon has been using machine '
      'learning extensively for 25 years, employing it in everything from '
      'personalized ecommerce recommendations, to fulfillment center pick paths, '
      'to drones for Prime Air, to Alexa, to the many machine learning services '
      'AWS offers (where AWS has the broadest machine learning functionality and '
      'customer base of any cloud provider). More recently, a newer form of '
      'machine learning, called Generative AI, has burst onto the scene and '
      'promises to significantly accelerate machine learning adoption. Generative '
      'AI is based on very Large Language Models (trained on up to hundreds of '
      'billions of parameters, and growing), across expansive datasets, and has '
      'radically general and broad recall and learning capabilities.',
      'Generative AI is based on very Large Language Models (trained on up to '
      'hundreds of billions of parameters, and growing), across expansive '
      'datasets, and has radically general and broad recall and learning '
      'capabilities. We have been working on our own LLMs for a while now, believe '
      'it will transform and improve virtually every customer experience, and will '
      'continue to invest substantially in these models across all of our '
      'consumer, seller, brand, and creator experiences. Additionally, as we’ve '
      'done for years in AWS, we’re democratizing this technology so companies of '
      'all sizes can leverage Generative AI. AWS is offering the most '
      'price-performant machine learning chips in Trainium and Inferentia so small '
      'and large companies can afford to train and run their LLMs in production. '
      'We enable companies to choose from various LLMs and build applications with '
      'all of the AWS security, privacy and other features that customers are '
      'accustomed to using. And, we’re delivering applications like AWS’s '
      'CodeWhisperer, which revolutionizes        developer productivity by '
      'generating code suggestions in real time. I could write an entire letter on '
      'LLMs and Generative AI as I think they will be that transformative, but '
      'I’ll leave that for a future letter. Let’s just say that LLMs and '
      'Generative AI are going to be a big deal for customers, our shareholders, '
      'and Amazon.   So, in closing, I’m optimistic that we’ll emerge from this '
      'challenging macroeconomic time in a stronger position than when we entered '
      'it. There are several reasons for it and I’ve mentioned many of them above. '
      'But, there are two relatively simple statistics that underline our immense '
      'future opportunity. While we have a consumer business that’s $434B in 2022, '
      'the vast majority of total market segment share in global retail still '
      'resides in physical stores (roughly 80%). And, it’s a similar story for '
      'Global IT spending, where we have AWS revenue of $80B in 2022, with about '
      '90% of Global IT spending still on-premises and yet to migrate to the '
      'cloud.',
      'Most companies are still in the training stage, but as they develop models '
      'that graduate to large-scale production, they’ll find that most of the cost '
      'is in inference because models are trained periodically whereas inferences '
      'are happening all the time as their associated application is being '
      'exercised. We launched our first inference chips (“Inferentia”) in 2019, '
      'and they have saved companies like Amazon over a hundred million dollars in '
      'capital expense already. Our Inferentia2 chip, which just launched, offers '
      'up to four times higher throughput and ten times lower latency than our '
      'first Inferentia processor. With the enormous upcoming growth in machine '
      'learning, customers will be able to get a lot more done with AWS’s training '
      'and inference chips at a significantly lower cost. We’re not close to being '
      'done innovating here, and this long-term investment should prove fruitful '
      'for both customers and AWS. AWS is still in the early stages of its '
      'evolution, and has a chance for unusual growth in the next decade.   '
      'Similarly high potential, Amazon’s Advertising business is uniquely '
      'effective for brands, which is part of why it continues to grow at a brisk '
      'clip. Akin to physical retailers’ advertising businesses selling shelf '
      'space, end- caps, and placement in their circulars, our sponsored products '
      'and brands offerings have been an integral part        of the Amazon '
      'shopping experience for more than a decade. However, unlike physical '
      'retailers, Amazon can tailor these sponsored products to be relevant to '
      'what customers are searching for given what we know about shopping '
      'behaviors and our very deep investment in machine learning algorithms. This '
      'leads to advertising that’s more useful for customers; and as a result, '
      'performs better for brands. This is part of why our Advertising revenue has '
      'continued to grow rapidly (23% YoY in Q4 2022, 25% YoY overall for 2022 on '
      'a $31B revenue base), even as most large advertising-focused businesses’ '
      'growth have slowed over the last several quarters.',
      'Generative AI is based on very Large Language Models (trained on up to '
      'hundreds of billions of parameters, and growing), across expansive '
      'datasets, and has radically general and broad recall and learning '
      'capabilities. We have been working on our own LLMs for a while now, believe '
      'it will transform and improve virtually every customer experience, and will '
      'continue to invest substantially in these models across all of our '
      'consumer, seller, brand, and creator experiences. Additionally, as we’ve '
      'done for years in AWS, we’re democratizing this technology so companies of '
      'all sizes can leverage Generative AI. AWS is offering the most '
      'price-performant machine learning chips in Trainium and Inferentia so small '
      'and large companies can afford to train and run their LLMs in production. '
      'We enable companies to choose from various LLMs and build applications with '
      'all of the AWS security, privacy and other features that customers are '
      'accustomed to using. And, we’re delivering applications like AWS’s '
      'CodeWhisperer, which revolutionizes        developer productivity by '
      'generating code suggestions in real time. I could write an entire letter on '
      'LLMs and Generative AI as I think they will be that transformative, but '
      'I’ll leave that for a future letter. Let’s just say that LLMs and '
      'Generative AI are going to be a big deal for customers, our shareholders, '
      'and Amazon.   So, in closing, I’m optimistic that we’ll emerge from this '
      'challenging macroeconomic time in a stronger position than when we entered '
      'it. There are several reasons for it and I’ve mentioned many of them above. '
      'But, there are two relatively simple statistics that underline our immense '
      'future opportunity. While we have a consumer business that’s $434B in 2022, '
      'the vast majority of total market segment share in global retail still '
      'resides in physical stores (roughly 80%). And, it’s a similar story for '
      'Global IT spending, where we have AWS revenue of $80B in 2022, with about '
      '90% of Global IT spending still on-premises and yet to migrate to the '
      'cloud.']
    
    ---------- Generated using Claude 3 Haiku:
    ('Amazon is heavily investing in large language models (LLMs) and generative '
     'AI, which they believe will transform and improve virtually every customer '
     'experience. They have been working on their own LLMs and are democratizing '
     'this technology so companies of all sizes can leverage generative AI. AWS is '
     'offering the most price-performant machine learning chips in Trainium and '
     'Inferentia to enable companies to train and run their LLMs in production. '
     'Additionally, AWS is delivering applications like CodeWhisperer that use '
     'generative AI to revolutionize developer productivity by generating code '
     'suggestions in real time.')
    ---------- The citations for the response generated by Claude 3 Haiku:
    [ 'The customer reaction to what we’ve shared thus far about Kuiper has been '
      'very positive, and we believe Kuiper represents a very large potential '
      'opportunity for Amazon. It also shares several similarities to AWS in that '
      'it’s capital intensive at the start, but has a large prospective consumer, '
      'enterprise, and government customer base, significant revenue and operating '
      'profit potential, and relatively few companies with the technical and '
      'inventive aptitude, as well as the investment hypothesis to go after it.   '
      'One final investment area that I’ll mention, that’s core to setting Amazon '
      'up to invent in every area of our business for many decades to come, and '
      'where we’re investing heavily is Large Language Models (“LLMs”) and '
      'Generative AI. Machine learning has been a technology with high promise for '
      'several decades, but it’s only been the last five to ten years that it’s '
      'started to be used more pervasively by companies. This shift was driven by '
      'several factors, including access to higher volumes of compute capacity at '
      'lower prices than was ever available. Amazon has been using machine '
      'learning extensively for 25 years, employing it in everything from '
      'personalized ecommerce recommendations, to fulfillment center pick paths, '
      'to drones for Prime Air, to Alexa, to the many machine learning services '
      'AWS offers (where AWS has the broadest machine learning functionality and '
      'customer base of any cloud provider). More recently, a newer form of '
      'machine learning, called Generative AI, has burst onto the scene and '
      'promises to significantly accelerate machine learning adoption. Generative '
      'AI is based on very Large Language Models (trained on up to hundreds of '
      'billions of parameters, and growing), across expansive datasets, and has '
      'radically general and broad recall and learning capabilities.',
      'Generative AI is based on very Large Language Models (trained on up to '
      'hundreds of billions of parameters, and growing), across expansive '
      'datasets, and has radically general and broad recall and learning '
      'capabilities. We have been working on our own LLMs for a while now, believe '
      'it will transform and improve virtually every customer experience, and will '
      'continue to invest substantially in these models across all of our '
      'consumer, seller, brand, and creator experiences. Additionally, as we’ve '
      'done for years in AWS, we’re democratizing this technology so companies of '
      'all sizes can leverage Generative AI. AWS is offering the most '
      'price-performant machine learning chips in Trainium and Inferentia so small '
      'and large companies can afford to train and run their LLMs in production. '
      'We enable companies to choose from various LLMs and build applications with '
      'all of the AWS security, privacy and other features that customers are '
      'accustomed to using. And, we’re delivering applications like AWS’s '
      'CodeWhisperer, which revolutionizes        developer productivity by '
      'generating code suggestions in real time. I could write an entire letter on '
      'LLMs and Generative AI as I think they will be that transformative, but '
      'I’ll leave that for a future letter. Let’s just say that LLMs and '
      'Generative AI are going to be a big deal for customers, our shareholders, '
      'and Amazon.   So, in closing, I’m optimistic that we’ll emerge from this '
      'challenging macroeconomic time in a stronger position than when we entered '
      'it. There are several reasons for it and I’ve mentioned many of them above. '
      'But, there are two relatively simple statistics that underline our immense '
      'future opportunity. While we have a consumer business that’s $434B in 2022, '
      'the vast majority of total market segment share in global retail still '
      'resides in physical stores (roughly 80%). And, it’s a similar story for '
      'Global IT spending, where we have AWS revenue of $80B in 2022, with about '
      '90% of Global IT spending still on-premises and yet to migrate to the '
      'cloud.']
    


<h4>Retrieve API</h4>

Retrieve API converts user queries into embeddings, searches the knowledge base, and returns the relevant results, giving you more control to build custom workﬂows on top of the semantic search results. The output of the Retrieve API includes the the retrieved text chunks, the location type and URI of the source data, as well as the relevance scores of the retrievals.


```python
# retrieve api for fetching only the relevant context.
relevant_documents = bedrock_agent_runtime_client.retrieve(
    retrievalQuery= {
        'text': query
    },
    knowledgeBaseId=kb_id,
    retrievalConfiguration= {
        'vectorSearchConfiguration': {
            'numberOfResults': 3 # will fetch top 3 documents which matches closely with the query.
        }
    }
)
```


```python
pp.pprint(relevant_documents["retrievalResults"])
```

    [ { 'content': { 'text': 'Generative AI is based on very Large Language Models '
                             '(trained on up to hundreds of billions of '
                             'parameters, and growing), across expansive datasets, '
                             'and has radically general and broad recall and '
                             'learning capabilities. We have been working on our '
                             'own LLMs for a while now, believe it will transform '
                             'and improve virtually every customer experience, and '
                             'will continue to invest substantially in these '
                             'models across all of our consumer, seller, brand, '
                             'and creator experiences. Additionally, as we’ve done '
                             'for years in AWS, we’re democratizing this '
                             'technology so companies of all sizes can leverage '
                             'Generative AI. AWS is offering the most '
                             'price-performant machine learning chips in Trainium '
                             'and Inferentia so small and large companies can '
                             'afford to train and run their LLMs in production. We '
                             'enable companies to choose from various LLMs and '
                             'build applications with all of the AWS security, '
                             'privacy and other features that customers are '
                             'accustomed to using. And, we’re delivering '
                             'applications like AWS’s CodeWhisperer, which '
                             'revolutionizes        developer productivity by '
                             'generating code suggestions in real time. I could '
                             'write an entire letter on LLMs and Generative AI as '
                             'I think they will be that transformative, but I’ll '
                             'leave that for a future letter. Let’s just say that '
                             'LLMs and Generative AI are going to be a big deal '
                             'for customers, our shareholders, and Amazon.   So, '
                             'in closing, I’m optimistic that we’ll emerge from '
                             'this challenging macroeconomic time in a stronger '
                             'position than when we entered it. There are several '
                             'reasons for it and I’ve mentioned many of them '
                             'above. But, there are two relatively simple '
                             'statistics that underline our immense future '
                             'opportunity. While we have a consumer business '
                             'that’s $434B in 2022, the vast majority of total '
                             'market segment share in global retail still resides '
                             'in physical stores (roughly 80%). And, it’s a '
                             'similar story for Global IT spending, where we have '
                             'AWS revenue of $80B in 2022, with about 90% of '
                             'Global IT spending still on-premises and yet to '
                             'migrate to the cloud.'},
        'location': { 's3Location': { 'uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf'},
                      'type': 'S3'},
        'metadata': { 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AD-7juJEBXwKXtPXx95ct',
                      'x-amz-bedrock-kb-data-source-id': 'MVXWUY4MBU',
                      'x-amz-bedrock-kb-source-uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf'},
        'score': 0.60410386},
      { 'content': { 'text': 'The customer reaction to what we’ve shared thus far '
                             'about Kuiper has been very positive, and we believe '
                             'Kuiper represents a very large potential opportunity '
                             'for Amazon. It also shares several similarities to '
                             'AWS in that it’s capital intensive at the start, but '
                             'has a large prospective consumer, enterprise, and '
                             'government customer base, significant revenue and '
                             'operating profit potential, and relatively few '
                             'companies with the technical and inventive aptitude, '
                             'as well as the investment hypothesis to go after '
                             'it.   One final investment area that I’ll mention, '
                             'that’s core to setting Amazon up to invent in every '
                             'area of our business for many decades to come, and '
                             'where we’re investing heavily is Large Language '
                             'Models (“LLMs”) and Generative AI. Machine learning '
                             'has been a technology with high promise for several '
                             'decades, but it’s only been the last five to ten '
                             'years that it’s started to be used more pervasively '
                             'by companies. This shift was driven by several '
                             'factors, including access to higher volumes of '
                             'compute capacity at lower prices than was ever '
                             'available. Amazon has been using machine learning '
                             'extensively for 25 years, employing it in everything '
                             'from personalized ecommerce recommendations, to '
                             'fulfillment center pick paths, to drones for Prime '
                             'Air, to Alexa, to the many machine learning services '
                             'AWS offers (where AWS has the broadest machine '
                             'learning functionality and customer base of any '
                             'cloud provider). More recently, a newer form of '
                             'machine learning, called Generative AI, has burst '
                             'onto the scene and promises to significantly '
                             'accelerate machine learning adoption. Generative AI '
                             'is based on very Large Language Models (trained on '
                             'up to hundreds of billions of parameters, and '
                             'growing), across expansive datasets, and has '
                             'radically general and broad recall and learning '
                             'capabilities.'},
        'location': { 's3Location': { 'uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf'},
                      'type': 'S3'},
        'metadata': { 'x-amz-bedrock-kb-chunk-id': '1%3A0%3ADu7juJEBXwKXtPXx95ct',
                      'x-amz-bedrock-kb-data-source-id': 'MVXWUY4MBU',
                      'x-amz-bedrock-kb-source-uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf'},
        'score': 0.5745951},
      { 'content': { 'text': 'Most companies are still in the training stage, but '
                             'as they develop models that graduate to large-scale '
                             'production, they’ll find that most of the cost is in '
                             'inference because models are trained periodically '
                             'whereas inferences are happening all the time as '
                             'their associated application is being exercised. We '
                             'launched our first inference chips (“Inferentia”) in '
                             '2019, and they have saved companies like Amazon over '
                             'a hundred million dollars in capital expense '
                             'already. Our Inferentia2 chip, which just launched, '
                             'offers up to four times higher throughput and ten '
                             'times lower latency than our first Inferentia '
                             'processor. With the enormous upcoming growth in '
                             'machine learning, customers will be able to get a '
                             'lot more done with AWS’s training and inference '
                             'chips at a significantly lower cost. We’re not close '
                             'to being done innovating here, and this long-term '
                             'investment should prove fruitful for both customers '
                             'and AWS. AWS is still in the early stages of its '
                             'evolution, and has a chance for unusual growth in '
                             'the next decade.   Similarly high potential, '
                             'Amazon’s Advertising business is uniquely effective '
                             'for brands, which is part of why it continues to '
                             'grow at a brisk clip. Akin to physical retailers’ '
                             'advertising businesses selling shelf space, end- '
                             'caps, and placement in their circulars, our '
                             'sponsored products and brands offerings have been an '
                             'integral part        of the Amazon shopping '
                             'experience for more than a decade. However, unlike '
                             'physical retailers, Amazon can tailor these '
                             'sponsored products to be relevant to what customers '
                             'are searching for given what we know about shopping '
                             'behaviors and our very deep investment in machine '
                             'learning algorithms. This leads to advertising '
                             'that’s more useful for customers; and as a result, '
                             'performs better for brands. This is part of why our '
                             'Advertising revenue has continued to grow rapidly '
                             '(23% YoY in Q4 2022, 25% YoY overall for 2022 on a '
                             '$31B revenue base), even as most large '
                             'advertising-focused businesses’ growth have slowed '
                             'over the last several quarters.'},
        'location': { 's3Location': { 'uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf'},
                      'type': 'S3'},
        'metadata': { 'x-amz-bedrock-kb-chunk-id': '1%3A0%3ABe7juJEBXwKXtPXx95ct',
                      'x-amz-bedrock-kb-data-source-id': 'MVXWUY4MBU',
                      'x-amz-bedrock-kb-source-uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf'},
        'score': 0.5324177}]


<h2>Next Steps</h2>

Proceed to the next labs to learn how to use Amazon Bedrock Knowledge Base with Open Source Libraries.

<h2>Clean Up</h2>


<div class="alert alert-block alert-warning">
In case you are done with your labs and the sample codes then remember to Clean Up the resources at the end of your session by following <a href="https://github.com/aws-samples/amazon-bedrock-samples/opensource-libraries/knowledge-base/3_clean_up.ipynb">3_clean_up.ipynb</a> 
</div>


```python

```
