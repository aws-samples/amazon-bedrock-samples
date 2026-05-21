# Amazon Bedrock Knowledge Bases

[Amazon Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) allows you to integrate proprietary information into your generative-AI applications. Using the Retrieval Augment Generation (RAG) technique, a knowledge base searches your data to find the most useful information and then uses it to answer natural language questions. Once set up, you can take advantage of a knowledge base in the following ways:
- Configure your RAG application to use the [RetrieveAndGenerate](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_RetrieveAndGenerate.html
) API to query your knowledge base and generate responses from the information it retrieves. You can also call the [Retrieve API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Retrieve.html) to query your knowledge base with information retrieved directly from the knowledge base.
- Associate your knowledge base with an agent (for more information, see [Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)) to add RAG capability to the agent by helping it reason through the steps it can take to help end users.
- A knowledge base can be used not only to answer user queries, and analyze documents, but also to augment prompts provided to foundation models by providing context to the prompt. When answering user queries, the knowledge base retains conversation context. The knowledge base also grounds answers in citations so that users can find further information by looking up the exact text that a response is based on and also check that the response makes sense and is factually correct.

## Contents

This repository contains examples and use-cases to get you started with Amazon Bedrock Knowledge Bases and its capabilities. It is organized in the following folders:

- **Feature examples**: code examples of how to use specific features of Amazon Bedrock Knowledge Bases. For mor details, please refer [here](./features-examples/)

- **Use case examples**: code examples of Amazon Bedrock Knowledge Bases for various use cases.
For mor details, please refer [here](./use-case-examples/)


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
