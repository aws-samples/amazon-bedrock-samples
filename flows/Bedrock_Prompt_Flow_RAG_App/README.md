# Build a simple RAG Application with Amazon Bedrock Flows 


Bedrock Flows accelerates the creation, testing, and deployment of user-defined workflows for generative AI applications through an intuitive visual builder. Using Bedrock prompt flows, users can drag, drop and link Prompts, existing Agents, Knowledge Bases, Guardrails and other AWS services. This enables generative AI teams to build a business logic via workflow creations. 

In this example, we will be building a simple RAG application. We will follow the following steps:

1. We will be creating a RAG prompt. This prompt will be stored in Amazon Bedrock within the prompt management feature functionality. Prompt management on Bedrock simplifies the creation, evaluation, versioning, and sharing of prompts to help developers and prompt engineers get the best responses from foundation models (FMs) for their use cases. 

1. Next, we will create a knowledge base, which will store sample information about AWS services. 

1. We will create a prompt flow with the user provided prompt, retrieval of chunks from the knowledge base via a lambda function, followed by answering the user defined question. We will also introduce Guardrails and update our flow at the end.

1. Lastly, we want to be able to access the prompt flow from an external application via an API or export it via a CloudFormation template. We will be doing so at the end. This helps developers to seamlessly access their RAG applications through a simple invocation.


[Amazon Bedrock Prompt Management](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-management.html) streamlines the creation, evaluation, deployment, and sharing of prompts in the Amazon Bedrock console and via APIs in the SDK. This feature helps developers and business users obtain the best responses from foundation models for their specific use cases.

[Amazon Bedrock Prompt Flows](https://docs.aws.amazon.com/bedrock/latest/userguide/flows.html) allows you to easily link multiple foundation models (FMs), prompts, and other AWS services, reducing development time and effort. It introduces a visual builder in the Amazon Bedrock console and a new set of APIs in the SDK, that simplifies the creation of complex generative AI workflows.