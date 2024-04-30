# Agents for Amazon Bedrock

[Agents for Amazon Bedrock](https://aws.amazon.com/bedrock/agents/) helps you accelerate the development of GenAI applications by orchestrating multistep tasks. Agents uses the reasoning capability of foundation models (FMs) to break down user-requested tasks into  steps. Agents for Amazon Bedrock can perform the following tasks:
- Breakdown user requests into multiple smaller steps
- Collect additional information from a user through natural conversation
- Decide which APIs to call and provide the necessary parameters for calling the APIs
- Take actions to fulfill a customer's request calling provided APIs
- Augment performance and accuracy by querying integrated Knowledge Bases


An agent consists of the following components:

1. **Foundation model** – You choose a foundation model that the agent invokes to interpret user input and subsequent prompts in its orchestration process, and to generate responses and follow-up steps in its process
2. **Instructions** – You author instructions that describe what the agent is designed to do
a. (Optional) With **Advanced Prompts**, you can further customize instructions for the agent at every step of orchestration,
b. With customized **Lambda Parser** functions you can parse the output of each orchestration step
3. (Optional) **Action groups** – You define the actions that the agent should carry out by providing the available APIs with
a. **Function Definition** where you specify functions and define parameters as JSON objects that will be associated to the action group invocation or, 
b. **API Schema** file that defines the APIs that the agent can invoke to carry out its tasks resources

Additionally, you can define a Lambda function to execute API calls with the selected parameters
3. (Optional) **Knowledge bases** – Associate knowledge bases with an agent to allow it to retrieve context to augment response generation and input into orchestration steps


## Contents

This repository contains examples and use-cases to get you started with Agents for Amazon Bedrock and its capabilities. It is organized in the following folders:

- **Use case examples**: examples of Agents in specific use cases, including:
a. [Retail Agent with Bedrock Agents](./use-case-examples/agentsforbedrock-retailagent/README.md) - Agent designed to help with retail transactions
b. [Financial Services Agent for Insurance Claims handling] - Agent desided to help insurance employees working with claims
c. [Text to SQL Agent](./use-case-examples/text-2-sql-agent/README.md) - Agent designed to generate and execute SQL queries using natural language
d. [Customer Relationship Management Agent](./use-case-examples/customer-relationship-management-agent/README.md) - Agent designed to help sales employees work with their customers 
e. [HR Vacation Agent] - Agent to manage employee vacation time

- **Feature examples**: examples of how to use specific features of Agents for Bedrock
a. [Integrate Knowledge Base](./features-examples/04-create-agent-with-single-knowledge-base/README.md) - Creating an Agent with a Knowledge Base integration
b. [Action Groups with Return of Control](./features-examples/03-create-agent-with-return-of-control/README.md) - Creating an Action Group without lambda function integration
c. [Action Groups with Function Definition](./features-examples/01-create-agent-with-function-definition/README.md) - Creating an Action Group with a function definition in JSON format
d. [Action Groups with API Schema](./features-examples/02-create-agent-with-api-schema/README.md) - Creating an Action Group with an OpenAPI schema file
c. [Creating agents using AWS CloudFormation] - Creating Agents using AWS CloudFormation templates


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
