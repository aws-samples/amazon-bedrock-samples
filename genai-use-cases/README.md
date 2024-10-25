# Amazon Bedrock Samples 

This repository contains pre-built examples to help customers get started with the Amazon Bedrock service.

## Contents

- [Introduction to Bedrock](introduction-to-bedrock) - Learn the basics of the Bedrock service
- [Prompt Engineering ](prompt-engineering) - Tips for crafting effective prompts 
- [Bedrock Fine-tuning](bedrock-fine-tuning) - Fine-tune Bedrock models for your specific use case
- [Custom Model Import](custom-models) - Import custom models into Bedrock
- [Generative AI Solutions](generative-ai-solutions) - Example use cases for generative AI
- [Knowledge Bases](knowledge-bases) - Build knowledge bases with Bedrock
- [Retrival Augmented Generation (RAG)](rag-solutions) - Implementing RAG with Amazon Bedrock
- [Agents](agents-and-function-calling) - Generative AI agents with Bedrock
- [Security and Governance](security-and-governance) - Secure your Bedrock applications
- [Responsible AI](responsible-ai) - Use Bedrock responsibly and ethically
- [Operational Tooling](ops-tooling) - Helpful samples to help operationalize your useage of Amazon Bedrock
- [Multimodal](multimodal) - Working with multimodal data using Amazon Bedrock

## Getting Started

To get started with the code examples, ensure you have access to [Amazon Bedrock](https://aws.amazon.com/bedrock/). Then clone this repo and navigate to one of the folders above. Detailed instructions are provided in each folder's README.

### Enable AWS IAM permissions for Bedrock

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

## Contributing

We welcome community contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
