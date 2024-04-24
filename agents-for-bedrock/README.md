# Agents for Amazon Bedrock

[Agents for Amazon Bedrock](https://aws.amazon.com/bedrock/agents/) helps you accelerating the development of GenAI application by orchestrating multistep tasks. Agents uses the reasoning capability of foundation models (FMs) to break down user-requested tasks into multiple steps. Agents for Amazon Bedrock can perform the following tasks:
- Breakdown user requests into multiple smaller steps
- Collect additional information from a user through natural conversation
- Decide which APIs to call and provide the necessary parameters for calling the APIs
- Take actions to fulfill a customer's request calling provided APIs
- Augment performance and accuracy by querying integrated Knowledge Bases


An agent consists of the following components:

1. **Foundation model** – You choose a foundation model that the agent invokes to interpret user input and subsequent prompts in its orchestration process, and to generate responses and follow-up steps in its process.
2. **Instructions** – You write up instructions that describe what the agent is designed to do
a. With **Advanced Prompts**, you can further customize instructions for the agent at every step of orchestration
b. With customized **Lambda Parser** functions you can parse the output of each step.
3. (Optional) **Action groups** – You define the actions that the agent should carry out by providing the available APIs with
a. **Function Definition** where you specify functions and define parameters as JSON objects that will be associated to the action group invocation or
b. **API Schema** file that defines the APIs that the agent can invoke to carry out its tasks resources.

Additionally, you can define a Lambda function to execute the API calls with the the selected parameters
3. (Optional) **Knowledge bases** – Associate knowledge bases with an agent to allow it to query the knowledge base for extra context to augment response generation and input into steps of the orchestration process.


## Contents

This repository contains examples and use-cases to get you started with Agents for Amazon Bedrock and its functionalities. It is organized in the following folders:

- **Use Cases**: examples of Agents in the industry, including:
a. [Retail Agent with Bedrock Agents](agentsforbedrock-retailagent) - An agent designed to help with retail transactions
b. [Financial Services Agent for Insurance Claims handling] - Agent desided to help insurance employees with claims transactions
c. [Text to SQL Agent] - Agent designed to generate and execute SQL queries using Natural Language
d. [Customer Management Agent] - Agent designed to help customer support employees 
e. [HR Vacation Booking Agent] - Agent to book vacations for employees

- **Features examples**: example of how to build specific Agent's features
a. [Integrate Knowledge Base] - Creating an Agent with a Knowledge Base integration
b. [Action Groups with Return of Control] - Creating an Action Group without lambda function integration
c. [Action Groups with Function Definition] - Creating an Action Group with a function definition in JSON format
d. [Action Groups with API Schema] - Creating an Action Group with an OpenAPI schema file
c. [Creating agents with AWS CloudFormation] - Creating Agents using AWS CloudFormation templates


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
