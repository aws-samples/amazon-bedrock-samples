# Dynamic Metadata Filtering for Knowledge Bases for Amazon Bedrock

This repository demonstrates how to implement dynamic metadata filtering for Knowledge Bases for Amazon Bedrock using the tool use (function calling) capability and Pydantic for data validation. This approach enhances the flexibility and accuracy of retrieval-augmented generation (RAG) applications, leading to more relevant and contextually appropriate AI-generated responses.

Metadata filtering is a powerful feature that allows you to refine search results by pre-filtering the vector store based on custom metadata attributes. This approach narrows down the search space to the most relevant documents or passages, reducing noise and irrelevant information. By implementing dynamic metadata filtering, this repository aims to improve the retrieval of relevant context from Knowledge Bases for Amazon Bedrock, leading to more accurate and relevant AI-generated responses.

## Importance of Context Quality in RAG Applications
In RAG applications, the accuracy and relevance of generated responses heavily depend on the quality of the context provided to the language model. This context, typically retrieved from the knowledge base based on user queries, directly impacts the model's ability to generate accurate and contextually appropriate outputs. By implementing dynamic metadata filtering, this repository aims to improve the retrieval of relevant context from Knowledge Bases for Amazon Bedrock, leading to more accurate and relevant AI-generated responses.

The notebook also discusses handling edge cases when the function calling process fails to extract metadata from the user query, and strategies to improve context-related RAG metrics such as answer relevancy, context recall, and context precision.

## Prerequisites

Before proceeding, ensure you have:

1. An AWS account with access to Amazon Bedrock.
2. A Knowledge Base created in Amazon Bedrock with ingested data and metadata. If you do not have one setup, you can follow the instructions as mentioned in the [aws blogpost on metadata filtering with Knowledge Bases for Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/knowledge-bases-for-amazon-bedrock-now-supports-metadata-filtering-to-improve-retrieval-accuracy/).

