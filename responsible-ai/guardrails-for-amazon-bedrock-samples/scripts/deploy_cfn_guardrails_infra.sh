#!/bin/bash

# Function to deploy CloudFormation stack
deploy_cloudformation() {
    local template_file=$1
    local stack_name="CustomerSupportChatbotGuardrailStack"
    
    # Read CloudFormation template
    cloudformation_template=$(cat "$template_file")
    
    # Create CloudFormation stack
    echo "Creating CloudFormation stack..."
    create_response=$(aws cloudformation create-stack --stack-name "$stack_name" --template-body "$cloudformation_template" --capabilities CAPABILITY_NAMED_IAM)
    
    if [ $? -ne 0 ]; then
        echo "Error creating CloudFormation stack."
        exit 1
    fi
    
    stack_id=$(echo $create_response | jq -r '.StackId')
    echo "Stack ID: $stack_id"
    
    # Wait for stack creation to complete
    echo "Waiting for CloudFormation stack to be created..."
    aws cloudformation wait stack-create-complete --stack-name "$stack_id"
    
    if [ $? -ne 0 ]; then
        echo "Error waiting for CloudFormation stack creation."
        exit 1
    fi
    
    echo "CloudFormation stack created successfully."
    
    # Retrieve the outputs
    stack=$(aws cloudformation describe-stacks --stack-name "$stack_id")
    echo "Stack description: $stack"
    outputs=$(echo $stack | jq -r '.Stacks[0].Outputs')
    echo "Stack outputs: $outputs"
    
    guardrail_identifier=""
    
    for row in $(echo "${outputs}" | jq -r '.[] | @base64'); do
        _jq() {
            echo ${row} | base64 --decode | jq -r ${1}
        }
        
        description=$(_jq '.Description')
        output_value=$(_jq '.OutputValue')
        
        if [ "$description" == "The unique identifier of the guardrail" ]; then
            guardrail_identifier=$(echo $output_value | awk -F'/' '{print $NF}')
            echo "${description}: ${guardrail_identifier}"
        else
            echo "${description}: ${output_value}"
        fi
    done
    
    if [ -z "$guardrail_identifier" ]; then
        echo "Guardrail Identifier not found in the stack outputs."
        exit 1
    fi
    
    echo "$guardrail_identifier"
}

# Path to the CloudFormation template file
template_file="../infra/cfn/guardrails.yaml"

# Deploy CloudFormation stack and get the guardrail identifier
guardrail_identifier=$(deploy_cloudformation "$template_file")

echo "The Guardrail Identifier is: ${guardrail_identifier}"


