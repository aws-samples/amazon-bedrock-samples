# Amazon Bedrock Knowledge Base - Samples for building RAG workflows

## Contents
Contains following folders: 
- 00-zero-setup-chat-with-your-document
- 01-rag-concepts
- 02-advanced-concepts

### 00-zero-setup-chat-with-your-document
- [0_chat_with_document_kb.ipynb](./00-zero-setup-chat-with-your-document/0_chat_with_document_kb.ipynb) - Enables you to chat with your document without setting up any vector database. You can either upload the document or simply point to the document in your S3 location. 

### 01-rag-concepts
- [1a_create_ingest_documents_test_kb.ipynb](./01-rag-concepts/1a_create_ingest_documents_test_kb.ipynb) - creates necessary role and policies required using the `utility.py` file. It uses the roles and policies to create Open Search Serverless vector index, knowledge base, data source, and then ingests the documents to the vector store. Once the documents are ingested it will then test the knowledge base using `RetrieveAndGenerate` API for question answering, and `Retrieve` API for fetching relevant documents. Finally, it deletes all the resources. If you want to continue with other notebooks, you can choose not to delete the resources and move to other notebooks. Please note, that if you do not delete the resources, you may be incurred cost of storing data in OpenSearch Serverless, even if you are not using it. Therefore, once you are done with trying out the sample code, make sure to delete all the resources. 

- [1b_create_ingest_documents_test_kb_multi_ds.ipynb](./01-rag-concepts/1b_create_ingest_documents_test_kb_multi_ds.ipynb) - creates necessary role and policies required using the `utility.py` file. It creates knowledge bases with multiple s3 buckets as data sources.  

- [2_managed-rag-kb-retrieve-generate-api.ipynb](./01-rag-concepts/2_managed-rag-kb-retrieve-generate-api.ipynb) - Code sample for managed retrieval augmented generation (RAG) using `RetrieveAndGenerate` API from Knowledge Bases for Amazon Bedrock.

- [3_customized-rag-retrieve-api-claude-v2.ipynb](./01-rag-concepts/3_customized-rag-retreive-api-hybrid-search-claude-3-sonnet-langchain.ipynb) - If you want to customize your RAG workflow, you can use the `retrieve` API provided by Knowledge Bases for Amazon Bedrock. You can either performa `semantic` or `hybrid` search over your vector store. This notebook, provides sample code for `hybrid` search using Claude 3 models as well as demonstrates LangChain integraion with Knowledge Bases for Amazon Bedrock.

- [4_customized-rag-retrieve-api-titan-lite-evaluation.ipynb](./01-rag-concepts/4_customized-rag-retreive-api-titan-lite-evaluation.ipynb) - If you are interested in evaluating your RAG application, try this sample code where we are using the `Amazon Titan Lite` model for generating responses and `Anthropic Claude V2` for evaluating the response.

- [5_customized-rag-retreive-api-langchain-claude-v2-evaluation-ragas.ipynb](./01-rag-concepts/5_customized-rag-retreive-api-langchain-claude-v2-evaluation-ragas.ipynb) - If you are interested in building Q&A application using Retrieve API provide by Knowledge Bases for Amazon Bedrock, along with LangChain and RAGAS for evaluating the responses, try this sample.

- [6_customized-rag-retreive-api-langchain-claude-v2-online-evaluation-ragas.ipynb](./01-rag-concepts/6_customized-rag-retreive-api-langchain-claude-v2-online-evaluation-ragas.ipynb) - The popularity of large language models (LLMs) is skyrocketing, and with it the need to observe and analyze their performance. Tracing model usage in production and getting detailed insights on quality, cost and speed are crucial for the continued growth of generative AI apps.  Now let's explore Langfuse, another emerging project tackling observability for these complex systems.  

    Langfuse aims to provide granular visibility into model invocation traces and metrics like accuracy, latency and cost per query. With advanced analytics and visualization, it can help teams optimize performance, reduce expenses and identify issues early. As generative AI enters the mainstream, Langfuse and similar tools will be key enablers for delivering reliable, cost-effective services at scale. 

    In this notebook, we will use RAGAS to run the evaluations for each trace item and score them. This gives you better idea of how each call to RAG pipelines is performing. You compute the score with each request from getting question from the user and fetch context from the Knoweldge base then pass the question and the contexts to the LLM to generate the answer. All these step are logged as spans in a single trace in langfuse. You can read more about traces and spans from the [langfuse documentation](https://langfuse.com/docs/tracing/overview).


    ### Vidoe : Langfuse Dashboard and Traces view
    
    https://github.com/aws-samples/amazon-bedrock-samples/assets/136643863/3277e195-faa4-4c36-8acf-d7d967b20cb5


### 02-advanced-concepts
- [0_chunk_size_evaluation_for_KB_RAG.ipynb](./02-advanced-concepts/0_chunk_size_evaluation_for_KB_RAG.ipynb) - This notebook provides sample code for chunking size evaluation for building optimum RAG applcation.

***

### Note
If you use the notebook - `0_create_ingest_documents_test_kb.ipynb` for creating the knowledge bases and do not delete the resources, you may be incurred cost of storing data in OpenSearch Serverless, even if you are not using it. Therefore, once you are done with trying out the sample code, make sure to delete all the resources. 

## Contributing

We welcome community contributions! Please ensure your sample aligns with [AWS best practices](_!https://aws.amazon.com/architecture/well-architected/_), and please update the Contents section of this README file with a link to your sample, along with a description..
