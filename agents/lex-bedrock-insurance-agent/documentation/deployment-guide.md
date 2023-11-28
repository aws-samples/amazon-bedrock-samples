# Deployment Guide
---

## Content
- [Pre-Deployment](#pre-deployment)
- [Deployment](#deployment)
- [Post-Deployment](#post-deployment)

## Pre-Deployment

### Fork and Clone [_generative-ai-amazon-bedrock-langchain-agent-example_](https://github.com/aws-samples/generative-ai-amazon-bedrock-langchain-agent-example) Repository
The AWS Amplify configuration points to a GitHub source repository from which our website's frontend is built. To control the source code that builds your Amplify website, follow [GitHub's instructions](https://docs.github.com/en/get-started/quickstart/fork-a-repo?tool=webui&platform=mac) to fork this _generative-ai-amazon-bedrock-langchain-agent-example_ repository. This creates a copy of the repository that is disconnected from the original codebase, so you can make the appropriate modifications.

❗ Take note of your forked repository URL as you will use it to clone the repository in the next step and to configure the _GITHUB_PAT_ environment variable used in the [Deployment Automation Script](#deployment).

Clone the _generative-ai-amazon-bedrock-langchain-agent-example_ repository:

```sh
git clone https://github.com/aws-samples/generative-ai-amazon-bedrock-langchain-agent-example
```

### Create GitHub Personal Access Token (PAT)
The Amplify hosted website uses a GitHub PAT as the OAuth token for third-party source control. The OAuth token is used to create a webhook and a read-only deploy key using SSH cloning.

To create your PAT, please follow the GitHub instructions for [creating a personal access token (classic)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic). You may prefer to use a [GitHub App](https://docs.github.com/en/apps/creating-github-apps/creating-github-apps/about-apps) to access resources on behalf of an organization or for long-lived integrations. 

❗ Take note of your PAT before closing your browser as you will use it to configure the _GITHUB_PAT_ environment variable used in the [Deployment Automation Script](deployment-automation-script). The script will publish your PAT to AWS Secrets Manager using AWS CLI commands and the secret name will be used as the _GitHubToken_ CloudFormation parameter.

#### Optional - Run Security Scan on the CloudFormation Templates
To run a security scan on the [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) templates using [`cfn_nag`](https://github.com/stelligent/cfn_nag) (recommended), you have to install `cfn_nag`:
```sh
brew install ruby brew-gem
brew gem install cfn-nag
```

To initiate the security scan, run the following command:
```sh
# git clone https://github.com/aws-samples/generative-ai-amazon-bedrock-langchain-agent-example
# cd generative-ai-amazon-bedrock-langchain-agent-example
cfn_nag_scan --input-path cfn/GenAI-FSI-Agent.yml
```

## Deployment 
The [create-stack.sh](../shell/create-stack.sh) shell script allows for automated solution provisioning through a parameterized CloudFormation template, [GenAI-FSI-Agent.yml](../cfn/GenAI-FSI-Agent.yml), which includes the following resources:

1. AWS Amplify website to simulate customer's frontend environment.
2. Amazon Lex bot configured through a bot import deployment package.
3. Four Amazon DynamoDB tables:
	- _UserPendingAccountsTable_: Records pending transactions (e.g., loan applications).
	- _UserExistingAccountsTable_: Contains user account information (e.g., mortgage account summary).
	- _ConversationIndexTable_: Tracks conversation state.
	- _ConversationTable_: Stores conversation history.
4. Amazon S3 bucket that contains AWS Lambda Handler, Lambda Data Loader, and Lex deployment packages, along with Customer FAQ and Mortgage Application example documents.
5. Two Lambda functions:
	- Agent Handler: Contains the LangChain Conversational Agent logic that can intelligently employ a variety of tools based on user input.
	- Data Loader: Loads example customer account data into _UserExistingAccountsTable_ and is invoked as a custom CloudFormation resource during stack creation.
6. AWS Lambda layer built from [requirements.txt](../agent/lambda-layers/requirements.txt). Supplies LangChain's LLM library with an Amazon Bedrock hosted model as the underlying LLM. Also serves PyPDF as an open-source PDF library for creating and modifying PDF files.
7. Amazon Kendra Index: Provides a searchable index of customer proprietary information, including documents, FAQs, knowledge bases, manuals, websites, and more.
8. Two Kendra Data Sources:
	- S3: Hosts an example customer [FAQ document](../agent/assets/Octank-Financial-FAQs.csv).
	- Web Crawler: Configured with a root domain that emulates the customer-specific website.
9. AWS Identity and Access Management (IAM) permissions for the above resources.

CloudFormation prepopulates stack parameters with the default values provided in the template. To provide alternative input values, you can specify parameters as environment variables that are referenced in the `ParameterKey=<ParameterKey>,ParameterValue=<Value>` pairs in the below shell script's `aws cloudformation create-stack` command. 

Before executing the shell script, navigate to your forked version of the _generative-ai-amazon-bedrock-langchain-agent-example_ repository as your working directory and modify the shell script permissions to executable:

```sh
# If not already forked, fork the remote repository (https://github.com/aws-samples/generative-ai-amazon-bedrock-langchain-agent-example) and change working directory to shell folder:
cd generative-ai-amazon-bedrock-langchain-agent-example/shell/
chmod u+x create-stack.sh
```

Next, set your Amplify Repository and GitHub PAT environment variables created during the pre-deployment steps:

```sh
export AMPLIFY_REPOSITORY=<YOUR-FORKED-REPOSITORY-URL> # Forked repository URL from Pre-Deployment (Exclude '.git' from repository URL)
export GITHUB_PAT=<YOUR-GITHUB-PAT> # GitHub PAT copied from Pre-Deployment
export STACK_NAME=<YOUR-STACK-NAME> # Stack name must be lower case for S3 bucket naming convention
export KENDRA_WEBCRAWLER_URL=<YOUR-WEBSITE-ROOT-DOMAIN> # Public or internal HTTPS website for Kendra to index via Web Crawler (e.g., https://www.investopedia.com/) - Please see https://docs.aws.amazon.com/kendra/latest/dg/data-source-web-crawler.html
```

Finally, execute the shell script to deploy the [GenAI-FSI-Agent.yml](../cfn/GenAI-FSI-Agent.yml) CloudFormation stack.

```sh
source ./create-stack.sh
```

#### Deployment Automation Script
The above ```source ./create-stack.sh``` shell command executes the following AWS CLI commands to deploy the solution stack:

```sh
# If not already forked, fork the remote repository (https://github.com/aws-samples/generative-ai-amazon-bedrock-langchain-agent-example) and change working directory to shell folder
# cd generative-ai-amazon-bedrock-langchain-agent-example/shell/
# chmod u+x create-stack.sh
# source ./create-stack.sh

export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export S3_ARTIFACT_BUCKET_NAME=$STACK_NAME-$ACCOUNT_ID
export DATA_LOADER_S3_KEY="agent/lambda/data-loader/loader_deployment_package.zip"
export LAMBDA_HANDLER_S3_KEY="agent/lambda/agent-handler/agent_deployment_package.zip"
export LEX_BOT_S3_KEY="agent/bot/lex.zip"

aws s3 mb s3://${S3_ARTIFACT_BUCKET_NAME} --region us-east-1
aws s3 cp ../agent/ s3://${S3_ARTIFACT_BUCKET_NAME}/agent/ --recursive --exclude ".DS_Store"

export BEDROCK_LANGCHAIN_LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name bedrock-langchain-pypdf \
    --description "Bedrock LangChain PyPDF layer" \
    --license-info "MIT" \
    --content S3Bucket=${S3_ARTIFACT_BUCKET_NAME},S3Key=agent/lambda-layers/bedrock-langchain-pypdf.zip \
    --compatible-runtimes python3.11 \
    --query LayerVersionArn --output text)

export GITHUB_TOKEN_SECRET_NAME=$(aws secretsmanager create-secret --name $STACK_NAME-git-pat \
--secret-string $GITHUB_PAT --query Name --output text)

aws cloudformation create-stack \
--stack-name ${STACK_NAME} \
--template-body file://../cfn/GenAI-FSI-Agent.yml \
--parameters \
ParameterKey=S3ArtifactBucket,ParameterValue=${S3_ARTIFACT_BUCKET_NAME} \
ParameterKey=DataLoaderS3Key,ParameterValue=${DATA_LOADER_S3_KEY} \
ParameterKey=LambdaHandlerS3Key,ParameterValue=${LAMBDA_HANDLER_S3_KEY} \
ParameterKey=LexBotS3Key,ParameterValue=${LEX_BOT_S3_KEY} \
ParameterKey=GitHubTokenSecretName,ParameterValue=${GITHUB_TOKEN_SECRET_NAME} \
ParameterKey=KendraWebCrawlerUrl,ParameterValue=${KENDRA_WEBCRAWLER_URL} \
ParameterKey=BedrockLangChainPyPDFLayerArn,ParameterValue=${BEDROCK_LANGCHAIN_LAYER_ARN} \
ParameterKey=AmplifyRepository,ParameterValue=${AMPLIFY_REPOSITORY} \
--capabilities CAPABILITY_NAMED_IAM

aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].StackStatus"
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME

export LEX_BOT_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`LexBotID`].OutputValue' --output text)

export LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaARN`].OutputValue' --output text)

aws lexv2-models update-bot-alias --bot-alias-id 'TSTALIASID' --bot-alias-name 'TestBotAlias' --bot-id $LEX_BOT_ID --bot-version 'DRAFT' --bot-alias-locale-settings "{\"en_US\":{\"enabled\":true,\"codeHookSpecification\":{\"lambdaCodeHook\":{\"codeHookInterfaceVersion\":\"1.0\",\"lambdaARN\":\"${LAMBDA_ARN}\"}}}}"

aws lexv2-models build-bot-locale --bot-id $LEX_BOT_ID --bot-version "DRAFT" --locale-id "en_US"

export KENDRA_INDEX_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`KendraIndexID`].OutputValue' --output text)

export KENDRA_S3_DATA_SOURCE_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`KendraS3DataSourceID`].OutputValue' --output text)

export KENDRA_WEBCRAWLER_DATA_SOURCE_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`KendraWebCrawlerDataSourceID`].OutputValue' --output text)

aws kendra start-data-source-sync-job --id $KENDRA_S3_DATA_SOURCE_ID --index-id $KENDRA_INDEX_ID

aws kendra start-data-source-sync-job --id $KENDRA_WEBCRAWLER_DATA_SOURCE_ID --index-id $KENDRA_INDEX_ID

export AMPLIFY_APP_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`AmplifyAppID`].OutputValue' --output text)

export AMPLIFY_BRANCH=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`AmplifyBranch`].OutputValue' --output text)

aws amplify start-job --app-id $AMPLIFY_APP_ID --branch-name $AMPLIFY_BRANCH --job-type 'RELEASE'
```

## Post-Deployment

### Confirm Amazon Lex Bot Alias Locale is Built
Amazon Lex V2 locales contain the intents and slot types that the bot uses in conversations with users in the specified language and locale. The above [Deployment Automation Script](#deployment) builds the bot, its intents, and its slot types into the 'en_US' locale.

Use the [Amazon Lex Console](https://us-east-1.console.aws.amazon.com/lexv2/home?region=us-east-1#welcome) to confirm your bot's default alias, _TestBotAlias_, has been configured for the English (US) locale and integrated with the Agent Handler Lambda function for initialization, validation, and fulfillment.

<p align="center">
  <img src="../design/lex-lambda.png">
</p>

Ensure the correct Lambda function and _$LATEST_ version are selected:

<p align="center">
  <img src="../design/lex-lambda-config.png">
</p>

### (OPTIONAL) Integrate Amazon Lex with Kommunicate
[Kommunicate](https://docs.kommunicate.io/) integrates with Amazon Lex to produce a JavaScript plugin that will embed a Lex-powered chat widget within the solution's Amplify website. Kommunicate only requires _AmazonLexReadOnly_ and _AmazonLexRunBotsOnly_ permissions.

❗ Kommunicate end user information usage: End users are defined as individuals who interact with the Lex chatbot through the Web channel. End user prompts are proxied through Kommunicate and sent to the Lex chatbot. End users may submit information such as personal information including names, email addresses, and phone numbers in the chat or connected email. Kommunicate only stores chat history and other information provided by end users for the sole purpose of displaying analytics and generating reports within the Kommunicate console, which is protected by username/password or SAML login credentials. Kommunicate does not expose the personal information of end users to any 3rd party. Please refer to [Kommunicate's privacy policy](https://www.kommunicate.io/privacy-policy) for additional information.

Follow the instructions for [Kommunicate's Amazon Lex bot integration](https://docs.kommunicate.io/docs/bot-lex-integration):

<p align="center">
  <img src="../design/Kommunicate-lex.png">
</p>

Then copy the [JavaScript plugin](https://dashboard.kommunicate.io/settings/install) generated by Kommunicate:

<p align="center">
  <img src="../design/Kommunicate.svg">
</p>

Edit your forked version of the Amplify GitHub source repository by adding your Kommunicate JavaScript plugin to the section labeled '_<-- Paste your Kommunicate JavaScript plugin here -->_' for each of the HTML files under the [frontend directory](../frontend/): _index.html, contact.html, about.html_.

<p align="center">
  <img src="../design/Kommunicate-plugin.svg">
</p>

Amplify provides an automated build and release pipeline that triggers based on new commits to your forked repository and publishes the new version of your website to your Amplify domain. You can view the deployment status in the [AWS Amplify Console](https://us-east-1.console.aws.amazon.com/amplify/home?region=us-east-1#/).

<p align="center">
  <img src="../design/amplify-deployment.png">
</p>

Customize your chat widget styling and greeting message in the [Kommunicate console](https://dashboard.kommunicate.io/settings/chat-widget-customization#chat-widget-styling).

<p align="center">
  <img src="../design/Kommunicate-chat-widget.png">
</p>

<p align="center">
  <img src="../design/Kommunicate-greeting.png">
</p>

### Launch Amplify Website
With your JavaScript plugin in place, you are now ready to launch your Amplify demo website. To access your website's domain, navigate to the [Outputs section of the Amazon CloudFormation Console](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-view-stack-data-resources.html) or enter the below command:

```
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`AmplifyDemoWebsite`].OutputValue' --output text
```

Access your Amplify domain URL and continue to [Testing and Validation](testing-and-validation.md).

<p align="center">
  <img src="../design/amplify-website.png">
</p>

## Testing and Validation
see [Testing and Validation](testing-and-validation.md)

---

## README
see [README](../README.md)

---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
