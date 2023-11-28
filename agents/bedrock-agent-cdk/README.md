# Introduction
============

**Side note: If you want to use AWS CDK BedrockAgent construct to deploy agents and knowledge bases, feel free to check out [npm package](https://www.npmjs.com/package/bedrock-agents-cdk?activeTab=readme) repository.**

This guide details how to install, configure, and use the agent CDK deployemnt. The instructions assume that the deployment will be deployed from a terminal running from Linux or MacOS.

Resources provisioned by deployment:

* S3 bucket
* Bedrock Agent
* Action Group
* Bedrock Agent IAM role
* Bedrock Agent Action Group
* Lambda function
* Lambda service-policy permission 
* Lambda IAM role

The tutorial deploys Bedrock agent backed by Anthropic Clause V2 model and creates an Action Group within this agent with the schema that user uploads to ``lib/assets/api-schema`` and Python function that user uploads to ``lib/assets/lambdas/agent``. To do that, the demo also creates an S3 bucket and uploads schema to it. By default IAM roles that are provisioned by CDK are empty so make sure you attach policies appropriate for your needs.

# Prerequisites
=============

* node >= 16.0.0
* npm >= 8.0.0
* Docker
* AWS CLI >= 2.0.0
* AWS CDK >= 2.66.1

# How to run

Before you start, make sure you upload the python function to ``lib/assets/lambdas/agent`` and api schema to ``lib/assets/api-schema`` that you want your action group within your agent to have. By default it has template lambda ``create-agent.py`` and API schema ``create-agent-schema.json`` that will be used in deployment. Make sure you remove these files if you upload your own schema and Python file for Lambda.

From within the root project folder (``bedrock-agent-cdk``), run the following commands:

```
cdk bootstrap
```

```
npm install
```

```
cdk deploy --require-approval never
```
Note - in rare cases there might be "Access denied" when Docker tries to pull a public image from AWS public ECR Repository. To overcome this run the following command before you start deployment: 
```
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
``` 

Optional - if you want your agent to have a custom name you can do deployment like this (substituting "my-agent-name" with your desired name):

```
cdk deploy -c agentName="my-agent-name" --require-approval never
```

# How to delete (before GA you need to delete manualy in the console)

From within the root project folder (``bedrock-agent-cdk``), run the following commands:

```
cdk destroy --force
```