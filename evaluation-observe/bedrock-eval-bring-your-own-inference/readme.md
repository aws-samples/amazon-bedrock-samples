# Amazon Bedrock Model Evaluation with Bring Your Own Inference Response (BYOI)

This repository contains notebooks and sample data to help you get started with Amazon Bedrock Model Evaluation capabilities using Bring Your Own Inference Responses (BYOI). These examples demonstrate how to evaluate both foundation models and RAG systems regardless of where they're deployed.

## Repository Contents

- **Notebooks**
  - `llmaaj-bring-your-own-inference.ipynb`: Demonstrates how to use LLM-as-a-Judge for evaluating model responses from any source
  - `rag-eval-bring-your-own-inference.ipynb`: Shows how to evaluate RAG systems with the new citation metrics

- **Sample Data**
  - `sample-data/`: Contains example JSONL files for both model and RAG evaluation

## Getting Started

### Prerequisites

- An AWS account with Amazon Bedrock access
- A configured AWS CLI with appropriate permissions
- Python 3.7+ environment with boto3 installed
- An Amazon S3 bucket with CORS enabled for storing evaluation data
- IAM role with necessary permissions for Bedrock and S3

### Setup Instructions

1. Clone this repository to your local machine
2. Install required dependencies:
   ```
   pip install boto3 pandas
   ```
3. Configure your AWS credentials:
   ```
   aws configure
   ```
4. Open the notebooks in Jupyter or your preferred environment
5. Follow the step-by-step instructions in each notebook

## Use Cases

### LLM-as-a-Judge with BYOI

Evaluate responses from any model against multiple quality dimensions:
- Compare models from different providers using standardized metrics
- Assess custom or fine-tuned models deployed elsewhere
- Benchmark model performance before and after optimization

### RAG Evaluation with BYOI

Evaluate any RAG system's retrieval and generation quality:
- Assess citation quality with precision and coverage metrics
- Optimize retrieval strategies across different implementations
- Compare different foundation models for RAG generation quality

## Additional Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Model Evaluation User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation-judge.html)
- [RAG Evaluation Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation-kb.html)

