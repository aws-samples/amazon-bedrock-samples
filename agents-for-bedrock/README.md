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
   1. (Optional) With **Advanced Prompts** you can further customize instructions for the agent at every step of orchestration
   1. With customized **Lambda Parser** functions you can parse the output of each orchestration step

3. (Optional) **Action groups** – You define the actions that the agent should carry out by providing the available APIs with
   1. **Function Definition** where you specify functions and define parameters as JSON objects that will be associated to the action group invocation or,
   1. **API Schema** file that defines the APIs that the agent can invoke to carry out its tasks resources

   Additionally, you can define a Lambda function to execute API calls with the selected parameters

4. (Optional) **Knowledge bases** – Associate knowledge bases with an agent to allow it to retrieve context to augment response generation and input into orchestration steps


## Contents

This repository contains examples and use-cases to get you started with Agents for Amazon Bedrock and its capabilities. It is organized in the following folders:

- **Use case examples**: examples of Agents in specific use cases, including:
1. [Retail Agent with Bedrock Agents](./use-case-examples/agentsforbedrock-retailagent/README.md) - Agent designed to help with retail transactions
1. [Insurance Claim Lifecycle Automation Agent](./use-case-examples/insurance-claim-lifecycle-automation/README.md) - Agent desided to help insurance employees working with claims
1. [Text to SQL Agent](./use-case-examples/text-2-sql-agent/README.md) - Agent designed to generate and execute SQL queries using natural language
1. [Text to SQL  Agent CDK Enhanced](./use-case-examples/text-2-sql-agent-cdk-enhanced/Readme.md) - Agent designed to generate and execute SQL queries using natural language. This repository enhances the original Text to SQL Bedrock Agent with improvment on: using CDK, works with any dataset, wroks with super large answers.
1. [Customer Relationship Management Agent](./use-case-examples/customer-relationship-management-agent/README.md) - Agent designed to help sales employees work with their customers 
1. [HR Vacation Agent](./use-case-examples/hr-assistant/README.md) - Agent to manage employee vacation time
1. [Cost Explorer Agent](./use-case-examples/cost-explorer-agent/README.md) - Agent designed to help users understand and optimize their AWS costs

- **Feature examples**: examples of how to use specific features of Agents for Bedrock
1. [Create Agent with Function Definition](features-examples/01-create-agent-with-function-definition): Example of how to create an HR assistant agent defining the Action Group function and parameters as JSON object that is associated with the Action Group invocation. It connects with an [AWS Lambda](https://aws.amazon.com/lambda/) function to execute the actions
1. [Create Agent with API Schema](features-examples/02-create-agent-with-api-schema): Example of how to create an Insurance Claim's handler agent using an API schema for the functions and parameters definition. The API schema follows the [OpenAPI Specificiation](https://swagger.io/specification/) format and connects with an AWS Lambda function for the actions exection.
1. [Create Agent with Return of Control](features-examples/03-create-agent-with-return-of-control): Example of how to create an HR assistant agent defining the Action Group function and parameters as JSON object that is associated with the Action Group invocation. It skips the AWS Lambda function definition to return the control to the user's application.
1. [Create Agent with a Single Knowledge](features-examples/04-create-agent-with-single-knowledge-base): Example of how to create a restaurant assistant agent that connects with a single [Knowledge Base for Amazon Bedrock](https://aws.amazon.com/bedrock/knowledge-bases/) to find informations on the menus for adults and children.
1. [Create Agent with Knowledge Base and Action Group](features-examples/05-create-agent-with-knowledge-base-and-action-group): Example of how to create extend the Insurance Claim's handler to connect to a Knowledge Base and get the requirements for missing documents. 
1. [Using Agent's Prompt and Session Parameters](features-examples/06-prompt-and-session-parameters): Example of how to pass prompt and session parameters to an agent invocation in order to extend the agent's knowledge.
1. [Changing Agent's Advanced Prompts and creating custom Lambda Parsers](features-examples/07-advanced-prompts-and-custom-parsers): Example of how to change an Agent's advanced prompt and how to create a custom lambda parser for advanced agents use cases
1. [Securing Bedrock Agents using session attributes and Amazon Verified Permissions](features-examples/09-fine-grained-access-permissions): Example of how to use session parameters and use Amazon Verified Permissions to implement fine grained permissions

## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
