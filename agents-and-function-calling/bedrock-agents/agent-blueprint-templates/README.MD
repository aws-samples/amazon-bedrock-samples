# Agent Blueprint Templates

This folder contains various CDK blueprint templates for creating Amazon Bedrock Agents, leveraging [Agent Blueprints](https://awslabs.github.io/agents-for-amazon-bedrock-blueprints/). Each template demonstrates different capabilities and use cases for building intelligent agents.

## Prerequisites

Before you begin, ensure you have the following installed:

- **AWS CLI**
- **Node.js and NPM**
- **AWS CDK**
- **TypeScript**

## Installation

### Shell Script Installation (Recommended)

The provided shell script automatically checks for and installs the necessary prerequisites, including Node.js, AWS CLI, and AWS CDK. You do not need to install these separately if you use this method. Follow these steps
1. **Clone the repository:**

    ```bash
    git clone https://github.com/aws-samples/amazon-bedrock-samples.git
    ```

2. **Navigate to the appropriate folder:**

    ```bash
    cd amazon-bedrock-samples/agents-and-function-calling-for-bedrock/agent-blueprint-templates/
    ```

3. **Run the shell script to install all dependencies:**

    ```bash
    ./blueprints.sh init
    ```

After completing these steps, you should have the Agent Blueprints package installed along with its dependencies, and your environment will be ready to use the Agent Blueprints.

> **Note:** You may still have to configure your AWS CLI. The shell script will only install the necessary dependencies. To learn about configuring AWS CLI, [click here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html).

### Manual Installation

Alternatively, you can manually install the dependencies by following these steps:

1. **AWS CLI:** Make sure you have the AWS CLI installed and configured with your credentials.

2. **Node.js and NPM:** Install the latest stable version of Node.js and NPM.

    ```bash
    # For Mac
    brew install node
    
    # For Ubuntu
    sudo apt install nodejs
    ```

3. **AWS CDK:** Install the AWS CDK globally.

    ```bash
    npm install -g aws-cdk@2.147.3
    ```

4. **TypeScript:** The Agent Blueprints are only available in TypeScript.

5. **CDK Bootstrap:** Bootstrap your AWS environment.

    ```bash
    cdk bootstrap aws://<your-account-number>/<region-to-bootstrap>
    ```

After completing either method, you should have all the necessary dependencies installed and your environment prepared to use Agent Blueprints.

### Deploy an Agent from a Template

To deploy an agent from a template using the shell script helper, follow these steps:

1. **Find and deploy agent templates using the shell script:**

    ```bash
    # List available templates
    ./blueprints.sh ls 

    # Deploy a template
    ./blueprints.sh deploy <name-of-the-example-stack> 

    # Example deployment
    ./blueprints.sh deploy 01-agent-with-function-definitions
    ```

### Script Commands

The `blueprints.sh` script provides the following commands:

- **`init`**: Install project dependencies.
- **`ls`**: List available stacks.
- **`deploy <stack>`**: Deploy a specified stack.

## Contents

- **Stacks**: This folder contains the stacks for different agent blueprints.
  - [01-agent-with-function-definitions](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/agent-blueprint-templates/lib/stacks/01-agent-with-function-definitions): Stack for creating an agent with function definitions.
  - [02-agent-with-return-of-control](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/agent-blueprint-templates/lib/stacks/02-agent-with-return-of-control): Stack for creating an agent with return of control.
  - [03-agent-with-kb-and-guardrails](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/agent-blueprint-templates/lib/stacks/03-agent-with-kb-and-guardrails): Stack for creating an agent with a knowledge base and guardrails.
  - [04-agent-with-lambda-parser](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/agent-blueprint-templates/lib/stacks/04-agent-with-lambda-parser): Stack for creating an agent with a custom Lambda parser.
  - [05-agent-with-classification-instructions](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/agent-blueprint-templates/lib/stacks/05-agent-with-classification-instructions): Stack for creating an agent with simple classification instructions.
- **bin**: This folder contains the entry point for deploying the stacks.
  - [main.ts](notion://www.notion.so/bin/main.ts): Main entry point for deploying the stacks using AWS CDK.
- **cdk.json**: Configuration file for AWS CDK.
- **package.json**: Node.js package configuration file.
- **tsconfig.json**: TypeScript configuration file.

## Available Amazon Bedrock Agents Templates

### 01. Agent with Function Definitions

This template demonstrates how to create an HR assistant agent with Action Group defined using function details. The agent can manage vacation requests, review past vacation usage, and track remaining vacation days. It connects with an [AWS Lambda](https://aws.amazon.com/lambda/) function to execute the actions. 

### 02. Agent with Return of Control

This template demonstrates how to create an HR assistant agent with Action Group that is configured with return of control, allowing the agent to return control back to the developer after invoking an action. This means that instead of immediately executing the next step within the agent, the agent sends the elicited information back to the developer's backend service. The developer can then handle the information, perform any necessary processing, and send the results back to the agent to continue the workflow without relying solely on AWS Lambda functions.


### 03. Agent with Knowledge Base and Guardrails

This template demonstrates how to create an Restaurant Assistant agent with a single [Knowledge Base for Amazon Bedrock](https://aws.amazon.com/bedrock/knowledge-bases/) and [Guardrails for Amazon Bedrock](https://aws.amazon.com/bedrock/guardrails/). The agent is designed to assist with restaurant bookings, including retrieving, creating, and deleting bookings. It accesses a knowledge base for information on menu items and employs guardrails to ensure safe and compliant interactions

### 04. Agent with Custom Lambda Parser

This template demonstrates how to create an Restaurant Assistant agent with advanced prompts and custom Lambda parser, allowing custom parsing of the raw outputs from foundation models enabling advanced use cases for the agent.

### 05. Agent with Simple Classification Instructions

This template demonstrates how to create an agent with simple classification instructions, enabling the agent to classify and handle different types of user inputs.
