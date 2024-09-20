<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>


<h2>Building Q&A Application with LlamaIndex and Amazon Bedrock Knowledge Base</h2>

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/rag/open-source/amazon-bedrock-knowledge-base/2_how_to_use_knowledge_base_with_llamaindex.ipynb){:target="_blank"}"


<h2>Overview</h2>

In this notebook we will leverage Amazon Bedrock Knowledge Base that we created in [0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/rag/open-source/amazon-bedrock-knowledge-base/0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb) and use it with LlamaIndex to create a Q&A Application.


<h2>Context</h2>

Implementing RAG requires organizations to perform several cumbersome steps to convert data into embeddings (vectors), store the embeddings in a specialized vector database, and build custom integrations into the database to search and retrieve text relevant to the user’s query. This can be time-consuming and inefficient.

With Knowledge Bases for Amazon Bedrock, simply point to the location of your data in Amazon S3, and Knowledge Bases for Amazon Bedrock takes care of the entire ingestion workflow into your vector database. If you do not have an existing vector database, Amazon Bedrock creates an Amazon OpenSearch Serverless vector store for you. For retrievals, use the LLamaIndex - Amazon Bedrock integration via the Retrieve API to retrieve relevant results for a user query from knowledge bases.

In this notebook, we will dive deep into building Q&A application. We will query the knowledge base to get the desired number of document chunks based on similarity search, integrate it with LlamaIndex retriever and use Anthropic Claude 3 Haiku model from Amazon Bedrock for answering questions.

Following is the Architecture Diagram of the orchestration done by LlamaIndex by leveraging Large Language Model and Knowledge Base from Amazon Bedrock


![Custom RAG Workflow](./assets/images/retrieveAPI.png){align=center}


<h2>Prerequisites</h2>

Before being able to answer the questions, the documents must be processed and ingested in vector database as shown on [0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/rag/open-source/amazon-bedrock-knowledge-base/0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb). We will making use of the Knowledge Base ID that we stored in this notebook.

In case you are wanting to create the Knowledge Base from Console then you can follow the [official documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html).

<h3>Dataset</h3>

In this example, you will use several years of Amazon's Letter to Shareholders as a text corpus to perform Q&A on. This data is already ingested into the Knowledge Bases for Amazon Bedrock. You will need the `knowledge_base_id` to run this example. In your specific use case, you can sync different files for different domain topics and query this notebook in the same manner to evaluate model responses using the retrieve API from knowledge bases.


!!! info "Note"

    This notebook has been tested in 
    **Mumbai (ap-south-1)** in **Python 3.10.14**


<h2>Setup</h2>

To run this notebook you would need to install following packages.


```python
!pip install --upgrade boto3==1.34.162 botocore==1.34.162
!pip install --upgrade llama-index==0.10.30 llama-index-retrievers-bedrock==0.1.1 llama-index-llms-bedrock==0.1.6
```

<strong>Restart the kernel with the updated packages that are installed through the dependencies above</strong>


```python
# restart kernel
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```


!!! info "Note"

    If the following cell execution gives you error then please manually restart the kernel, the error will go away.


<h3>Imports</h3>

<b>Follow the steps below to initilize the required python modules</b>

<ol>
<li>Import necessary libraries and initialize bedrock client required by the Langchain module to communicate with Foundation Models (FM) or Large Language Models (LLM) available in Amazon Bedrock.</li>
<li>Import and Initialize Knoweledge Base Retriver available in LlamaIndex to communicate with Knowledge Base from Amazon Bedrock</li>
</ol>


```python
import boto3
import pprint
from botocore.client import Config
import json

import llama_index
from llama_index.core import get_response_synthesizer
from llama_index.llms.bedrock.base import Bedrock
from llama_index.retrievers.bedrock import AmazonKnowledgeBasesRetriever
from llama_index.core import PromptTemplate
```


```python
%store -r
```


```python
pp = pprint.PrettyPrinter(indent=2)
session = boto3.session.Session()
region = session.region_name   # use can you the region of your choice.
botocore_config = Config(
    connect_timeout=120, read_timeout=120, retries={'max_attempts': 0}
)
# bedrock_client = boto3.client('bedrock-runtime', region_name=region)

llm = Bedrock(
    region_name=region,
    botocore_config= botocore_config,
    model="anthropic.claude-3-haiku-20240307-v1:0", # Model ID of the LLM of our choice from Amazon Bedrock
    temperature=0, 
    max_tokens=3000
)

retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=kb_id, # we are using the id of the knowledge base that we created in earlier notebook
    retrieval_config={
        "vectorSearchConfiguration": {
            "numberOfResults": 3,
            "overrideSearchType": "HYBRID",
            # "filter": {"equals": {"key": "tag", "value": "space"}}, # Optional Field for for metadata filtering.
        }
    },
)
```

Above we initialized the following two objects from Langchain:
<ol>
<li><strong>ChatBedrock</strong> - This object will orchestrates the communication with  the LLM from Amazon Bedrock. It will take care of structuring the prompt/messages, model arguments, etc for us whenever it invokes the LLM.</li>
<li><strong>AmazonKnowledgeBasesRetriever</strong> - This objects will calls APIs of Knowledge Bases for Amazon Bedrock which converts user queries into embeddings, searches the knowledge base, and returns the relevant results, giving you more control to build custom workﬂows on top of the semantic search results.</li>
</ol>

<h3>Usage</h3>

Below is the method to directly fetch the relevant documents usign the `AmazonKnowledgeBasesRetriever` object.


```python
query = "By what percentage did AWS revenue grow year-over-year in 2021?"

response = retriever.retrieve(query)

pp.pprint(response)
```

<h2>Code</h2>

<h3>Using Knowledge Base within a LlamaIndex Based RAG architecture</h3>

<h4>Prompt specific to the model to personalize responses</h4>

Here, we will use the specific prompt below for the model to act as a financial advisor AI system that will provide answers to questions by using fact based and statistical information when possible. We will provide the Retrieve API responses from above as a part of the {context} in the prompt for the model to refer to, along with the user query.


```python
query = "By what percentage did AWS revenue grow year-over-year in 2021?"

PROMPT_TEMPLATE = """
Human: You are a financial advisor AI system, and provides answers to questions by using fact based and statistical information when possible. 
Use the following pieces of information to provide a concise answer to the question enclosed in <question> tags. 
If you don't know the answer, just say that you don't know, don't try to make up an answer.
<context>
{context}
</context>

<question>
{question}
</question>

The response should be specific and use statistics or numbers when possible.

Assistant:"""

qa_template = PromptTemplate(
    template=PROMPT_TEMPLATE, 
    template_var_mappings={"query_str": "question", "context_str": "context"}
)

response_synthesizer = get_response_synthesizer(
    response_mode="compact", llm=llm
)

response_synthesizer.update_prompts(
    {"text_qa_template": qa_template}
)
retrieved_results = retriever.retrieve(query)

response = response_synthesizer.synthesize(query, retrieved_results)
pp.pprint(response)
```

<h2>Conclusion</h2>

We saw how easy it is to use Amazon Bedrock with LlamaIndex. Specifically we saw how LLM models form Amazon Bedrock and Knowledge base from Amazon Bedrock can be used by LlamaIndex to orchestrate the Q&A capability. 

<h2>Next Steps</h2>

Cleaning up the resources that we created.


<h2>Clean Up</h2>

!!! warning "Deleting Resources to avoid incurring cost"

    In case you are done with your labs and the sample codes then remember to Clean Up the resources at the end of your session by following [3_clean_up.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/rag/open-source/amazon-bedrock-knowledge-base/3_clean_up.ipynb)