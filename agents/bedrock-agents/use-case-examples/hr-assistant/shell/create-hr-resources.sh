# If not already cloned, clone the remote repository (https://github.com/aws-samples/amazon-bedrock-samples) and change working directory to HR agent shell folder
# cd amazon-bedrock-samples/agents/hr-agent/shell/
# chmod u+x create-hr-resources.sh
# export STACK_NAME=<YOUR-STACK-NAME> # Stack name must be lower case for S3 bucket naming convention
# export SNS_EMAIL=<YOUR-EMPLOYEE-EMAIL> # Email used for SNS notifications
# export AWS_REGION=<YOUR-STACK-REGION> # Stack deployment region
# source ./create-hr-resources.sh

check_query_status() {
    sleep 5
    query_status=$(aws athena get-query-execution --query-execution-id "$1" --output json)
    if [[ "$query_status" =~ "FAILED" ]]; then
        echo QueryID: "$1", Reason: "$2" Check QueryID for debugging.
        exit 1
    fi
    echo "Query execution succeeded."
}



export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ARTIFACT_BUCKET_NAME=$ACCOUNT_ID-$STACK_NAME-hr-resources

aws s3 mb s3://${ARTIFACT_BUCKET_NAME} --region ${AWS_REGION}
aws s3 cp ../agent/ s3://${ARTIFACT_BUCKET_NAME}/agent/ --region ${AWS_REGION} --recursive --exclude ".DS_Store"

# Execute Athena queries and check for errors
query_output=$(aws athena start-query-execution \
    --query-string "CREATE DATABASE employee" \
    --result-configuration "OutputLocation='s3://$ARTIFACT_BUCKET_NAME/query_output'")
query_execution_id=$(echo "$query_output" | jq -r '.QueryExecutionId')
check_query_status "$query_execution_id" "Failed to create database."

query_output=$(aws athena start-query-execution \
    --query-string "CREATE TABLE employee.employeetimeoff (employeename string, employeealias string, vacationbalanceinhours int, personaltimeoffbalanceinhours int) LOCATION 's3://$ARTIFACT_BUCKET_NAME/athena/timeoff' TBLPROPERTIES ('table_type'='iceberg');" \
    --query-execution-context "Database='employee'" \
    --result-configuration "OutputLocation='s3://$ARTIFACT_BUCKET_NAME/query_output'")
query_execution_id=$(echo "$query_output" | jq -r '.QueryExecutionId')
check_query_status "$query_execution_id" "Failed to create table."


query_output=$(aws athena start-query-execution \
    --query-string "INSERT INTO employeetimeoff (EmployeeName, EmployeeAlias, vacationbalanceinhours, personaltimeoffbalanceinhours) VALUES ('Pepper Li', 'hremployee', 40, 70);" \
    --query-execution-context "Database='employee'" \
    --result-configuration "OutputLocation='s3://$ARTIFACT_BUCKET_NAME/query_output'")
query_execution_id=$(echo "$query_output" | jq -r '.QueryExecutionId')
check_query_status "$query_execution_id" "Failed to insert data into table."


aws cloudformation create-stack \
--stack-name ${STACK_NAME} \
--template-body file://../cfn/hr-resources.yml \
--parameters \
ParameterKey=ArtifactBucket,ParameterValue=${ARTIFACT_BUCKET_NAME} \
ParameterKey=SNSEmail,ParameterValue=$SNS_EMAIL \
--capabilities CAPABILITY_NAMED_IAM \
--region ${AWS_REGION}

aws cloudformation describe-stacks --stack-name $STACK_NAME --region ${AWS_REGION} --query "Stacks[0].StackStatus"
# aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region ${AWS_REGION}
# aws cloudformation describe-stacks --stack-name $STACK_NAME --region ${AWS_REGION} --query "Stacks[0].StackStatus"