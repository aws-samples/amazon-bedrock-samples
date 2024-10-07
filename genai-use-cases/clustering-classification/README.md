
# Text Clustering & Classification with AWS Bedrock API in Financial Industry

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/{add-this-notebooks-exact-location-here}){:target="_blank"}"

## Overview

This runbook demonstrates how to use AWS Bedrock API to perform text clustering and classification, specifically in the financial sector. In this scenario, we will address the issue of categorizing and grouping customer inquiries for better response management.

The steps included are:
1. Problem statement in the financial industry
2. Introduction to AWS Bedrock and its capabilities
3. Code examples in Jupyter notebooks for clustering and classification
4. Instructions for using Bedrock API for text processing

---

## Problem Statement

### Scenario: 
A financial institution receives thousands of inquiries every day about various products such as loans, credit cards, and mortgages. These queries need to be grouped into clusters for better management and classified into categories like 'Loan Inquiry', 'Credit Card Issues', or 'Mortgage Questions'. 

By using AWS Bedrock, we can automatically cluster these inquiries and classify them using advanced NLP models, reducing manual overhead.

---

## Prerequisites

Make sure the following prerequisites are fulfilled:
- AWS Account with access to Bedrock
- IAM permissions to invoke AWS Bedrock API
- Python environment with Jupyter Notebook installed
- AWS CLI with credentials configured

---

## Architecture

This is how the architecture of the solution works:
1. **Data Collection**: Customer inquiries are collected through various channels (email, chat, etc.).
2. **Text Clustering**: Group similar inquiries using clustering algorithms.
3. **Text Classification**: Categorize the inquiries into predefined groups.
4. **Output**: Results are used for further analysis or automating customer responses.

---

## Step-by-Step Solution

### Step 1: Install Required Libraries

To get started, install the required libraries such as `boto3`, `pandas`, `matplotlib`, and `scikit-learn`:

```bash
!pip install boto3 pandas matplotlib scikit-learn
```

### Step 2: Set Up AWS Bedrock API Access

Ensure your AWS credentials are configured with the AWS CLI:

```bash
aws configure
```

This will prompt you to input your AWS access keys, secret key, and region.

---

### Step 3: Initialize Bedrock Client with Default Credentials

```python
import boto3

# Initialize AWS Bedrock client using default AWS credentials
bedrock_client = boto3.client('bedrock')
```

### Step 4: Sample Data for Financial Inquiries

We'll create a dataset containing a few sample inquiries from customers in the financial sector.

```python
import pandas as pd

# Sample financial customer inquiry data
data = {
    "query": [
        "What are the current mortgage rates?",
        "How do I increase my credit card limit?",
        "Can I apply for a loan online?",
        "What are the charges for early loan repayment?",
        "I need help with my credit card bill."
    ]
}

# Creating a DataFrame
df = pd.DataFrame(data)
print(df)
```

### Step 5: Text Clustering

We will first transform the text data into features using `TfidfVectorizer` and apply `KMeans` for clustering.

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

# Convert text into TF-IDF features
vectorizer = TfidfVectorizer(stop_words='english')
X = vectorizer.fit_transform(df['query'])

# Perform KMeans clustering
kmeans = KMeans(n_clusters=3, random_state=42).fit(X)
df['cluster'] = kmeans.labels_

# Displaying clustered queries
print(df)
```

### Step 6: Text Classification

For basic classification, we'll use a simple keyword-based approach. For more advanced classification, we can use AWS Bedrock.

```python
def classify_query(query):
    if 'mortgage' in query.lower():
        return 'Mortgage Inquiry'
    elif 'credit card' in query.lower():
        return 'Credit Card Inquiry'
    elif 'loan' in query.lower():
        return 'Loan Inquiry'
    else:
        return 'General Inquiry'

df['category'] = df['query'].apply(classify_query)
print(df)
```

### Step 7: Visualization of Results

Now, we can visualize the clustered queries using a scatter plot.

```python
import matplotlib.pyplot as plt

# Visualizing clusters
plt.scatter(X.toarray()[:, 0], X.toarray()[:, 1], c=df['cluster'])
plt.title("Customer Inquiries Clustering")
plt.show()

# Display the categorized results
print(df[['query', 'category']])
```

### Step 8: Using AWS Bedrock API for Enhanced Classification

Finally, let's integrate AWS Bedrock for more advanced classification using a pre-trained model. The following code prepares the input prompt and calls the API using the `anthropic.claude-v2` model.

```python
import json

# Create a properly formatted prompt for Bedrock
queries = df['query'].tolist()
formatted_queries = "
".join([f"Human: {query}" for query in queries])

# Add the required "Assistant:" ending to the prompt
prompt = f"{formatted_queries}
Assistant:"

# Call AWS Bedrock for classification
response = bedrock_client.invoke_model(
    modelId='anthropic.claude-v2',
    contentType='application/json',
    body=json.dumps({
        "prompt": prompt,
        "max_tokens_to_sample": 100
    })
)

# Processing and printing the response
print(response)
```

---

## Conclusion

In this runbook, we demonstrated how to use AWS Bedrock for text clustering and classification in the financial industry. We showed how to structure and process customer inquiries to group similar queries and categorize them using both traditional methods and AWS Bedrock’s advanced NLP models.

---

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/index.html)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Scikit-learn Documentation](https://scikit-learn.org/stable/)

