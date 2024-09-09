#!/usr/bin/env python3
import os

import aws_cdk as cdk
from lib.cdk_bedrock_guardrail_stack import CdkBedrockGuardrailStack

app = cdk.App()
CdkBedrockGuardrailStack(app, "CdkBedrockGuardrailStack")

app.synth()
