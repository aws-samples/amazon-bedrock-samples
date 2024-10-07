<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>

## Text Classification with AWS Bedrock using Pydantic

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/text-classification-pydantic-bedrock){:target="_blank"}"

## Overview

This notebook demonstrates how to perform text classification using Pydantic for data validation and AWS Bedrock for machine learning. We'll build a system that categorizes customer feedback for an e-commerce platform, helping the business route issues to the appropriate department efficiently.

## Context

### What is Text Classification?

Text classification is the task of assigning predefined categories to free-text documents. In our case, we'll be categorizing customer feedback into different departments: Product, Shipping, Customer Service, and Website.

### Why use Pydantic?

Pydantic is a data validation library that uses Python type annotations. It ensures that the data we're working with conforms to expected structures, reducing errors and improving code reliability.

### AWS Bedrock for Machine Learning

AWS Bedrock provides a unified API to access foundation models from various AI companies. We'll use it to leverage a pre-trained language model for our classification task.

## Prerequisites

!!! info ""
    Before starting this tutorial, ensure you have:
    - An AWS account with access to AWS Bedrock
    - Python 3.7+ installed
    - Basic understanding of Python and machine learning concepts

## Setup

First, let's install the necessary libraries:

```bash
pip install boto3 pydantic transformers
```

Now, let's set up our AWS credentials and import the required libraries:

```python
import boto3
from pydantic import BaseModel, Field, ValidationError
from typing import List
import json
import logging

# Set up logging for error tracking
logging.basicConfig(level=logging.INFO)

# Set up AWS Bedrock client
bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
```

## Notebook

### Step 1: Define our data model with Pydantic

We'll start by defining our data model for customer feedback:

```python
class Feedback(BaseModel):
    text: str
    category: str = Field(..., regex="^(Product|Shipping|Customer Service|Website)$")

class FeedbackBatch(BaseModel):
    items: List[Feedback]
```

### Step 2: Prepare sample data

Let's create some sample customer feedback data:

```python
sample_data = [
    {"text": "The product quality is excellent, but it arrived late.", "category": "Product"},
    {"text": "I can't find the return policy on your website.", "category": "Website"},
    {"text": "Your customer service rep was very helpful.", "category": "Customer Service"},
    {"text": "The packaging was damaged when it arrived.", "category": "Shipping"}
]

try:
    feedback_batch = FeedbackBatch(items=[Feedback(**item) for item in sample_data])
except ValidationError as e:
    logging.error(f"Validation Error: {e.json()}")
    feedback_batch = None
```

### Step 3: Define the classification function

Now, let's create a function that uses AWS Bedrock to classify the feedback:

```python
def classify_feedback(text):
    prompt = f"""Human: Classify the following customer feedback into one of these categories: Product, Shipping, Customer Service, or Website.
    Customer Feedback: "{text}"
    Classification:
    Assistant:"""
    
    try:
        # Call the Bedrock API with the correct format
        response = bedrock.invoke_model(
            modelId="anthropic.claude-v2",
            body=json.dumps({
                "prompt": prompt,
                "max_tokens_to_sample": 50,  # Adjust this based on the length of your expected output
                "temperature": 0.5,  # Adjust this parameter for controlling randomness
                "stop_sequences": ["\n"]  # Stops at the first new line after the answer
            })
        )
        # Extract and return the classification from the response
        return json.loads(response['body'].read())['completion'].strip()
    except boto3.exceptions.Boto3Error as api_error:
        logging.error(f"API call to Bedrock failed: {api_error}")
        return "Error"
    except KeyError as key_error:
        logging.error(f"Unexpected response format: {key_error}")
        return "Error"
```

### Step 4: Process the feedback batch

Now we can process our batch of feedback:

```python
for item in feedback_batch.items:
    predicted_category = classify_feedback(item.text)
    print(f"Text: {item.text}")
    print(f"Actual Category: {item.category}")
    print(f"Predicted Category: {predicted_category}")
    print("---")
```

## Other Considerations / Best Practices

1. **Error Handling**: Implement robust error handling for API calls and data processing.
2. **Batch Processing**: For large datasets, consider implementing batch processing to optimize API usage.
3. **Model Fine-tuning**: If you have a large dataset of labeled feedback, consider fine-tuning a model specifically for your use case.
4. **Confidence Scores**: Implement a system to handle cases where the model's confidence is low, possibly flagging them for human review.

## Cleanup

Remember to properly manage your AWS resources to avoid unnecessary charges:

1. Ensure you stop any running Bedrock endpoints.
2. Delete any stored data that you no longer need.
3. Review and update your IAM permissions as necessary.

!!! warning "Cost Management"
    Always be mindful of the costs associated with using cloud services. Monitor your usage and set up billing alerts in AWS to avoid unexpected charges.
