# Protecting sensitive data in RAG-based applications with Amazon Bedrock

This blog post shows two architecture patterns for protecting sensitive data in RAG-based applications using Amazon Bedrock.

In the **first scenario (Scenario 1)**, we'll show how users can redact or mask sensitive data before storing it in a vector store (a.k.a Ingestion) or Amazon Bedrock Knowledge Base. This zero-trust approach reduces the risk of sensitive information being inadvertently disclosed to unauthorized parties.

The **second scenario (Scenario 2)** will show on situations where sensitive data needs to be stored in the vector store, such as in healthcare settings with distinct user roles like administrators (doctors) and non-administrators (nurses or support personnel). Here, we'll show how a role-based access control pattern enables selective access to sensitive information based on user roles and permissions during retrieval.

Both scenarios come with an [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/) and an accompanying [streamlit](https://streamlit.io/) app to test each scenario.

## Pre-requisites

Python version >= 3.10.16

Create and activate venv

```shell
python -m venv .venv
source .venv/bin/activate
```

upgrade pip and install `requirements.txt`

```shell
pip install -U pip
pip install -r requirements.txt
```

### Amazon Bedrock Model Access

Ensure you have access to Anthropic Claude models in Amazon Bedrock. Refer to [getting started](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html) guide for more info.

## Synthetic Data Generation Tool

For testing each scenario with sensitive data, we use [`synthetic_data.py`](./synthetic_data.py) data generation script.\
The script generates synthetic healthcare and financial data for testing purposes. \
The data generated is completely fictional and does not contain any real Personal Identifiable Information (PII).

Run [`synthetic_data.py`](./synthetic_data.py) script to generate sample data for the demo.

```shell
python synthetic_data.py --seed 123 generate -n 10
```

Data files will be available under a new `data/` directory.

## Scenario 1 (Data identification and redaction before Ingestion to KnowledgeBase)

Refer to [Scenario 1 README.md](./scenario_1/README.md)

## Scenario 2 (Role-Based access to PII data during retrieval)

Refer to [Scenario 2 README.md](./scenario_2/README.md)
