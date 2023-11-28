#!/usr/bin/env python3
import os

import aws_cdk as cdk

from process_dynamodb_table_bedrock.process_dynamodb_table_bedrock_stack import ProcessDynamoDBTableBedrockStack


app = cdk.App()
ProcessDynamoDBTableBedrockStack(app, "ProcessDynamoDBTableBedrockStack")

app.synth()
