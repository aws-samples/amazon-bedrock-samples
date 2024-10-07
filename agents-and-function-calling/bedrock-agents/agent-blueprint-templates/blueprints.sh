#!/bin/bash

# Define available stacks by reading from lib/stacks
declare -a stacks=()
for folder in ./lib/stacks/*; do
    if [ -d "$folder" ]; then
        stack_name=$(basename "$folder")
        stacks+=("$stack_name")
    fi
done

# Install dependencies using npm
install_dependencies() {
  echo "Installing dependencies..."

  # Check if nvm is installed
  if ! command -v nvm &> /dev/null; then
    echo "nvm is not installed. Installing..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
    export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm
  fi

  # Check if Node.js and npm are installed
  if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Installing..."
    nvm install --lts
    nvm use --lts
  else
    echo "Node.js is already installed."
  fi

  # Install AWS CLI
  if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Installing..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
  else
    echo "AWS CLI is already installed."
  fi

  # Install AWS CDK
  if ! command -v cdk &> /dev/null; then
    echo "AWS CDK is not installed. Installing..."
    npm install -g aws-cdk
  else
    echo "AWS CDK is already installed."
  fi

  echo "All set! Configure your aws cli using the options defined here: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html"
}


# List available stacks
list_stacks() {
  echo "Available stacks:"
  for stack in "${stacks[@]}"; do
    echo "- $stack"
  done
}

# Deploy selected stack
deploy_stack() {
  local stack="$1"
  local stack_found=false

  # Check if the provided stack is valid
  for s in "${stacks[@]}"; do
    if [ "$s" == "$stack" ]; then
      stack_found=true
      break
    fi
  done

  if [ "$stack_found" == false ]; then
    echo "Invalid stack: $stack"
    return
  fi
  
  # Fetch account and region infor from AWS profile
  accountId=$(aws sts get-caller-identity --query Account --output text)
  region=$(aws configure get region)

  # Ask the user to confirm or input the account ID
  read -p "The retrieved account ID from env is $accountId. Is this correct? (y/n) " confirm
  if [ "$confirm" != "y" ]; then
      read -p "Please enter the correct account ID: " accountId
  fi

  # Ask the user to confirm or input the region
  read -p "The retrieved region from env is $region. Is this correct? (y/n) " confirm
  if [ "$confirm" != "y" ]; then
      read -p "Please enter the correct region: " region
  fi

  # Set the CDK_DEFAULT environment variables
  export USER_ACCOUNT=$accountId
  export USER_REGION=$region
  export STACK_TO_DEPLOY=$stack

  echo $USER_REGION

  # Install project dependencies then deploy the stack
  echo "Installing dependencies through npm"
  npm install
  # Synth the stack for user to view
  cdk synth

  read -p "Verify the stack in cdk.out. Are you sure you want to deploy the $stack stack? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Bootstrapping account $accountId in region $region."
    cdk bootstrap aws://$accountId/$region

    echo "Deploying $stack stack."
    cdk deploy
  else
    echo "Deployment canceled."
  fi
}

# Parse command-line arguments
case "$1" in
  init)
    install_dependencies
    ;;
  ls)
    list_stacks
    ;;
  deploy)
    if [ -z "$2" ]; then
      echo "Usage: $0 deploy <stack>"
      exit 1
    fi
    deploy_stack "$2"
    ;;
  *)
    echo "Usage: $0 <command> [parameters]"
    echo "Commands:"
    echo "  init      Install project dependencies"
    echo "  ls        List available stacks"
    echo "  deploy <value>   Deploy a blueprint stack"
    exit 1
    ;;
esac
