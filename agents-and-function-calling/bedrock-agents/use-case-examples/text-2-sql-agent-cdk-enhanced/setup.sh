#!/bin/bash


# Upgrade pip
pip install --upgrade pip
pip install --upgrade boto3

# Install nvm if it is not already installed
if ! command -v nvm &> /dev/null; then
  echo "nvm not found, installing..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
  # Load nvm into the current shell session
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
fi

# Load nvm into the current shell session
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Install Node.js version 18 using nvm
nvm install 18
nvm use 18


# Install and update AWS CDK globally
npm install -g aws-cdk@latest
npm update -g aws-cdk

# Install Node.js project dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
