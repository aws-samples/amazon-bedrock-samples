# Deployment Guide
---

## Content
- [Pre-Implementation](#pre-Implementation)
- [Get Model Access for Titan Image Generator](#get-model-access)

## Pre-Implementation
By default, [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) uses a temporary session that it generates from your user credentials for stack operations. If you specify a service role, CloudFormation will instead use that role's credentials.

To deploy this solution, your IAM user/role or service role must have permissions to deploy the resources specified in the CloudFormation template. For more details on [AWS Identity and Access Management](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html) (IAM) with CloudFormation, please refer to the [AWS CloudFormation User Guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-template.html).

You must also have [AWS Command Line Interface](https://aws.amazon.com/cli/) (CLI) installed. For instructions on installing AWS CLI, please see [Installing, updating, and uninstalling the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html).

Run the following commands to deploy the resources:
1. ```cd amazon-bedrock-samples/agents/hr-agent/shell/```
2. ```chmod u+x create-hr-resources.sh```
3. ```export STACK_NAME=<YOUR-STACK-NAME>``` # Stack name must be lower case for S3 bucket naming convention
4. ```export SNS_EMAIL=<YOUR-EMPLOYEE-EMAIL>``` # Email used for SNS notifications. You need to confirm SNS subscription to receive emails sent by the agent.
5. ```export AWS_REGION=<YOUR-STACK-REGION>``` # Stack deployment region
6. ```source ./create-hr-resources.sh```

## Knowledge Base Preparation
- Create a Knowledge Base manually, using the S3 bucket created by CloudFormation `<STACK_NAME>-customer-resources/agent/knowledge-base-assets/`.
- Associate the Knowledge Base with the Agent, using instruction "Company's leave and pay policy."

Once creation is completed, go to the AWS console to prepare the Agent and test.

## Get Model Access for Titan Image Generator G1
One of the action API requires access to the Titan Image Generator model, therefore we need to request the model permission.

To request access to a model:
1. Login to AWS Console and go to "Amazon Bedrock".
2. select Model access at the bottom of the left navigation pane in the Amazon Bedrock management console.
3. On the Model access page, select "Manage model access". 
4. Select the checkboxes next to the Titan Image Generator G1 model.
5. Select Save changes to request access. The changes may take several minutes to take place.
6. If your request is successful, the Access status changes to Access granted.


---

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0