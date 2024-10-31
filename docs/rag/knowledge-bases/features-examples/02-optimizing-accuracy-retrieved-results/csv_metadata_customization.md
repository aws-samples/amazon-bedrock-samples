---
tags:
    - RAG/ Metadata-Filtering
    - RAG/ Data-Ingestion
    - RAG/ Knowledge-Bases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/02-optimizing-accuracy-retrieved-results/csv_metadata_customization.ipynb){:target="_blank"}"

<h2>CSV metadata customization walkthrough</h2>
This notebook provides sample code walkthrough for 'CSV metadata customization' feature, a newly realsed feautre for Knowledge bases for Amazon Bedrock.

For more details on this feature, please read this [blog](https://aws.amazon.com/blogs/machine-learning/knowledge-bases-for-amazon-bedrock-now-supports-advanced-parsing-chunking-and-query-reformulation-giving-greater-control-of-accuracy-in-rag-based-applications/#:~:text=Machine%20Learning%20Blog-,Knowledge%20Bases%20for%20Amazon%20Bedrock%20now%20supports%20advanced%20parsing%2C%20chunking,accuracy%20in%20RAG%20based%20applications).

<h2>1. Import the needed libraries</h2>
First step is to install the pre-requisites packages.


```python
%pip install --force-reinstall -q -r utils/requirements.txt
```


```python
<h2>restart kernel</h2>
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```


```python
import botocore
botocore.__version__
```


```python
import os
import time
import boto3
import logging
import pprint
import json

from utils.knowledge_base import BedrockKnowledgeBase
```


```python
#Clients
s3_client = boto3.client('s3')
sts_client = boto3.client('sts')
session = boto3.session.Session()
region =  session.region_name
account_id = sts_client.get_caller_identity()["Account"]
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime') 
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
region, account_id
```


```python
import time

<h2>Get the current timestamp</h2>
current_time = time.time()

<h2>Format the timestamp as a string</h2>
timestamp_str = time.strftime("%Y%m%d%H%M%S", time.localtime(current_time))[-7:]
<h2>Create the suffix using the timestamp</h2>
suffix = f"{timestamp_str}"
knowledge_base_name_standard = 'csv-metadata-kb'
knowledge_base_name_hierarchical = 'hierarchical-kb'
knowledge_base_description = "Knowledge Base csv metadata customization."
bucket_name = f'{knowledge_base_name_standard}-{suffix}'
foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"
```

<h2>2 - Create knowledge bases with fixed chunking strategy</h2>
Let's start by creating a [Knowledge Base for Amazon Bedrock](https://aws.amazon.com/bedrock/knowledge-bases/) to store video games data in csv format. Knowledge Bases allow you to integrate with different vector databases including [Amazon OpenSearch Serverless](https://aws.amazon.com/opensearch-service/features/serverless/), [Amazon Aurora](https://aws.amazon.com/rds/aurora/), [Pinecone](http://app.pinecone.io/bedrock-integration), [Redis Enterprise]() and [MongoDB Atlas](). For this example, we will integrate the knowledge base with Amazon OpenSearch Serverless. To do so, we will use the helper class `BedrockKnowledgeBase` which will create the knowledge base and all of its pre-requisites:
1. IAM roles and policies
2. S3 bucket
3. Amazon OpenSearch Serverless encryption, network and data access policies
4. Amazon OpenSearch Serverless collection
5. Amazon OpenSearch Serverless vector index
6. Knowledge base
7. Knowledge base data source

We will create a knowledge base using fixed chunking strategy. 

You can chhose different chunking strategies by changing the below parameter values: 
```
"chunkingStrategy": "FIXED_SIZE | NONE | HIERARCHICAL | SEMANTIC"
```


```python
knowledge_base_standard = BedrockKnowledgeBase(
    kb_name=f'{knowledge_base_name_standard}-{suffix}',
    kb_description=knowledge_base_description,
    data_bucket_name=bucket_name, 
    chunking_strategy = "FIXED_SIZE", 
    suffix = suffix
)
```

<h3>2.1 Download csv dataset and upload it to Amazon S3</h3>
Now that we have created the knowledge base, let's populate it with the `video_games.csv` dataset to KB. This data is being downloaded from [here](https://github.com/ali-ce/datasets/blob/master/Most-Expensive-Things/Videogames.csv). It contains the sales data of video games originally collected by Alice Corona is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://github.com/ali-ce/datasets/blob/master/README.md#:~:text=Creative%20Commons%20Attribution%2DShareAlike%204.0%20International%20License.).


The Knowledge Base data source expects the data to be available on the S3 bucket connected to it and changes on the data can be syncronized to the knowledge base using the `StartIngestionJob` API call. In this example we will use the [boto3 abstraction](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent/client/start_ingestion_job.html) of the API, via our helper classes. 


```python
!mkdir -p ./csv_data
```


```python
!wget https://raw.githubusercontent.com/ali-ce/datasets/master/Most-Expensive-Things/Videogames.csv -O ./csv_data/video_games.csv
```

Let's upload the video games data available on the `csv_data` folder to s3.


```python
def upload_directory(path, bucket_name):
        for root,dirs,files in os.walk(path):
            for file in files:
                file_to_upload = os.path.join(root,file)
                print(f"uploading file {file_to_upload} to {bucket_name}")
                s3_client.upload_file(file_to_upload,bucket_name,file)

upload_directory("csv_data", bucket_name)
```

Now we start the ingestion job.


```python
<h2>ensure that the kb is available</h2>
time.sleep(30)
<h2>sync knowledge base</h2>
knowledge_base_standard.start_ingestion_job()
```

Finally we save the Knowledge Base Id to test the solution at a later stage. 


```python
kb_id_standard = knowledge_base_standard.get_knowledge_base_id()
```

<h3>2.2 Query the Knowledge Base with Retrieve and Generate API - without metadata</h3>

Let's test the knowledge base using the [**retrieve_and_generate**](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime/client/retrieve_and_generate.html) API. With this API, Bedrock takes care of retrieving the necessary references from the knowledge base and generating the final answer using a foundation model from Bedrock.

'''
query = "List the video games published by Rockstar Games and released after 2010"
'''

Expected Results: Grand Theft Auto V, L.A. Noire, Max Payne 3



```python

```


```python
query = "Provide a list of all video games published by Rockstar Games and released after 2010"
```


```python
response = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": query
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id_standard,
            "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(region, foundation_model),
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5
                } 
            }
        }
    }
)

pprint.pp(response['output']['text'])
```

<h4>2.3 Prepeare metadata for ingestion</h4>



```python
import csv
import json
```


```python
def generate_json_metadata(csv_file, content_field, metadata_fields, excluded_fields):
    # Open the CSV file and read its contents
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames

    # Create the JSON structure
    json_data = {
        "metadataAttributes": {},
        "documentStructureConfiguration": {
            "type": "RECORD_BASED_STRUCTURE_METADATA",
            "recordBasedStructureMetadata": {
                "contentFields": [
                    {
                        "fieldName": content_field
                    }
                ],
                "metadataFieldsSpecification": {
                    "fieldsToInclude": [],
                    "fieldsToExclude": []
                }
            }
        }
    }

    # Add metadata fields to include
    for field in metadata_fields:
        json_data["documentStructureConfiguration"]["recordBasedStructureMetadata"]["metadataFieldsSpecification"]["fieldsToInclude"].append(
            {
                "fieldName": field
            }
        )

    # Add fields to exclude (all fields not in content_field or metadata_fields)
    if not excluded_fields:
        excluded_fields = set(headers) - set([content_field] + metadata_fields)
    
    for field in excluded_fields:
        json_data["documentStructureConfiguration"]["recordBasedStructureMetadata"]["metadataFieldsSpecification"]["fieldsToExclude"].append(
            {
                "fieldName": field
            }
        )

    # Generate the output JSON file name
    output_file = f"{csv_file.split('.')[0]}.csv.metadata.json"

    # Write the JSON data to the output file
    with open(output_file, 'w') as file:
        json.dump(json_data, file, indent=4)

    print(f"JSON metadata file '{output_file}' has been generated.")
```


```python
csv_file = 'csv_data/video_games.csv'
content_field = 'Videogame'
metadata_fields = ['Year', 'Developer', 'Publisher']
excluded_fields =['Description']

generate_json_metadata(csv_file, content_field, metadata_fields, excluded_fields)
```


```python
<h2>upload metadata file to S3</h2>
upload_directory("csv_data", bucket_name)

<h2>delete metadata file from local</h2>
os.remove('csv_data/video_games.csv.metadata.json')
```

Now start the ingestion job. Since, we are using the same documents as used for fixed chunking, we are skipping the step to upload documents to s3 bucket. 


```python
<h2>ensure that the kb is available</h2>
time.sleep(30)
<h2>sync knowledge base</h2>
knowledge_base_standard.start_ingestion_job()
```

<h3>2.4 Query the Knowledge Base with Retrieve and Generate API - without metadata</h3>

create the filter 


```python
one_group_filter= {
    "andAll": [
        {
            "equals": {
                "key": "Publisher",
                "value": "Rockstar Games"
            }
        },
        {
            "greaterThan": {
                "key": "Year",
                "value": 2010
            }
        }
    ]
}
```

Pass the filter to `retrievalConfiguration` of the [**retrieve_and_generate**](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime/client/retrieve_and_generate.html).


```python
response = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": query
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id_standard,
            "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(region, foundation_model),
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5,
                    "filter": one_group_filter
                } 
            }
        }
    }
)

print(response['output']['text'])
```

As you can see, with the retrieve and generate API we get the final response directly, now let's observe the citations for `RetreiveAndGenerate` API. Also, let's  observe the retrieved chunks and citations returned by the model while generating the response. When we provide the relevant context to the foundation model alongwith the query, it will most likely generate the high quality response. 


```python
response_standard = response['citations'][0]['retrievedReferences']
print("# of citations or chunks used to generate the response: ", len(response_standard))
def citations_rag_print(response_ret):
#structure 'retrievalResults': list of contents. Each list has content, location, score, metadata
    for num,chunk in enumerate(response_ret,1):
        print(f'Chunk {num}: ',chunk['content']['text'],end='\n'*2)
        print(f'Chunk {num} Location: ',chunk['location'],end='\n'*2)
        print(f'Chunk {num} Metadata: ',chunk['metadata'],end='\n'*2)

citations_rag_print(response_standard)
```


```python
%store kb_id_standard
```

<h3>Clean up</h3>
Please make sure to uncomment and run below cells to delete the resources created in this notebook. If you are planning to run `dynamic-metadata-filtering` notebook under `03-advanced-concepts` section, then make sure to come back here to delete the resources. 


```python
<h2># Empty and delete S3 Bucket</h2>

objects = s3_client.list_objects(Bucket=bucket_name)
if 'Contents' in objects:
    for obj in objects['Contents']:
        s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
s3_client.delete_bucket(Bucket=bucket_name)
```


```python
print("===============================Knowledge base==============================")
knowledge_base_standard.delete_kb(delete_s3_bucket=True, delete_iam_roles_and_policies=True)
```
