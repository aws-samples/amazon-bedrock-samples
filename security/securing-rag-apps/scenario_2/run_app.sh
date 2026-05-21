#!/bin/bash

# Enable error handling
set -e
set -o pipefail

# Stack name
STACK_NAME="PiiMaskDuringRetrievalStack"

# Function to check if a command was successful
check_command() {
    if [ $? -ne 0 ]; then
        echo "Error: $1 failed"
        exit 1
    fi
}

# Check if AWS CLI is installed
if ! command -v aws &>/dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Set CDK environment variables
echo "Setting up CDK environment..."
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=$(aws configure get region)
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

echo "Using AWS Account: $CDK_DEFAULT_ACCOUNT"
echo "Using AWS Region: $CDK_DEFAULT_REGION"


# Check if CDK is installed
if ! command -v cdk &>/dev/null; then
    echo "Error: AWS CDK is not installed"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi


# Check if Streamlit is installed
if ! command -v streamlit &>/dev/null; then
    echo "Error: Streamlit is not installed"
    exit 1
fi

# Navigate to CDK directory
echo "Navigating to cdk/ directory..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/cdk" || {
    echo "Error: CDK directory not found"
    exit 1
}


# Bootstrap CDK
echo "Bootstrapping CDK..."
cdk bootstrap || {
    echo "CDK bootstrap failed. Attempting to clean up and retry..."
    echo "Checking if CDKToolkit stack exists..."
    if aws cloudformation describe-stacks --stack-name CDKToolkit >/dev/null 2>&1; then
        echo "Deleting existing CDKToolkit stack..."
        aws cloudformation delete-stack --stack-name CDKToolkit
        echo "Waiting for stack deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name CDKToolkit
        echo "Sleeping for 60s..."
        sleep 60
    fi
    echo "Retrying CDK bootstrap..."
    cdk bootstrap
    check_command "CDK bootstrap"
}

# Synthesize and deploy CDK app
echo "Synthesizing and deploying CDK app..."
cdk synth --quiet && cdk deploy --require-approval never
check_command "CDK deployment"

# Return to the main directory
cd "$SCRIPT_DIR" || {
    echo "Error: Failed to navigate back to script directory"
    exit 1
}

# Verify stack exists first
aws cloudformation describe-stacks --stack-name $STACK_NAME >/dev/null 2>&1 || {
    echo "Error: Stack $STACK_NAME not found"
    exit 1
}

# Read required outputs with error checking
echo "Reading CloudFormation outputs for stack $STACK_NAME..."

# USERPOOL_ID
export USERPOOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
    --output text)
[ -z "$USERPOOL_ID" ] && {
    echo "Error: Failed to get CognitoUserPoolId"
    exit 1
}
echo "USERPOOL_ID = $USERPOOL_ID"

# USERPOOL_CLIENTID
export USERPOOL_CLIENTID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolClientId`].OutputValue' \
    --output text)
[ -z "$USERPOOL_CLIENTID" ] && {
    echo "Error: Failed to get CognitoUserPoolClientId"
    exit 1
}
echo "USERPOOL_CLIENTID = $USERPOOL_CLIENTID"

# BUCKET_NAME
export BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`PiiS2BucketName`].OutputValue' \
    --output text)
[ -z "$BUCKET_NAME" ] && {
    echo "Error: Failed to get PiiS2BucketName"
    exit 1
}
echo "BUCKET_NAME = $BUCKET_NAME"

# KNOWLEDGEBASE_ID
export KNOWLEDGEBASE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseIdS2`].OutputValue' \
    --output text)
[ -z "$KNOWLEDGEBASE_ID" ] && {
    echo "Error: Failed to get KnowledgeBaseIdS2"
    exit 1
}
echo "KNOWLEDGEBASE_ID = $KNOWLEDGEBASE_ID"

# DATASOURCE_ID
export DATASOURCE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`KBDataSourceIDS2`].OutputValue' \
    --output text)
[ -z "$DATASOURCE_ID" ] && {
    echo "Error: Failed to get KBDataSourceIDS2"
    exit 1
}
echo "DATASOURCE_ID = $DATASOURCE_ID"

# API_ENDPOINT
export API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayEndpointS2`].OutputValue' \
    --output text)
[ -z "$API_ENDPOINT" ] && {
    echo "Error: Failed to get APIGatewayEndpointS2"
    exit 1
}
echo "API_ENDPOINT = $API_ENDPOINT"

# echo "Get Cloudformation Outputs"
# # Read required outputs
# USERPOOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
# USERPOOL_CLIENTID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolClientId`].OutputValue' --output text)
# BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`PiiS2BucketName`].OutputValue' --output text)
# KNOWLEDGEBASE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseIdS2`].OutputValue' --output text)
# DATASOURCE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`KBDataSourceIDS2`].OutputValue' --output text)
# API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayEndpointS2`].OutputValue' --output text)

echo "Reset default passwords for Cognito users"

validate_password() {
    local password=$1
    # Minimum 8 characters, at least one uppercase, one lowercase, one number, and one special character
    if [[ ${#password} -lt 8 || ! $password =~ [A-Z] || ! $password =~ [a-z] || ! $password =~ [0-9] || ! $password =~ ['!@#\$%^&*()_+'] ]]; then
        return 1
    fi
    return 0
}

# Prompt for new password securely (hidden input)
TIMEOUT=300 # 5 minutes
TIMER=0
while true; do
    if [ $TIMER -ge $TIMEOUT ]; then
        echo "Password entry timed out after ${TIMEOUT} seconds"
        exit 1
    fi

    echo "Password requirements:"
    echo "- Minimum 8 characters"
    echo "- At least one uppercase letter"
    echo "- At least one lowercase letter"
    echo "- At least one number"
    echo "- At least one special character (!@#\$%^&*()_+)"

    # First password entry
    read -s -p "Enter new password for test users: " PASSWORD
    echo

    # Validate password strength
    if ! validate_password "$PASSWORD"; then
        echo "Password does not meet requirements. Please try again."
        continue
    fi

    # Confirm password
    read -s -p "Confirm new password: " PASSWORD_CONFIRM
    echo

    # Check if passwords match
    if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
        echo "Passwords do not match. Please try again."
        continue
    fi

    break
done

echo "Resetting password for john@example.com"
if aws cognito-idp admin-set-user-password \
    --user-pool-id $USERPOOL_ID \
    --username john@example.com \
    --password $PASSWORD \
    --permanent; then
    echo "Password reset successful!"
else
    echo "Failed to reset password. Please check the error message above."
    exit 1
fi

echo "Resetting password for jane@example.com"
if aws cognito-idp admin-set-user-password \
    --user-pool-id $USERPOOL_ID \
    --username jane@example.com \
    --password $PASSWORD \
    --permanent; then
    echo "Password reset successful!"
else
    echo "Failed to reset password. Please check the error message above."
    exit 1
fi

# Verify input directory exists
if [ ! -d "../data/" ]; then
    echo "Error: ../data/ directory not found!"
    echo "Please run synthetic_data.py script and run this script again"
    exit 1
fi


echo "Generating sample admin data"
if ! curl -L -o "../data/admin_sample.pdf" "https://www.cms.gov/research-statistics-data-and-systems/monitoring-programs/medicare-ffs-compliance-programs/cert/downloads/ex_pmd_newpdf"; then
    echo "Error: Failed to download admin sample data"
else
    cat <<'EOF' >"../data/admin_sample.pdf.metadata.json"
{
    "metadataAttributes": {
        "accessType": {
            "value": {
                "type": "STRING",
                "stringValue": "admin"
            },
            "includeForEmbedding": true
        }
    }
}
EOF

fi

echo "Upload test data to S3 bucket"
aws s3 cp ../data/admin_sample.pdf s3://$BUCKET_NAME/admin_sample.pdf
aws s3 cp ../data/admin_sample.pdf.metadata.json s3://$BUCKET_NAME/admin_sample.pdf.metadata.json
aws s3 cp ../data/financial s3://$BUCKET_NAME/ --recursive
aws s3 cp ../data/medical s3://$BUCKET_NAME/ --recursive

### Sync knowledgebase
echo "Sync KnowledgeBase"
SYNC_JOB_ID=$(aws bedrock-agent start-ingestion-job --knowledge-base-id $KNOWLEDGEBASE_ID --data-source-id $DATASOURCE_ID --query 'ingestionJob.ingestionJobId' --output text)

if [ -z "$SYNC_JOB_ID" ]; then
    echo "Failed to start sync job"
    exit 1
fi

echo "Sync job started with ID: $SYNC_JOB_ID"

# Monitor sync status
echo "Monitoring sync status..."
while true; do
    STATUS=$(aws bedrock-agent get-ingestion-job --knowledge-base-id $KNOWLEDGEBASE_ID --data-source-id $DATASOURCE_ID --ingestion-job-id $SYNC_JOB_ID --query 'ingestionJob.status' --output text)

    echo "Current status: $STATUS"

    if [ "$STATUS" = "COMPLETE" ]; then
        echo "Sync completed successfully"
        break
    elif [ "$STATUS" = "FAILED" ]; then
        echo "Sync failed"
        exit 1
    elif [ "$STATUS" = "STOPPED" ]; then
        echo "Sync was stopped"
        exit 1
    fi

    sleep 1
done

# Verify streamlit app directory exists
if [ ! -d "streamlit_app" ] || [ ! -f "streamlit_app/app.py" ]; then
    echo "Error: Streamlit app not found at streamlit_app/app.py"
    exit 1
fi

### Start streamlit
echo "Starting Streamlit app..."
streamlit run streamlit_app/app.py $USERPOOL_CLIENTID $API_ENDPOINT
