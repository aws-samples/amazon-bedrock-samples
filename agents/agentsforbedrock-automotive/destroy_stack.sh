#!/usr/bin/env bash

# export JSII_SILENCE_WARNING_DEPRECATED_NODE_VERSION=true

# npm install -g aws-cdk
# python3 -m venv .venv
# source .venv/bin/activate
# pip3 install -r requirements.txt


ACCOUNT_ID=$(aws sts get-caller-identity --query Account | tr -d '"')
AWS_REGION=$(aws configure get region)
cd ./setup
cdk destroy