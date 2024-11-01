<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>

## Intent Classification with AWS Bedrock

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/intent-classification-bedrock.ipynb){:target="_blank"}"

## Overview

This notebook demonstrates how to use AWS Bedrock to perform intent classification using Large Language Models (LLMs). We'll walk through a real-world scenario of a customer support system that needs to automatically classify incoming customer queries into different intent categories.

![Intent Classification](../images/intent_classification.png){align=center}

## Context

Intent classification is a crucial task in natural language processing, particularly in customer support systems. It involves categorizing user queries or messages into predefined intent categories, allowing for efficient routing and handling of customer inquiries.

### Why AWS Bedrock?

AWS Bedrock provides a unified API to access state-of-the-art foundation models from leading AI companies. For our intent classification task, we'll be using the Anthropic Claude v2 model, which excels in understanding context and generating human-like responses.

## Prerequisites

!!! info ""
    Before starting this notebook, ensure you have:
    
    1. An AWS account with access to AWS Bedrock
    2. Python 3.7 or later installed
    3. Required Python libraries: boto3, pandas, scikit-learn

## Setup

First, let's install the necessary Python libraries:

```python
!pip install boto3 pandas scikit-learn
```

Now, let's import the required libraries and set up our AWS Bedrock client:

```python
import boto3
import json
import pandas as pd
from sklearn.metrics import classification_report

# Initialize a session using Amazon Bedrock
client = boto3.client('bedrock-runtime')
```

## Dataset Preparation

We'll create a sample dataset of customer queries and their corresponding intents:

```python
data = {
    'Query': [
        'Why is my bill higher this month?',
        'How do I reset my password?',
        'Can I get a discount on my next purchase?',
        'What are your business hours?',
        'I need help with my internet connection',
        'Do you offer any promotions?',
        'When will my order be delivered?',
        'How can I update my payment method?',
        'Is there a warranty on this product?',
        'Can I speak to a human representative?'
    ],
    'Intent': [
        'Billing Inquiry',
        'Technical Support',
        'Sales Inquiry',
        'General Information',
        'Technical Support',
        'Sales Inquiry',
        'Order Status',
        'Account Management',
        'Product Information',
        'Customer Service'
    ]
}

df = pd.DataFrame(data)
print(df)
```

## Intent Classification Function

Let's create a function that uses AWS Bedrock to classify the intent of a given query:

```python
def classify_intent(query):
    prompt = f"""
    You are an AI assistant trained to classify customer support queries into intent categories.
    Given the following query, classify it into one of these intent categories:
    - Billing Inquiry
    - Technical Support
    - Sales Inquiry
    - General Information
    - Order Status
    - Account Management
    - Product Information
    - Customer Service

    Query: {query}

    Respond with only the intent category, nothing else.
    """

    payload = {
        "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
        "max_tokens_to_sample": 100,
        "temperature": 0.1,
        "top_p": 1
    }

    response = client.invoke_model(
        modelId='anthropic.claude-v2', 
        contentType='application/json',
        accept='application/json',
        body=json.dumps(payload)
    )

    response_body = json.loads(response['body'].read())
    return response_body['completion'].strip()
```

## Testing the Classification

Now, let's test our classification function on our dataset:

```python
y_true = df['Intent'].tolist()
y_pred = []

for query in df['Query']:
    intent = classify_intent(query)
    y_pred.append(intent)
    print(f"Query: {query}")
    print(f"Predicted Intent: {intent}")
    print("---")

# Generate classification report
report = classification_report(y_true, y_pred)
print("\nClassification Report:")
print(report)
```

## Results Analysis

The classification report will show us how well our model is performing in terms of precision, recall, and F1-score for each intent category. This helps us understand the strengths and weaknesses of our intent classification system.

## Other Considerations

1. **Fine-tuning**: For better performance, consider fine-tuning the model on a larger, domain-specific dataset.
2. **Confidence Threshold**: Implement a confidence threshold to handle queries that the model is unsure about.
3. **Continuous Learning**: Regularly update the model with new data to improve its performance over time.

## Next Steps

1. Integrate this intent classification system into your customer support pipeline.
2. Implement a feedback loop to continuously improve the model's performance.
3. Explore other AWS Bedrock models to compare performance.

## Cleanup

To clean up resources and avoid unnecessary charges:

1. Stop any running Jupyter notebook instances.
2. Ensure you've terminated any persistent AWS resources created during this exercise.

!!! warning "Billing"
    Remember to monitor your AWS Bedrock usage to avoid unexpected charges.

