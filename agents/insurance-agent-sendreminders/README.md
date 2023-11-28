# Insurance Claims Processing Agent

#### Authors: @Maira, @Mark, @Madhur

##### Side Note: For users interested in deploying agents and knowledge bases with AWS CDK BedrockAgent, check out our npm package repository. Additionally, for advanced users looking to create and link a knowledge base to a new agent, explore our documentation on the same.

### Description:

This agent automates insurance claim management tasks. It integrates email communication with a knowledge base (KB), handling claims efficiently by identifying outstanding documents and reminding policyholders via email. 
<img width="1079" alt="Screenshot 2023-11-28 at 12 35 12 PM" src="https://github.com/madhurprash/amazon-bedrock-samples/assets/129979633/92245c0e-c4ef-4463-bbea-eb01d6ba74a5">



### Key Functionalities:

1. Claim Detail Retrieval: Fetches detailed insurance claim information.

API Path: /claims/{claimId}/detail

Response: Claim ID, creation date, last activity date, status, and policy type.

Open Claims Listing: Provides a list of all open insurance claims.

2. API Path: /claims

Response: List of open claims with IDs, policyholder IDs, and statuses.

Outstanding Paperwork Identification: Identifies pending documents for a claim.

API Path: /claims/{claimId}/outstanding-paperwork

Response: Details of required documents for the claim.

Email Reminder for Outstanding Paperwork: Sends email reminders for missing documents based on the KB.

3. API Path: /send-reminder

Utilizes: "insurance-claims-agent-kb" Knowledge Base.

### Workflow:

1. Claim Information Retrieval: On request, retrieves claim details or lists open claims.

2. Outstanding Paperwork Check: Identifies any pending paperwork for claims.

3. Knowledge Base Reference: Accesses KB for document requirements.

4. Email Reminder Composition and Dispatch: Uses the email sender action group to notify relevant parties about missing documents.

  Example Email sent:
    <img width="713" alt="Screenshot 2023-11-28 at 12 39 04 PM" src="https://github.com/madhurprash/amazon-bedrock-samples/assets/129979633/8aa905ea-4dbf-45b1-8f93-be12648e985d">

  
    <img width="646" alt="Screenshot 2023-11-28 at 12 37 58 PM" src="https://github.com/madhurprash/amazon-bedrock-samples/assets/129979633/10ea9588-f4f7-4f6a-b5b8-aea934901f76">

6. Confirmation of Task Completion: Confirms successful reminder dispatch.

### Agent Manual Deployment Guide:

1. S3 Bucket Preparation: Ensure an existing S3 bucket in the same region as the agent.
Agent IAM Role Creation: Follow these instructions for IAM role creation.

2. Initial Agent Setup: Use Amazon Bedrock service for initial agent creation. Instructions are in the Agent Instruction section.

3. Lambda Function Setup: Create a Lambda function with provided code and upload necessary files.

4. Working Draft and Action Group: Set up a working draft, action group, and associate resources.

5. Execution Timeout and IAM Roles: Configure Lambda function settings and attach IAM roles.

6. Resource-Based Policy Attachment: Implement the provided policy for Lambda function access.

### Agent Instruction:
"You are an agent that can handle various tasks related to insurance claims,including looking up claim details, finding what paperwork is outstanding andgetting the requirements for those based on documents available in a Knowledge Base,and sending reminders. Once you have sent the reminder, say "Reminder on claims and missing documents and requirements sent successfully". Send all of the information on the missing and pending documents you get from the "insurance-claims-agent-kb" knowledge base in the reminder email to the recipients while invoking the emailsender action group."

#### Model Used: Anthropic Claude-V2

### Knowledge Base Instructions for Agent:
"Use this Knowledge Base to detail the requirements of each missing document in a insurance claim"
