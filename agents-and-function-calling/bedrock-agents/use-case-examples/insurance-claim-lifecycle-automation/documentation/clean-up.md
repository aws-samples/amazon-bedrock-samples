# Clean up
---

To avoid charges in your AWS account, please clean up the solution's provisioned resources.

## Delete Emulated Customer Resources
The [delete-customer-resources.sh](../shell/delete-customer-resources.sh) shell script empties and deletes the solution's Amazon S3 bucket and deletes the resources that were originally provisioned from the [bedrock-customer-resources.yml](../cfn/bedrock-customer-resources.yml) CloudFormation stack. The following commands use the default stack name. If you customized the stack name, adjust the commands accordingly.

```sh
# cd amazon-bedrock-samples/agents-and-function-calling-for-bedrock/use-case-examples/insurance-claim-lifecycle-automation/shell/
# chmod u+x delete-customer-resources.sh
./delete-customer-resources.sh
```

The preceding ./delete-customer-resources.sh shell command runs the following AWS CLI commands to delete the emulated customer resources stack and Amazon S3 bucket:

```sh
echo "Emptying and Deleting S3 Bucket: $ARTIFACT_BUCKET_NAME"

aws s3 rm s3://${ARTIFACT_BUCKET_NAME} --region ${AWS_REGION} --recursive
aws s3 rb s3://${ARTIFACT_BUCKET_NAME} --region ${AWS_REGION}

echo "Deleting CloudFormation Stack: $STACK_NAME"

aws cloudformation delete-stack --stack-name $STACK_NAME --region ${AWS_REGION} 
aws cloudformation describe-stacks --stack-name $STACK_NAME --region ${AWS_REGION} --query "Stacks[0].StackStatus"
```

## Delete Agent and Knowledge Base
Follow the instructions for [deleting an agent](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-edit.html#agents-delete) and [deleting a knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-manage.html).

---

## README
see [README](../README.md)

---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
