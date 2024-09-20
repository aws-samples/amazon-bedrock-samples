<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>


<h2>How to create index and ingest documents in Amazon Bedrock Knowledge Base</h2>


!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/rag/open-source/amazon-bedrock-knowledge-base/0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb){:target="_blank"}"


<h2>Overview</h2>

This notebook provides sample code for building an empty OpenSearch Serverless (OSS) index in Amazon Bedrock Knowledge Base and then ingest documents into it.


In this notebook we create a data pipeline that ingests documents (typically stored in Amazon S3) into a knowledge base i.e. a vector database such as Amazon OpenSearch Service Serverless (AOSS) so that it is available for lookup when a question is received.

<ul>
<li>Load the documents into the knowledge base by connecting your s3 bucket (data source). </li>
<li>Ingestion - Knowledge base will split them into smaller chunks (based on the strategy selected), generate embeddings and store it in the associated vectore store.</li>
</ul>


![Data Ingestion in Index of Knowledge Base](./assets/images/data_ingestion.png){align=center}


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


!!! info "Note"

    This notebook has been tested in 
    **Mumbai (ap-south-1)** in **Python 3.10.14**


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


!!! info "Note"

    Please make sure to enable `Cohere Embed Multilingual`, `Anthropic Claude 3 Sonnet`  and `Anthropic Claude 3 Haiku` model access in Amazon Bedrock Console, as the notebook will use `Cohere Embed Multilingual` for creating the embeddings & `Anthropic Claude 3 Sonnet` and `Claude 3 Haiku` models for testing the knowledge base once its created.


Next we install the required python libraries.


```python
%pip install -U opensearch-py==2.7.1
%pip install -U boto3==1.34.162
%pip install -U retrying==1.3.4
```

<h2>Setup</h2>

Before running the rest of this notebook, you'll need to run the cell below to restart the kernel. If it does not work please manually restar the kernel. 


```python
# restart kernel
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```

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


```python
%store bucket_name
```

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


```python
%store encryption_policy network_policy access_policy collection
```


```python
# Get the OpenSearch serverless collection URL
collection_id = collection['createCollectionDetail']['id']
host = collection_id + '.' + region_name + '.aoss.amazonaws.com'
print(host)
```


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


```python
# Get DataSource 
bedrock_agent_client.get_data_source(knowledgeBaseId = kb['knowledgeBaseId'], dataSourceId = ds["dataSourceId"])
```

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


```python
# Print the knowledge base Id in bedrock, that corresponds to the Opensearch index in the collection we created before, we will use it for the invocation later
kb_id = kb["knowledgeBaseId"]
pp.pprint(kb_id)
```


```python
# keep the kb_id for invocation later in the invoke request
%store kb_id
```

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

<h2>Next Steps</h2>

Proceed to the next labs to learn how to use Amazon Bedrock Knowledge Base with Open Source Libraries.

<h2>Clean Up</h2>


!!! warning "Deleting Resources to avoid incurring cost"

    In case you are done with your labs and the sample codes then remember to Clean Up the resources at the end of your session by following [3_clean_up.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/rag/open-source/amazon-bedrock-knowledge-base/3_clean_up.ipynb)