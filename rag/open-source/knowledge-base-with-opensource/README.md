<h2>Examples of OpenSource Libraries leveraging Amazon Bedrock Knowledge Base</h2>

<h3>Contents</h3>

- [0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb](./0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb) : Creates necessary role and policies required using the `utility.py` file. It uses the roles and policies to create Open Search Serverless vector index, knowledge base, data source, and then ingests the documents to the vector store. Once the documents are ingested it will then test the knowledge base using `RetrieveAndGenerate` API for question answering, and `Retrieve` API for fetching relevant documents. You can choose not to delete the resources and move to other sample notebooks, which will use the knowledge base that we just created. Please note, that if you do not delete the resources, you may be incurred cost of storing data in OpenSearch Serverless, even if you are not using it. Therefore, once you are done with trying out the sample codes, make sure to delete all the resources by following the `3_clean_up.ipynb` Notebook.

- [1_how_to_use_knowledge_base_with_langchain.ipynb](./1_how_to_use_knowledge_base_with_langchain.ipynb) : Code sample of using Langchain to build Q&A or retrieval augmented generation (RAG) application by leveraging large Language Models from Amazon Bedrock and Knowledge Base for Amazon Bedrock.

- [2_how_to_use_knowledge_base_with_llamaindex.ipynb](./2_how_to_use_knowledge_base_with_llamaindex.ipynb) : Code sample of using LlamaIndex to build Q&A or retrieval augmented generation (RAG) application by leveraging large Language Models from Amazon Bedrock and Knowledge Base for Amazon Bedrock.

Remember to use the [3_clean_up.ipynb](./3_clean_up.ipynb) to delete the resources.

***

<h3>Note</h3>

If you use the notebook [0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb](./0_how_to_create_index_and_ingest_documents_in_knowledge_base.ipynb) for creating the knowledge bases and do not delete the resources, you may incur cost of storing data in OpenSearch Serverless, even if you are not using it. Therefore, once you are done with trying out the sample code, make sure to delete all the resources by following [3_clean_up.ipynb](./3_clean_up.ipynb)


<h2>Contributing</h2>

We welcome community contributions! Please ensure your sample aligns with  [AWS best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
