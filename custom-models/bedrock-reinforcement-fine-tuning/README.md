# Bedrock Reinforcement Fine-Tuning (RFT)

Examples for training models on Amazon Bedrock using Reinforcement Fine-Tuning.

## What's here

End-to-end notebooks showing how to RFT various models on different datasets:

| Model | Dataset | Notebook |
|-------|---------|----------|
| Amazon Nova Lite | GSM8K (math) | [models/nova/nova_gsm8k_rft.ipynb](models/nova/nova_gsm8k_rft.ipynb) |

More coming soon—additional Nova variants, Llama models, and datasets beyond math (code, reasoning, etc.).

## Directory structure

```
bedrock-reinforcement-fine-tuning/
├── models/                  # Training notebooks organized by model
│   └── nova/
├── reward-functions/        # Lambda functions that score model outputs
├── helpers/                 # Shared utilities (IAM roles, Lambda deployment, etc.)
└── README.md
```

## Prerequisites

- AWS account with Bedrock access
- S3 bucket for training data and outputs
- IAM permissions to create Lambda functions and IAM roles

## Quick start

1. Pick a notebook from the table above
2. Update the config section with your S3 bucket and region
3. Run all cells

The notebook handles everything: data prep, Lambda deployment, IAM setup, and job submission.

## Resources

- [AWS Blog: Improve model accuracy with RFT in Amazon Bedrock](https://aws.amazon.com/blogs/aws/improve-model-accuracy-with-reinforcement-fine-tuning-in-amazon-bedrock/)
- [Docs: RFT for Amazon Nova](https://docs.aws.amazon.com/bedrock/latest/userguide/nova-rft.html)
- [Docs: Reinforcement Fine-Tuning overview](https://docs.aws.amazon.com/bedrock/latest/userguide/reinforcement-fine-tuning.html)
- [Video: RFT walkthrough](https://www.youtube.com/watch?v=oNERioZEJiw)
- [Interactive demo: RFT in the console](https://aws.storylane.io/share/2wbkrcppkxdr)
