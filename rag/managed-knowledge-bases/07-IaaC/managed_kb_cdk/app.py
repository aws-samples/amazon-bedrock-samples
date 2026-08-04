#!/usr/bin/env python3
"""
CDK app for deploying an end-to-end Bedrock Managed Knowledge Base with S3 data source.

Much simpler than DIY KB — no vector store stack needed.
Bedrock manages the storage, indexing, and retrieval infrastructure.
"""

import aws_cdk as cdk

from config import EnvSettings
from stacks.managed_kb_stack import ManagedKbStack

app = cdk.App()

# Single stack — creates S3 bucket, IAM role, Managed KB, and S3 data source
ManagedKbStack(
    app,
    "ManagedKbStack",
    env=cdk.Environment(
        account=EnvSettings.ACCOUNT_ID,
        region=EnvSettings.ACCOUNT_REGION,
    ),
)

app.synth()
