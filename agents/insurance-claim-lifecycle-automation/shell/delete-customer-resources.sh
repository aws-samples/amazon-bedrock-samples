# If not already cloned, clone the remote repository (https://github.com/aws-samples/amazon-bedrock-samples) and change working directory to insurance agent shell folder
# cd amazon-bedrock-samples/agents/insurance-claim-lifecycle-automation/shell/
# chmod u+x delete-customer-resources.sh
# ./delete-customer-resources.sh

echo "Emptying and Deleting S3 Bucket: $ARTIFACT_BUCKET_NAME"

aws s3 rm s3://${ARTIFACT_BUCKET_NAME} --recursive
aws s3 rb s3://${ARTIFACT_BUCKET_NAME}

echo "Deleting CloudFormation Stack: $STACK_NAME"

aws cloudformation delete-stack --stack-name $STACK_NAME
aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].StackStatus"
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME
