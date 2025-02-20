#!/bin/bash

# Stack name
STACK_NAME="PiiMaskDuringRetrievalStack"

# Check if AWS CLI is installed
if ! command -v aws &>/dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

echo "Get Cloudformation Outputs"
# Read required outputs
USERPOOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
USERPOOL_CLIENTID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolClientId`].OutputValue' --output text)
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`PiiS2BucketName`].OutputValue' --output text)
KNOWLEDGEBASE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseIdS2`].OutputValue' --output text)
DATASOURCE_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`KBDataSourceIDS2`].OutputValue' --output text)
API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayEndpointS2`].OutputValue' --output text)

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
while true; do
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

echo "Generating sample admin data"
curl -L -o "../data/admin_sample.pdf" "https://www.cms.gov/research-statistics-data-and-systems/monitoring-programs/medicare-ffs-compliance-programs/cert/downloads/ex_pmd_newpdf"
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

### Start streamlit
streamlit run streamlit_app/app.py $USERPOOL_CLIENTID $API_ENDPOINT
