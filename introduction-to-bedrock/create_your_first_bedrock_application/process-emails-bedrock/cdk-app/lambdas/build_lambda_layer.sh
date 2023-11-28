#!/bin/bash

cd lambdas

# Create a new directory for the Python packages
mkdir python
cd python

# Install the Python packages in the new directory
pip install boto3 -t .

# Go back to the parent directory
cd ..

# Create a ZIP archive of the directory
zip -r bedrock_boto3_layer.zip python

rm -rf python