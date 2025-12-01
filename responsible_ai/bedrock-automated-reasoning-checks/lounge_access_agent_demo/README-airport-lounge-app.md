# Airport Lounge Access Agent with Automated Reasoning

This project demonstrates an agentic use case for airport lounge access automation using the strands-agents framework with Amazon Bedrock and Automated Reasoning safeguards.

## Overview

The Airport Lounge Access Agent automates the process of determining passenger eligibility for airport lounge access by:

1. **Boarding Pass Validation**: Extracting and validating passenger information from boarding passes
2. **Flight Status Lookup**: Determining domestic/international flight status
3. **Frequent Flier Data**: Checking passenger privileges from a mock DynamoDB
4. **Policy Enforcement**: Applying Star Alliance lounge access policies
5. **Automated Reasoning Validation**: Using Bedrock Guardrails to cross-check agent decisions
6. **Knowledge Base Integration**: Answering lounge-related questions using a Knowledge Base

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Streamlit UI   │    │ Strands Agent    │    │ Bedrock Model   │.   │ Guardrail with  │
│                 │───▶│                  │───▶│                 │───▶│ Automated       │
│ Passenger Input │    │ - Boarding Pass  │    │ Decision Making │.   │ Reasoning       │
└─────────────────┘    │ - Flight Status  │    └─────────────────┘.   └─────────────────┘
                       │ - FF Miles       │              │
                       │ - Policy Check   │              ▼
                       └──────────────────┘     ┌─────────────────┐
                                │               │ Knowledge Base  │
                                ▼               │ Lounge Info     │
                       ┌──────────────────┐     └─────────────────┘
                       │ Mock DynamoDB    │    
                       │ Frequent Flier   │              
                       │ Data             │              
                       └──────────────────┘    
                                               
                                               
                                               
```

## Key Features

- **Automated Reasoning Safeguards**: Cross-validation of agent decisions using policy-based reasoning
- **Response Rewriting**: Ability to rewrite responses based on Automated Reasoning feedback
- **Mock Data Integration**: Realistic passenger and lounge data for demonstration
- **Policy-Based Access Control**: Implementation of Star Alliance lounge access policies
- **Interactive Demo**: Streamlit-based UI for testing various scenarios

## Files

- `lounge_access_agent.py` - Main strands agent implementation
- `boarding_pass_validator.py` - Boarding pass parsing and validation
- `flight_status_service.py` - Flight status lookup service
- `dynamo_mock.py` - Mock DynamoDB for frequent flier data
- `policy_engine.py` - Lounge access policy implementation
- `bedrock_utils.py` - Bedrock and Automated Reasoning utilities
- `demo.py` - Streamlit demo application
- `data/` - Mock data for passengers and lounge information

## Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Set up AWS credentials and configure Bedrock access
3. **Set the required environment variables (IMPORTANT):**
   ```bash
   export GUARDRAIL_ID="your-guardrail-id"
   export GUARDRAIL_VERSION="DRAFT"
   export KNOWLEDGE_BASE_ID="your-knowledge-base-id"  # Optional
   ```
4. Run the demo: `streamlit run demo.py`

## Environment Variables

- `GUARDRAIL_ID` - **REQUIRED** The ID of the configured Bedrock Guardrail
- `GUARDRAIL_VERSION` - Version of the Guardrail to use (default: `DRAFT`)
- `KNOWLEDGE_BASE_ID` - ID of the Knowledge Base containing lounge information
- `AWS_DEFAULT_REGION` - The AWS region that the application is being run in
