#!/bin/bash

# Enable error handling
set -e
set -o pipefail

# Stack name
STACK_NAME="CdkPiiScenario1Stack"

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

# Check if Macie is enabled
MACIE_STATUS=$(aws macie2 get-macie-session --query "status" --output text 2>/dev/null || echo "DISABLED")
if [[ "$MACIE_STATUS" == "DISABLED" ]]; then
    echo "Error: Amazon Macie is not enabled. Please enable Macie before running this script."
    echo "Refer to https://docs.aws.amazon.com/macie/latest/user/getting-started.html for instructions."
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

# INPUT_BUCKET
export INPUT_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`SourceBucketName`].OutputValue' \
    --output text)
[ -z "$INPUT_BUCKET" ] && {
    echo "Error: Failed to get SourceBucketName"
    exit 1
}
echo "INPUT_BUCKET = $INPUT_BUCKET"

# JOB_TRACKING_TABLE
export JOB_TRACKING_TABLE=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`DynamoDBTrackingTable`].OutputValue' \
    --output text)
[ -z "$JOB_TRACKING_TABLE" ] && {
    echo "Error: Failed to get DynamoDBTrackingTable"
    exit 1
}
echo "JOB_TRACKING_TABLE = $JOB_TRACKING_TABLE"

# COMPREHEND_LAMBDA
export COMPREHEND_LAMBDA=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`ComprehendLambdaFunction`].OutputValue' \
    --output text)
[ -z "$COMPREHEND_LAMBDA" ] && {
    echo "Error: Failed to get ComprehendLambdaFunction"
    exit 1
}
echo "COMPREHEND_LAMBDA = $COMPREHEND_LAMBDA"

# MACIE_LAMBDA
export MACIE_LAMBDA=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`MacieLambdaFunction`].OutputValue' \
    --output text)
[ -z "$MACIE_LAMBDA" ] && {
    echo "Error: Failed to get MacieLambdaFunction"
    exit 1
}
echo "MACIE_LAMBDA = $MACIE_LAMBDA"

# KB_ID
export KB_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`BedrockKBId`].OutputValue' \
    --output text)
[ -z "$KB_ID" ] && {
    echo "Error: Failed to get BedrockKBId"
    exit 1
}
echo "KB_ID = $KB_ID"

# DATASOURCE_ID
export DATASOURCE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`BedrockKBDataSourceID`].OutputValue' \
    --output text)
[ -z "$DATASOURCE_ID" ] && {
    echo "Error: Failed to get BedrockKBDataSourceID"
    exit 1
}
echo "DATASOURCE_ID = $DATASOURCE_ID"

# GUARDRAILS_ID
export GUARDRAILS_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`GuardrailsId`].OutputValue' \
    --output text)
[ -z "$GUARDRAILS_ID" ] && {
    echo "Error: Failed to get GuardrailsId"
    exit 1
}
echo "GUARDRAILS_ID = $GUARDRAILS_ID"

# USER_POOL_ID
export USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
    --output text)
[ -z "$USER_POOL_ID" ] && {
    echo "Error: Failed to get UserPoolId"
    exit 1
}
echo "USER_POOL_ID = $USER_POOL_ID"

# COGNITO_CLIENT_ID
export COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoClientId`].OutputValue' \
    --output text)
[ -z "$COGNITO_CLIENT_ID" ] && {
    echo "Error: Failed to get CognitoClientId"
    exit 1
}
echo "COGNITO_CLIENT_ID = $COGNITO_CLIENT_ID"

# API_ENDPOINT
export API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayURL`].OutputValue' \
    --output text)
[ -z "$API_ENDPOINT" ] && {
    echo "Error: Failed to get APIGatewayURL"
    exit 1
}
echo "API_ENDPOINT = $API_ENDPOINT"

# Verify input directory exists
if [ ! -d "../data/" ]; then
    echo "Error: ../data/ directory not found!"
    echo "Please run synthetic_data.py script and run this script again"
    exit 1
fi

echo "Upload test data to S3 bucket"
aws s3 cp ../data/ s3://$INPUT_BUCKET/inputs/ --recursive --exclude "*" --include "*.txt"
check_command "S3 upload"

echo "Invoke Comprehend Lambda"
aws lambda invoke \
    --function-name $COMPREHEND_LAMBDA \
    response_comprehend.json
check_command "Comprehend Lambda invocation"

echo "Reset default passwords for Cognito user (jane@example.com)"

validate_password() {
    local password=$1
    # Minimum 8 characters, at least one uppercase, one lowercase, one number, and one special character
    if [[ ${#password} -lt 8 || ! $password =~ [A-Z] || ! $password =~ [a-z] || ! $password =~ [0-9] || ! $password =~ ['!@#\$%^&*()_+'] ]]; then
        return 1
    fi
    return 0
}

# Add timeout for password prompt
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

    read -s -p "Enter new password for test users: " PASSWORD
    echo

    if ! validate_password "$PASSWORD"; then
        echo "Password does not meet requirements. Please try again."
        TIMER=$((TIMER + 30))
        continue
    fi

    read -s -p "Confirm new password: " PASSWORD_CONFIRM
    echo

    if [ "$PASSWORD" != "$PASSWORD_CONFIRM" ]; then
        echo "Passwords do not match. Please try again."
        TIMER=$((TIMER + 30))
        continue
    fi

    break
done

echo "Resetting password for jane@example.com"
aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username jane@example.com \
    --password "$PASSWORD" \
    --permanent
check_command "Cognito password reset"

# Add timeout for job monitoring
MAX_WAIT_TIME=1800 # 0.5 hour
START_TIME=$(date +%s)

echo "Monitoring Comprehend Job completion. Please wait..."
while true; do
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - START_TIME)) -gt $MAX_WAIT_TIME ]; then
        echo "Error: Comprehend job monitoring timed out after 1 hour"
        exit 1
    fi

    COMPREHEND_STATUS=$(aws dynamodb scan \
        --table-name $JOB_TRACKING_TABLE \
        --filter-expression "comprehend_job_status = :status" \
        --expression-attribute-values '{":status":{"S":"COMPLETED"}}' \
        --query 'Items[0].comprehend_job_status.S' \
        --output text)

    if [ "$COMPREHEND_STATUS" == "COMPLETED" ]; then
        echo "Comprehend PII redaction job completed successfully"
        break
    elif [ "$COMPREHEND_STATUS" == "FAILED" ]; then
        echo "Comprehend PII redaction job failed"
        exit 1
    fi
    echo "Waiting for Comprehend job completion  (next check in 60s)..."
    sleep 60
done

echo "Invoking Macie Lambda for sensitive data detection..."
aws lambda invoke \
    --function-name $MACIE_LAMBDA \
    response_macie.json
check_command "Macie Lambda invocation"

START_TIME=$(date +%s)
echo "Monitoring Macie Job completion. Please wait..."
while true; do
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - START_TIME)) -gt $MAX_WAIT_TIME ]; then
        echo "Error: Macie job monitoring timed out after 1 hour"
        exit 1
    fi

    MACIE_STATUS=$(aws dynamodb scan \
        --table-name $JOB_TRACKING_TABLE \
        --query 'Items[0].macie_job_status.S' \
        --output text)

    if [ "$MACIE_STATUS" == "COMPLETE" ]; then
        echo "Macie sensitive data detection job completed successfully"
        break
    elif [ "$MACIE_STATUS" == "FAILED" ]; then
        echo "Macie sensitive data detection job failed"
        exit 1
    fi
    echo "Waiting for Macie job completion (next check in 60s)..."
    sleep 60
done

# echo "Invoking Macie Lambda again to process findings and move files..."
# aws lambda invoke \
#     --function-name $MACIE_LAMBDA \
#     response_macie.json
# check_command "Macie Lambda invocation"


echo "KnowledgeBase data ingestion..."
SYNC_JOB_ID=$(aws bedrock-agent start-ingestion-job \
    --knowledge-base-id $KB_ID \
    --data-source-id $DATASOURCE_ID \
    --query 'ingestionJob.ingestionJobId' \
    --output text)

if [ -z "$SYNC_JOB_ID" ]; then
    echo "Failed to start sync job"
    exit 1
fi

echo "Sync job started with ID: $SYNC_JOB_ID"

echo "Monitoring KnowledgeBase Ingestion job..."
while true; do
    STATUS=$(aws bedrock-agent get-ingestion-job \
        --knowledge-base-id $KB_ID \
        --data-source-id $DATASOURCE_ID \
        --ingestion-job-id $SYNC_JOB_ID \
        --query 'ingestionJob.status' \
        --output text)

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

# Run streamlit app
echo "Starting Streamlit app..."
streamlit run streamlit_app/app.py $COGNITO_CLIENT_ID $API_ENDPOINT