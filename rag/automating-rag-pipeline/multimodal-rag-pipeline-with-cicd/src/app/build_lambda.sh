#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Check if the required environment variables are set
if [ -z "$CODE_PIPELINE_NAME" ] || [ -z "$STAGE_NAME" ]; then
  echo "Error: CODE_PIPELINE_NAME or STAGE_NAME environment variable is not set."
  exit 1
fi

# Construct the exact SSM parameter name
PARAMETER_NAME="/${CODE_PIPELINE_NAME}/${STAGE_NAME}/lambda-package-bucket-name"
REGION="${AWS_REGION}"

echo "Retrieving S3 bucket name from SSM parameter: $PARAMETER_NAME in region $REGION"

# Retrieve the S3 bucket name from SSM Parameter Store
LAMBDA_PACKAGE_BUCKET=$(aws ssm get-parameter --name "$PARAMETER_NAME" --region "$REGION" --query "Parameter.Value" --output text)

if [ -z "$LAMBDA_PACKAGE_BUCKET" ]; then
  echo "Error: Could not retrieve the Lambda package bucket name from SSM."
  exit 1
fi

echo "Using S3 bucket: $LAMBDA_PACKAGE_BUCKET"
echo "Current working directory: $(pwd)",
ls -ltr
echo "File contents: ls -ltr",

# Variables
SRC_DIR="./src/app/CustomChunker"
# SRC_DIR="./rag/automating-rag-pipeline/multimodal-rag-pipeline-with-cicd/src/app/build_lambda.sh"
TMP_DIR="/tmp/my-lambda-package"  # Use /tmp for temporary storage
ZIP_FILE="$TMP_DIR/lambda.zip"
S3_KEY="custom_chunking_lambda_package.zip"

# Step 1: Prepare the temp directory
echo "Cleaning up old package..."
rm -rf "$TMP_DIR"  # Remove old temp folder if it exists
mkdir -p "$TMP_DIR"  # Create a new temp folder

# Step 2: Copy the Python script and dependencies to the temp folder
echo "Copying Python code to temp directory..."
cp -R "$SRC_DIR"/* "$TMP_DIR/"

# Step 3: Install dependencies in the temp folder
echo "Installing dependencies..."
pip install pypdf -t "$TMP_DIR" --quiet

# Step 4: Create the zip package
echo "Creating Lambda package zip file..."
cd "$TMP_DIR"
if zip -r "$ZIP_FILE" ./*; then
  echo "Lambda package created successfully at: $ZIP_FILE"
else
  echo "Error: Failed to create the Lambda package zip file."
  exit 1
fi

# Step 5: Upload the zip package to the specified S3 bucket
echo "Uploading Lambda package to S3 bucket: $LAMBDA_PACKAGE_BUCKET"
if aws s3 cp "$ZIP_FILE" "s3://$LAMBDA_PACKAGE_BUCKET/$S3_KEY"; then
  echo "Lambda package uploaded successfully to: s3://$LAMBDA_PACKAGE_BUCKET/$S3_KEY"
else
  echo "Error: Failed to upload the Lambda package to S3."
  exit 1
fi
