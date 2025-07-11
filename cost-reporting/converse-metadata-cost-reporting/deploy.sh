#!/bin/bash
# Bedrock Cost Reporting Deployment Script
# This script deploys the Bedrock Cost Reporting solution

set -e  # Exit immediately if a command exits with a non-zero status

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="${SCRIPT_DIR}/logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="${LOGS_DIR}/deploy_$(date +%Y%m%d_%H%M%S).log"
CONFIG_FILE="${SCRIPT_DIR}/.deploy_config"
MAX_WAIT_TIME=1800  # 30 minutes in seconds

# Display usage information
usage() {
  echo "=================================================="
  echo "       Bedrock Cost Reporting Deployment          "
  echo "=================================================="
  echo ""
  echo "Prerequisites:"
  echo "  - AWS CLI configured with appropriate permissions"
  echo "  - AWS CDK installed (npm install -g aws-cdk)"
  echo "  - Python 3.12+ with uv package manager (uv sync)"
  echo "  - Bedrock Model invocation logging enabled with S3 destination"
  echo "  - Read access to the model invocation logs folder in S3"
  echo "  - QuickSight enabled with an Admin user"
  echo ""
}

# Logging function
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Error handling function
handle_error() {
  log "ERROR" "An error occurred on line $1"
  exit 1
}

# Set up error handling
trap 'handle_error $LINENO' ERR

# Validate S3 bucket exists
validate_s3_bucket() {
  local bucket_name=$1
  log "INFO" "Validating S3 bucket: $bucket_name"
  
  if aws --profile $AWS_PROFILE s3 ls "s3://$bucket_name" >/dev/null 2>&1; then
    log "INFO" "✅ S3 bucket '$bucket_name' exists."
    return 0
  else
    log "ERROR" "❌ S3 bucket '$bucket_name' does not exist or you don't have access to it."
    return 1
  fi
}

# Validate QuickSight user exists
validate_quicksight_user() {
  local region=$1
  local username=$2
  local profile=$3
  
  log "INFO" "Validating QuickSight user: $username in region $region using profile $profile"
  
  # This is a simplified check - in production you might want to use the QuickSight API
  # to verify the user exists with proper permissions
  if aws --profile $profile quicksight list-users --aws-account-id $(aws --profile $profile sts get-caller-identity --query Account --output text) --namespace default --region $region 2>/dev/null | grep -q "$username"; then
    log "INFO" "✅ QuickSight user '$username' exists."
    return 0
  else
    log "WARN" "⚠️ Could not verify QuickSight user '$username'. Please ensure the user exists."
    while true; do
      read -p "Continue anyway? (y/n): " continue_anyway
      if [[ $continue_anyway == "y" || $continue_anyway == "Y" ]]; then
        break
      elif [[ $continue_anyway == "n" || $continue_anyway == "N" ]]; then
        break
      else
        echo "Please enter 'y' or 'n'"
      fi
    done
    if [[ $continue_anyway == "y" || $continue_anyway == "Y" ]]; then
      return 0
    else
      return 1
    fi
  fi
}

# Check if CDK is bootstrapped in the account/region
check_cdk_bootstrap() {
  local region=$1
  local profile=$2
  log "INFO" "Checking if CDK is bootstrapped in region $region using profile $profile..."
  
  if aws --profile $profile cloudformation describe-stacks --stack-name CDKToolkit --region $region >/dev/null 2>&1; then
    log "INFO" "✅ CDK is bootstrapped in region $region."
    return 0
  else
    log "WARN" "❌ CDK is not bootstrapped in region $region."
    while true; do
      read -p "Would you like to bootstrap CDK now? (y/n): " bootstrap_now
      if [[ $bootstrap_now == "y" || $bootstrap_now == "Y" ]]; then
        break
      elif [[ $bootstrap_now == "n" || $bootstrap_now == "N" ]]; then
        break
      else
        echo "Please enter 'y' or 'n'"
      fi
    done
    if [[ $bootstrap_now == "y" || $bootstrap_now == "Y" ]]; then
      log "INFO" "Bootstrapping CDK in region $region..."
      uv run cdk bootstrap --profile $profile aws://$(aws --profile $profile sts get-caller-identity --query Account --output text)/$region
      return $?
    else
      log "ERROR" "CDK bootstrap is required to deploy this stack."
      return 1
    fi
  fi
}

# Check Python version
check_python_version() {
  local min_version="3.10"
  local python_cmd=$1
  
  log "INFO" "Checking Python version..."
  local version=$($python_cmd -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
  
  if [[ "$(printf '%s\n' "$min_version" "$version" | sort -V | head -n1)" != "$min_version" ]]; then
    log "ERROR" "❌ Python version $version is less than the required version $min_version"
    return 1
  else
    log "INFO" "✅ Python version $version meets the minimum requirement of $min_version"
    return 0
  fi
}

# Check dependencies
check_dependencies() {
  log "INFO" "Checking dependencies..."
  
  # Check if AWS CLI is installed
  if ! command -v aws &> /dev/null; then
    log "ERROR" "❌ AWS CLI is not installed. Please install it first."
    exit 1
  fi
  
  # Check if CDK is installed
  if ! command -v cdk &> /dev/null; then
    log "ERROR" "❌ AWS CDK is not installed. Please install it using 'npm install -g aws-cdk'."
    exit 1
  fi
  
  # Check CDK CLI version compatibility
  log "INFO" "Checking CDK CLI version compatibility..."
  CDK_VERSION=$(cdk --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
  REQUIRED_VERSION="2.1019.1"
  
  if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$CDK_VERSION" | sort -V | head -n1)" == "$CDK_VERSION" && "$CDK_VERSION" != "$REQUIRED_VERSION" ]]; then
    log "WARN" "⚠️ CDK CLI version $CDK_VERSION is older than required version $REQUIRED_VERSION"
    while true; do
      read -p "Would you like to upgrade CDK CLI now? (y/n): " upgrade_cdk
      if [[ $upgrade_cdk == "y" || $upgrade_cdk == "Y" ]]; then
        break
      elif [[ $upgrade_cdk == "n" || $upgrade_cdk == "N" ]]; then
        break
      else
        echo "Please enter 'y' or 'n'"
      fi
    done
    if [[ $upgrade_cdk == "y" || $upgrade_cdk == "Y" ]]; then
      log "INFO" "Upgrading CDK CLI..."
      sudo npm install -g aws-cdk@latest
    else
      log "ERROR" "❌ CDK CLI version $REQUIRED_VERSION or higher is required."
      exit 1
    fi
  else
    log "INFO" "✅ CDK CLI version $CDK_VERSION is compatible."
  fi
  
  # Check if uv is installed
  if ! command -v uv &> /dev/null; then
    log "ERROR" "❌ uv is not installed. Please install it first and run 'uv sync'."
    exit 1
  fi
  
  log "INFO" "✅ Required dependencies check completed."
}

# Wait for Glue job with timeout
wait_for_glue_job() {
  local job_name=$1
  local job_run_id=$2
  local start_time=$(date +%s)
  
  log "INFO" "Waiting for ETL job completion..."
  while true; do
    local current_time=$(date +%s)
    local elapsed_time=$((current_time - start_time))
    
    if [ $elapsed_time -gt $MAX_WAIT_TIME ]; then
      log "ERROR" "❌ Timeout waiting for ETL job to complete after $(($MAX_WAIT_TIME / 60)) minutes."
      return 1
    fi
    
    local STATUS=$(aws --profile $AWS_PROFILE glue get-job-run --job-name $job_name --run-id $job_run_id --query "JobRun.JobRunState" --output text)
    log "INFO" "Status: $STATUS (elapsed: ${elapsed_time}s)"
    
    if [ "$STATUS" == "SUCCEEDED" ]; then
      log "INFO" "✅ ETL job completed successfully!"
      return 0
    elif [[ "$STATUS" == "FAILED" || "$STATUS" == "TIMEOUT" || "$STATUS" == "STOPPED" || "$STATUS" == "ERROR" ]]; then
      log "ERROR" "❌ ETL job failed with status: $STATUS"
      return 1
    fi
    
    sleep 30
  done
}

# Wait for Glue crawler with timeout
wait_for_crawler() {
  local crawler_name=$1
  local start_time=$(date +%s)
  
  log "INFO" "Checking status of $crawler_name..."
  while true; do
    local current_time=$(date +%s)
    local elapsed_time=$((current_time - start_time))
    
    if [ $elapsed_time -gt $MAX_WAIT_TIME ]; then
      log "ERROR" "❌ Timeout waiting for crawler $crawler_name to complete after $(($MAX_WAIT_TIME / 60)) minutes."
      return 1
    fi
    
    local STATUS=$(aws --profile $AWS_PROFILE glue get-crawler --name $crawler_name --query "Crawler.State" --output text)
    if [ "$STATUS" != "RUNNING" ]; then
      log "INFO" "✅ $crawler_name completed with status: $STATUS"
      return 0
    fi
    log "INFO" "$crawler_name is still running... (elapsed: ${elapsed_time}s)"
    sleep 15
  done
}

# Main deployment
deploy() {
  local bedrock_logs_bucket=$1
  local quicksight_username=$2
  local quicksight_region=$3
  
  log "INFO" "Deploying Bedrock Cost Reporting CDK stack..."
  log "INFO" "  - Bedrock Logs S3 Bucket: $bedrock_logs_bucket"
  log "INFO" "  - QuickSight Username: $quicksight_username"
  log "INFO" "  - QuickSight Region: $quicksight_region"
  
  # Navigate to CDK directory
  cd "$SCRIPT_DIR/cdk"
  
  # Synthesize the CloudFormation template
  log "INFO" "Synthesizing CloudFormation template..."
  uv run cdk synth --profile $AWS_PROFILE --parameters BedrockLogsS3Bucket=$bedrock_logs_bucket \
            --parameters QuickSightUserName=$quicksight_username \
            --parameters QuickSightRegion=$quicksight_region
  
  # Deploy the stack
  log "INFO" "Deploying stack..."
  uv run cdk deploy --profile $AWS_PROFILE --parameters BedrockLogsS3Bucket=$bedrock_logs_bucket \
             --parameters QuickSightUserName=$quicksight_username \
             --parameters QuickSightRegion=$quicksight_region \
             --require-approval never
  
  log "INFO" "✅ Deployment completed successfully!"
  return 0
}

# Run Glue jobs and crawlers
run_glue_resources() {
  local transformed_bucket=$1
  
  # Upload pricing.csv to S3
  log "INFO" "Uploading pricing.csv to S3..."
  if ! aws --profile $AWS_PROFILE s3 cp "$SCRIPT_DIR/cdk/glue/pricing.csv" "s3://$transformed_bucket/pricing/"; then
    log "ERROR" "❌ Failed to upload pricing.csv to S3"
    log "WARN" "⚠️ Skipping Glue resources due to errors"
    log "INFO" "Please run the Glue jobs and crawlers manually from the AWS Glue console"
    return 0
  fi
  log "INFO" "✅ Pricing data uploaded successfully!"
  
  # Run the Glue ETL job
  local job_name="bedrock-flatten-logs"
  log "INFO" "Starting Glue job: $job_name"
  local job_run_id
  if ! job_run_id=$(aws --profile $AWS_PROFILE glue start-job-run --job-name $job_name --query "JobRunId" --output text 2>&1); then
    log "ERROR" "❌ Failed to start Glue job: $job_name"
    log "WARN" "⚠️ Skipping remaining Glue resources due to errors"
    log "INFO" "Please run the Glue job 'bedrock-flatten-logs' and crawlers manually from the AWS Glue console"
    return 0
  fi
  log "INFO" "Job started with run ID: $job_run_id"
  
  # Wait for ETL job completion
  if ! wait_for_glue_job "$job_name" "$job_run_id"; then
    log "WARN" "⚠️ Skipping remaining Glue resources due to job failure"
    log "INFO" "Please run the Glue crawlers manually from the AWS Glue console"
    return 0
  fi
  
  # Run all Glue crawlers
  log "INFO" "Starting Glue crawlers..."
  
  # Start logs crawler
  if ! aws --profile $AWS_PROFILE glue start-crawler --name bedrock-logs-crawler; then
    log "ERROR" "❌ Failed to start bedrock-logs-crawler"
    log "WARN" "⚠️ Skipping remaining Glue resources due to errors"
    log "INFO" "Please run the remaining Glue crawlers manually from the AWS Glue console"
    return 0
  fi
  log "INFO" "Started bedrock-logs-crawler"
  
  # Start metadata crawler
  if ! aws --profile $AWS_PROFILE glue start-crawler --name bedrock-metadata-crawler; then
    log "ERROR" "❌ Failed to start bedrock-metadata-crawler"
    log "WARN" "⚠️ Skipping remaining Glue resources due to errors"
    log "INFO" "Please run the remaining Glue crawlers manually from the AWS Glue console"
    return 0
  fi
  log "INFO" "Started bedrock-metadata-crawler"
  
  # Start pricing crawler
  if ! aws --profile $AWS_PROFILE glue start-crawler --name bedrock-pricing-crawler; then
    log "ERROR" "❌ Failed to start bedrock-pricing-crawler"
    log "WARN" "⚠️ Skipping remaining Glue resources due to errors"
    log "INFO" "Please run the pricing crawler manually from the AWS Glue console"
    return 0
  fi
  log "INFO" "Started bedrock-pricing-crawler"
  
  # Wait for all crawlers to complete
  log "INFO" "Waiting for crawlers to complete..."
  for crawler in "bedrock-logs-crawler" "bedrock-metadata-crawler" "bedrock-pricing-crawler"; do
    if ! wait_for_crawler "$crawler"; then
      log "WARN" "⚠️ Crawler $crawler failed, but continuing with deployment"
      log "INFO" "Please check and run the $crawler manually from the AWS Glue console if needed"
    fi
  done
  
  log "INFO" "Glue resources processing completed"
  return 0
}

# Cleanup function
cleanup() {
  log "INFO" "Cleaning up temporary resources..."
  # Add cleanup code here if needed
}

# Save configuration
save_config() {
  cat > "$CONFIG_FILE" << EOF
AWS_PROFILE="$AWS_PROFILE"
AWS_REGION="$AWS_REGION"
BEDROCK_LOGS_BUCKET="$BEDROCK_LOGS_BUCKET"
QUICKSIGHT_REGION="$QUICKSIGHT_REGION"
QUICKSIGHT_USERNAME="$QUICKSIGHT_USERNAME"
GENERATE_LOGS="$GENERATE_LOGS"
RUN_JOBS="$RUN_JOBS"
EOF
  log "INFO" "Configuration saved to $CONFIG_FILE"
}

# Load configuration
load_config() {
  if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
    return 0
  else
    return 1
  fi
}

# Main function
main() {
  # Start logging
  log "INFO" "Starting Bedrock Cost Reporting deployment"
  log "INFO" "Log file: $LOG_FILE"
  
  # Check for previous configuration
  if load_config; then
    log "INFO" "Found previous configuration:"
    log "INFO" "  - AWS Profile: $AWS_PROFILE"
    log "INFO" "  - AWS Region: $AWS_REGION"
    log "INFO" "  - Bedrock Logs S3 Bucket: $BEDROCK_LOGS_BUCKET"
    log "INFO" "  - QuickSight Username: $QUICKSIGHT_USERNAME"
    log "INFO" "  - QuickSight Region: $QUICKSIGHT_REGION"
    log "INFO" "  - Generate Logs: $GENERATE_LOGS"
    log "INFO" "  - Run Jobs: $RUN_JOBS"
    echo ""
    while true; do
      read -p "Use previous configuration? (y/n): " USE_PREVIOUS
      if [[ $USE_PREVIOUS == "y" || $USE_PREVIOUS == "Y" ]]; then
        log "INFO" "Using previous configuration"
        break
      elif [[ $USE_PREVIOUS == "n" || $USE_PREVIOUS == "N" ]]; then
        log "INFO" "Will prompt for new configuration"
        break
      else
        echo "Please enter 'y' or 'n'"
      fi
    done
  else
    USE_PREVIOUS="n"
  fi
  
  # Display banner
  usage
  
  # Skip prerequisite check if using previous config
  if [[ $USE_PREVIOUS != "y" && $USE_PREVIOUS != "Y" ]]; then
    # Confirm prerequisites are met
    while true; do
      read -p "Have you met all the prerequisites listed above? (y/n): " PREREQ_MET
      if [[ $PREREQ_MET == "y" || $PREREQ_MET == "Y" ]]; then
        break
      elif [[ $PREREQ_MET == "n" || $PREREQ_MET == "N" ]]; then
        break
      else
        echo "Please enter 'y' or 'n'"
      fi
    done
    if [[ $PREREQ_MET != "y" && $PREREQ_MET != "Y" ]]; then
      log "INFO" "Please meet all prerequisites before running this script."
      exit 0
    fi
  fi
    
  # Check if virtual environment exists and activate it
  if [[ ! -d ".venv" ]]; then
    log "INFO" "Creating Python virtual environment..."
    # Find Python3 in the PATH
    PYTHON_PATH=$(which python3)
    if [ -z "$PYTHON_PATH" ]; then
      log "ERROR" "❌ Python 3 not found in PATH. Please install Python 3.10 or later."
      exit 1
    fi
    
    # Check Python version
    check_python_version "$PYTHON_PATH" || exit 1
    
    # Create virtual environment using the found Python path
    $PYTHON_PATH -m venv .venv
    log "INFO" "✅ Virtual environment created."
  fi
  
  # Activate virtual environment
  log "INFO" "Activating Python virtual environment..."
  source .venv/bin/activate
  
  # Verify Python path is from the virtual environment
  VENV_PYTHON=$(which python)
  if [[ "$VENV_PYTHON" == *".venv"* ]]; then
    log "INFO" "✅ Virtual environment activated successfully."
  else
    log "WARN" "⚠️ Virtual environment may not be activated correctly."
    log "WARN" "Continuing with installation anyway..."
  fi
  
  # Check and install dependencies
  check_dependencies
  
  # Get configuration (either from previous or prompt user)
  if [[ $USE_PREVIOUS != "y" && $USE_PREVIOUS != "Y" ]]; then
    # Get AWS profile
    echo ""
    read -p "Enter AWS CLI profile (default: default): " AWS_PROFILE
    AWS_PROFILE=${AWS_PROFILE:-default}
    log "INFO" "Using AWS profile: $AWS_PROFILE"
    
    # Get AWS region
    echo ""
    AWS_REGION=$(aws --profile $AWS_PROFILE configure get region)
    if [ -z "$AWS_REGION" ]; then
      read -p "Enter AWS region: " AWS_REGION
    fi
    
    # Prompt for required parameters
    echo ""
    read -p "Enter the S3 bucket name where Bedrock logs are stored: " BEDROCK_LOGS_BUCKET
    while ! validate_s3_bucket "$BEDROCK_LOGS_BUCKET"; do
      read -p "Enter a valid S3 bucket name: " BEDROCK_LOGS_BUCKET
    done
    
    echo ""
    read -p "Enter the QuickSight region (default: $AWS_REGION): " QUICKSIGHT_REGION
    QUICKSIGHT_REGION=${QUICKSIGHT_REGION:-$AWS_REGION}
    
    echo ""
    read -p "Enter the QuickSight username: " QUICKSIGHT_USERNAME
    validate_quicksight_user "$QUICKSIGHT_REGION" "$QUICKSIGHT_USERNAME" "$AWS_PROFILE" || exit 1

    # Ask if user wants to generate sample Bedrock logs
    echo ""
    while true; do
      read -p "Do you want to generate sample Bedrock logs for testing? (This will trigger 50 simulated calls to Bedrock) (y/n): " GENERATE_LOGS
      if [[ $GENERATE_LOGS == "y" || $GENERATE_LOGS == "Y" || $GENERATE_LOGS == "n" || $GENERATE_LOGS == "N" ]]; then
        break
      else
        echo "Please enter 'y' or 'n'"
      fi
    done
  fi
  
  # Check if CDK is bootstrapped
  check_cdk_bootstrap $AWS_REGION $AWS_PROFILE || exit 1
  
  # Confirm deployment
  echo ""
  log "INFO" "Ready to deploy with the following parameters:"
  log "INFO" "  - Bedrock Logs S3 Bucket: $BEDROCK_LOGS_BUCKET"
  log "INFO" "  - QuickSight Username: $QUICKSIGHT_USERNAME"
  log "INFO" "  - QuickSight Region: $QUICKSIGHT_REGION"
  if [[ $GENERATE_LOGS == "y" || $GENERATE_LOGS == "Y" ]]; then
    log "INFO" "  - Will generate sample Bedrock logs: Yes"
  fi
  echo ""
  while true; do
    read -p "Proceed with deployment? (y/n): " CONFIRM
    if [[ $CONFIRM == "y" || $CONFIRM == "Y" || $CONFIRM == "n" || $CONFIRM == "N" ]]; then
      break
    else
      echo "Please enter 'y' or 'n'"
    fi
  done
  
  if [[ $CONFIRM == "y" || $CONFIRM == "Y" ]]; then
    # Generate sample logs if requested
    if [[ $GENERATE_LOGS == "y" || $GENERATE_LOGS == "Y" ]]; then
      log "INFO" "Generating sample Bedrock logs with 50 simulated API calls..."
      uv run python generatelogs.py --profile $AWS_PROFILE
      log "INFO" "Sample logs generated successfully."
    fi
    deploy "$BEDROCK_LOGS_BUCKET" "$QUICKSIGHT_USERNAME" "$QUICKSIGHT_REGION" || exit 1
    
    # Get the transformed bucket name from CloudFormation stack outputs
    log "INFO" "Getting transformed bucket name from CloudFormation stack..."
    TRANSFORMED_BUCKET=$(aws --profile $AWS_PROFILE cloudformation describe-stacks --stack-name BedrockCostReportingStack --query "Stacks[0].Outputs[?OutputKey=='TransformedBucketName'].OutputValue" --output text)
    
    if [ -z "$TRANSFORMED_BUCKET" ]; then
      log "WARN" "Could not find transformed bucket name in stack outputs. Using default naming convention..."
      ACCOUNT_ID=$(aws --profile $AWS_PROFILE sts get-caller-identity --query Account --output text)
      TRANSFORMED_BUCKET="bedrock-logs-transformed-${ACCOUNT_ID}"
    fi
    
    # Get the dashboard URL from CloudFormation stack outputs
    log "INFO" "Getting QuickSight dashboard URL from CloudFormation stack..."
    DASHBOARD_URL=$(aws --profile $AWS_PROFILE cloudformation describe-stacks --stack-name BedrockCostReportingStack --query "Stacks[0].Outputs[?OutputKey=='DashboardURL'].OutputValue" --output text)
    
    if [ -n "$DASHBOARD_URL" ]; then
      log "INFO" "✅ QuickSight dashboard URL: $DASHBOARD_URL"
    else
      log "WARN" "Could not find dashboard URL in stack outputs."
    fi
    
    # Ask if user wants to run the Glue job and crawlers (only if not using previous config)
    if [[ $USE_PREVIOUS != "y" && $USE_PREVIOUS != "Y" ]]; then
      echo ""
      while true; do
        read -p "Do you want to run the Glue ETL job and crawlers now? (y/n): " RUN_JOBS
        if [[ $RUN_JOBS == "y" || $RUN_JOBS == "Y" || $RUN_JOBS == "n" || $RUN_JOBS == "N" ]]; then
          break
        else
          echo "Please enter 'y' or 'n'"
        fi
      done
    fi
    
    if [[ $RUN_JOBS == "y" || $RUN_JOBS == "Y" ]]; then
      run_glue_resources "$TRANSFORMED_BUCKET" || exit 1
    fi
    
    # Save configuration for next time
    save_config
    
    log "INFO" "✅ Deployment process completed successfully!"
    if [ -n "$DASHBOARD_URL" ]; then
      log "INFO" "You can now access the QuickSight dashboard at: $DASHBOARD_URL"
    else
      log "INFO" "You can now access the QuickSight dashboard in the QuickSight console."
    fi
  else
    log "INFO" "Deployment cancelled."
    exit 0
  fi
}

# Execute main function
main