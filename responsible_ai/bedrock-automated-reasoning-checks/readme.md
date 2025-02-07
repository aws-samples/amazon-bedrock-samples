# Automated Reasoning Checks with Amazon Bedrock Guardrails

This repository demonstrates how to implement Automated Reasoning (AR) checks using Amazon Bedrock Guardrails. The implementation validates model responses against business policies and automatically corrects policy violations.

## Repository Structure
```
├── automated_reasoning_checks.ipynb  # Main notebook with implementation
├── conversation.py  # Conversation management module
├── feedback.py  # AR feedback processing module
├── validation_client.py  # Bedrock validation client
├── models/  # Directory for Bedrock service models. This will be given to you by your account manager
│   ├── bedrock-<version>.api.json
│   └── bedrock-runtime-<version>.api.json
└── README.md
```

## Prerequisites
- AWS account with Bedrock access
- Appropriate IAM roles and permissions
- Python 3.8+
- Required Python packages:
  - `boto3`
  - `botocore`
  - `jupyter`

## Setup Instructions
1. Clone this repository
   ```bash
   git clone <repository-url>
   cd automated_reasoning_checks
   ```
4. Download Bedrock service models
   - Place model files in the `models/` directory
   - Ensure correct file naming convention

## Usage
1. Create AR Policy (via AWS Console)
   - Navigate to Amazon Bedrock > Safeguards > Automated Reasoning
   - Follow the policy creation steps in the notebook
2. Run the Notebook
   ```bash
   jupyter notebook automated_reasoning_checks.ipynb
   ```
3. Follow the implementation steps in the notebook:
   - Configure environment
   - Load service models
   - Create/attach guardrails
   - Test with sample queries

## Implementation Details
- `conversation.py`: Manages conversation flow and history
- `feedback.py`: Processes AR policy validation feedback
- `validation_client.py`: Handles Bedrock model interactions and guardrail validation
- `models/`: Contains required Bedrock service model files

## Example Usage
```python
# Initialize validation client
client = ValidatingConversationalClient(
    bedrock_client=runtime_client,
    guardrail_id=guardrail_id,
    guardrail_version=guardrail_version,
    model=model_id
)

# Process question with AR validation
process_qa("I am a part-time employee, am I eligible for LoAP?")
```

## Contributing
Feel free to submit issues and enhancement requests!

## References
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock)
- [Bedrock Guardrails Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)