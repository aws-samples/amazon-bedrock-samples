#!/bin/bash

# Name for the virtual environment
VENV_NAME="agentenv"

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

export BEDROCK_AGENT_ID=U8TWVNTXPJ
export BEDROCK_AGENT_ALIAS_ID=TSTALIASID
export SESSION_ID=12345
export BEDROCK_KB_ID=9VFKA9OKIZ
export BEDROCK_DS_ID=U4YRTDTOCD
export KB_BUCKET_NAME=bedrock-bedrock-kb
export AWS_REGION=us-east-1

# Install packages listed in requirements.txt using pip within the virtual environment
pip install -r requirements.txt

# Check if pip install command was successful
if [ $? -eq 0 ]; then
    echo "All packages from requirements.txt have been installed successfully."
else
    echo "Failed to install packages from requirements.txt."
fi