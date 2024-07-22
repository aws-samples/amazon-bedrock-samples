# Responsible AI

This folder contains examples related to responsible AI with Amazon Bedrock.

Key elements of responsible AI include:

- **Fairness**: How a system impacts different subpopulations of users (e.g. by gender, ethnicity)
- **Explainability**: Mechanisms to understand and evaluate the outputs of an AI system
- **Privacy and security**: Data protected from theft and exposure
- **Robustness**: Mechanisms to ensure an AI system operates reliably
- **Governance**: Processes to define, implement and enforce responsible AI practices within an organization
- **Transparency**: Communicating information about an AI system so stakeholders can make informed choices about their use of the system

More on responsible AI [here](https://aws.amazon.com/machine-learning/responsible-ai/) and [here](https://aws.amazon.com/blogs/machine-learning/announcing-new-tools-and-capabilities-to-enable-responsible-ai-innovation/).

## What are Guardrails?

Guardrails in Large Language Models (LLMs) act as safety mechanisms to ensure that the responses produced match specific criteria, effectively preventing and correcting inappropriate content and behaviour. This programming of LLMs to navigate particular conversational pathways, address user queries in set manners, and adhere to a specific style of language, among other regulations.

Going beyond system messages as a way to manage content concerns guardrails offer a superior approach that goes beyond mere prompt-based systems. Guardrails treat the LLM as an independent component, monitoring inputs and outputs separately. This separation enables the LLM to concentrate on its primary function while the guardrails system oversees and monitors conversations and ensures safety.

Guardrails enable the implementation of sophisticated policies. Unlike system messages, which are limited to basic statements, guardrails can provide comprehensive measures for cleaning inputs, filtering outputs, and directing the flow of conversations. Therefore, while system prompts serve a purpose, implementing guardrails can represent a significant enhancement ensuring that the system operates within a framework of responsibility, ethics, and safety, thereby enhancing the value, trustworthiness, and effectiveness.

Implementation of guardrails can happen via custom implementations, existing open source frameworks or with Guardrails for Amazon Bedrock as a native part of Amazon Bedrock.

[Guardrails for Amazon Bedrock](https://aws.amazon.com/bedrock/guardrails/) enables you to implement safeguards for your generative AI applications. Guardrails helps control the interaction between users and Foundation Models (FMs) by filtering undesirable and harmful content. You can create multiple guardrails with different configurations tailored to specific use cases. Additionally, you can continuously monitor and analyze user inputs and FM responses that may violate customer-defined policies in the guardrails.

[NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) is an open-source toolkit for adding programmable guardrails to LLM-based conversational systems. It can be a good consideration if Guardrails for Amazon Bedrock is not available in your desired region or you require specific, advanced features. There are other guardrails open-source implementations out there you might want to consider.

For the majority of users, Guardrails for Amazon Bedrock will likely be the preferred choice for implementing safeguards in their applications, primarily due to ease of use and no-code implementation.

## Contents

- [Guardrails for Amazon Bedrock Samples](guardrails-for-amazon-bedrock-samples) - Examples of Building, Updating, Versioning and Testing your Guardrails
- [NeMo Guardrails](nemo-guardrails) - using an open-source toolkit for easily adding programmable guardrails to Amazon Bedrock

## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
