# Clean up
---

To avoid charges in your AWS account, please clean up the solution's provisioned resources.

## Delete `bedrock-insurance-agent.yml` CloudFormation Stack
The following commands use the default stack name. If you customized the stack name, adjust the commands accordingly.

```sh
# export STACK_NAME=<YOUR-STACK-NAME>
./delete-customer-resources.sh
```

#### Resource Deletion Automation Script
The [delete-stack.sh](../shell/delete-customer-resources.sh) shell script deletes the resources that were originally provisioned from the [bedrock-insurance-agent.yml](../cfn/bedrock-insurance-agent.yml) CloudFormation stack.

```sh
# cd amazon-bedrock-samples/agents/bedrock-insurance-agent/shell/
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
```

---

[Back to README](../README.md)

---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
