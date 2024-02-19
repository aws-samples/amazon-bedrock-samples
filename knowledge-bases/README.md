# Amazon Bedrock Knowledge Base - Samples for building RAG workflows

## Contents
- [0_create_ingest_documents_test_kb.ipynb](./0\_create_ingest_documents_test_kb.ipynb) - creates necessary role and policies required using the `utility.py` file. It uses the roles and policies to create Open Search Serverless vector index, knowledge base, data source, and then ingests the documents to the vector store. Once the documents are ingested it will then test the knowledge base using `RetrieveAndGenerate` API for question answering, and `Retrieve` API for fetching relevant documents. Finally, it deletes all the resources. If you want to continue with other notebooks, you can choose not to delete the resources and move to other notebooks. Please note, that if you do not delete the resources, you may be incurred cost of storing data in OpenSearch Serverless, even if you are not using it. Therefore, once you are done with trying out the sample code, make sure to delete all the resources. 

- [1_managed-rag-kb-retrieve-generate-api.ipynb](./1\_managed-rag-kb-retrieve-generate-api.ipynb) - Code sample for managed retrieval augmented generation (RAG) using `RetrieveAndGenerate` API from Knowledge Bases for Amazon Bedrock.

- [2_customized-rag-retrieve-api-claude-v2.ipynb](./2\_customized-rag-retrieve-api-claude-v2.ipynb) - If you want to customize your RAG workflow, you can use the `retrieve` API provided by Knowledge Bases for Amazon Bedrock. Use this code sample as a starting point.

- [3_customized-rag-retrieve-api-langchain-claude-v2.ipynb](./3\_customized-rag-retrieve-api-langchain-claude-v2.ipynb) - Code sample for using the `RetrieveQA` chain from LangChain and Amazon Knowledge Base as the retriever.

- [4_customized-rag-retrieve-api-titan-lite-evaluation.ipynb](./4\_customized-rag-retrieve-api-titan-lite-evaluation.ipynb) - If you are interested in evaluating your RAG application, try this sample code where we are using the `Amazon Titan Lite` model for generating responses and `Anthropic Claude V2` for evaluating the response.

- [5_customized-rag-retreive-api-langchain-claude-v2-evaluation-ragas.ipynb](./5_customized-rag-retreive-api-langchain-claude-v2-evaluation-ragas.ipynb) - If you are interested in building Q&A application using Retrieve API provide by Knowledge Bases for Amazon Bedrock, along with LangChain and RAGAS for evaluating the responses, try this sample.

- [6_customized-rag-retreive-api-langchain-claude-v2-online-evaluation-ragas.ipynb](./6_customized-rag-retreive-api-langchain-claude-v2-online-evaluation-ragas.ipynb) - The popularity of large language models (LLMs) is skyrocketing, and with it the    need to observe and analyze their performance. Tracing model usage in production and getting detailed insights on quality, cost and speed are crucial for the continued growth of generative AI apps.  Now let's explore Langfuse, another emerging project tackling observability for these complex systems.  

    Langfuse aims to provide granular visibility into model invocation traces and metrics like accuracy, latency and cost per query. With advanced analytics and visualization, it can help teams optimize performance, reduce expenses and identify issues early. As generative AI enters the mainstream, Langfuse and similar tools will be key enablers for delivering reliable, cost-effective services at scale. 

    In this notebook, We will use Ragas to run the evaluations for each trace item and score them. This gives you better idea of how each call to RAG pipelines is performing. You compute the score with each request from getting question from the user and fetch context from the Knoweldge base then pass the question and the contexts to the LLM to generate the answer. All these step are logged as spans in a single trace in langfuse. You can read more about traces and spans from the [langfuse documentation](https://langfuse.com/docs/tracing/overview).


    ### Vidoe : Langfuse Dashboard and Traces view
    
    https://github.com/aws-samples/amazon-bedrock-samples/assets/136643863/2380aafe-8936-4fd1-b9c9-3462de007b11




***

### Note
If you use the notebook - `0_create_ingest_documents_test_kb.ipynb` for creating the knowledge bases and do not delete the resources, you may be incurred cost of storing data in OpenSearch Serverless, even if you are not using it. Therefore, once you are done with trying out the sample code, make sure to delete all the resources. 

## Contributing

We welcome community contributions! Please ensure your sample aligns with [AWS best practices](_!https://aws.amazon.com/architecture/well-architected/_), and please update the Contents section of this README file with a link to your sample, along with a description..
