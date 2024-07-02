# Responsible AI

This folder contains examples related to Responsible AI on Bedrock

## Contents

[Guardrails for Amazon Bedrock Samples](guardrails-for-amazon-bedrock-samples) - Examples of Building, Updating, Versioning and Testing your Guardrails


# Deploying the Customer Support Chatbot with Guardrails

This guide will walk you through the steps to deploy a customer support chatbot with guardrails using Amazon Bedrock. Follow these steps to set up your environment, deploy the CloudFormation stack, and run the Streamlit app.

## Prerequisites

1. **Python and pip**: Ensure you have Python and pip installed.
2. **AWS CLI**: Ensure you have the AWS CLI installed and configured with appropriate permissions.

## Steps

### 1. Install the Required Python Packages

First, install the required Python packages from the `requirements.txt` file.

```sh
cd guardrails-for-amazon-bedrock-samples
pip install -r requirements.txt
```

### 2. Set Executable Permissions for the Deployment Script

Ensure the deployment script `deploy_guardrail_infra.sh` is executable.

```sh
cd scripts
chmod +x deploy_guardrails_app.sh
```

### 3. Install `jq` for JSON Processing

Depending on your operating system, use one of the following methods to install `jq`.

#### On macOS (using Homebrew)

If you are using macOS, you can install `jq` using Homebrew. If you don't have Homebrew installed, you can install it from [brew.sh](https://brew.sh).

```sh
brew install jq
```

#### On Ubuntu/Debian (using apt-get)

If you are using Ubuntu or Debian, you can install `jq` using `apt-get`.

```sh
sudo apt-get update -y
sudo apt-get install -y jq
```

#### On Amazon Linux/CentOS/Red Hat (using yum)

If you are using Amazon Linux, CentOS, or Red Hat, you can install `jq` using `yum`.

```sh
sudo yum install -y jq
```

### 4. Deploy the CloudFormation Stack

Run the `deploy_guardrails_infra.sh` script to deploy the CloudFormation stack and get the unique identifier of the guardrail.

```sh
./deploy_guardrails_app.sh
```

This script will:
- Read the CloudFormation template.
- Create the CloudFormation stack.
- Wait for the stack creation to complete.
- Retrieve the outputs, including the unique identifier of the guardrail.

### 5. Run the Streamlit App with the Guardrail Identifier

Take the outputted unique identifier of the guardrail from the previous step and use it to run the Streamlit app. Replace `<guardrail_unique_id>` with the actual unique identifier.

```sh
streamlit run streamlit_guardrails_app.py -- --guardrail_identifier=<guardrail_unique_id>
```

### Example Command

If the outputted unique identifier is `tvsm6gry4pe8`, the command would be:

```sh
streamlit run streamlit_guardrails_app.py -- --guardrail_identifier=tvsm6gry4pe8
```

By following these steps, you will deploy the CloudFormation stack, retrieve the unique identifier of the guardrail, and run the Streamlit app with the guardrails applied. This setup ensures that the chatbot interactions are safe and appropriate for users.


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
