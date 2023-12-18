# If not already cloned, clone the remote repository (https://github.com/aws-samples/amazon-bedrock-samples) and change working directory to insurance agent shell folder
# cd amazon-bedrock-samples/agents/bedrock-insurance-agent/shell/
# chmod u+x create-customer-resources.sh
# export KB_ID=<YOUR-KNOWLEDGE-BASE-ID>
# export DS_ID=<YOUR-DATA-SOURCE-ID>
# source ./create-customer-resources.sh

export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ARTIFACT_BUCKET_NAME=$STACK_NAME-customer-resources
export KB_BUCKET_NAME=$STACK_NAME-knowledge-base
export DATA_LOADER_KEY="agent/lambda/data-loader/loader_deployment_package.zip"
export CREATE_CLAIM_KEY="agent/lambda/action-groups/create_claim.zip"
export GATHER_EVIDENCE_KEY="agent/lambda/action-groups/gather_evidence.zip"
export SEND_REMINDER_KEY="agent/lambda/action-groups/send_reminder.zip"

aws s3 mb s3://${KB_BUCKET_NAME} --region us-east-1
aws s3 cp ../agent/knowledge-base-assets/ s3://${KB_BUCKET_NAME}/knowledge-base-assets/ --recursive --exclude ".DS_Store"

aws s3 mb s3://${ARTIFACT_BUCKET_NAME} --region us-east-1
aws s3 cp ../agent/ s3://${ARTIFACT_BUCKET_NAME}/agent/ --recursive --exclude ".DS_Store"

export BEDROCK_AGENTS_LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name bedrock-agents \
    --description "Agents for Bedrock Layer" \
    --license-info "MIT" \
    --content S3Bucket=${ARTIFACT_BUCKET_NAME},S3Key=agent/lambda/lambda-layer/bedrock-agents-layer.zip \
    --compatible-runtimes python3.11 \
    --query LayerVersionArn --output text)

aws cloudformation create-stack \
--stack-name ${STACK_NAME} \
--template-body file://../cfn/bedrock-insurance-agent.yml \
--parameters \
ParameterKey=ArtifactBucket,ParameterValue=${ARTIFACT_BUCKET_NAME} \
ParameterKey=DataLoaderKey,ParameterValue=${DATA_LOADER_KEY} \
ParameterKey=CreateClaimKey,ParameterValue=${CREATE_CLAIM_KEY} \
ParameterKey=GatherEvidenceKey,ParameterValue=${GATHER_EVIDENCE_KEY} \
ParameterKey=SendReminderKey,ParameterValue=${SEND_REMINDER_KEY} \
ParameterKey=BedrockAgentsLayerArn,ParameterValue=${BEDROCK_AGENTS_LAYER_ARN} \
ParameterKey=SNSEmail,ParameterValue=${SNS_EMAIL} \
ParameterKey=CustomerWebsiteUrl,ParameterValue=${CUSTOMER_WEBSITE_URL} \
--capabilities CAPABILITY_NAMED_IAM

aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].StackStatus"
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME