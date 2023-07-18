#!/bin/bash

# Download the private dependencies for the project

echo "Creating directory"
mkdir -p ./dependencies
cd ./dependencies
echo "Downloading dependencies"
curl -sS https://preview.documentation.bedrock.aws.dev/Documentation/SDK/bedrock-python-sdk.zip > sdk.zip
echo "Unpacking dependencies"
unzip sdk.zip
rm sdk.zip
cd ..
echo "Creating a python environment"
python -m pip install virtualenv
python -m virtualenv python
echo "Installing dependencies"
source python/bin/activate
pip install ./dependencies/botocore-1.29.162-py3-none-any.whl ./dependencies/boto3-1.26.162-py3-none-any.whl ./dependencies/awscli-1.27.162-py3-none-any.whl
zip -r bedrock_layer.zip ./python/lib/python3.9/site-packages/
rm -r ./python
echo "Done"