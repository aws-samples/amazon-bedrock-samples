---
tags:
    - RAG/ Knowledge-Bases
    - RAG/ Metadata-Filtering
    - Agents/ Return of Control
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/02-optimizing-accuracy-retrieved-results/query_reformulation.ipynb){:target="_blank"}"

<h2>Query Reformulation Supported by Knowledge Bases on Amazon Bedrock</h2>

Optimizing quality, cost, and latency are some of the most important factors when developing RAG-based GenAI applications. Very often, input queries to an Foundation Model (FM) can be very complex with many questions and complex relationships. With such complex queries, the embedding step may mask or dilute important components of the query, resulting in retrieved chunks that may not provide context for all aspects of the query. This can produce a less than desirable response from your RAG application.

Now with query reformulation, we can take a complex input prompt and break it down into multiple sub-queries. These sub-queries will then separately go through their own retrieval steps for relevant chunks. The resulting chunks will then be pooled and ranked together before passing them to the FM to generate a response. Query reformulation is another tool we can use which can help increase accuracy for complex queries that your application may face in production.


<h2>Notebook setup</h2>
Follow the steps below with a compatible role and compute environment to get started


```python
%pip install --force-reinstall -q -r utils/requirements.txt
```


```python
<h2>restart kernel</h2>
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```


```python
%store -r kb_id
```


```python
import boto3
import botocore
import os
import json
import logging
import os

<h2>confirm we are at boto3 version 1.34.143 or above</h2>
print(boto3.__version__)
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


<h2>Pre-requisites</h2>

In this notebook, we will use a already created knowledge base using Octank Financial 10K document available [here](../synthetic_dataset) as a text corpus to perform Q&A on. 

So, before exploring this notebook further, make sure that you have created the Knowledge Bases for Amazon Bedrock and ingested your documents in this knowledge base.

for more details on how to create the Knowledge Base and ingest you documents, please refer this [notebook](../01-rag-concepts/01_create_ingest_documents_test_kb_multi_ds.ipynb)

Note the Knowledge Base ID




```python
<h2>kb_id = "<<knowledge_base_id>>" # Replace with your knowledge base id here.</h2>

<h2>Define FM to be used for generations </h2>
foundation_model ='anthropic.claude-3-sonnet-20240229-v1:0'  # we will be using Anthropic Claude 3 Sonnet throughout the notebook
```

<h2>Query Reformulation in Action</h2>

In this notebook, we will investigate a simple and a more complex query that could benefit from query reformulation and see how it affects the generated responses. 

<h2> Complex prompt</h2>

To demonstrate the functionality, lets take a look at a query that has a few asks being made about some information contained in the Octank 10K financial document. This query contains a few asks that are not semantically related. When this query is embedded during the retrieval step, some aspects of the query may become diluted and therefore the relevant chunks returned may not address all components of this complex query.

To query our Knowledge Base and generate a response we will use the __retrieve_and_generate__ API call. To use the query reformulation feature, we will include in our knowledge base configuration the additional information as shown below:

```
'orchestrationConfiguration': {
        'queryTransformationConfiguration': {
            'type': 'QUERY_DECOMPOSITION'
        }
    }
```

__Note:__ The output response structure is the same as a normal __retrieve_and_generate__ without query reformulation.

<h4>Without Query Reformulation</h4>

Let's see how the generated result looks like for the following query without using query reformulation: 

"Where is the Octank company waterfront building located and how does the whistleblower scandal hurt the company and its image?"


```python
query = "What is octank tower and how does the whistleblower scandal hurt the company and its image?"
```


```python
response_ret = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": query
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id,
            "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(region, foundation_model),
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5
                } 
            }
        }
    }
)


<h2>generated text output</h2>

print(response_ret['output']['text'],end='\n'*2)
```


```python
response_without_qr = response_ret['citations'][0]['retrievedReferences']
print("# of citations or chunks used to generate the response: ", len(response_without_qr))
def citations_rag_print(response_ret):
#structure 'retrievalResults': list of contents. Each list has content, location, score, metadata
    for num,chunk in enumerate(response_ret,1):
        print(f'Chunk {num}: ',chunk['content']['text'],end='\n'*2)
        print(f'Chunk {num} Location: ',chunk['location'],end='\n'*2)
        print(f'Chunk {num} Metadata: ',chunk['metadata'],end='\n'*2)

citations_rag_print(response_without_qr)
```

As seen from the above citations, our retrieval with the complex query did not return any chunks relevant to the building, instead focusing on embeddings that was most similar to the whistleblower incident. 

This may indicate the embedding of the query resulted in some dilution of the semantics of that part of the query.

<h4>With Query Reformulation</h4>

Now let's see how query reformulation can benefit the more aligned context retrieval, which in turn, will enhace the accuracy of response generation.


```python
response_ret = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": query
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id,
            "modelArn": "arn:aws:bedrock:{}::foundation-model/{}".format(region, foundation_model),
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5
                } 
            },
            'orchestrationConfiguration': {
                'queryTransformationConfiguration': {
                    'type': 'QUERY_DECOMPOSITION'
                }
            }
        }
    }
)


<h2>generated text output</h2>

print(response_ret['output']['text'],end='\n'*2)
```

Let's take a look at the retrieved chunks with query reformulation


```python
response_with_qr = response_ret['citations'][0]['retrievedReferences']
print("# of citations or chunks used to generate the response: ", len(response_with_qr))


citations_rag_print(response_with_qr)
```

We can see that with query reformulation turned on, the chunks that have been retrieved now provide context for the whistlblower scandal and the location of the waterfront property components.

<h3>Observing prompt decomposition using CloudWatch Logs</h3>

Before performing retrieval, the complex query is broken down into multiple subqueries. This can be seen for the above example query when we isolate the invocation for the decomposition action where our __standalone_question__ is our original query and the resulting subqueries are shown between __\<query\>__ tags

__Note__: You must enable invocation logging in Bedrock for the logs to be viewed in CloudWatch. Please refer [here](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) for details.


```
<generated_queries>

<standalone_question>
What is octank tower and how does the whistleblower scandal hurt the company and its image?
</standalone_question>

<query>
What is octank tower?
</query>

<query>
What is the whistleblower scandal involving Octank company?
</query>

<query>
How did the whistleblower scandal affect Octank company's reputation and public image?
</query>

</generated_queries>
```


<div class="alert alert-block alert-warning">
<b>Note:</b> Remember to delete KB, OSS index and related IAM roles and policies to avoid incurring any charges.
</div>

Now that we have seen how query reformulation works and how it can improve responses to complex queries, we invite you to dive deeper and experiment with this technique to optimize your RAG worflow. 
