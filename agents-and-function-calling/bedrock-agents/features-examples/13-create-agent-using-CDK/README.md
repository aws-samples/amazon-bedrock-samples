
# AWS CDK (Python) to provision AWS Bedrock Agent with Knowledge Base and an Action Group Connection

In this folder, we provide an example to create Bedrock Agent using Infrastructure as Code (IaC).IaC is implemented using with [AWS CDK Python APIs](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_bedrock.html). The Bedrock agent is integrated with a Knowledge Base and an Action Group. With this integration, the agent will be able to respond to a user query by taking a sequence of actions, consulting the knowledge base to obtain more information, and/or executing tasks using the lambda function connected with an Action Group. 

AWS CDK for Python is implemented with configurable parameters from 'config.json' file. 

The Agent architecture can be referred [here](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/agents-and-function-calling/bedrock-agents/features-examples/05-create-agent-with-knowledge-base-and-action-group)


## Pre-requisites

Ensure that Node.js, Python and CDK are installed on your enviorment. These are required for next steps to deploy this Bedrock Agent.

## Build and Deploy with AWS CDK 

This project is set up like a standard Python project. The initialization process also creates a virtualenv within this project, stored under the .venv directory. To create the virtualenv it assumes that there is a python3 (or python for Windows) executable in your path with access to the venv package. If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv manually.

The `cdk.json` file tells the CDK toolkit how to execute your app.

### Python Setup

Manually create a virtualenv on MacOS and Linux:

```
cd amazon-bedrock-samples/agents-and-function-calling/bedrock-agents/features-examples/13-create-agent-using-CDK
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

 You can add a new parameter or edit the existing parameter in config.json file. Here is the example to edit an existing parameter:

      a) Change the "agentName" parameter with "test-booking-agent" in 'config.json' file 

      b) Ensure that same parameter is used correctly in 'BedrockAgentStack_stack.py' file 

      c) Finally deploy the updated stack with 'cdk deploy'   


Note: AgentModelId with claude-3-sonnet and EmbeddingModelId with titan-embed-text-v2 are used in this example.

### CDK Destroy

You use `cdk destroy` to remove the resources you created with `cdk deploy`.

```
cdk destroy
```

Enjoy!
