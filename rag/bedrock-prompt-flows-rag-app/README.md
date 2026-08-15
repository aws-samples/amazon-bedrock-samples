# Build a simple RAG Application with Amazon Bedrock Flows 

Amazon Bedrock Flows accelerates the creation, testing, and deployment of user-defined workflows for generative AI applications through an intuitive visual builder. Using Bedrock prompt flows, users can drag, drop and link Prompts, existing Agents, Knowledge Bases, Guardrails and other AWS services. This enables generative AI teams to build a business logic via workflow creations. 

In this example, we will be building a simple RAG application. We will follow the following steps:

## Overview

This example focuses on building a basic **RAG (Retrieval-Augmented Generation)** application. The high-level steps are:

1. **Create a RAG prompt** and a **router prompt** and store it in **Bedrock prompt management**.  
   - Bedrock prompt management simplifies the creation, evaluation, versioning, and sharing of prompts, ensuring you can easily reuse and maintain them.
   - In this example we create two prompts, one for RAG and one as a router prompt. The router prompt is powered by an SLM (`haiku`) to route requests and figure
   out whether a question is of one type versus another
   
1. **Apply a condition** via the router, to route requests to different Knowledge Bases based on different user questions.

1. **Create two knowledge bases** that contains sample information about AWS services. One of the knowledge bases contains information about basic AWS services and the other contains information about specific generative AI services.

3. **Create a prompt flow** that:
   - Takes a user-provided question.
   - Routes the request to the right KB based on the condition.
   - Retrieve relevant chunks from the knowledge base.
   - Sends the retrieved context and user question to a foundation model for an answer along with a RAG prompt stored in the prompt management library.
   - Return the final output to the user.


[Amazon Bedrock Prompt Management](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-management.html) streamlines the creation, evaluation, deployment, and sharing of prompts in the Amazon Bedrock console and via APIs in the SDK. This feature helps developers and business users obtain the best responses from foundation models for their specific use cases.

[Amazon Bedrock Prompt Flows](https://docs.aws.amazon.com/bedrock/latest/userguide/flows.html) allows you to easily link multiple foundation models (FMs), prompts, and other AWS services, reducing development time and effort. It introduces a visual builder in the Amazon Bedrock console and a new set of APIs in the SDK, that simplifies the creation of complex generative AI workflows.
