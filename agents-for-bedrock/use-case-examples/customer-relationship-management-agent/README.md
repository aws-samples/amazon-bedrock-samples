# Customer relationship management (CRM) Bedrock Agent

## Authors:
Sawyer Hirt @sawyehir, Zeek Granston @zeekg, Eashan Kaushik @eashank

## Reviewer:
Maira Ladeira Tanke @mttanke

# Introduction
The Customer Relationship Management (CRM) Bedrock Agent is a conversational AI solution that utilizes natural language processing to facilitate interactions with customer data and management of customer relationships. This agent bridges the gap between complex customer information systems and user-friendly communication by allowing users to retrieve insights, update tasks, and receive recommendations using natural language prompts.

Built with Agents for Amazon Bedrock and leveraging AWS services like Amazon DynamoDB and AWS Lambda, the CRM Bedrock Agent integrates AI capabilities with an intuitive chat interface. By connecting with AWS services and the Jira API, the agent streamlines customer relationship management processes, enhances customer experiences, and improves efficiency.

Through natural language interaction, the agent provides access to customer information, enabling users to retrieve company overviews, fetch recent interactions, update Jira tasks, and receive personalized recommendations based on customer preferences. This functionality caters to the needs of modern customer-centric businesses, making data-driven decision-making more accessible and user-friendly.

# Architecture

![architecture](/agents-for-bedrock/use-case-examples/customer-relationship-management-agent/architecture.png)

## Customer Use Case

AnyCompany Manufacturing Inc. is a producer of industrial equipment and machinery. With a vast customer base spanning multiple continents, the company constantly struggles to maintain effective customer relationships. Customer data is scattered across various systems, making it challenging to track interactions, preferences, and open tasks. This often results in missed opportunities, delayed responses, and suboptimal customer experiences, ultimately hindering business growth.

A seasoned project manager at AnyCompany, is responsible for overseeing the company's software solutions. Recently, the sales team expressed frustration with the cumbersome process of accessing customer information and updating related tasks during customer interactions. This sales team frequently engages with existing and potential clients, discussing projects, gathering requirements, and providing progress updates. However, the lack of a centralized system made it difficult for them to access relevant customer data and manage follow-up actions efficiently.

To address these challenges, AnyCompany decided to implement the Customer Relationship Management (CRM) Agent, a conversational AI solution that leverages natural language processing and integrates with existing systems. The CRM Agent acts as a bridge between the company's customer data, task management tools (like Jira), and their sales and support teams. By allowing users to interact with customer information and manage tasks through natural language prompts, the agent provides a user-friendly interface that simplifies data access and updates Jira as needed for issue and project tracking.

With the CRM Agent, the team can leverage the in-built functionality combining these disparate resources. The sales team can retrieve customer overviews, recent interactions, and communication preferences from DynamoDB tables using natural language prompts. They can also fetch open Jira tasks for a project and update task timelines by interacting with the agent, which communicates via the Jira API. This streamlined process allows the sales team to efficiently access customer data and manage follow-up actions within their project management system, enhancing productivity and customer interactions.

## Jira Integration (Optional)

The agent can integrate with Jira for task management. Provide the necessary Jira configuration parameters during the CloudFormation deployment. To get more information about Jira developer API refer the [documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/#about). 

## Deployment

> [!NOTE]  
> This repository provides base code for Streamlit application's and is not production ready. It is your responsibility as a developer to test and vet the application according to your security guidlines.

Upload the [codepipleline.yaml](/agents-for-bedrock/use-case-examples/customer-relationship-management-agent/codepipeline.yaml) file to AWS CloudFormation. This template sets up a CodePipeline to build and deploy the Streamlit application to an ECS Fargate service. It also creates the necessary infrastructure (VPC, subnets, etc.) and integrates with Jira (optional).

|   Region   | codepipeline.yaml |
| ---------- | ----------------- |
| us-east-1  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=CRMBot&templateURL=https://ws-assets-prod-iad-r-iad-ed304a55c2ca1aee.s3.us-east-1.amazonaws.com/0a9f7588-a2c4-4484-b051-6658ce32605c/CRM/codepipeline.yaml)|
| us-west-2  | [![launch-stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=CRMBot&templateURL=https://ws-assets-prod-iad-r-pdx-f3b3f9f1a7d6a3d0.s3.us-west-2.amazonaws.com/0a9f7588-a2c4-4484-b051-6658ce32605c/CRM/codepipeline.yaml)|


Follow these steps to implement the CRM Agent in your environment:

1. Deploy the `codepipeline.yaml` CloudFormation template. The following CloudFormation parameters are provided:
   - GitURL: Initial repository for CRM Agent - leave unchanged.
   - EnvironmentName: Unique name to distinguish different CRM applications in the same AWS account- min length 1 and max length 4.
   - DeployVPCInfrastructure: Select `true` if this is your first deployment of CRM application in your AWS account, else `false`.
   - JiraURL: URL of the Jira without `https://`. 
   - JiraAPIToken: API Token for Jira API.
   - JiraUsername: Username for Jira API.
     
> [!IMPORTANT]
> `JiraURL`, `JiraAPIToken`, and `JiraUsername` needs to be left unchanged if you are not configuring Jira for this application. 

2. AWS CodePipeline will automatically build and deploy the application to an ECS Fargate service. Wait for AWS CodePipeline to deploy `<StackName>deploy<EnvironmentName>` CloudFormation stack.
3. Get the CloudFront URL from the Output of the stack `<StackName>deploy<EnvironmentName>`. Paste it in the browser to view CRM app. Invoke the agent by interacting with the chat interface.

> [!IMPORTANT]
> Use the supported prompts as shown [below](#supported-prompts).

> [!NOTE]  
> To get more information about deployment of the streamlit application refer [aws-streamlit-deploy-cicd](https://github.com/aws-samples/aws-streamlit-deploy-cicd) aws-samples.

4. Access to Amazon Bedrock foundation models isn't granted by default. In order to gain access to a foundation model follow [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html). 

## Amazon Bedrock Agent API Paths and Actions

The agent supports the following API paths and actions:

- `GET /recent-interactions/{customerId}/{count}`: Retrieve the latest interactions for a given customer ID and count.
- `GET /company-overview/{customerId}`: Fetch the company overview details for a given customer ID.
- `GET /preferences/{customerId}`: Retrieve the meeting preferences (type, time, day) for a given customer ID.
- `GET /open-jira-tasks/{projectID}`: Fetch a list of open Jira issues based on project key.
- `PUT /update-jira-task/{issueKey}`: Update the timeline of a Jira issues.

## Sample Data

The customer and interactions DynamoDB tables are filled with mock data.

### [Customer data](/agents/customer-relationship-management-agent/src/data/customer.json)

![customer](/agents-for-bedrock/use-case-examples/customer-relationship-management-agent/src/data/customers.png)


## [Interactions data](/agents/customer-relationship-management-agent/src/data/interactions.json)

![interactions](/agents-for-bedrock/use-case-examples/customer-relationship-management-agent/src/data/interactions.png)

## Supported Prompts

The agent can be invoked using the following prompts:

- Provide a brief overview of customer [CUSTOMER_ID].
- List the last [COUNT] recent interactions for customer [CUSTOMER_ID].
- What communication method does customer [CUSTOMER_ID] prefer?
- Recommend optimal time and contact channel to reach out to [CUSTOMER_ID] based on their preferences and our last interaction.

The following prompts only work if you have configured Jira CloudForation parameters with valid values.

- What are the open Jira Tasks for project id [PROJECT_KEY]?
- Please update Jira Task [IssueKey] to [DURATION] weeks out.

Replace [CUSTOMER_ID], [COUNT], [PROJECT_KEY], [IssueKey] and [DURATION] with the appropriate values in the prompts.

## Clean Up
- Open the [CloudFormation console](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks).
- Select the stack `codepipeline.yaml` you created then click **Delete** twice. Wait for the stack to be deleted.
- Delete the nested stack `<StackName>-Infra-<StackId>` created by `codepipeline.yaml`. Please ensure that you refrain from deleting this stack if there are any additional web deployments utilizing this repository within the specified region of your current work environment.
- Delete the role `StreamlitCfnRole-<EnvironmentName>` manually.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
