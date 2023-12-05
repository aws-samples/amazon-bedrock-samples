# Amazon Bedrock Knowledge Base - Samples for building RAG workflows

## Contents

- [1_managed-rag-kb-retrieve-generate-api.ipynb](./1\_managed-rag-kb-retrieve-generate-api.ipynb) - Code sample for managed retrieval augmented generation (RAG) using `RetrieveAndGenerate` API from Knowledge Bases for Amazon Bedrock.

- [2_customized-rag-retrieve-api-claude-v2.ipynb](./2\_customized-rag-retrieve-api-claude-v2.ipynb) - If you want to customize your RAG workflow, you can use the `retrieve` API provided by Knowledge Bases for Amazon Bedrock. Use this code sample as a starting point.

- [3_customized-rag-retrieve-api-langchain-claude-v2.ipynb](./3\_customized-rag-retrieve-api-langchain-claude-v2.ipynb) - Code sample for using the `RetrieveQA` chain from LangChain and Amazon Knowledge Base as the retriever.

- [4_customized-rag-retrieve-api-titan-lite-evaluation.ipynb](./4\_customized-rag-retrieve-api-titan-lite-evaluation.ipynb) - If you are interested in evaluating your RAG application, try this sample code where we are using the `Amazon Titan Lite` model for generating responses and `Anthropic Claude V2` for evaluating the response.

- [5_eval_claudeV2_instant_llamaindex.ipynb] - If you are interested in evaluating your RAG application, try this sample code where we are using the `Amazon Titan embed test model` to create embeddings, and we are testing and evaluating results of claude V2 versus claude instant on the retrieve API from the knowledge base.

- [6_retrieveAndGenerateAPI_eval_llamaindex.ipynb] - If you are interested in evaluating your RAG application using retrieveAndGenerate APIs, try this sample code where we are using the `Amazon Titan embed test model` to create embeddings, and we are testing and evaluating results of claude V2 versus claude instant on the retrieve and generate API from the knowledge base.

***

## Contributing

We welcome community contributions! Please ensure your sample aligns with [AWS best practices](_!https://aws.amazon.com/architecture/well-architected/_), and please update the Contents section of this README file with a link to your sample, along with a description..
