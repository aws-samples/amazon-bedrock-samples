# Building a two-stage agentic RAG System with Amazon Bedrock Knowledge Bases and Amazon Bedrock Converse API

This repository demonstrates how to build an advanced agentic RAG (Retrieval-Augmented Generation) system using Amazon Bedrock. The solution processes large document collections, extracts metadata and implements an intelligent agent that makes strategic decisions about document retrieval, using metadata and summaries to enhance response accuracy.

## Overview

The project is divided into two main components, each implemented as a Jupyter notebook:

1. [Extract Metadata and Create Knowledge Base](01-metadata-extraction-and-kb-creation.ipynb): This notebook focuses on processing PDF documents, extracting metadata, and creating two Amazon Bedrock Knowledge Bases.
2. [Create Agent Resources](02-agentic-rag-converse-api.ipynb): This notebook builds upon the Knowledge Bases created in the first step to construct an intelligent agent for document querying.

These notebooks guide you through the process of building a sophisticated document processing and querying system using Amazon Bedrock's powerful AI capabilities. By following this two-step process, you'll create a system that can efficiently search through document summaries, understand on which documents to dive deep, retrieve relevant information using filters, and provide accurate answers to complex queries.

### Why two Knowledge Bases?

We create two separate Knowledge Bases for several reasons:

1. **Efficiency**: The summaries Knowledge Base allows for quick, high-level searches across all documents without the need to search through every detail. This initial semantic search allows the agent to understand which are the relevant documents containing the relevant information.

2. **Precision**: The documents Knowledge Base provides detailed information when needed, allowing for more accurate answers to specific questions. It stores smaller, context-preserving chunks of the documents along with their associated metadata, like the filename, that willl be used to filter retrieved chunks

3. **Scalability**: This two-tier approach scales well with large document collections, maintaining quick response times even as the corpus grows.

### How the Agent Uses Metadata for Filtering

The agent leverages metadata in a two-stage search process:

1. **Summary Search**: The agent first searches the summaries Knowledge Base to identify the most relevant documents based on their summaries and filenames.

2. **Chunk Retrieval**: Using the results from the summary search, the agent then performs a targeted search within the documents Knowledge Base. It uses the metadata (specifically the filenames) to filter and retrieve only the most relevant chunks from the identified documents.

This approach allows the agent to efficiently narrow down the search space, first identifying relevant documents, then pinpointing the most pertinent information within those documents. The use of metadata ensures that the agent can quickly focus on the most relevant parts of the document collection, improving both the speed and accuracy of responses to user queries.

## Features

- Extract metadata and generate summaries from PDF files
- Create two Amazon Bedrock Knowledge Bases:
  1. High-level summaries and filenames of documents
  2. Detailed chunks from files with associated metadata
- Build an intelligent agentic RAG system with a two-stage search process
- Utilize Amazon Bedrock for advanced natural language processing and generation
- Implement efficient, context-aware search and retrieval from large document corpora
- Provide accurate and relevant answers to complex queries about document content

## Key Capabilities

1. **Intelligent Document Processing**: Automatically extract key information and generate summaries from PDF documents.
2. **Advanced Knowledge Base Creation**: Utilize Amazon Bedrock to create sophisticated, searchable knowledge repositories.
3. **Two-Stage Search Process**: Implement a summary search followed by targeted chunk retrieval for efficient information access.
4. **Contextual Question Answering**: Generate accurate, context-aware responses to user queries using retrieved document chunks.
5. **Scalable Document Management**: Handle large document collections with ease, making information readily accessible and queryable.

## Prerequisites

- Python 3.7 or higher
- AWS account with access to Amazon Bedrock and permissions to access to the following services: **Amazon S3, AWS STS,  AWS CloudFormation, Amazon Bedrock and Amazon Opensearch Serverless**.
- Basic understanding of Jupyter notebooks and Python programming

## Setup

1. Clone this repository to your local machine or SageMaker instance.

2. Configure your AWS credentials with access to Amazon Bedrock (ensure you're using the `us-east-1` region or update as necessary).

3. Prepare your PDF documents in a designated folder (default is `./PDFs/`).

## Usage

1. Start with the [Extract Metadata and Create Knowledge Base](01-metadata-extraction-and-kb-creation.ipynb) notebook:
   - This notebook guides you through processing PDF documents, extracting metadata, and creating two Amazon Bedrock Knowledge Bases.
   - Follow the instructions within the notebook to set up your environment and process your documents.

2. Once you've completed the first notebook, proceed to the [Create Agent Resources](02-agentic-rag-converse-api.ipynb) notebook:
   - This notebook builds upon the Knowledge Bases created in the first step to construct an intelligent agent for document querying.
   - Follow the step-by-step instructions to set up your agent and test it with sample queries.

## Output

After completing both notebooks, you will have:
- Two Amazon Bedrock Knowledge Bases containing document summaries and detailed document chunks
- An intelligent agent capable of answering complex queries about your document collection
- A system that can be easily expanded to handle larger document sets and more diverse query types

## Customization

You can customize various aspects of the system, including:
- The chunking strategy for documents
- The prompts used for generating summaries and answers
- The system prompt of the agent
- The number of results returned in searches

Refer to the comments within each notebook for guidance on customization options.

## Troubleshooting

If you encounter any issues:
1. Ensure your AWS credentials are correctly configured and have the necessary permissions.
2. Check that you're using the correct versions of the required libraries.
3. Verify that your PDF documents are in the expected format and location.

For more detailed troubleshooting, refer to the Amazon Bedrock documentation or open an issue in this repository.

## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.

---

We hope this project helps you leverage the power of Amazon Bedrock to build intelligent document processing and querying systems. Happy coding!
