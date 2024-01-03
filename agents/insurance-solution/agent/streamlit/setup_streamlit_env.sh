#!/bin/bash

# Name for the virtual environment
VENV_NAME="agent-env"

# Check if virtual environment already exists
if [ ! -d "$VENV_NAME" ]; then
    echo "Creating virtual environment..."
    python -m venv "$VENV_NAME"
    if [ $? -eq 0 ]; then
        echo "Virtual environment '$VENV_NAME' created successfully."
    else
        echo "Failed to create virtual environment."
        exit 1
    fi
fi

# Activate the virtual environment
source "$VENV_NAME/bin/activate"

export BEDROCK_AGENT_ID=<YOUR-AGENT-ID>
export BEDROCK_AGENT_ALIAS_ID=<YOUR-AGENT-ALIAS-ID>
export BEDROCK_KB_ID=<YOUR-KNOWLEDGE-BASE-ID>
export BEDROCK_DS_ID=<YOUR-DATA-SOURCE-ID>
export KB_BUCKET_NAME=<YOUR-KNOWLEDGE-BASE-S3-BUCKET-NAME>
export AWS_REGION=us-east-1

# Install packages listed in requirements.txt using pip within the virtual environment
pip install -r requirements.txt

# Check if pip install command was successful
if [ $? -eq 0 ]; then
    echo "All packages from requirements.txt have been installed successfully."
else
    echo "Failed to install packages from requirements.txt."
fi