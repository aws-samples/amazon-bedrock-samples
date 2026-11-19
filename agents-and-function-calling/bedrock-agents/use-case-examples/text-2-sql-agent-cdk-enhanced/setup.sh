#!/bin/bash

set -e  # Exit on any error

echo "Starting setup for Text to SQL Bedrock Agent CDK Enhanced..."

# Check if Python 3.9+ is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "Error: Python 3.9+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "Python version check passed: $PYTHON_VERSION"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install nvm if it is not already installed
if ! command -v nvm &> /dev/null; then
  echo "nvm not found, installing..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  # Load nvm into the current shell session
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
fi

# Load nvm into the current shell session
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Install Node.js version 20 (LTS) using nvm
echo "Installing Node.js 20 (LTS)..."
nvm install 20
nvm use 20

# Verify Node.js installation
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# Install and update AWS CDK globally
echo "Installing AWS CDK..."
npm install -g aws-cdk@latest

# Verify CDK installation
echo "CDK version: $(cdk --version)"

# Install Node.js project dependencies
echo "Installing Node.js dependencies..."
npm install

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Make sure your AWS CLI is configured with appropriate credentials"
echo "2. Run: cdk bootstrap --profile YOUR_PROFILE --context zip_file_name=EV_WA.zip"
echo "3. Run: cdk deploy --profile YOUR_PROFILE --context zip_file_name=EV_WA.zip --context region=us-east-1"
