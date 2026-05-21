#!/usr/bin/env python3

import aws_cdk as cdk
from cdk.cdk_stack import CdkStack
# Uncomment cdk-nag for testing
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from aws_cdk import Aspects

app = cdk.App()

# Enable CDK-nag checks
Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# Create the stack
stack = CdkStack(
    app,
    "CdkStack",
    stack_name="BedrockCostReportingStack",
)

# Enable suppressions
NagSuppressions.add_stack_suppressions(
    stack,
    [
        {
            "id": "AwsSolutions-IAM5",
            "reason": "Wildcard permission to allow access to all objects in the transformed bucket"
        },
        {
            "id": "AwsSolutions-IAM4",
            "reason": "Using AWS managed policies is acceptable for this solution"
        },
        {
            "id": "AwsSolutions-GL1",
            "reason": "CloudWatch Log encryption is not required for this demo solution"
        },
        {
            "id": "AwsSolutions-GL3",
            "reason": "Job bookmark encryption is not required for this demo solution"
        },
        {
            "id": "AwsSolutions-S1",
            "reason": "Transformed logs bucket does not have any sensitive data"
        }
    ]
)

app.synth()
