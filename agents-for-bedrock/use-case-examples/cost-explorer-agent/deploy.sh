#!/bin/bash
set -e

# Prompt user for stackname
read -p "Enter Name for the Stack [BillingAgentStack]: " STACK_NAME
STACK_NAME=${STACK_NAME:-"BillingAgentStack"}

# Set variables
TEMPLATE_FILE="agent_template.yaml"
REGION=${REGION:-"us-east-1"}
DEFAULT_BUCKET_NAME="billing-agent-${RANDOM}"

# Function to check if a bucket exists
bucket_exists() {
  if aws s3api head-bucket --bucket "$1" > /dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

# Function to create a bucket if it doesn't exist
create_bucket_if_not_exists() {
  if bucket_exists "$1"; then
    echo "Bucket $1 already exists"
  else
    echo "Creating bucket $1"
    if [ "$REGION" = "us-east-1" ]; then
      if aws s3api create-bucket --bucket "$1" --region "$REGION" > /dev/null 2>&1; then
        echo "Bucket created successfully"
      else
        echo "Failed to create bucket. Exiting."
        exit 1
      fi
    else
      if aws s3api create-bucket --bucket "$1" --region "$REGION" --create-bucket-configuration LocationConstraint=$REGION > /dev/null 2>&1; then
        echo "Bucket created successfully"
      else
        echo "Failed to create bucket. Exiting."
        exit 1
      fi
    fi
  fi
}

# Prompt user for S3 bucket
read -p "Enter an existing S3 bucket name or press Enter to create a new one [$DEFAULT_BUCKET_NAME]: " S3_BUCKET
S3_BUCKET=${S3_BUCKET:-$DEFAULT_BUCKET_NAME}

# Check if the bucket exists or create a new one
create_bucket_if_not_exists "$S3_BUCKET"

# Prompt for other parameters
read -p "Enter the Agent Name [aws-billing-agent]: " AGENT_NAME
AGENT_NAME=${AGENT_NAME:-"aws-billing-agent"}
read -p "Enter the Agent Alias Name [beta]: " AGENT_ALIAS_NAME
AGENT_ALIAS_NAME=${AGENT_ALIAS_NAME:-"beta"}
read -p "Enter the Agent Foundational Model [anthropic.claude-3-haiku-20240307-v1:0]: " AGENT_FOUNDATIONAL_MODEL
AGENT_FOUNDATIONAL_MODEL=${AGENT_FOUNDATIONAL_MODEL:-"anthropic.claude-3-haiku-20240307-v1:0"}

# Prompt for Slack integration
read -p "Do you want to enable Slack integration? (yes/no) [no]: " ENABLE_SLACK
ENABLE_SLACK=${ENABLE_SLACK:-"no"}

if [[ $ENABLE_SLACK == "yes" ]]; then
  ENABLE_SLACK_INTEGRATION="true"
  read -p "Enter the Slack Bot Token: " SLACK_BOT_TOKEN
  read -p "Enter the Slack Signing Secret: " SLACK_SIGNING_SECRET
else
  ENABLE_SLACK_INTEGRATION="false"
  SLACK_BOT_TOKEN=""
  SLACK_SIGNING_SECRET=""
fi

# Create Slack Bolt Lambda layer if Slack integration is enabled
if [[ $ENABLE_SLACK_INTEGRATION == "true" ]]; then
  echo "Creating Slack Bolt Lambda layer..."
  mkdir -p slack_bolt_layer/python
  pip3 install slack_bolt -t slack_bolt_layer/python
  pip3 install aws_lambda_powertools -t slack_bolt_layer/python
  cd slack_bolt_layer
  zip -r ../slack_bolt_layer.zip .
  cd ..
fi

# Package Lambda functions
echo "Packaging Lambda functions..."
zip -j billingagent.zip src/actiongroup/billingagent.py
zip -j savingsplanagent.zip src/actiongroup/SavingsPlan.py

if [[ $ENABLE_SLACK_INTEGRATION == "true" ]]; then
  zip -j slack_integration.zip src/slack_integration.py
fi

# Upload files to S3
echo "Uploading files to S3 bucket: $S3_BUCKET"
aws s3 cp billingagent.zip s3://$S3_BUCKET/billingagent.zip
aws s3 cp savingsplanagent.zip s3://$S3_BUCKET/savingsplanagent.zip
aws s3 cp src/actiongroup/schema/BillingAgent_OpenAPI.json s3://$S3_BUCKET/BillingAgent_OpenAPI.json
aws s3 cp src/actiongroup/schema/SavingsPlan_OpenAPI.json s3://$S3_BUCKET/SavingsPlan_OpenAPI.json

if [[ $ENABLE_SLACK_INTEGRATION == "true" ]]; then
  aws s3 cp slack_integration.zip s3://$S3_BUCKET/slack_integration.zip
  aws s3 cp slack_bolt_layer.zip s3://$S3_BUCKET/slack_bolt_layer.zip
fi

echo "Files uploaded successfully!"

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file $TEMPLATE_FILE \
  --stack-name $STACK_NAME \
  --region $REGION \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
  EnableSlackIntegration="$ENABLE_SLACK_INTEGRATION" \
  SlackBotToken="$SLACK_BOT_TOKEN" \
  SlackSigningSecret="$SLACK_SIGNING_SECRET" \
  AgentName="$AGENT_NAME" \
  AgentAliasName="$AGENT_ALIAS_NAME" \
  AgentFoundationalModel="$AGENT_FOUNDATIONAL_MODEL" \
  SourceBucket="$S3_BUCKET"

if [ $? -eq 0 ]; then
  echo "Deployment complete!"
else
  echo "Deployment failed. Check the CloudFormation events for more information."
  exit 1
fi