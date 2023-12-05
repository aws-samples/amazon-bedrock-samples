# If not already cloned, clone the remote repository (https://github.com/aws-samples/amazon-bedrock-samples) and change working directory to insurance agent shell folder
# cd amazon-bedrock-samples/agents/bedrock-insurance-agent/shell/
# chmod u+x create-kb-data-source.sh
# export STACK_NAME=bedrock-insurance-agent
# source ./create-kb-data-source.sh

export KB_BUCKET_NAME=$STACK_NAME-bedrock-kb
aws s3 mb s3://${KB_BUCKET_NAME} --region us-east-1
aws s3 cp ../agent/knowledge-base-assets/ s3://${KB_BUCKET_NAME}/knowledge-base-assets/ --recursive --exclude ".DS_Store"