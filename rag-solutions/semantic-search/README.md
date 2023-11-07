# Semantic Search Example



This demonstrates a simple embeddings search application with Amazon Titan Embeddings, LangChain, and Streamlit.

The example matches a user’s query to the closest entries in an in-memory vector database. We then display those matches directly in the user interface. This can be useful if you want to troubleshoot a RAG application, or directly evaluate an embeddings model.

For simplicity, we use the in-memory [FAISS](https://github.com/facebookresearch/faiss) database to store and search for embeddings vectors. In a real-world scenario at scale, you will likely want to use a persistent data store like the vector engine for [Amazon OpenSearch Serverless](https://aws.amazon.com/opensearch-service/serverless-vector-engine/) or the pgvector extension for PostgreSQL.



## Contents

The example consists of four files: A Streamlit application in Python, a supporting file to make calls to Bedrock, a requirements file, and a data file to search against.


## Setup 

From the command line, run the following in the code folder:

```
pip3 install -r requirements.txt -U
```

## Running

From the command line, run the following in the code folder:

```
streamlit run search_app.py
```

You should now be able to access the Streamlit web application from your browser.


## Try a few prompts from the web application:


* How can I monitor my usage?
* How can I customize models?
* Which programming languages can I use?
* Comment mes données sont-elles sécurisées ?
* 私のデータはどのように保護されていますか？
* Quais fornecedores de modelos estão disponíveis por meio do Bedrock?
* In welchen Regionen ist Amazon Bedrock verfügbar?
* 有哪些级别的支持？

Note that even though the source material was in English, the queries in other languages were matched with relevant entries.


