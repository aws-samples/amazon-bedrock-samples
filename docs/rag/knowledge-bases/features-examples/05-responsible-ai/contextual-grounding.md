---
tags:
    - RAG/ Knowledge-Bases
    - Responsible-AI/ Guardrails
    - Vector-DB/ OpenSearch
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/05-responsible-ai/contextual-grounding.ipynb){:target="_blank"}"

<h2>Combining Guardrails Contextual Grounding and Knowledge Bases</h2>
This notebook demonstrates how to combine Guardrails for Amazon Bedrock contextual grounding filter with the Knowledge Bases for Amazon Bedrock. By doing so, we can ensure that the model's responses are factually grounded and aligned with the information stored in the Knowledge Base.

In the notebook we will be using the [D&D Systems Reference Document (SRD)](https://www.dndbeyond.com/resources/1781-systems-reference-document-srd)(CC-BY-4.0) to store it into the Knowledge Base.  

What we are going to create in this notebook:
1. **Import libraries:** We will load the needed libraries to make the notebook work correctly. 
2. **Create Knowledge Base:** We are going to store the D&D Systems Reference Document in a managed knowledge base in Amazon Bedrock. 
3. **Configure Guardrail:** We are going to configure our guardrail with the contextual grounding filter thresholds.
4. **Test the contextual grounding:** We are going to retrieve context from the KB and pass it to a LLM with a query and evaluate hallucinations. 
5. **Delete resources:** To save in costs, we are going to delete all the resources created. 

<div class="alert alert-block alert-info">
<b>Note:</b> Please make sure to enable `Anthropic Claude 3 Sonnet`and `Titan Embedding Text V2`  model access in Amazon Bedrock Console, as the notebook will use these models.
</div>

<h2>1. Import libraries</h2>


```python
%pip install --force-reinstall -q -r ../requirements.txt
```


```python
import os
import time
import uuid
import boto3
import json
import requests
from knowledge_base import BedrockKnowledgeBase
from utils import print_results,print_results_with_guardrail
session = boto3.session.Session()
region = session.region_name
unique_id = str(uuid.uuid4())[:4]
s3_client = boto3.client("s3",region_name=region)
bedrock = boto3.client("bedrock",region_name=region)
bedrock_runtime = boto3.client("bedrock-runtime",region_name=region)
bedrock_agent_client = boto3.client("bedrock-agent",region_name=region)
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime",region_name=region)
```

<h2>2. Create Knowledge Base for Amazon Bedrock</h2>

<h3>2.1 Download the dataset</h3>


```python
url = "https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf"
file_name = "kb_documents/SRD_CC_v5.1.pdf"
os.makedirs("kb_documents", exist_ok=True)
response = requests.get(url)
with open(file_name, "wb") as file:
    file.write(response.content)
print(f"File '{file_name}' has been downloaded.")
```

<h3>2.1 Creating Knowledge Base for Amazon Bedrock</h3>

We will now going to create a Knowledge Base for Amazon Bedrock and its requirements including:
- [Amazon OpenSearch Serverless](https://aws.amazon.com/opensearch-service/features/serverless/) for the vector database
- [AWS IAM](https://aws.amazon.com/iam/) roles and permissions
- [Amazon S3](https://aws.amazon.com/s3/) bucket to store the knowledge base documents

To create the knowledge base and its dependencies, we will use the `BedrockKnowledgeBase` support class, available in this folder. It allows you to create a new knowledge base, ingest documents to the knowledge base data source and delete the resources after you are done working with this lab


```python
knowledge_base_name = "{}-cgdemo".format(unique_id)
knowledge_base_description = "Knowledge Base containing d&d Guide"
bucket_name = "{}-cgdemo-bucket".format(unique_id)
```


```python
knowledge_base = BedrockKnowledgeBase(
    kb_name=knowledge_base_name,
    kb_description=knowledge_base_description,
    data_bucket_name=bucket_name,
    chunking_strategy = "FIXED_SIZE", 
    suffix = f'{unique_id}-f'
)
```

We now upload the knowledge base documents to S3


```python
def upload_directory(path, bucket_name):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".pdf"):
                file_to_upload = os.path.join(root, file)
                print(f"uploading file {file_to_upload} to {bucket_name}")
                s3_client.upload_file(file_to_upload, bucket_name, file)

upload_directory("kb_documents", bucket_name)
```

And ingest the documents to the knowledge base


```python
<h2>ensure that the kb is available</h2>
time.sleep(30)
<h2>sync knowledge base</h2>
knowledge_base.start_ingestion_job()
```


```python
kb_id = knowledge_base.get_knowledge_base_id()
```

<h3>2.2 Testing Knowledge Base</h3>
Let's now test that the created knowledge base works as expected. To do so, we first retrieve the knowledge base id. 

Next we can use the [`RetrieveAndGenerate`](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime/client/retrieve_and_generate.html) 
API from boto3 to retrieve the context for the question from the knowledge base and generate the final response


```python
model_id="anthropic.claude-3-sonnet-20240229-v1:0"
response = bedrock_agent_runtime_client.retrieve_and_generate(
    input={
        "text": "What should I know about elves?"
    },
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            'knowledgeBaseId': kb_id,
            "modelArn": model_id,
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                    "numberOfResults":5
                } 
            }
        }
    }
)

print(response['output']['text'],end='\n'*2)
```

<h2>3. Configure Guardrail for Amazon Bedrock</h2>

Now we have the Knowledge Base created, configured and synced with our documents, let's go and create our Guardrail for Amazon Bedrock. 

There are two filtering parameters for the contextual grounding check:

- **Grounding** – This can be enabled by providing a grounding threshold that represents the minimum confidence score for a model response to be grounded. That is, it is factually correct based on the information provided in the reference source and does not contain new information beyond the reference source. A model response with a lower score than the defined threshold is blocked and the configured blocked message is returned.

- **Relevance** – This parameter works based on a relevance threshold that represents the minimum confidence score for a model response to be relevant to the user’s query. Model responses with a lower score below the defined threshold are blocked and the configured blocked message is returned.

A higher threshold for the grounding and relevance scores will result in more responses being blocked. Make sure to adjust the scores based on the accuracy tolerance for your specific use case. For example, a customer-facing application in the finance domain may need a high threshold due to lower tolerance for inaccurate content.


```python
response = bedrock.create_guardrail(
    name="contextual-grounding-guardrail-{}".format(unique_id),
    description="D&D Guardrail",
    contextualGroundingPolicyConfig={
        'filtersConfig': [
            {
                'type': 'GROUNDING',
                'threshold': 0.5
            },
            {
                'type': 'RELEVANCE',
                'threshold': 0.8
            },
        ]
    },
    blockedInputMessaging="Sorry, I can not respond to this.",
    blockedOutputsMessaging="Sorry, I can not respond to this.",
)
guardrailId = response["guardrailId"]
print("The guardrail id is",response["guardrailId"])
```

<h2>4. Test the contextual grounding capability</h2>
Now we have set up the Knowledge Base and Guardrail let's test them together.

In this section we will first retrieve the KB results and then pass it on to the Converse API which has the Guardrail integrated.


```python
def invoke_kb(kb_query):
    kb_response = bedrock_agent_runtime_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 2,
            }
        },
        retrievalQuery={
            'text': kb_query
        }
    )
    model_id="anthropic.claude-3-sonnet-20240229-v1:0"
 
    inference_config = {"temperature": 0.1}

    # The message for the model and the content that you want the guardrail to assess.
    messages = [
        {
            "role": "user",
            "content": [
                {"text": str(kb_response)},
                {"text": kb_query}
            ]
        }
    ]
    response = bedrock_runtime.converse(modelId=model_id,messages=messages, inferenceConfig=inference_config)
    print("""
    ================================
    Invoke KB without Guardrails
    ================================
    """)
    print_results(kb_response, response)


def invoke_kb_with_guardrail(kb_query):
    kb_response = bedrock_agent_runtime_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 2,
            }
        },
        retrievalQuery={
            'text': kb_query
        }
    )
    model_id="anthropic.claude-3-sonnet-20240229-v1:0"
    inference_config = {"temperature": 0.1}
    guardrail_config = {
        "guardrailIdentifier": guardrailId,
        "guardrailVersion": "DRAFT",
        "trace": "enabled"
    }

    # The message for the model and the content that you want the guardrail to assess.
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "guardContent": {
                        "text": {
                            "text": str(kb_response),
                            "qualifiers": ["grounding_source"],
                        }
                    }
                },
                {
                    "guardContent": {
                        "text": {
                            "text": kb_query,
                            "qualifiers": ["query"],
                        }
                    }
                },
            ],
        }
    ]
    response = bedrock_runtime.converse(modelId=model_id,messages=messages,guardrailConfig=guardrail_config, inferenceConfig=inference_config,)
    print("""
    ================================
    Invoke KB with Guardrails
    ================================
    """)
    print_results_with_guardrail(kb_response, response)

```


```python
kb_query = "What are High Elves?"
invoke_kb(kb_query)
invoke_kb_with_guardrail(kb_query)
```


```python
kb_query = "Where should the elves go if they arrive in Paris?"
invoke_kb(kb_query)
invoke_kb_with_guardrail(kb_query)
```

<h2>5. Delete resources</h2>
Let's delete all the resources to avoid unnecessary costs. 


```python
<h2>Delete the Knowledge Base</h2>
knowledge_base.delete_kb(delete_s3_bucket=True, delete_iam_roles_and_policies=True)
<h2>Delete the Guardrail</h2>
bedrock.delete_guardrail(guardrailIdentifier = guardrailId)
```
