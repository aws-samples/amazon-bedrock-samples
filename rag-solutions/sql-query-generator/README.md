# SQL Query Generator & Executor Example


This demonstrates a simple application using public [Northwind](https://docs.yugabyte.com/preview/sample-data/northwind/) with Amazon Titan Embeddings, Amazon Bedrock Claude Model, LangChain, and Streamlit for the front-end.

The example receives a user’s prompt, generates a SQL query using in-memory vector database and few-shot examples. We then run the query using SQLite database and display query results in the user interface.

For simplicity, we use the in-memory [Chroma](https://www.trychroma.com/) database to store and search for embeddings vectors. In a real-world scenario at scale, you will likely want to use a persistent data store like the vector engine for [Amazon OpenSearch Serverless](https://aws.amazon.com/opensearch-service/serverless-vector-engine/) or the pgvector extension for PostgreSQL.


## Contents

The example consists of four files:

* Streamlit application in Python
* Supporting file to make calls to Bedrock to run the SQL chain
* Requirements file, and a data file to search against
* SQLite helper file to run queries
* Local SQLite Northwind database

## Requirements

You need an AWS account with following Bedrock models enabled;
* amazon.titan-embed-text-v1
* anthropic.claude-v2

You need to [setup your AWS profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) and setup your "default" profile with the AWS account credentials where you have above Bedrock models enabled

## Setup

From the command line, run the following in the code folder:

```
pip3 install -r requirements.txt -U
```

## Running

From the command line, run the following in the code folder:

```
streamlit run sql_chat_ui.py
```

You should now be able to access the Streamlit web application from your browser.

![SQL Generator & Executor Frontend](rag-solutions\sql-query-generator\images\sql_chat_ui.png)

## Try a few prompts from the web application:

* Can you list customers which placed orders in the last 30 days?
* Can you get alphabetical list of products?
* For each order, calculate a subtotal for each Order (identified by OrderID)?
* For each employee, can you get their sales amount, broken down by country name?
* Can you calculate sales price for each order after discount is applied?
* For each category, can you get the list of products sold and the total sales amount?
* Can you list ten most expensive products?
* Can you list products above average price?
* Can you show sales amount for each quarter?
* Can you list number of units in stock by category and supplier continent?
* What are the total sales amounts by year?
* What are the top 5 most expensive products?
* What customers have spent over $1000 in total?
* What products were sold in the last month?
* What is the total revenue for each employee?
