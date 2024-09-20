<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>

<h2>Amazon Bedrock Samples</h2>

This repository contains pre-built examples to help customers get started with the Amazon Bedrock service.

<h2>Contents</h2>

- [Introduction to Agents](https://github.com/aws-samples/amazon-bedrock-samples/agents/introduction-to-agents) - Learn the basics of a Generative AI agent.
- [Function Calling](https://github.com/aws-samples/amazon-bedrock-samples/agents/function-calling) - Getting Started with Funtion Calling for Generative AI Models hosted on Amazon Bedrock. 
- [Bedrock Agents](https://github.com/aws-samples/amazon-bedrock-samples/agents/agents-for-bedrock) - Getting started with Amazon Bedrock Agents.
<!-- - 
- [Bedrock Fine-tuning](bedrock-fine-tuning) - Fine-tune Bedrock models for your specific use case
- [Custom Model Import](custom-models) - Import custom models into Bedrock
- [Generative AI Solutions](generative-ai-solutions) - Example use cases for generative AI
- [Knowledge Bases](knowledge-bases) - Build knowledge bases with Bedrock
- [Retrival Augmented Generation (RAG)](rag-solutions) - Implementing RAG with Amazon Bedrock

- [Security and Governance](security-and-governance) - Secure your Bedrock applications
- [Responsible AI](responsible-ai) - Use Bedrock responsibly and ethically
- [Operational Tooling](ops-tooling) - Helpful samples to help operationalize your useage of Amazon Bedrock
- [Multimodal](multimodal) - Working with multimodal data using Amazon Bedrock -->

<h2>Getting Started</h2>

To get started with the code examples, ensure you have access to [Amazon Bedrock](https://aws.amazon.com/bedrock/). Then clone this repo and navigate to one of the folders above. Detailed instructions are provided in each folder's README.

<h3>Enable AWS IAM permissions for Bedrock</h3>

The AWS identity you assume from your environment (which is the [*Studio/notebook Execution Role*](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html) from SageMaker, or could be a role or IAM User for self-managed notebooks or other use-cases), must have sufficient [AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) to call the Amazon Bedrock service.

To grant Bedrock access to your identity, you can:

- Open the [AWS IAM Console](https://us-east-1.console.aws.amazon.com/iam/home?#)
- Find your [Role](https://us-east-1.console.aws.amazon.com/iamv2/home?#/roles) (if using SageMaker or otherwise assuming an IAM Role), or else [User](https://us-east-1.console.aws.amazon.com/iamv2/home?#/users)
- Select *Add Permissions > Create Inline Policy* to attach new inline permissions, open the *JSON* editor and paste in the below example policy:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockFullAccess",
            "Effect": "Allow",
            "Action": ["bedrock:*"],
            "Resource": "*"
        }
    ]
}
```

> ⚠️ **Note:** With Amazon SageMaker, your notebook execution role will typically be *separate* from the user or role that you log in to the AWS Console with. If you'd like to explore the AWS Console for Amazon Bedrock, you'll need to grant permissions to your Console user/role too.

For more information on the fine-grained action and resource permissions in Bedrock, check out the Bedrock Developer Guide.

<h2>Contributing</h2>

We welcome community contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

<h2>Security</h2>

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

<h2>License</h2>

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
