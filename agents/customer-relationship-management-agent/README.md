# Customer relationship management (CRM) Bedrock Agent

## Authors:
Sawyer Hirt @sawyehir, Zeek Granston @zeekg, Eashan Kaushik @eashank

## Reviewer:
TODO: 

# Introduction
The Customer Relationship Management (CRM) Bedrock Agent is a conversational AI solution that utilizes natural language processing to facilitate interactions with customer data and management of customer relationships. This agent bridges the gap between complex customer information systems and user-friendly communication by allowing users to retrieve insights, update tasks, and receive recommendations using natural language prompts.

Built with Agents for Amazon Bedrock and leveraging AWS services like Amazon DynamoDB and AWS Lambda, the CRM Bedrock Agent integrates AI capabilities with an intuitive chat interface. By connecting with AWS services and the Jira API, the agent streamlines customer relationship management processes, enhances customer experiences, and improves efficiency.

Through natural language interaction, the agent provides access to customer information, enabling users to retrieve company overviews, fetch recent interactions, update Jira tasks, and receive personalized recommendations based on customer preferences. This functionality caters to the needs of modern customer-centric businesses, making data-driven decision-making more accessible and user-friendly.

# Architecture

![architecture](/architecture.png)

## Customer Use Case

A manufacturing company is facing challenges in managing customer relationships effectively. With a diverse customer base and complex data spread across multiple systems, the company struggles to keep track of customer interactions, preferences, and open tasks. This situation often leads to missed opportunities, delayed responses, and a suboptimal customer experience.

In an effort to streamline customer relationship management and enhance customer satisfaction, the company has decided to implement the Customer Relationship Management (CRM) Bedrock Agent, a conversational AI solution that leverages natural language processing and integrates with existing systems.

The CRM Bedrock Agent acts as a bridge between the company's customer data, task management tools, and their sales and support teams. By allowing users to interact with customer information and manage tasks through natural language prompts, the agent provides a user-friendly interface that simplifies data access and decision-making.

## Jira Integration (Optional)

The agent can integrate with Jira for task management. Provide the necessary Jira configuration parameters during the CloudFormation deployment. To get more information about Jira developer API refer the [documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/#about). 

## Deployment

Upload the [codepipleline.yaml](/codepipleline.yaml) file to AWS CloudFormation. This template sets up a CodePipeline to build and deploy the Streamlit application to an ECS Fargate service. It also creates the necessary infrastructure (VPC, subnets, etc.) and integrates with Jira (optional).

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
> To get more information about deployment of the streamlit application refer [this](https://github.com/aws-samples/aws-streamlit-deploy-cicd) aws-samples.

## Amazon Bedrock Agent API Paths and Actions

The agent supports the following API paths and actions:

- `GET /recent-interactions/{customerId}/{count}`: Retrieve the latest interactions for a given customer ID and count.
- `GET /company-overview/{customerId}`: Fetch the company overview details for a given customer ID.
- `GET /preferences/{customerId}`: Retrieve the meeting preferences (type, time, day) for a given customer ID.
- `GET /open-jira-tasks/{projectID}`: Fetch a list of open Jira issues based on project key.
- `PUT /update-jira-task/{issueKey}`: Update the timeline of a Jira issues.

## Sample Data

The customer and interactions DynamoDB tables are filled with mock data.

### [Customer data](src/data/customer.json)

| customer_id | company_name            | overview                  | meetingType | dayOfWeek | timeOfDay | email         |
|--------------|--------------------------|----------------------------|--------------|------------|------------|----------------|
| C-abc123     | Acme Inc                 | Acme Inc is a leading... | InPerson     | Tuesday    | Afternoon | abc@kmal.com   |
| C-def456     | 123 Designs              | 123 Designs is a...      | Online       | Wednesday  | Morning   | abc@kmal.com   |
| C-ghi789     | Builders R Us            | Builders R Us supplies... | InPerson     | Thursday   | Afternoon | abc@kmal.com   |
| C-jkl01112   | Modern Home Furnishings  | Modern Home Furnishings  | Online       | Friday     | Morning   | abc@kmal.com   |
| C-mno131415  | Web Works                | Web Works is a...         | InPerson     | Monday     | Evening   | abc@kmal.com   |

## [Interactions data](src/data/interactions.json)

| customer_id | date | notes |
|-|-|-|
| C-abc123 | 2023-02-14T14:30:00Z | Discussed current projects and timeline for new website launch. Provided feedback on design mockups. |
| C-abc123 | 2023-02-21T10:00:00Z | Reviewed final website design and content, provided approval to proceed with development. Answered additional questions about branding guidelines. |
| C-abc123 | 2023-02-28T15:00:00Z | Website launch check-in call. Discussed analytics setup and initial traffic results. Scheduled future call to review SEO optimization opportunities. |
| C-abc123 | 2023-03-07T16:00:00Z | Follow-up call to review website traffic and SEO performance. Analyzed site metrics and identified areas for improvement. |
| ........ | .................... | ........................................ |
| C-mno131415 | 2023-03-27T14:45:00Z | Follow-up call to review website traffic and SEO performance. Analyzed site metrics and identified areas for improvement.|

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
