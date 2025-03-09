# Bedrock Data Automation (BDA) Samples

Amazon Bedrock Data Automation is a GenAI-powered capability of Bedrock that streamlines the development of generative AI applications and automates workflows involving documents, images, audio, and videos. By leveraging Bedrock Data Automation, developers can reduce development time and effort, making it easier to build intelligent document processing, media analysis, and other multimodal data-centric automation solutions. 

Bedrock Data Automation offers industry-leading accuracy at lower cost than alternative solutions, along with features such as visual grounding with confidence scores for explainability and built-in hallucination mitigation. This ensures trustworthy and accurate insights from unstructured, multi-modal data sources. 

Bedrock Data Automation is also integrated with Bedrock Knowledge Bases, making it easier for developers to generate meaningful information from their unstructured multi-modal content to provide more relevant responses for retrieval augmented generation (RAG).

## Getting started
To get started with the code examples, ensure you have access to Amazon Bedrock. Then clone this repo and navigate to one of the folders above. Detailed instructions are provided in each folder's README.

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
            "Sid": "BdaAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeDataAutomationAsync",
                "bedrock:CreateDataAutomationProject",
                "bedrock:DeleteDataAutomationProject",
                "bedrock:GetDataAutomationProject",
                "bedrock:GetDataAutomationStatus",
                "bedrock:ListDataAutomationProjects",
                "bedrock:UpdateDataAutomationProject",
                "bedrock:GetBlueprint",
                "bedrock:GetBlueprintRecommendation",
                "bedrock:InvokeBlueprintRecommendationAsync",
                "bedrock:ListBlueprints",
                "bedrock:CreateBlueprint",
                "bedrock:DeleteBlueprint",
                "bedrock:UpdateBlueprint"
            ],
            "Resource": "*"
        },
        {
            "Sid": "SagemakerGetDefaultS3",
            "Effect": "Allow",
            "Action": "sagemaker:ListNotebookInstanceLifecycleConfigs",
            "Resource": "*"
        },
        {
            "Sid": "KnowledgeBasesCreateRole",
            "Effect": "Allow",
            "Action": [
                "iam:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "S3Access",
            "Effect": "Allow",
            "Action": [
                "s3:DeleteObject",
                "s3:PutObject",
                "s3:GetObject",
                "s3:PutObject",
                "s3:CreateBucket",
                "s3:ListBucket"
            ],
            "Resource": "*",
        },
        {
            "Sid": "BedrockKnowledgeBasesAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateKnowledgeBase",
                "bedrock:UpdateKnowledgeBase",
                "bedrock:ListKnowledgeBases",
                "bedrock:Retrieve",
                "bedrock:RetrieveAndGenerate",
                "bedrock:ListDataSources",
                "bedrock:ListIngestionJobs",
                "bedrock:GetDataSource",
                "bedrock:StartIngestionJob",
                "bedrock:InvokeModel",
                "bedrock:CreateDataSource",
                "bedrock:GetIngestionJob",
                "bedrock:DeleteDataSource",
                "bedrock:GetKnowledgeBase",
                "bedrock:DeleteKnowledgeBase"
            ],
            "Resource": "*"
        },
        {
            "Sid": "OpenSearchAccessForKb",
            "Effect": "Allow",
            "Action": [
                "aoss:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "LambdaForKbDeployment",
            "Effect": "Allow",
            "Action": [
                "lambda:AddPermission",
                "lambda:CreateFunction",
                "lambda:DeleteFunction",
                "lambda:GetFunction"
            ],
            "Resource": "*"
        }
    ]
}
```

> ⚠️ **Note 1:** With Amazon SageMaker AI, your notebook execution role will typically be *separate* from the user or role that you log in to the AWS Console with. If you'd like to explore the AWS Console for Amazon Bedrock, you'll need to grant permissions to your Console user/role too.

> ⚠️ **Note 2:** For top level folder changes, please reach out to the GitHub maintainers.

For more information on the fine-grained action and resource permissions in Bedrock, check out the [Bedrock Developer Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api.html).

## Contributing

We welcome community contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
