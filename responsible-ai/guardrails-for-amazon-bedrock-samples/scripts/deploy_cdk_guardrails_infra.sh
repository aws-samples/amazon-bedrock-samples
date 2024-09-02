#!/bin/bash

# Exit on any error
set -e

# Function to prompt user for input with a default value
prompt() {
  read -rp "$1 [$2]: " input
  echo "${input:-$2}"
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

# Install AWS CDK and necessary dependencies
echo "Installing AWS CDK and necessary Python packages..."
pip install aws-cdk-lib constructs

# Initialize CDK project
echo "Initializing CDK project..."
cdk init app --language python

# Prompt user for AWS configuration
echo "Configuring AWS credentials and environment..."
AWS_ACCESS_KEY_ID=$(prompt "Enter your AWS Access Key ID" "")
AWS_SECRET_ACCESS_KEY=$(prompt "Enter your AWS Secret Access Key" "")
AWS_DEFAULT_REGION=$(prompt "Enter your AWS Default Region" "us-east-1")
AWS_ACCOUNT_ID=$(prompt "Enter your AWS Account ID" "")

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
  "app": "python3 app.py",
  "context": {
    "aws:accountId": "$AWS_ACCOUNT_ID",
    "aws:region": "$AWS_DEFAULT_REGION"
  }
}
EOF

echo "AWS credentials and environment configured."

# Run cdk bootstrap to prepare the environment for deploying stacks
echo "Bootstrapping the CDK environment..."
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_DEFAULT_REGION

# Final message
echo "Setup complete. You can now add your stack definition in the 'lib' directory and deploy using 'cdk deploy'."

