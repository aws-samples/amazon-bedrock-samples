# If not already cloned, clone the remote repository (https://github.com/aws-samples/amazon-bedrock-samples) and change working directory to insurance agent shell folder
# cd amazon-bedrock-samples/agents-and-function-calling-for-bedrock/use-case-examples/insurance-claim-lifecycle-automation/shell/
# chmod u+x create-customer-resources.sh

# export STACK_NAME=<YOUR-STACK-NAME> # Stack name must be lower case for S3 bucket naming convention
# export SNS_EMAIL=<YOUR-POLICY-HOLDER-EMAIL> # Email used for SNS notifications
# export EVIDENCE_UPLOAD_URL=<YOUR-EVIDENCE-UPLOAD-URL> # URL provided by the agent to the policy holder for evidence upload
# export AWS_REGION=<YOUR-STACK-REGION> # Stack deployment region

# source ./create-customer-resources.sh

export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ARTIFACT_BUCKET_NAME=$STACK_NAME-customer-resources
export DATA_LOADER_KEY="agent/lambda/data-loader/loader_deployment_package.zip"
export CREATE_CLAIM_KEY="agent/lambda/action-groups/create_claim.zip"
export GATHER_EVIDENCE_KEY="agent/lambda/action-groups/gather_evidence.zip"
export SEND_REMINDER_KEY="agent/lambda/action-groups/send_reminder.zip"

aws s3 mb s3://${ARTIFACT_BUCKET_NAME} --region ${AWS_REGION}
aws s3 cp ../agent/ s3://${ARTIFACT_BUCKET_NAME}/agent/ --region ${AWS_REGION} --recursive --exclude ".DS_Store" --exclude "*/.DS_Store"

export BEDROCK_AGENTS_LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name bedrock-agents-and-function-calling \
    --description "Agents for Bedrock Layer" \
    --license-info "MIT" \
    --content S3Bucket=${ARTIFACT_BUCKET_NAME},S3Key=agent/lambda/lambda-layer/bedrock-agents-layer.zip \
    --compatible-runtimes python3.11 \
    --region ${AWS_REGION} \
    --query LayerVersionArn --output text)

export CFNRESPONSE_LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name cfnresponse \
    --description "cfnresponse Layer" \
    --license-info "MIT" \
    --content S3Bucket=${ARTIFACT_BUCKET_NAME},S3Key=agent/lambda/lambda-layer/cfnresponse-layer.zip \
    --compatible-runtimes python3.11 \
    --region ${AWS_REGION} \
    --query LayerVersionArn --output text)

aws cloudformation create-stack \
--stack-name ${STACK_NAME} \
--template-body file://../cfn/bedrock-customer-resources.yml \
--parameters \
ParameterKey=ArtifactBucket,ParameterValue=${ARTIFACT_BUCKET_NAME} \
ParameterKey=DataLoaderKey,ParameterValue=${DATA_LOADER_KEY} \
ParameterKey=CreateClaimKey,ParameterValue=${CREATE_CLAIM_KEY} \
ParameterKey=GatherEvidenceKey,ParameterValue=${GATHER_EVIDENCE_KEY} \
ParameterKey=SendReminderKey,ParameterValue=${SEND_REMINDER_KEY} \
ParameterKey=BedrockAgentsLayerArn,ParameterValue=${BEDROCK_AGENTS_LAYER_ARN} \
ParameterKey=CfnresponseLayerArn,ParameterValue=${CFNRESPONSE_LAYER_ARN} \
ParameterKey=SNSEmail,ParameterValue=${SNS_EMAIL} \
ParameterKey=EvidenceUploadUrl,ParameterValue=${EVIDENCE_UPLOAD_URL} \
--capabilities CAPABILITY_NAMED_IAM \
--region ${AWS_REGION}

aws cloudformation describe-stacks --stack-name $STACK_NAME --region ${AWS_REGION} --query "Stacks[0].StackStatus"
# aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region ${AWS_REGION}
# aws cloudformation describe-stacks --stack-name $STACK_NAME --region ${AWS_REGION} --query "Stacks[0].StackStatus"
