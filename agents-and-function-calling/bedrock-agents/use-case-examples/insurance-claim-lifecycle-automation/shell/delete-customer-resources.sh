# If not already cloned, clone the remote repository (https://github.com/aws-samples/amazon-bedrock-samples) and change working directory to insurance agent shell folder
# cd amazon-bedrock-samples/agents-and-function-calling-for-bedrock/use-case-examples/insurance-claim-lifecycle-automation
# chmod u+x delete-customer-resources.sh
# ./delete-customer-resources.sh

echo "Emptying and Deleting S3 Bucket: $ARTIFACT_BUCKET_NAME"

aws s3 rm s3://${ARTIFACT_BUCKET_NAME} --region ${AWS_REGION} --recursive
aws s3 rb s3://${ARTIFACT_BUCKET_NAME} --region ${AWS_REGION}

echo "Deleting CloudFormation Stack: $STACK_NAME"

aws cloudformation delete-stack --stack-name $STACK_NAME --region ${AWS_REGION} 
aws cloudformation describe-stacks --stack-name $STACK_NAME --region ${AWS_REGION} --query "Stacks[0].StackStatus"

# aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region ${AWS_REGION} 
# echo "DELETE_COMPLETE"
