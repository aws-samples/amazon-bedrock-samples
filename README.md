# Amazon Bedrock Samples 

To leverage this repository please use our website powered by this GitHub: [Website](https://aws-samples.github.io/amazon-bedrock-samples/)

This repository contains pre-built examples to help customers get started with the Amazon Bedrock service.

## Contents

- [Introduction to Bedrock](introduction-to-bedrock) - Learn the basics of the Bedrock service
- [Prompt Engineering ](articles-guides) - Tips for crafting effective prompts 
- [Agents](agents-and-function-calling) - Ways to implement Generative AI Agents and its components.
- [Custom Model Import](custom-models) - Import custom models into Bedrock
- [Multimodal](multi-modal) - Working with multimodal data using Amazon Bedrock
- [Generative AI Use cases](genai-use-cases) - Example use cases for generative AI
- [Retrival Augmented Generation (RAG)](rag) - Implementing RAG
- [Responsible AI](responsible_ai) - Use Bedrock responsibly and ethically
- [Workshop](workshops) - Example for Amazon Bedrock Workshop
- [POC to Prod](poc-to-prod) - Productionize workloads using Bedrock
- [Embeddings](embeddings) - Learn how to use Embedding Models available on Amazon Bedrock 
- [Observability & Evaluation](evaluation-observe) - Learn how Amazon Bedrock helps with improving observability and evalution of Models, Gen AI Applications.


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

> ⚠️ **Note 1:** With Amazon SageMaker, your notebook execution role will typically be *separate* from the user or role that you log in to the AWS Console with. If you'd like to explore the AWS Console for Amazon Bedrock, you'll need to grant permissions to your Console user/role too.

> ⚠️ **Note 2:** For top level folder changes, please reach out to the GitHub mainterners.

For more information on the fine-grained action and resource permissions in Bedrock, check out the Bedrock Developer Guide.

## Contributing

We welcome community contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
