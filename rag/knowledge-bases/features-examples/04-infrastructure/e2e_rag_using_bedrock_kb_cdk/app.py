#!/usr/bin/env python3
import os

import aws_cdk as cdk
from constructs import DependencyGroup

from config import EnvSettings, KbConfig
# from e2e_rag_using_bedrock_kb_cdk.e2e_rag_using_bedrock_kb_cdk_stack import E2ERagUsingBedrockKbCdkStack
from stacks.kb_role_stack import KbRoleStack
from stacks.kb_infra_stack import KbInfraStack
from stacks.vector_store_stacks.aurora_infra_stack import AuroraStack
from stacks.vector_store_stacks.oss_infra_stack import OpenSearchServerlessStack

app = cdk.App()

# Get the vector store parameter from user config in config.py
vector_store_type = KbConfig.VECTOR_STORE_TYPE

if vector_store_type not in ["OSS", "Aurora"]:
    raise ValueError("VECTOR_STORE_TYPE in config.py must be either 'OSS' or 'Aurora'")

# create IAM role for e2e RAG
kbRole_stack = KbRoleStack(app, "KbRoleStack")

# setup vector store (Aurora or OSS) based on user parameter
if vector_store_type == "OSS":
    infra_stack = OpenSearchServerlessStack(app, "OpenSearchServerlessStack")
elif vector_store_type == "Aurora":
    infra_stack = AuroraStack(app, "AuroraStack")

# create Knowledgebase and datasource
kbInfra_stack = KbInfraStack(app, "KbInfraStack")

# set up dependencies 
infra_stack.add_dependency(kbRole_stack)
kbInfra_stack.add_dependency(infra_stack)

app.synth()
