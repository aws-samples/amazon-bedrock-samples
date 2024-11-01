#!/usr/bin/env python3
import os
import json
import aws_cdk as cdk

from BedrockAgentStack.BedrockAgentStack_stack import BedrockAgentStack


app = cdk.App()

BedrockAgentStack(app, "BedrockAgentStack")

app.synth()
