# cd generative-ai-amazon-bedrock-langchain-agent-example/shell/
# chmod u+x delete-customer-resources.sh
# ./delete-customer-resources.sh

echo "Emptying and Deleting S3 Bucket: $ARTIFACT_BUCKET_NAME"

aws s3 rm s3://${ARTIFACT_BUCKET_NAME} --recursive
aws s3 rb s3://${ARTIFACT_BUCKET_NAME}

echo "Emptying and Deleting S3 Bucket: $KB_BUCKET_NAME"

aws s3 rm s3://${KB_BUCKET_NAME} --recursive
aws s3 rb s3://${KB_BUCKET_NAME}

echo "Deleting CloudFormation Stack: $STACK_NAME"

aws cloudformation delete-stack --stack-name $STACK_NAME
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME