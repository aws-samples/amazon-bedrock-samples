# Amazon Bedrock - Meta Llama 2 Fine-tuning for Text Summarization Task

This is a blog post code repository and it is a deep dive example for Meta Llama 2 Fine-tuning for a text summarization task. 

## Content and Step

- [requirements.txt](./requirements.txt) - It's for setting up Python packages in the notebook environment.

- [00_setup.ipynb](./00\_setup.ipynb) - It's for creating a S3 bucket and IAM role for fine-tuning process using Custom Models for Amazon Bedrock. The S3 bucket is for storing training, evaluation dataset & model customization job output, and the IAM role is for Amazon Bedrock to access the S3 bucket during fine-tuning. Espcially, please ensure that the IAM user / role you used to run model customization job may include below permissions:

    > Please replace `AWS_ACCOUNT_ID` with the actual account id.

    ```json
    ...
            {
                "Sid": "PassRoleToBedrockPermission",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": "arn:aws:iam::{AWS_ACCOUNT_ID}:role/BedrockFineTuningBlogResourceAccessRole"
            }
    ...
    ```

- [01_llama2-fine-tuning-text-summarization.ipynb](./01\_llama2-fine-tuning-text-summarization.ipynb) - It's for building an end to end fine-tuning process in Custom Models for Amazon Bedrock. We will be sampling 1,000 records from open sourced [DialogSum](https://huggingface.co/datasets/knkarthick/dialogsum) dataset, transform the data to be compatible format, running model customization job for fine-tuning, analyzing the training job result, deployment using [Provisioned Throughput](https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html), and evaluate the model with [BERTScore](https://huggingface.co/spaces/evaluate-metric/bertscore) & doing a comparison between fine-tuned Llama 2 13B and Llama2 13B Chat in Amazon Bedrock.  

## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.