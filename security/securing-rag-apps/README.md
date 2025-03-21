# Protecting sensitive data in RAG-based applications with Amazon Bedrock

This blog post shows two architecture patterns for protecting sensitive data in RAG-based applications using Amazon Bedrock.

In the **first scenario (Scenario 1)**, we'll show how users can redact or mask sensitive data before storing it in a vector store (a.k.a Ingestion) or Amazon Bedrock Knowledge Base. This zero-trust approach reduces the risk of sensitive information being inadvertently disclosed to unauthorized parties.

The **second scenario (Scenario 2)** will show on situations where sensitive data needs to be stored in the vector store, such as in healthcare settings with distinct user roles like administrators (doctors) and non-administrators (nurses or support personnel). Here, we'll show how a role-based access control pattern enables selective access to sensitive information based on user roles and permissions during retrieval.

Both scenarios come with an [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/) and an accompanying [streamlit](https://streamlit.io/) app to test each scenario.

## Pre-requisites

Please ensure you have Python version == 3.10.16

**NOTE:** This project assumes you have python v3.10.16 installed. If you want to use a later version, you may have to make changes to the dependency versions in [`requirements.txt`](./requirements.txt).

### Clone the repository

clone the [amazon-bedrock-samples](https://github.com/aws-samples/amazon-bedrock-samples.git) repository and switch to `securing-rag-apps` directory

```shell
git clone https://github.com/aws-samples/amazon-bedrock-samples.git

cd amazon-bedrock-samples/security/securing-rag-apps
```

### Install `aws-cdk` CLI tool

To deploy the CDK application stack we need to install `aws-cdk` cli tool.

Refer to [AWS CDK CLI reference](https://docs.aws.amazon.com/cdk/v2/guide/cli.html) for info and help on using the CDK cli.

If you already have cdk cli version installed you can check the current installed version with the below command.

```shell
cdk --version
# 2.1005.0 (build be378de)
```

**NOTE:** This application was tested with `aws-cdk` cli version == `2.1005.0 (build be378de)`.\

```shell
npm install -g aws-cdk@2.1002.0
```

### Create and activate python virtual environment

Create and activate python venv

```shell
python -m venv .venv
source .venv/bin/activate
```

upgrade pip and install `requirements.txt`

```shell
pip install -U pip
pip install -r requirements.txt
```

### Enabled model access in Amazon Bedrock

>**IMPORTANT**: Ensure `Access status` shows as `Access granted` for the below models under `Model Access` Amazon Bedrock console.

- All Anthropic Claude (Text and Text & Vision generation models)
- Amazon Titan Text Embedding V2 (Embedding Model)

1. Refer to [Model support by AWS Region in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html) for list of supported regions by model.
2. Refer to [bedrock getting started](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html) user guide for info on how to request access to models in Amazon Bedrock.

## Synthetic Data Generation Tool

For testing each scenario with sensitive data, we use [`synthetic_data.py`](./synthetic_data.py) script to generate synthetic data.

The script generates synthetic healthcare and financial data for testing purposes. \
The data generated is completely fictional and does not contain any real Personal Identifiable Information (PII).

Run [`synthetic_data.py`](./synthetic_data.py) script to generate sample data for the demo.

```shell
python synthetic_data.py --seed 123 generate -n 10
```

Data files will be available under a new `data/` directory.

Next, Refer to relevant README.md files referenced below for deploying each Scenario

---

## Scenario 1 (Data identification and redaction before Ingestion to KnowledgeBase)

To deploy Scenario 1 refer to [Scenario 1 README.md](./scenario_1/README.md#usage)

## Scenario 2 (Role-Based access to PII data during retrieval)

To deploy Scenario 2 refer to[Scenario 2 README.md](./scenario_2/README.md#usage)
