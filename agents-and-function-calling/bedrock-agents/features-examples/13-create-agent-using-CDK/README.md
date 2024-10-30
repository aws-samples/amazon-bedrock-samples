
# AWS CDK (Python) to provision AWS Bedrock Agent with Knowledge Base and an Action Group Connection

In this folder, we provide an example of creating an agent with Amazon Bedrock and integrating it with a 
Knowledge Base for Amazon Bedrock and with an Action Group using Infrastructure as Code (IaC). IaC is implemented using AWS CDK for Python. With this integration, the agent will be able to respond to a user query by taking a sequence of actions, consulting the knowledge base to obtain more information, and/or executing tasks using the lambda function 
connected with an Action Group. AWS CDK for Python is implemented configurable parameters from 'config.json' file. 

The Agent architecture can be referred [here](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/05-create-agent-with-knowledge-base-and-action-group)

## Build and Deploy with AWS CDK 
The complete provisioning of Amazon Bedrock agent, integration with a Knowledge Base and an Action Group is automated using AWS CDK [Cloud Development Kit](https://aws.amazon.com/cdk/) in [Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html). AWS CDK is used primarily used to provision and manage cloud resources in a programmatic and infrastructure-as-code (IaC) manner.

Developers can leverage their existing skills as CDK supports TypeScript, JavaScript, Python, Java, C#/.Net, and Go programming languages and tools to define infrastructure, leading to faster development cycles. Develop faster by using and sharing reusable components called [constructs](https://docs.aws.amazon.com/cdk/v2/guide/constructs.html). Use high-level constructs to quickly define larger components of your application, with secure defaults for your AWS resources, defining more infrastructure with less code.  It's common to see reductions ranging from 30% to 50% or more in terms of lines of code when moving from notebook-based implementations to CDK. This reduction primarily stems from improved organization, modularity, and abstraction capabilities offered by CDK.

CDK integrates well with CI/CD pipelines (e.g., AWS CodePipeline, CodeBuild). This enables automated testing, deployment, and rollback of infrastructure changes, enhancing reliability and speed of deployments. 

For complex architectures or microservices-based applications, CDK can manage dependencies and relationships between resources, ensuring they are provisioned and configured correctly.CDK promotes adherence to AWS best practices through built-in constructs and libraries. For example, it can enforce secure defaults for IAM policies, VPC configurations, and encryption settings.

This folder contains the complete Python CDK code for of Amazon Bedrock agent, integration with a Knowledge Base and with an Action Group.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

### Python Setup

This project is set up like a standard Python project. The initialization process also needs a virtualenv within this project, stored under the `.env` directory. To create the virtualenv it assumes that there is a `python3` (or `python` for Windows) executable in your path with access to the `venv` package.

Manually create a virtualenv on MacOS and Linux:

```
python3 -m venv .env
```

After the bootstrap process completes and the virtualenv is created, use the following step to activate your virtualenv.

```
source .env/bin/activate
```

If you are a Windows platform, activate the virtualenv like this:

```
.env\Scripts\activate.bat
```

Once the virtualenv is activated, install the required dependencies.

```
pip3 install -r requirements.txt
```
Install AWS [GenAI CDK constructs](https://github.com/awslabs/generative-ai-cdk-constructs) for provisioning of Bedrock Knowledgebase and Agent

```
pip3 install cdklabs.generative-ai-cdk-constructs
```
### CDK Synthesize

Now synthesize the CloudFormation template for this code. This will generate the CloudFormation template for you to examine, and verify that your setup is complete.

```
cdk synth
```

### CDK Deploy

You use `cdk deploy` actually to create the resources with default parameters and their values.

```
cdk deploy
```

### CDK Deploy with Parameters 

You use `cdk deploy` with parameters in 'config.json' file. 

You can update the number of supported parameters shown as examples below:

  "agentName": "booking-agent",

  "agentAliasName": "booking-agent-alias", 
  
  "knowledgeBaseName": "booking-agent-kb",

  "knowledgeBaseDescription": "Knowledge Base containing the restaurant menu's collection"
  
  "func_getbooking_name": "get_booking_details",
  
  "func_getbooking_description": "Retrieve details of a restaurant booking",
  
  "func_getbooking_id": "booking_id",

Note: AgentModelId with claude-3-sonnet and EmbeddingModelId with titan-embed-text-v2 are only supported in this example.

### CDK Destroy

You use `cdk destroy` to remove the resources you created with `cdk deploy`.

```
cdk destroy
```

Enjoy!
