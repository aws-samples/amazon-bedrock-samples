# Deployment Guide
---

## Content
- [Pre-Implementation](#pre-Implementation)
- [Test Conversation](#test-conversation)
- [Deploy Streamlit Web UI for Your Agent](#deploy-streamlit-web-ui-for-your-agent)
- [Get Model Access for Titan Image Generator](#get-model-access)

## Pre-Implementation
By default, [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) uses a temporary session that it generates from your user credentials for stack operations. If you specify a service role, CloudFormation will instead use that role's credentials.

To deploy this solution, your IAM user/role or service role must have permissions to deploy the resources specified in the CloudFormation template. For more details on [AWS Identity and Access Management](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) (IAM) with CloudFormation, please refer to the [AWS CloudFormation User Guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-template.html).

You must also have [AWS Command Line Interface](https://aws.amazon.com/cli/) (CLI) installed. For instructions on installing AWS CLI, please see [Installing, updating, and uninstalling the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html).

### 1. Clone [_amazon-bedrock-samples_](https://github.com/aws-samples/amazon-bedrock-samples) Repository

1. Create a local copy of the **amazon-bedrock-samples** repository using _git clone_:

```sh
git clone https://github.com/aws-samples/amazon-bedrock-samples.git
```

#### Optional - Run Security Scan on the AWS CloudFormation Templates
To run a security scan on the AWS CloudFormation templates using [`cfn_nag`](https://github.com/stelligent/cfn_nag) (recommended), you have to install `cfn_nag`:

```sh
brew install ruby brew-gem
brew gem install cfn-nag
```

To initiate the security scan, run the following command:
```sh
# git clone https://github.com/aws-samples/amazon-bedrock-samples
# cd amazon-bedrock-samples
cfn_nag_scan --input-path agents-for-bedrock/use-case-examples/hr-assistant/cfn/hr-resources.yml
```
---

### 2. Deploy CloudFormation Stack to Emulate HR Resources 
To emulate the creation of HR resources utilized by the agent, this solution uses the [create-hr-resources.sh](../shell/create-hr-resources.sh) shell script to automate provisioning of the parameterized CloudFormation template, [hr-resources.yml](../cfn/bedrock-hr-resources.yml)

CloudFormation prepopulates stack parameters with the default values provided in the template. To provide alternative input values, you can specify parameters as environment variables that are referenced in the `ParameterKey=<ParameterKey>,ParameterValue=<Value>` pairs in the _create-customer-resources.sh_ shell script's `aws cloudformation create-stack` command. 

1. Before you run the shell script, navigate to the directory where you cloned the _amazon-bedrock-samples_ repository and modify the shell script permissions to executable:
```sh
# If not already cloned, clone the remote repository (https://github.com/aws-samples/amazon-bedrock-samples) and change working directory to shell folder:
cd amazon-bedrock-samples/agents-for-bedrock/use-case-examples/hr-assistant/shell/
chmod u+x create-hr-resources.sh
```
2. Set your CloudFormation stack name(STACK_NAME), SNS email(SNS_EMAIL) and the stack deployment region(AWS_REGION). The SNS email will be used for SNS notifications. You need to confirm SNS subscription to receive emails sent by the agent. 
```sh
export STACK_NAME=<YOUR-STACK-NAME> # Stack name must be lower case for S3 bucket naming convention
export SNS_EMAIL=<YOUR-EMPLOYEE-EMAIL> # Email used for SNS notifications. You need to confirm SNS subscription to receive emails sent by the agent.
export AWS_REGION=<YOUR-STACK-REGION> # Stack deployment region
```
3. Run the [create-hr-resources.sh](../shell/create-hr-resources.sh) shell script to deploy the emulated hr resources defined in the [hr-resources.yml](../cfn/bedrock-hr-resources.yml) CloudFormation template. These are the resources on which the agent and knowledge base will be built:

Run the following commands to deploy the resources:
```sh
source ./create-hr-resources.sh
```

4. Once the Cloudformation succeeds you will see following resources created
 - `SNSTopic` and `SNSSubscription` for the Email sending Action
 - Associated IAM policies and IAM roles such as `HRAgentRoleDefaultPolicy`, `HRAgentActionGroupLambdaRoleDefaultPolicy`, `HRAgentActionGroupLambdaRole`, `AmazonBedrockExecutionRoleForAgentsHRAgent`
 - Apart from that, we also see `BedrockHRFunction` lambda function and `BedrockCreateHrFunctionPermission` for lambda permissions.
 - Lastly, we also see the Agent created under `HRAgent`

 <p align="center">
  <img src="../imgs/01_cfn_resources.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 1: CloudFormation resources created</em></span>
</p>


---
### 3. Get Model Access for Titan Text Premier G1 & Titan Image Generator G1

We will use Titan Text Premier as the underlining core model along with one of the action API also requiring access to the Titan Image Generator model, therefore we need to request the model permission for both the models.
To request access to a model:

1. Login to AWS Console and go to "Amazon Bedrock".
2. Select Model access at the bottom of the left navigation pane in the Amazon Bedrock management console.
3. On the Model access page, select "Manage model access". 
4. Select the checkboxes next to the Titan Image Generator G1 model, Titan Text Premier G1 model.
5. Select Save changes to request access. The changes may take several minutes to take place.
6. If your request is successful, the Access status changes to Access granted.

Next, we cover how to associate a Knowledge Bases to the created Agent.

---

### 4. Knowledge Base 

Knowledge Bases for Amazon Bedrock leverage Retrieval Augmented Generation (RAG), a technique that harnesses customer data stores to enhance responses generated by foundation models. Knowledge bases allow agents to access existing customer data repositories without extensive administrator overhead. To connect a knowledge base to your data, you specify an S3 bucket as the [data source](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ingest.html). By employing knowledge bases, applications gain enriched contextual information, streamlining development through a fully-managed RAG solution. This level of abstraction accelerates time-to-market by minimizing the effort of incorporating your data into agent functionality and it optimizes cost by negating the necessity for continuous model retraining to leverage private data.

#### Knowledge Base Preparation

 Navigate to the [Amazon Bedrock > Knowledge base > Create knowledge base console](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/knowledge-bases/create-knowledge-base):

 a. Under **Provide knowledge base details**, enter a name and the following optional description, leaving all other default settings:

    Use to retrieve Company's leave and pay policy based on policy and pay documents

 b. Under **Configure data source**, enter a datasource name then choose _Browse S3_ and select the 'agent/knowledge-base-assets' folder of the data source S3 bucket you deployed in the preceding deployment step (e.g. `<ACCOUNT-ID>-<YOUR-STACK-NAME>-hr-resources/agent/knowledge-base-assets/`):

<p align="center">
    <img src="../imgs/02_kb_data_source.png"><br>
    <span style="display: block; text-align: center;"><em>Figure 2: Knowledge Base Data Source Configuration</em></span>
</p>

c. Under **Select embeddings model and configure vector store**, select _Titan Embeddings G1 - Text_ and leave the other default settings. An [OpenSearch Serverless collection](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-vector-search.html) will be created for you. This vector store is where the knowledge base pre-processing embeddings are stored and later used for semantic similarity search between queries and data source text.

d. Under **Review and create**, confirm your configuration settings then select **Create knowledge base**:

<p align="center">
  <img src="../imgs/03_kb_review.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 3: Knowledge Base Review Page</em></span>
</p>

2. Once your knowledge base is created, a green "created successfully" banner will display with the option to sync your data source. Select **Go To Data sources** and then select the datasource and click **Sync** to initiate the data source sync:

<p align="center">
  <img src="../imgs/04_kb_creation_banner.png" width="90%" height="90%"><br>
  <span style="display: block; text-align: center;"><em>Figure 4: Knowledge Base Creation Banner</em></span>
</p>

<p align="center">
  <img src="../imgs/05_kb_data_sync.png" width="90%" height="90%"><br>
  <span style="display: block; text-align: center;"><em>Figure 5: Knowledge Base Data Source Sync</em></span>
</p>

3. Navigate to the [Knowledge Bases for Amazon Bedrock console](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/knowledge-bases), select the knowledge base you just created, then note the **Knowledge base ID** under Knowledge base overview:

<p align="center">
  <img src="../imgs/06_kb_id.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 6: Knowledge Base Overview</em></span>
</p>

4. With your knowledge base still selected in the knowledge base console, select your knowledge base data source listed under **Data source**, then note the **Data source ID** under _Data source overview_:

<p align="center">
  <img src="../imgs/07_kb_ds_id.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 7: Knowledge Base Data Source Overview</em></span>
</p>

5. Once the sync is completed, you will see another green banner with showing that the sync status being completed.

❗ _Knowledge base ID and Data source ID will be used as environment variables in the later _Deploy Streamlit Web UI for Your Agent_ section

5. Navigate to the [Amazon Bedrock > Agents ](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents): Here you should see the `HRAgent` already created but not prepared as shown below:
<p align="center">
  <img src="../imgs/08_hr_agent.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 8: HRAgent Created</em></span>
</p>

6. Click into the HRAgent, and lets go under, **Edit in Agent Builder**. We see 4 actions associated already, lets go ahead and associate a newly created knowledge base under **Knowledge Bases** and click on **Add**:

<p align="center">
  <img src="../imgs/09_associated_actions.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 9: HRAgent Associated Actions</em></span>
</p>

 i. Under Select knowledge base, select the knowledge base you created in the preceding deployment step

ii. Under Knowledge base instructions for Agent, enter the following then select Next:

    Use to retrieve details about company's leave and pay policy using associated documents.

iii. Click **Save and Exit**

You should see KB now associated with the agent.

<p align="center">
  <img src="../imgs/10_associated_actions_withkb.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 10: HRAgent Associated Actions with Knowledge Bases</em></span>
</p>

### 5. Bedrock Agents

Bedrock Agents operate through a build-time execution process, comprising several key components:

* **Foundation Model**: Users select a foundation model that guides the agent in interpreting user inputs, generating responses, and directing subsequent actions during its orchestration process.
* **Instructions**: Users craft detailed instructions that outline the agent's intended functionality. Optional advanced prompts allow customization at each orchestration step, incorporating Lambda functions to parse outputs.
* **(Optional) Action Groups**: Users define actions for the agent, leveraging an OpenAPI schema to define APIs for task execution and Lambda functions to process API inputs and outputs.
* **(Optional) Knowledge Bases**: Users can associate agents with knowledge bases, granting access to additional context for response generation and orchestration steps.

The agent in this sample solution will use an Titan-Text Premier foundation model, a set of instructions, action groups, and one knowledge base. The underlining agent is pre-created through cloudformation, and we just associated the knowledge base to it. Next lets prepare and test the agent.

Following the successful deployments, the next development phase involves the preparation and testing of your agent's functionality. Preparing the agent involves packaging the latest changes, while testing provides a critical opportunity to interact with and evaluate the agent's behavior. Through this process, you can refine agent capabilities, enhance its efficiency, and address any potential issues or improvements necessary for optimal performance.

1. Navigate to the Agents section of the Amazon Bedrock console

2. Select your `HR Agent`created and note your Agent ID:
<p align="center">
  <img src="../imgs/11_agent_overview.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 11: Agent Selection</em></span>
</p>

❗ _Agent ID will be used as an environment variable in the later Deploy Streamlit web UI for your agent section._

3. Navigate to your working draft. Initially, you have a working draft and a default TestAlias pointing to this draft. The working draft allows for iterative development. Select Prepare to package the agent with the latest changes before testing. Regularly check the agent's last prepared time to ensure testing with the latest configurations:

<p align="center">
  <img src="../imgs/12_agent_working_draft.png" width="40%" height="1%"><br>
  <span style="display: block; text-align: center;"><em>Figure 12: Agent Working Draft Console</em></span>
</p>


4. Access the test window from any page within the agent's working draft console by selecting Test or the left arrow icon at the top right. In the test window, select an alias and its version that appears in the test window

5. You can also create an alias for your testing, To create an alias, click on **Create Alias**, a dialog box appears, enter alias name and description for your alias and click **create alias**

<p align="center">
  <img src="../imgs/13_create_alias.png" width="60%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 13: Agent Create Alias </em></span>
</p>

5. Test your agent using the following sample prompts and other various inputs of your own:

❗ Always select Prepare after making changes to apply them before testing the agent.

## Test Conversation
The following test conversation example highlights the agent’s ability to invoke action group APIs with AWS Lambda business logic that queries a customer’s Amazon DynamoDB table and sends customer notifications using Amazon Simple Notification Service. The same conversation thread showcases agent and knowledge base integration to provide the user with responses using customer authoritative data sources, like claim amount and FAQ documents.

* _(**KB call**) Can you get me some details about Parental Leave Policy?_

* _(**KB+Athena API**) My partner and I are expecting a baby on July 1st. Can I take 2 weeks off?_

  - _Employee Name: `Pepper Li`_
  - _Employee Alias: `hremployee`_

* _(**KB + Athena API Call**) Yes, Please request two weeks time off using my vacation time, from July 1st, 2024 to July 12, 2024_

* _(**Image Generator**) Generate a cartoon image of new born child with parents_


* _(**Email Action**) Send a email with above image to my team telling them that I will be away for 2 weeks starting July 1_

  - _Email Address: Use the email that you used at <SNS_EMAIL>_

* _(**Slack Message**) You can setup slack message API similarly using [Slack Webhooks](https://api.slack.com/messaging/webhooks)_
* Once you have created your webhook and get an API Key you can use the slack URL obtained to update the slack_integration.py [slack_integration.py](../agent/lambda/slack_integration.py). The URL looks like: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX

<p align="center">
  <img src="../imgs/14_testing.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 14: Agent Testing and Validation</em></span>
</p>

## Deploy Streamlit Web UI for Your Agent

Once you are satisfied with the performance of your agent and knowledge base, you are ready to productize their capabilities. We use Streamlit in this solution to launch an example frontend, intended to emulate what would be a customer's Production application. Streamlit is a Python library designed to streamline and simplify the process of building frontend applications. 
To set up:

1. Lets run:
```sh
export BEDROCK_AGENT_ID=<YOUR-AGENT-ID> # The ID of agent created
export BEDROCK_AGENT_ALIAS_ID=<YOUR-AGENT-ALIAS-ID> # The Alias ID of agent created
export PROFILE_NAME=<YOUR-AWS-PROFILE-NAME> # The AWS Profile used; can be default if not provided. 
```
❗ **Note**: If you do not have an AWS Profile created ![Checkout here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-format-profile) to setup a AWS profile with appropriate permissions.

2. Next lets install the required python dependencies:

```sh
pip install -r agents-for-bedrock/use-case-examples/hr-assistant/streamlit/requirements.txt
```

3. Run the streamlit app locally with 
```sh
python3 -m streamlit run agents-for-bedrock/use-case-examples/hr-assistant/streamlit/agent_streamlit.py
```

<p align="center">
  <img src="../imgs/15_streamlit.png" width="95%" height="95%"><br>
  <span style="display: block; text-align: center;"><em>Figure 15: Stremlit UI App</em></span>
</p>

---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
