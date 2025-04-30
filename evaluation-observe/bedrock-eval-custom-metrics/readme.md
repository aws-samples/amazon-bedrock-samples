# Amazon Bedrock Model Evaluation with Custom Metrics

This repository contains notebooks and sample code to help you get started with Amazon Bedrock Model Evaluation capabilities using Custom Metrics. These examples demonstrate how to define and use custom evaluation metrics for both foundation models and RAG systems to gain deeper insights into your AI applications.

## Repository Contents

- **Notebooks**
  - `custom-metrics-model-evaluation.ipynb`: Demonstrates how to implement and use custom metrics for evaluating foundation models
  - `custom-metrics-rag-evaluation.ipynb`: Shows how to apply custom metrics to evaluate RAG system performance

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
   pip install boto3
   ```
3. Configure your AWS credentials:
   ```
   aws configure
   ```
4. Open the notebooks in Jupyter or your preferred environment
5. Follow the step-by-step instructions in each notebook

## Use Cases

### Custom Metrics for Foundation Models

Define and implement custom evaluation metrics tailored to your specific use cases:
- Create domain-specific evaluation criteria beyond standard metrics
- Measure task-specific performance indicators for your applications
- Design composite metrics that combine multiple evaluation dimensions

### Custom Metrics for RAG Systems

Develop specialized metrics to evaluate the effectiveness of your RAG implementations:
- Measure domain-specific information relevance and accuracy
- Evaluate contextual appropriateness of retrieved information
- Assess factual grounding with customized evaluation criteria

## Additional Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Model Evaluation with Custom Metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-custom-metrics-create-job.html)
- [RAG Evaluation with Custom Metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-create-randg-custom.html)
