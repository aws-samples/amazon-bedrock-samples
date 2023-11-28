# AWS CDK Deployment

**Side note: If you want to use AWS CDK BedrockAgent construct to deploy agents and knowledge bases, feel free to check out [npm package](https://www.npmjs.com/package/bedrock-agents-cdk?activeTab=readme) repository.**

Installation guide assumes you have AWS account and Administrator Access to provision all the resources. 
Provisioning will take somewhere from 5 to 7 minutes.

# Prerequisites
=============

* node >= 16.0.0
* npm >= 8.0.0
* AWS CLI >= 2.0.0
* AWS CDK >= 2.66.1

# Installation

Download current directory or clone repo and cd into ``cdk-deployment``. From within the root project folder (``cdk-deployment``), run the following commands:

```
cdk bootstrap
```

```
npm install
```

```
cdk deploy --require-approval never
```

Optional - if you want your agent to have a custom name you can do deployment like this (substituting ``"my-agent-name"`` with your desired name). **Keep your agent name length under 20 characters**:

```
cdk deploy --parameters AgentName="my-agent-name" --require-approval never
```

# Prompt example

```
My s3 bucket is named 'maxtybar-bedrock'. Make me a new calculator agent called 'reinv-calc-agent', with methods to add, multiply, divide, and subtract two numbers. 
Name the parameters in a way that leaves no confusion about which number to subtract and which to divide. 
The instruction for a new agent is: "You can be asked to add, multiply, or divide two numbers. 
Do not hallucinate and always provide correct answer."
```

# How to delete

From within the root project folder (``cdk-deployment``), run the following command:

```
cdk destroy --force
```

More details to be added soon.