# Amazon Bedrock Agent with Code Interpreter

This repository demonstrates how to set up, use, and test an Amazon Bedrock Agent with Code Interpreter capabilities. The project is divided into three Jupyter notebooks, each focusing on a specific aspect of the process.

## Contents

1. [Data Preparation](#data-preparation)
2. [Bedrock Agent Creation](#bedrock-agent-creation)
3. [Testing and Cleanup](#testing-and-cleanup)

## Prerequisites

- An AWS account with access to Amazon Bedrock
- Python 3.7+
- Jupyter Notebook environment
  
## Notebooks

### 1. Data Preparation

`1_Data_Preparation.ipynb`

This notebook focuses on processing open-source taxi data to be used by our Amazon Bedrock Agent.

- Uses NYC TLC Trip Record Data
- Processes yellow and green taxi trip records
- Prepares data including pickup/dropoff times, locations, fares, etc.

### 2. Bedrock Agent Creation

`2_Bedrock_Agent_Creation.ipynb`

This notebook guides you through the process of creating an Amazon Bedrock Agent.

- Creates necessary IAM roles and policies
- Configures the Bedrock Agent
- Uses Claude 3.5 Sonnet as the foundation model

### 3. Testing and Cleanup

`3_Testing_and_Cleanup.ipynb`

The final notebook demonstrates how to test the Bedrock Agent and clean up resources.

- Sets up the Code Interpreter action
- Shows how to interact with the agent
- Demonstrates the agent's capabilities in writing/executing code and processing complex queries
- Includes cleanup procedures to remove all created resources

**Note**: Code Interpreter is in public preview at the time of writing.
