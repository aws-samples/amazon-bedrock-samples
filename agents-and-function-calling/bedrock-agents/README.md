# Amazon Bedrock Agents

[Amazon Bedrock Agents](https://aws.amazon.com/bedrock/agents/) helps you accelerate the development of GenAI applications by orchestrating multistep tasks. Agents uses the reasoning capability of foundation models (FMs) to break down user-requested tasks into  steps. Amazon Bedrock Agents can perform the following tasks:
- Breakdown user requests into multiple smaller steps
- Collect additional information from a user through natural conversation
- Decide which APIs to call and provide the necessary parameters for calling the APIs
- Take actions to fulfill a customer's request calling provided APIs
- Augment performance and accuracy by querying integrated Knowledge Bases


An agent consists of the following components:

1. **Foundation model** – You choose a foundation model that the agent invokes to interpret user input and subsequent prompts in its orchestration process, and to generate responses and follow-up steps in its process
2. **Instructions** – You author instructions that describe what the agent is designed to do
   1. (Optional) With **Advanced Prompts** you can further customize instructions for the agent at every step of orchestration
   1. With customized **Lambda Parser** functions you can parse the output of each orchestration step

3. (Optional) **Action groups** – You define the actions that the agent should carry out by providing the available APIs with
   1. **Function Definition** where you specify functions and define parameters as JSON objects that will be associated to the action group invocation or,
   1. **API Schema** file that defines the APIs that the agent can invoke to carry out its tasks resources

   Additionally, you can define a Lambda function to execute API calls with the selected parameters

4. (Optional) **Knowledge bases** – Associate knowledge bases with an agent to allow it to retrieve context to augment response generation and input into orchestration steps


## Contents

This repository contains examples and use-cases to get you started with Amazon Bedrock Agents and its capabilities. It is organized in the following folders:
* [Feature examples](features-examples/README.md): Examples of how to use specific features of Agents for Bedrock. Those examples are feature focuses and highlight how to use the service itself.
* [Use case examples](use-case-examples/README.md): examples of Agents in specific use cases, including:
* [Amazon Bedrock Agents Blueprint templates](https://awslabs.github.io/agents-for-amazon-bedrock-blueprints/) to create reusable and scalable agents using AWS CDK
* [Test Agent](test-agent/README.md) Sample code to test your agent for latency and accuracy (based on LLM judges)


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
