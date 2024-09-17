<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>


<h2>Building Q&A Application with Langchain and Amazon Bedrock Knowledge Base</h2>

<a href="https://github.com/aws-samples/amazon-bedrock-samples/opensource-libraries/knowledge-base/1_how_to_use_knowledge_base_with_langchain.ipynb">Open in Github</a>


<h2>Overview</h2>

In this notebook we will leverage Amazon Bedrock Knowledge Base that we created in <a href="https://github.com/aws-samples/amazon-bedrock-samples/opensource-libraries/knowledge-base/0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb">0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb</a> and use it with LangChain to create a Q&A Application.

<h2>Context</h2>

Implementing RAG requires organizations to perform several cumbersome steps to convert data into embeddings (vectors), store the embeddings in a specialized vector database, and build custom integrations into the database to search and retrieve text relevant to the user’s query. This can be time-consuming and inefficient.

With Knowledge Bases for Amazon Bedrock, simply point to the location of your data in Amazon S3, and Knowledge Bases for Amazon Bedrock takes care of the entire ingestion workflow into your vector database. If you do not have an existing vector database, Amazon Bedrock creates an Amazon OpenSearch Serverless vector store for you. For retrievals, use the Langchain - Amazon Bedrock integration via the Retrieve API to retrieve relevant results for a user query from knowledge bases.

In this notebook, we will dive deep into building Q&A application. We will query the knowledge base to get the desired number of document chunks based on similarity search, integrate it with LangChain retriever and use Anthropic Claude 3 Haiku model from Amazon Bedrock for answering questions.

Following is the Architecture Diagram of the orchestration done by Langchain by leveraging Large Language Model and Knowledge Base from Amazon Bedrock

<img src="./assets/images/retrieveAPI.png" alt="Custom RAG Workflow" style="margin:auto">

<h2>Prerequisites</h2>

Before being able to answer the questions, the documents must be processed and ingested in vector database as shown on [0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb](./0\_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb). We will making use of the Knowledge Base ID that we stored in this notebook.

In case you are wanting to create the Knowledge Base from Console then you can follow the [official documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html).

<h3>Dataset</h3>

In this example, you will use several years of Amazon's Letter to Shareholders as a text corpus to perform Q&A on. This data is already ingested into the Knowledge Bases for Amazon Bedrock. You will need the `knowledge_base_id` to run this example. In your specific use case, you can sync different files for different domain topics and query this notebook in the same manner to evaluate model responses using the retrieve API from knowledge bases.


<div class="alert alert-block alert-info">
<b>Note:</b> This notebook has been tested in <strong>Mumbai (ap-south-1)</strong> in <strong>Python 3.10.14</strong>
</div>

<h2>Setup</h2>

To run this notebook you would need to install following packages.


```python
!pip install -U boto3==1.34.162
!pip install -U langchain-aws==0.1.17
!pip install -U langchain-community==0.2.11
!pip install -U langchain==0.2.15
```

    Requirement already satisfied: boto3==1.34.162 in /opt/conda/lib/python3.10/site-packages (1.34.162)
    Requirement already satisfied: botocore<1.35.0,>=1.34.162 in /opt/conda/lib/python3.10/site-packages (from boto3==1.34.162) (1.34.162)
    Requirement already satisfied: jmespath<2.0.0,>=0.7.1 in /opt/conda/lib/python3.10/site-packages (from boto3==1.34.162) (1.0.1)
    Requirement already satisfied: s3transfer<0.11.0,>=0.10.0 in /opt/conda/lib/python3.10/site-packages (from boto3==1.34.162) (0.10.2)
    Requirement already satisfied: python-dateutil<3.0.0,>=2.1 in /opt/conda/lib/python3.10/site-packages (from botocore<1.35.0,>=1.34.162->boto3==1.34.162) (2.9.0)
    Requirement already satisfied: urllib3!=2.2.0,<3,>=1.25.4 in /opt/conda/lib/python3.10/site-packages (from botocore<1.35.0,>=1.34.162->boto3==1.34.162) (1.26.19)
    Requirement already satisfied: six>=1.5 in /opt/conda/lib/python3.10/site-packages (from python-dateutil<3.0.0,>=2.1->botocore<1.35.0,>=1.34.162->boto3==1.34.162) (1.16.0)
    Requirement already satisfied: langchain-aws==0.1.17 in /opt/conda/lib/python3.10/site-packages (0.1.17)
    Requirement already satisfied: boto3<1.35.0,>=1.34.131 in /opt/conda/lib/python3.10/site-packages (from langchain-aws==0.1.17) (1.34.162)
    Requirement already satisfied: langchain-core<0.3,>=0.2.33 in /opt/conda/lib/python3.10/site-packages (from langchain-aws==0.1.17) (0.2.37)
    Requirement already satisfied: numpy<2,>=1 in /opt/conda/lib/python3.10/site-packages (from langchain-aws==0.1.17) (1.26.4)
    Requirement already satisfied: botocore<1.35.0,>=1.34.162 in /opt/conda/lib/python3.10/site-packages (from boto3<1.35.0,>=1.34.131->langchain-aws==0.1.17) (1.34.162)
    Requirement already satisfied: jmespath<2.0.0,>=0.7.1 in /opt/conda/lib/python3.10/site-packages (from boto3<1.35.0,>=1.34.131->langchain-aws==0.1.17) (1.0.1)
    Requirement already satisfied: s3transfer<0.11.0,>=0.10.0 in /opt/conda/lib/python3.10/site-packages (from boto3<1.35.0,>=1.34.131->langchain-aws==0.1.17) (0.10.2)
    Requirement already satisfied: PyYAML>=5.3 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (6.0.1)
    Requirement already satisfied: jsonpatch<2.0,>=1.33 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (1.33)
    Requirement already satisfied: langsmith<0.2.0,>=0.1.75 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (0.1.98)
    Requirement already satisfied: packaging<25,>=23.2 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (24.1)
    Requirement already satisfied: pydantic<3,>=1 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (1.10.17)
    Requirement already satisfied: tenacity!=8.4.0,<9.0.0,>=8.1.0 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (8.5.0)
    Requirement already satisfied: typing-extensions>=4.7 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (4.12.2)
    Requirement already satisfied: python-dateutil<3.0.0,>=2.1 in /opt/conda/lib/python3.10/site-packages (from botocore<1.35.0,>=1.34.162->boto3<1.35.0,>=1.34.131->langchain-aws==0.1.17) (2.9.0)
    Requirement already satisfied: urllib3!=2.2.0,<3,>=1.25.4 in /opt/conda/lib/python3.10/site-packages (from botocore<1.35.0,>=1.34.162->boto3<1.35.0,>=1.34.131->langchain-aws==0.1.17) (1.26.19)
    Requirement already satisfied: jsonpointer>=1.9 in /opt/conda/lib/python3.10/site-packages (from jsonpatch<2.0,>=1.33->langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (3.0.0)
    Requirement already satisfied: orjson<4.0.0,>=3.9.14 in /opt/conda/lib/python3.10/site-packages (from langsmith<0.2.0,>=0.1.75->langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (3.10.6)
    Requirement already satisfied: requests<3,>=2 in /opt/conda/lib/python3.10/site-packages (from langsmith<0.2.0,>=0.1.75->langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (2.32.3)
    Requirement already satisfied: six>=1.5 in /opt/conda/lib/python3.10/site-packages (from python-dateutil<3.0.0,>=2.1->botocore<1.35.0,>=1.34.162->boto3<1.35.0,>=1.34.131->langchain-aws==0.1.17) (1.16.0)
    Requirement already satisfied: charset-normalizer<4,>=2 in /opt/conda/lib/python3.10/site-packages (from requests<3,>=2->langsmith<0.2.0,>=0.1.75->langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (3.3.2)
    Requirement already satisfied: idna<4,>=2.5 in /opt/conda/lib/python3.10/site-packages (from requests<3,>=2->langsmith<0.2.0,>=0.1.75->langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (3.7)
    Requirement already satisfied: certifi>=2017.4.17 in /opt/conda/lib/python3.10/site-packages (from requests<3,>=2->langsmith<0.2.0,>=0.1.75->langchain-core<0.3,>=0.2.33->langchain-aws==0.1.17) (2024.7.4)
    Requirement already satisfied: langchain-community==0.2.11 in /opt/conda/lib/python3.10/site-packages (0.2.11)
    Requirement already satisfied: PyYAML>=5.3 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (6.0.1)
    Requirement already satisfied: SQLAlchemy<3,>=1.4 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (2.0.30)
    Requirement already satisfied: aiohttp<4.0.0,>=3.8.3 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (3.9.5)
    Requirement already satisfied: dataclasses-json<0.7,>=0.5.7 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (0.6.7)
    Collecting langchain<0.3.0,>=0.2.12 (from langchain-community==0.2.11)
      Downloading langchain-0.2.15-py3-none-any.whl.metadata (7.1 kB)
    Requirement already satisfied: langchain-core<0.3.0,>=0.2.27 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (0.2.37)
    Requirement already satisfied: langsmith<0.2.0,>=0.1.0 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (0.1.98)
    Requirement already satisfied: numpy<2,>=1 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (1.26.4)
    Requirement already satisfied: requests<3,>=2 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (2.32.3)
    Requirement already satisfied: tenacity!=8.4.0,<9.0.0,>=8.1.0 in /opt/conda/lib/python3.10/site-packages (from langchain-community==0.2.11) (8.5.0)
    Requirement already satisfied: aiosignal>=1.1.2 in /opt/conda/lib/python3.10/site-packages (from aiohttp<4.0.0,>=3.8.3->langchain-community==0.2.11) (1.3.1)
    Requirement already satisfied: attrs>=17.3.0 in /opt/conda/lib/python3.10/site-packages (from aiohttp<4.0.0,>=3.8.3->langchain-community==0.2.11) (23.2.0)
    Requirement already satisfied: frozenlist>=1.1.1 in /opt/conda/lib/python3.10/site-packages (from aiohttp<4.0.0,>=3.8.3->langchain-community==0.2.11) (1.4.1)
    Requirement already satisfied: multidict<7.0,>=4.5 in /opt/conda/lib/python3.10/site-packages (from aiohttp<4.0.0,>=3.8.3->langchain-community==0.2.11) (6.0.5)
    Requirement already satisfied: yarl<2.0,>=1.0 in /opt/conda/lib/python3.10/site-packages (from aiohttp<4.0.0,>=3.8.3->langchain-community==0.2.11) (1.9.4)
    Requirement already satisfied: async-timeout<5.0,>=4.0 in /opt/conda/lib/python3.10/site-packages (from aiohttp<4.0.0,>=3.8.3->langchain-community==0.2.11) (4.0.3)
    Requirement already satisfied: marshmallow<4.0.0,>=3.18.0 in /opt/conda/lib/python3.10/site-packages (from dataclasses-json<0.7,>=0.5.7->langchain-community==0.2.11) (3.21.3)
    Requirement already satisfied: typing-inspect<1,>=0.4.0 in /opt/conda/lib/python3.10/site-packages (from dataclasses-json<0.7,>=0.5.7->langchain-community==0.2.11) (0.9.0)
    Requirement already satisfied: langchain-text-splitters<0.3.0,>=0.2.0 in /opt/conda/lib/python3.10/site-packages (from langchain<0.3.0,>=0.2.12->langchain-community==0.2.11) (0.2.2)
    Requirement already satisfied: pydantic<3,>=1 in /opt/conda/lib/python3.10/site-packages (from langchain<0.3.0,>=0.2.12->langchain-community==0.2.11) (1.10.17)
    Requirement already satisfied: jsonpatch<2.0,>=1.33 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3.0,>=0.2.27->langchain-community==0.2.11) (1.33)
    Requirement already satisfied: packaging<25,>=23.2 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3.0,>=0.2.27->langchain-community==0.2.11) (24.1)
    Requirement already satisfied: typing-extensions>=4.7 in /opt/conda/lib/python3.10/site-packages (from langchain-core<0.3.0,>=0.2.27->langchain-community==0.2.11) (4.12.2)
    Requirement already satisfied: orjson<4.0.0,>=3.9.14 in /opt/conda/lib/python3.10/site-packages (from langsmith<0.2.0,>=0.1.0->langchain-community==0.2.11) (3.10.6)
    Requirement already satisfied: charset-normalizer<4,>=2 in /opt/conda/lib/python3.10/site-packages (from requests<3,>=2->langchain-community==0.2.11) (3.3.2)
    Requirement already satisfied: idna<4,>=2.5 in /opt/conda/lib/python3.10/site-packages (from requests<3,>=2->langchain-community==0.2.11) (3.7)
    Requirement already satisfied: urllib3<3,>=1.21.1 in /opt/conda/lib/python3.10/site-packages (from requests<3,>=2->langchain-community==0.2.11) (1.26.19)
    Requirement already satisfied: certifi>=2017.4.17 in /opt/conda/lib/python3.10/site-packages (from requests<3,>=2->langchain-community==0.2.11) (2024.7.4)
    Requirement already satisfied: greenlet!=0.4.17 in /opt/conda/lib/python3.10/site-packages (from SQLAlchemy<3,>=1.4->langchain-community==0.2.11) (3.0.3)
    Requirement already satisfied: jsonpointer>=1.9 in /opt/conda/lib/python3.10/site-packages (from jsonpatch<2.0,>=1.33->langchain-core<0.3.0,>=0.2.27->langchain-community==0.2.11) (3.0.0)
    Requirement already satisfied: mypy-extensions>=0.3.0 in /opt/conda/lib/python3.10/site-packages (from typing-inspect<1,>=0.4.0->dataclasses-json<0.7,>=0.5.7->langchain-community==0.2.11) (1.0.0)
    Downloading langchain-0.2.15-py3-none-any.whl (1.0 MB)
    [2K   [90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[0m [32m1.0/1.0 MB[0m [31m47.8 MB/s[0m eta [36m0:00:00[0m
    [?25hInstalling collected packages: langchain
      Attempting uninstall: langchain
        Found existing installation: langchain 0.2.5
        Uninstalling langchain-0.2.5:
          Successfully uninstalled langchain-0.2.5
    Successfully installed langchain-0.2.15



```python
%store -r
```

<strong>Restart the kernel with the updated packages that are installed through the dependencies above</strong>


```python
# restart kernel
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```




<script>Jupyter.notebook.kernel.restart()</script>



<h3>Imports</h3>

<b>Follow the steps below to initilize the required python modules</b>

<ol>
<li>Import necessary libraries and initialize bedrock client required by the Langchain module to communicate with Foundation Models (FM) or Large Language Models (LLM) available in Amazon Bedrock.</li>
<li>Import and Initialize Knoweledge Base Retriver available in Langchain to communicate with Knowledge Base from Amazon Bedrock</li>
</ol>


```python
import boto3
import pprint
from botocore.client import Config
import json

from langchain_aws import ChatBedrock
from langchain.retrievers.bedrock import AmazonKnowledgeBasesRetriever


pp = pprint.PrettyPrinter(indent=2)
session = boto3.session.Session()
region = session.region_name   # use can you the region of your choice.
bedrock_config = Config(
    connect_timeout=120, read_timeout=120, retries={'max_attempts': 0}
)
bedrock_client = boto3.client('bedrock-runtime', region_name = region)


llm = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0", # Model ID of the LLM of our choice from Amazon Bedrock
    client=bedrock_client
)

retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=kb_id, # we are using the id of the knowledge base that we created in earlier notebook
    retrieval_config={
        "vectorSearchConfiguration": {
            "numberOfResults": 3,
            "overrideSearchType": "HYBRID", # optional
            # "filter": {"equals": {"key": "tag", "value": "space"}}, # Optional Field for for metadata filtering.
        }
    },
)
```

Above we initialized the following two objects from Langchain:

<ol>
<li><strong>ChatBedrock</strong> - This object will orchestrates the communication with  the LLM from Amazon Bedrock. It will take care of structuring the prompt/messages, model arguments, etc for us whenever it invokes the LLM.</li>
<li><strong>AmazonKnowledgeBasesRetriever</strong> - This objects will call the Retreive API provided by Knowledge Bases for Amazon Bedrock which converts user queries into embeddings, searches the knowledge base, and returns the relevant results, giving you more control to build custom workﬂows on top of the semantic search results. The output of the Retrieve API includes the the retrieved text chunks, the location type and URI of the source data, as well as the relevance scores of the retrievals.</li>
</ol>

<h3>Usage</h3>

Below is the method to directly fetch the relevant documents usign the `AmazonKnowledgeBasesRetriever` object.


```python
query = "By what percentage did AWS revenue grow year-over-year in 2021?"

response = retriever.invoke(query)

pp.pprint(response)
```

    [ Document(metadata={'location': {'s3Location': {'uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2021-Shareholder-Letter.pdf'}, 'type': 'S3'}, 'score': 0.6721358, 'source_metadata': {'x-amz-bedrock-kb-source-uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2021-Shareholder-Letter.pdf', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AXwLjuJEB1zTd7D-p8PFJ', 'x-amz-bedrock-kb-data-source-id': 'MVXWUY4MBU'}}, page_content='This was due in part to the uncertainty and slowing demand that so many businesses encountered, but also in part to our helping companies optimize their AWS footprint to save money. Concurrently, companies were stepping back and determining what they wanted to change coming out of the pandemic. Many concluded that they didn’t want to continue managing their technology infrastructure themselves, and made the decision to accelerate their move to the cloud. This shift by so many companies (along with the economy recovering) helped re-accelerate AWS’s revenue growth to 37% YoY in 2021.   Conversely, our Consumer revenue grew dramatically in 2020. In 2020, Amazon’s North America and International Consumer revenue grew 39% YoY on the very large 2019 revenue base of $245 billion; and, this extraordinary growth extended into 2021 with revenue increasing 43% YoY in Q1 2021. These are astounding numbers. We realized the equivalent of three years’ forecasted growth in about 15 months.   As the world opened up again starting in late Q2 2021, and more people ventured out to eat, shop, and travel, consumer spending returned to being spread over many more entities. We weren’t sure what to expect in 2021, but the fact that we continued to grow at double digit rates (with a two-year Consumer compounded annual growth rate of 29%) was encouraging as customers appreciated the role Amazon played for them during the pandemic, and started using Amazon for a larger amount of their household purchases.   This growth also created short-term logistics and cost challenges. We spent Amazon’s first 25 years building a very large fulfillment network, and then had to double it in the last 24 months to meet customer demand. As we were bringing this new capacity online, the labor market tightened considerably, making it challenging both to receive all of the inventory our vendors and sellers wanted to send us and to place that inventory as close to customers as we typically do.'),
      Document(metadata={'location': {'s3Location': {'uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf'}, 'type': 'S3'}, 'score': 0.6133656, 'source_metadata': {'x-amz-bedrock-kb-source-uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2022-Shareholder-Letter.pdf', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AEO7juJEBXwKXtPXx95cu', 'x-amz-bedrock-kb-data-source-id': 'MVXWUY4MBU'}}, page_content='While we have a consumer business that’s $434B in 2022, the vast majority of total market segment share in global retail still resides in physical stores (roughly 80%). And, it’s a similar story for Global IT spending, where we have AWS revenue of $80B in 2022, with about 90% of Global IT spending still on-premises and yet to migrate to the cloud. As these equations steadily flip—as we’re already seeing happen—we believe our leading customer experiences, relentless invention, customer focus, and hard work will result in significant growth in the coming years. And, of course, this doesn’t include the other businesses and experiences we’re pursuing at Amazon, all of which are still in their early days.   I strongly believe that our best days are in front of us, and I look forward to working with my teammates at Amazon to make it so.   Sincerely,   Andy Jassy President and Chief Executive Officer Amazon.com, Inc.   P.S. As we have always done, our original 1997 Shareholder Letter follows. What’s written there is as true today as it was in 1997.        1997 LETTER TO SHAREHOLDERS (Reprinted from the 1997 Annual Report)   To our shareholders:   Amazon.com passed many milestones in 1997: by year-end, we had served more than 1.5 million customers, yielding 838% revenue growth to $147.8 million, and extended our market leadership despite aggressive competitive entry.   But this is Day 1 for the Internet and, if we execute well, for Amazon.com. Today, online commerce saves customers money and precious time. Tomorrow, through personalization, online commerce will accelerate the very process of discovery. Amazon.com uses the Internet to create real value for its customers and, by doing so, hopes to create an enduring franchise, even in established and large markets.   We have a window of opportunity as larger players marshal the resources to pursue the online opportunity and as customers, new to purchasing online, are receptive to forming new relationships. The competitive landscape has continued to evolve at a fast pace.'),
      Document(metadata={'location': {'s3Location': {'uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2020-Shareholder-Letter.pdf'}, 'type': 'S3'}, 'score': 0.6088787, 'source_metadata': {'x-amz-bedrock-kb-source-uri': 's3://bedrock-kb-ap-south-1-874163252636/AMZN-2020-Shareholder-Letter.pdf', 'x-amz-bedrock-kb-chunk-id': '1%3A0%3AigLjuJEB1zTd7D-p_PGW', 'x-amz-bedrock-kb-data-source-id': 'MVXWUY4MBU'}}, page_content='We have 200 million Prime members, for a total in 2020 of $126 billion of value creation.   AWS is challenging to estimate because each customer’s workload is so different, but we’ll do it anyway, acknowledging up front that the error bars are high. Direct cost improvements from operating in the cloud versus on premises vary, but a reasonable estimate is 30%. Across AWS’s entire 2020 revenue of $45 billion, that 30% would imply customer value creation of $19 billion (what would have cost them $64 billion on their own cost $45 billion from AWS). The difficult part of this estimation exercise is that the direct cost reduction is the smallest portion of the customer benefit of moving to the cloud. The bigger benefit is the increased speed of software development – something that can significantly improve the customer’s competitiveness and top line. We have no reasonable way of estimating that portion of customer value except to say that it’s almost certainly larger than the direct cost savings. To be conservative here (and remembering we’re really only trying to get ballpark estimates), I’ll say it’s the same and call AWS customer value creation $38 billion in 2020.   Adding AWS and consumer together gives us total customer value creation in 2020 of $164 billion.        Summarizing: Shareholders $21B Employees $91B 3P Sellers $25B Customers $164B Total $301B   If each group had an income statement representing their interactions with Amazon, the numbers above would be the “bottom lines” from those income statements. These numbers are part of the reason why people work for us, why sellers sell through us, and why customers buy from us. We create value for them. And this value creation is not a zero-sum game. It is not just moving money from one pocket to another. Draw the box big around all of society, and you’ll find that invention is the root of all real value creation. And value created is best thought of as a metric for innovation.')]


<h2>Code</h2>

<h3>Using Knowledge Base within a Chain</h3>


<h4>Prompt specific to the model to personalize responses</h4>

Here, we will use the specific prompt below for the model to act as a financial advisor AI system that will provide answers to questions by using fact based and statistical information when possible. We will provide the Retrieve API responses from above as a part of the {context} in the prompt for the model to refer to, along with the user query.


```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts import PromptTemplate

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

prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


qa_chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
)

response = qa_chain.invoke(query)

print(response)
```

    According to the context provided, AWS revenue grew 37% year-over-year in 2021.


<h2>Conclusion</h2>

We saw how easy it is to use Amazon Bedrock with Langchain. Specifically we saw how LLM models form Amazon Bedrock and Knowledge base from Amazon Bedrock can be used by Langchain to orchestrate the Q&A capability. It should be noted that LangChain which uses AmazonKnowledgeBaseRetriever to connect with Knowledge base from Amazon Bedrock internally uses Retrieve API. 

Retrieve API provides you with the flexibility of using any foundation model provided by Amazon Bedrock, and choosing the right search type, either HYBRID or SEMANTIC, based on your use case. Here is the [blog](https://aws.amazon.com/blogs/machine-learning/knowledge-bases-for-amazon-bedrock-now-supports-hybrid-search/) for Hybrid Search feature, for more details.

<h2>Next Steps</h2>

You can check out the next example to see how LlamaIndex can leverage Amazon Bedrock to build intelligent RAG applications.


<h2>Clean Up</h2>
<div class="alert alert-block alert-warning">
In case you are done with your labs and the sample codes then remember to Clean Up the resources at the end of your session by following <a href="https://github.com/aws-samples/amazon-bedrock-samples/opensource-libraries/knowledge-base/3_clean_up.ipynb">3_clean_up.ipynb</a>
</div>



```python

```
