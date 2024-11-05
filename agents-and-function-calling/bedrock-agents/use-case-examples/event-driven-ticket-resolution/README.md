# Automating technical support and workflows with Amazon Bedrock Agents

## Authors:
Chris Pecora @chpecora, Ishan Singh @ishansin, Eashan Kaushik @eashanks

## Introduction

Generative AI applications can create powerful and innovative user experiences by leveraging natural language processing (NLP) to enable direct interaction with users. However, intelligent agents, with their ability to not only engage in conversational interactions but also intelligently create action plans, utilize tools to interact with external components, accomplish tasks on behalf of the user, and make decisions based on the results of those interactions, offer a greater level of depth and capability to applications. By employing agentic applications, Large Language Models (LLMs) can interact with live systems to fulfill customer requests across diverse applications. In addition to the potential benefits agents bring to end-user experiences, they can also be leveraged to interact with external systems, make decisions, and accomplish tasks for backend processing workflows that are not directly user-facing, unlike conventional chatbots.

Consider a ticket processing platform that processes support tickets submitted by users. Traditionally, this process would involve multiple steps and human intervention to properly understand and assign the tickets to the appropriate resolver groups. However, by leveraging intelligent agents, we can streamline this process by enabling the agents to understand and automatically assign tickets to the correct resolver groups, and even resolve tickets autonomously with the appropriate information. This approach not only enhances efficiency but also improves the overall experience and time-to-resolution for the ticket requester.

To complement this design, an event-driven architecture can be employed, triggering status notifications to the ticket requester and assigned resolvers. Furt
hermore, it can also trigger the agent itself and other components that support the agentic workflow. This event-driven approach enables seamless communication and coordination between the various components involved in the ticket processing pipeline, ensuring a smooth and efficient end-to-end experience.

By combining intelligent agents with an event-driven architecture, organizations can achieve significant improvements in ticket processing efficiency, response times, and overall customer satisfaction, while reducing the operational overhead associated with manual interventions.

Let's delve into the architecture of the solution we will be building, focusing on the technical aspects and components involved.

 ## Architecture


 ![Event-driven Ticket Agent Architecture](/agents-and-function-calling/bedrock-agents/use-case-examples/event-driven-ticket-resolution/images/architecture-event-driven.png)

The solution is composed of several components and services including:

 1. [Amazon Bedrock Agent](https://aws.amazon.com/bedrock/agents/)
 2. [AWS Lambda functions](https://aws.amazon.com/pm/lambda/)
 3. [Amazon DynamoDB](https://aws.amazon.com/dynamodb/)
 4. [Amazon Bedrock Knowledge Base](https://aws.amazon.com/bedrock/knowledge-bases/)
 5. [Amazon Simple Notification Service](https://aws.amazon.com/pm/sns) (SNS)
 6. [Amazon DynamoDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
 
The solution incorporates several pre-defined DynamoDB tables that serve as targets for the action groups for the agent:

1. **Environment Table**: This table holds the environment information.
2. **User Access Table**: This table stores information about the access privileges granted to each employees.
3. **User Table**: This table contains information about employee and their respective managers.
4. **Ticket Table**: This table holds data related to all the tickets submitted by employees and modified by the agent.

These DynamoDB tables play a crucial role in the solution's architecture, acting as data repositories for various entities and enabling the agent to interact with and manipulate the relevant information as required.

The workflow is initiated upon receiving a ticket submission from an employee. The submitted information is written to the **Ticket Table** in Amazon DynamoDB. This table change triggers an event via Amazon DynamoDB Streams, which is processed by a Lambda function. The Lambda function invokes the Amazon Bedrock Agent to process the ticket, performing reasoning and modifying items in the DynamoDB tables as required. Subsequently, the ticket update is notified to the user through Amazon Simple Notification Service (SNS).

The Knowledge Base implemented will provide relevant context that the agent can utilize to understand the various ticket resolution protocols, which may change over time. In this solution, we will ingest a pre-written document containing these protocols, which can be searched over during the agent's knowledge base retrieval step.

The architecture leverages Amazon DynamoDB Streams for event-driven processing, Lambda functions for serverless computation, and Amazon SNS for notification delivery. The Knowledge Base component plays a crucial role in providing the agent with the necessary context and protocols for effective ticket resolution.

## Prerequisites

> [!CAUTION]
> Running this workshop in your own environment will incur costs. Make sure to delete the AWS Cloudformation stacks created during this section.

As you are running the workshop in your own environment, you will incur costs for the resources you launch and API calls you make. Examples include Bedrock costs including Agents for Amazon Bedrock and Knowledge Bases. Costs vary based on which model you select, the amount of storage you use and more. You may also incur costs if you use Amazon SageMaker Studio. We recommend that you check the official pricing pages and monitor costs.

We recommend that you shut down all resources that you no longer need, when you have completed the workshop. If you are not sure about which resources you have launched in a particular notebook, then please jump to the end of the notebook for cleanup instructions.

### I. Create InfraStructure

Click the following button to deploy AWS resources via CloudFormation stack:

> [!WARNING]  
> Make sure you are in us-west-2 region.


|   Region   | codepipeline.yaml |
| ---------- | ----------------- |
| us-west-2  | [![launch-stack](/agents-and-function-calling/bedrock-agents/use-case-examples/event-driven-ticket-resolution/images/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=ticket-agent-infra&templateURL=https://ws-assets-prod-iad-r-pdx-f3b3f9f1a7d6a3d0.s3.us-west-2.amazonaws.com/1f096fe9-e179-4a2d-812f-d02c0b884e82/infrastructure-stack.yaml)|


> [!IMPORTANT]  
> This CloudFormation stack is designed to deploy the necessary infrastructure for an application that manages users, environments, user access, and tickets. Here's a breakdown of the resources created by this stack:
>
> 1. **LogsPolicy**: This is an AWS IAM Managed Policy that grants permissions to create and manage CloudWatch log groups, log streams, and log events. This policy is used by other resources in the stack that require logging capabilities.
>
> 2. **DynamoDB Tables**:
>   - **UserDynamoDBTable**: This DynamoDB table stores user information with the `employeeId` as the partition key.
>   - **EnvironmentDynamoDBTable**: This table stores environment information with the `environmentId` as the partition key.
>   - **UserAccessDynamoDBTable**: This table stores user access information with a composite key consisting of `employeeId` (partition key) and `environmentId` (sort key).
>   - **TicketDynamoDBTable**: This table stores ticket information with a composite key consisting of `ticketId` (partition key) and `employeeId` (sort key). It also has a DynamoDB stream enabled to capture data changes.
>
> 3. **DynamoDB Streams**:
>   - **TicketDynamoDBStream**: This is an AWS Lambda event source mapping that captures changes (inserts and updates) in the `TicketDynamoDBTable` and invokes the `ProcessTicketDynamoDBStreamFunction` Lambda function.
>   - **ProcessTicketDynamoDBStreamFunction**: This Lambda function is triggered by the `TicketDynamoDBStream`. It is designed to handle events from the stream, such as invoking an agent or sending notifications via Amazon SNS, depending on the type of event (insert or modify).
>
>4. **PutTicketDynamoDBFunction**: This Lambda function is responsible for inserting new ticket items into the `TicketDynamoDBTable`.
>
>5. **InitDynamoDBDataFunction**: This Lambda function is a custom resource that initializes the DynamoDB tables with sample data during the stack creation process.
>
>6. **Log Groups**: CloudWatch Log Groups are created for the `ProcessTicketDynamoDBStreamFunction` and `PutTicketDynamoDBFunction` Lambda functions to store their execution logs.
>
>The stack also includes IAM roles with appropriate permissions for the Lambda functions to interact with DynamoDB tables, CloudWatch Logs, and other necessary services.

### II. Model Access

First, log into your AWS account, go to the Amazon Bedrock console and click on **Model access**:

![1-model-access](/agents-and-function-calling/bedrock-agents/use-case-examples/event-driven-ticket-resolution/images/Prerequisites/01-model-access.png)

- Amazon
    * Titan Text Embeddings V2
- Anthropic
    * Anthropic Claude 3.5 Sonnet
    * Anthropic Claude 3 Sonnet

![2-model-access](/agents-and-function-calling/bedrock-agents/use-case-examples/event-driven-ticket-resolution/images/Prerequisites/02-model-access.png)


### III. Follow the below steps to launch the SageMaker Notebook Instance

1. Click on the **AWS Console** button, search for **SageMaker**, and then navigate to your SageMaker Console.
2. On the left panel, under **Applications and IDEs** click on **Notebooks**. 

![3-notebook-access](/agents-and-function-calling/bedrock-agents/use-case-examples/event-driven-ticket-resolution/images/Prerequisites/03-notebook-access.png)

3. Follow the steps on [Create an Amazon SageMaker notebook instance](https://docs.aws.amazon.com/sagemaker/latest/dg/howitworks-create-ws.html) to setup your environment, name the instance **agent-notebook-instance**.
4. Once created, click **Open JupyterLab**.

![4-lab-access](/agents-and-function-calling/bedrock-agents/use-case-examples/event-driven-ticket-resolution/images/Prerequisites/04-lab-access.png)


5. In the new Launcher, click on terminal and run the following commands: 

```
cd SageMaker/
git clone automating-technical-support-and-workflows-with-amazon-bedrock-agents
```


## Laying the groundwork: Collecting ground truth data

Developing a successful conversational agent or any AI system heavily relies on having high-quality reference data that accurately represents real-world scenarios. Before embarking on the development process, it is crucial to curate a comprehensive set of ground truth interactions or conversations. This dataset serves as a benchmark for evaluating the agent's expected behavior, including its integration with existing APIs, knowledge bases, and safeguards.

The ground truth data enables thorough testing, performance evaluation, and identification of edge cases or potential pitfalls. To build a robust dataset, it is essential to gather diverse examples covering various user intents and scenarios, ranging from simple to complex interactions. The dataset should encompass both the input and the desired output for each interaction.

Regularly updating and expanding the dataset is crucial as more insights into user behavior are gained. While grounding the data in actual customer interactions to reflect real-world use cases, it is imperative to de-identify and anonymize the data to protect privacy and comply with regulations.

| User Query              | Session Attributes | Session prompt Attributes | Expected Response | API, Knowledge Bases and Guardrails invoked |
| :---------------------- | :----------------: | :-----------------------: | :---------------- | :-----------------------------------------: |
| <pre> Please either auto-resolve the ticket or assign it to environment owner:<br>`<ticket>`<br> **Title**: Request Environment Access<br>**EnvironmentId**: 1<br>**Buisness Justification**: Need to test new features on Quicksight Dashboard<br>**Access duration**: 8 days<br>**Access Type**: Read<br>`</ticket>`<br>Ensure to resolve the ticket by calling TicketAPI.<br></pre> |   employee_id = 111 | None | **assignStatus**: auto-resolved <br> **communication**: Access granted automatically as per company policy. Employee's manager is the environment owner, access duration is less than 30 days, and access type is Read. | checkEmployeeAccess &#8594; KNOWLEDGE_BASE &#8594; getEmployeeManager &#8594; getEnvironmentOwner &#8594; giveAccess &#8594; autoResolveTicket |
| <pre> Please either auto-resolve the ticket or assign it to environment owner:<br>`<ticket>`<br> **Title**: Request Environment Access<br>**EnvironmentId**: 1<br>**Buisness Justification**: Need to test new features on Quicksight Dashboard<br>**Access duration**: 8 days<br>**Access Type**: Read<br>`</ticket>`<br>Ensure to resolve the ticket by calling TicketAPI.<br></pre> |   employee_id = 111 | None | * *In this case we are assuming employee 111 already have access to environmentId 1* <br> **assignStatus**: auto-resolved <br> **communication**: The employee already has access to Environment 1. The requested access duration is 8 days, and the access type is Read. No further action is required. | checkEmployeeAccess &#8594; autoResolveTicket |
| <pre> Please either auto-resolve the ticket or assign it to environment owner:<br>`<ticket>`<br>**Title**: Request Environment Access<br>**EnvironmentId**: 4<br>**Buisness Justification**: Need to view model results for sales forcast Q4<br>**Access duration**: 24 days<br>**Access Type**: Read<br>`</ticket>`<br>Ensure to resolve the ticket by calling TicketAPI.<br></pre> |   employee_id = 121 | None | **assignStatus**: assigned to @susi <br> **communication**: Please review the access request for Environment 4. The employee is requesting read access for 24 days to test new features on Quicksight Dashboard. As per company policy, please verify if the request is appropriate and grant access if approved. Remember to follow best practices for managing environment permissions, such as setting an expiration date for the access and ensuring the principle of least privilege is applied. | checkEmployeeAccess &#8594; KNOWLEDGE_BASE &#8594; getEmployeeManager &#8594;  getEnvironmentOwner &#8594; assignTicketToEnvironmentOwner |
| <pre> Please either auto-resolve the ticket or assign it to environment owner:<br>`<ticket>`<br>**Title**: Request Environment Access<br>**EnvironmentId**: 1<br>**Buisness Justification**: Need to test new features on Quicksight Dashboard<br>**Access duration**: 24 days<br>**Access Type**: Read<br>`</ticket>`<br>Ensure to resolve the ticket by calling TicketAPI.<br></pre> |   employee_id = 121 | None | **assignStatus**: auto-resolved <br> **communication**: Access granted automatically as per company policy. Employee's manager is the environment owner, requested duration is less than 30 days, and access type is Read. | checkEmployeeAccess &#8594; KNOWLEDGE_BASE &#8594; getEmployeeManager &#8594; getEnvironmentOwner &#8594; giveAccess &#8594; autoResolveTicket |
| <pre> Please either auto-resolve the ticket or assign it to environment owner:<br>`<ticket>`<br>**Title**: Request Environment Access<br>**EnvironmentId**: 4 <br>**Buisness Justification**: Building ML model for damage detection <br>**Access duration**: 24 days<br>**Access Type**: Admin <br>`</ticket>`<br>Ensure to resolve the ticket by calling TicketAPI.<br></pre> |   employee_id = 141 | None | **assignStatus**: assigned to @kirk <br> **communication**: : Please review the access request for Environment 4. The employee is requesting admin access for 24 days to build new ML model for damage detection. As per company policy, please verify if the request is appropriate and grant access if approved. Remember to follow best practices for managing environment permissions, such as setting an expiration date for the access and ensuring the principle of least privilege is applied. | checkEmployeeAccess &#8594; KNOWLEDGE_BASE &#8594; getEnvironmentOwner &#8594; assignTicketToEnvironmentOwner |
| <pre> Please either auto-resolve the ticket or assign it to environment owner:<br>`<ticket>`<br>**Title**: Request Environment Access<br>**EnvironmentId**: 2 <br>**Buisness Justification**: Need developer access to change button color <br>**Access duration**: 90 days<br>**Access Type**: Developer <br>`</ticket>`<br>Ensure to resolve the ticket by calling TicketAPI.<br></pre> |   employee_id = 131 | None | **assignStatus**: assigned to @sam <br> **communication**: : Please review the access request for Environment 2. The employee is requesting developer access for 90 days to change button color. As per company policy, please verify if the request is appropriate and grant access if approved. Remember to follow best practices for managing environment permissions, such as setting an expiration date for the access and ensuring the principle of least privilege is applied. | checkEmployeeAccess &#8594; KNOWLEDGE_BASE &#8594; getEnvironmentOwner &#8594; assignTicketToEnvironmentOwner |

## Clean Up
- Make sure to run the [cleanup.ipynb](/event-driven-ticket-resolution/CleanUp.ipynb) notebook.
- Open the [CloudFormation console](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks).
- Select the stack `infrastructure-stack.yaml` you created then click **Delete** twice. Wait for the stack to be deleted.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
