#!/bin/bash

# Exit on any error
set -e

# Set the stack name
STACK_NAME="CdkBedrockGuardrailStack"

# Function to prompt user for input with a default value
prompt() {
  read -rp "$1 [$2]: " input
  echo "${input:-$2}"
}

# Function to check if the stack exists
check_stack_exists() {
    aws cloudformation describe-stacks --stack-name "$STACK_NAME" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        return 0  # Stack exists
    else
        return 1  # Stack does not exist
    fi
}

# Check if virtualenv is installed, if not, install it
if ! command -v virtualenv &> /dev/null; then
    echo "virtualenv is not installed. Installing it now..."
    pip install virtualenv
fi

# Create a virtual environment
echo "Creating a virtual environment..."
virtualenv .venv
source .venv/bin/activate

# Check if npm is installed, and if not, prompt user to install it
if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install npm to proceed."
    exit 1
fi

# Check if CDK CLI is installed, and if not, install it
if ! command -v cdk &> /dev/null; then
    echo "CDK CLI is not installed. Installing it now..."
    npm install -g aws-cdk
else
    echo "Upgrading CDK CLI to the latest version..."
    npm install -g aws-cdk
fi

# Install AWS CDK and necessary dependencies in the virtual environment
echo "Installing AWS CDK and necessary Python packages..."
pip install aws-cdk-lib constructs

# Check if the directory already contains a CDK project
if [ ! -f "cdk.json" ]; then
    # Initialize CDK project only if it's not already initialized
    echo "Initializing CDK project..."
    cdk init app --language python
else
    echo "CDK project is already initialized, skipping 'cdk init'."
fi


# Check if environment variables exist, otherwise prompt the user
echo "Configuring AWS credentials and environment..."
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-$(prompt "Enter your AWS Access Key ID" "")}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-$(prompt "Enter your AWS Secret Access Key" "")}
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-$(prompt "Enter your AWS Default Region" "us-east-1")}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(prompt "Enter your AWS Account ID" "")}


# Set AWS credentials as environment variables
export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION

# Create or update ~/.aws/credentials file
mkdir -p ~/.aws

cat <<EOF > ~/.aws/credentials
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
EOF

# Create or update ~/.aws/config file
cat <<EOF > ~/.aws/config
[default]
region = $AWS_DEFAULT_REGION
output = json
EOF

# Generate CDK context file
cat <<EOF > cdk.json
{
  "app": "python3 ../infra/cdk/app.py"
}
EOF

echo "AWS credentials and environment configured."

# Check if the stack is already deployed
if check_stack_exists; then
    echo "The stack '$STACK_NAME' is already deployed. Skipping deployment."
    # Optionally, retrieve and display the Guardrail Identifier
    outputs=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs')
    guardrail_arn=$(echo "$outputs" | jq -r '.[] | select(.OutputKey=="GuardrailIdentifier") | .OutputValue')
    guardrail_identifier=$(echo "$guardrail_arn" | awk -F'/' '{print $NF}')
    echo "The Guardrail Identifier is: ${guardrail_identifier}"
    exit 0
else
    echo "Stack '$STACK_NAME' not found. Proceeding with deployment."
fi

# Run cdk bootstrap to prepare the environment for deploying stacks
echo "Bootstrapping the CDK environment..."
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_DEFAULT_REGION

# Synthesize the CDK stack to generate CloudFormation templates
echo "Synthesizing the CDK stack..."
cdk synth

# Deploy the stack to AWS
echo "Deploying the CDK stack..."
cdk deploy --outputs-file ./cdk-outputs.json

# Retrieve and display the Guardrail Identifier from the stack outputs
echo "Retrieving the Guardrail Identifier..."
guardrail_arn=$(jq -r '.CdkBedrockGuardrailStack.GuardrailIdentifier' < ./cdk-outputs.json)

# Extract the unique identifier from the ARN
guardrail_identifier=$(echo "$guardrail_arn" | awk -F'/' '{print $NF}')

if [ -n "$guardrail_identifier" ]; then
    echo "The Guardrail Identifier is: ${guardrail_identifier}"
else
    echo "Error: Guardrail Identifier not found."
    exit 1
fi