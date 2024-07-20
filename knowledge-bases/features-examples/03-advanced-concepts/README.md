# Advanced Concepts

## Contents

### RAG Two Stage Retrieval using Reranking Model
When it comes to building a chatbot using GenAI LLMs, RAG is a popular architectural choice. It combines the strengths of knowledge base retrieval and generative models for text generation. Using RAG approach for building a chatbot has many advantages. For example, retrieving responses from its database before generating a response could provide more relevant and coherent responses. This helps improve the conversational flow. RAG also scales better with more data compared to pure generative models and it doesn’t require fine tuning of the model when new data is added to the knowledge base. Additionally, the retrieval component enables the model to incorporate external knowledge by retrieving relevant background information from its database. This approach helps provide factual, in-depth and knowledgeable responses.

## RAG Challenges
Despite clear advantages of using RAG for building Chatbots, there are some challenges when it comes to applying it for practical use. In order to find an answer, RAG takes an approach that uses vector search across the documents. The advantage of using vector search is the speed and scalability. Rather than scanning every single document to find the aswer, using RAG approach, we would turn the texts (knowledge base) into embeddings and store these embeddings in the database. The embeddings are compressed version of the documents, represented by array of numerical values. After the embeddings are stored, vector search queries the vector database to find the similarity based on the vectors associated with the documents. Typically vector search will return the top k most relevant documents based on the user question, and return the k results. However, since the similarity algorithm in vector database works on vectors and not documents, vector search does not always return the most relevant information in the top k results. This directly impacts the accuracy of the response if the most relevant contexts are not available to the LLM.

A proposed solution to address the challenge of RAG approach is called Reranking. Reranking is a technique that can further improve the responses by selecting the best option out of several candidate responses. Here is how reranking could work, described in the sequential order:

The chatbot generates its top 5 response candidates using RAG.
These candidates are fed into a reranking model. This model scores each response based on how relevant, natural and informative they are.

The response with the highest reranking score is selected as the context to feed the LLM in generating a response .
In summary, reranking allows the chatbot to filter out poor responses and pick the best one to send back. This further improves the quality and consistency of the conversations.

## Getting started
To see the reranking model in action, run the following notebooks in the order for complete detail and an analysis.

* [deploy_reranking_model_sm.ipynb](deploy-reranking-model-sm.ipynb) - This notebook deploys an open source reranking model [bge-reranker-large](https://huggingface.co/BAAI/bge-reranker-large) to Amazon SageMaker as a realtime endpoint. The endpoint will be used as an example for a RAG two stage retrieval application in a separate notebook. This notebook is a prerequisite for reranking model integration with Knowledge Bases for Bedrock.

* [kb-reranker.ipynb](kb-reranker.ipynb) - This notebook leverages a reranking model deployed in [deploy_reranking_model_sm.ipynb](deploy-reranking-model-sm.ipynb) for building a RAG application for a sample dataset. The notebook creates a knowledge bases for Bedrock with Amazon OpenSearch Serverless as the vector database, and uses the Bedrock Agent runtime API and SageMaker to orchestrate the RAG two stage retrieval process. The notebook also provides an in depth evaluation of a two stage retrieval versus a standard RAG approach using an open source RAG evaluation framework  [RAGAS](https://github.com/explodinggradients/ragas). 

## Contributing

We welcome community contributions! Please ensure your sample aligns with [AWS best practices](_!https://aws.amazon.com/architecture/well-architected/_), and please update the Contents section of this README file with a link to your sample, along with a description..
