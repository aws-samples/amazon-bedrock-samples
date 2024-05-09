#!/bin/bash -eu

#########
# LEGAL #
######### 

# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
  
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### DESCRIPTION ###

# This script prepares the AWS CloudFormation templates to deploy the end-to-end RAG workflow
# using Knowledgebases for Amazon Bedrock

#############
### USAGE ###
#############

# 0. Call the script from the root of the repo:
#       Syntax: 
#       $ bash ./deploy.sh [region] [deployment_bucket_name]
#       Example:
#       $ bash ./deploy.sh us-east-1 my-cool-stack-deployment-bucket
# 1. Echo Deployment Parameters
#       To confirm the deployment parameters and make a go/no go launch decision
# 2. Create S3 bucket for deployment artifacts (if needed)
# 3. Update the CloudFormation templates with deployment bucket name
#        Note: this deploy.sh is for a SINGLE REGION deployment

#####################################
### 1. ECHO DEPLOYMENT PARAMETERS ###
#####################################

## Enter Deployment Checks

# Check for args > 0
#if [[ $# -eq 0 ]] ; then
#    echo "No arguments supplied"
#    echo
#    echo "Usage: bash ./deploy.sh [region] [deployment_bucket_name]"
#    exit 1
#fi

#####################################

## AWS Deployment Region
AWS_REGION=${1:-us-east-1}

#####################################

AWS="aws --output=text --region ${AWS_REGION}"
ACCOUNT_ID=$(${AWS} sts get-caller-identity --query 'Account')

#####################################
# Name of Amazon S3 Bucket used for CloudFormation deployments

DEPLOYMENT_BUCKET=${2:-e2e-rag-deployment-${ACCOUNT_ID}-${AWS_REGION}}

#####################################

## Echo Deployment Parameters
echo "[*] Verifying deployment parameters..."
echo "[X] Account ID: ${ACCOUNT_ID}"
echo "[X] Region: ${AWS_REGION}"
echo "[X] Deployment bucket name: ${DEPLOYMENT_BUCKET}"

#####################################
### 2. CREATE DEPLOYMENT BUCKET  ###
#####################################
# Do we have to create the bucket?
_BUCKETS=$(for _BUCKET in $(${AWS} s3api list-buckets --query 'Buckets[].Name'); do echo $_BUCKET; done)
if [ -z "$(grep "${DEPLOYMENT_BUCKET}" <<< ${_BUCKETS} || true)" ]; then
  echo -n "[!] Create new bucket '${DEPLOYMENT_BUCKET}' ? [Y/n] "
  read ANS
  if [ -z "${ANS}" -o "${ANS:0:1}" = "Y" -o "${ANS:0:1}" = "y" ]; then
    #${AWS} s3api create-bucket --acl private --create-bucket-configuration LocationConstraint=${AWS_REGION} --bucket ${DEPLOYMENT_BUCKET}
    ${AWS} s3api create-bucket --acl private --bucket ${DEPLOYMENT_BUCKET}
    
#    # create 'artifacts' objects (i.e. folders) inside the ${DEPLOYMENT_BUCKET}
#    DEPLOY_ARTIFACT_DIR=${DEPLOY_ARTIFACT_DIR:-artifacts}
#    ${AWS} s3api put-object --bucket ${DEPLOYMENT_BUCKET} --key ${DEPLOY_ARTIFACT_DIR}/

  else
    echo "Usage: bash ./scripts/deploy.sh [stack_name] [environment] [region] [deployment_bucket_name]"
    exit 1
  fi
fi

echo
echo "Press [Enter] to continue or Ctrl-C to abort."
read

# UPLOAD REQUIRED ARTIFACTS to Deployment S3 Bucket
LOCAL_ARTIFACT_DIR="artifacts"
aws s3 cp ${LOCAL_ARTIFACT_DIR} s3://${DEPLOYMENT_BUCKET}/${LOCAL_ARTIFACT_DIR}/ --recursive

###########################################################
### 3. UPDATE THE TEMPLATES WITH DEPLOYMENT BUCKET PATH ###
###########################################################

# Read the main-template-out-tmp.yml file into a variable
yml_file_contents=$(cat templates/main-template-out-tmp.yml)
# Use the sed command to replace the old parameter name with the new parameter name
updated_yml_file_contents=$(sed "s/pDeploymentBucket/${DEPLOYMENT_BUCKET}/g"<<< "$yml_file_contents")
# Write the updated YAML file to a new file
echo "$updated_yml_file_contents" >templates/main-template-out.yml

# Read the oss-infra-template-tmp.template file into a variable
yml_file_contents=$(cat templates/oss-infra-template-tmp.template)
# Use the sed command to replace the old parameter name with the new parameter name
updated_yml_file_contents=$(sed "s/pDeploymentBucket/${DEPLOYMENT_BUCKET}/g"<<< "$yml_file_contents")
# Write the updated YAML file to a new file
echo "$updated_yml_file_contents" >templates/oss-infra-template.template

# UPLOAD the templates to Deployment S3 Bucket
LOCAL_TEMPLATES_DIR="templates"
aws s3 cp ${LOCAL_TEMPLATES_DIR} s3://${DEPLOYMENT_BUCKET}/${LOCAL_TEMPLATES_DIR}/ --recursive

echo "Main CloudFormation template S3 URL:"
echo "https://${DEPLOYMENT_BUCKET}.s3.amazonaws.com/templates/main-template-out.yml"

echo "**********************************************************************************************************"
echo "Please note the Main CloudFormation template S3 URL, this will be needed for CloudFormation deployment."
echo "**********************************************************************************************************"
cat << __EOF__

All done. Now Deploy the RAG Workflow.

__EOF__
