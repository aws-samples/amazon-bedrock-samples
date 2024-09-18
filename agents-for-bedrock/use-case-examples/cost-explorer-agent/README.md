# Cost Explorer Agent: Decoding AWS Costs with Amazon Bedrock
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Cost Explorer Agent powered by Amazon Bedrock Agent help users understand and optimize their AWS costs. By utilizing AWS Cost Explorer data, this AI assistant does cost analysis, provides recommendations, and answers questions related to AWS billing and spend.

## Features

- Answer questions about your AWS Spend and does detailed AWS cost analysis
- Provide cost optimization recommendations
- Optional Slack integration for easy team collaboration
- Deployed using AWS CloudFormation for easy setup and management

## Prerequisites

Before deployment, ensure you have:

1. An AWS account with:
   - [AWS CLI](https://aws.amazon.com/cli/) installed and configured
   - [Access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) to Amazon Bedrock (with approved access to the desired Claude model)
   - API Gateway CloudWatch Logging Role set up (if not already configured - [AWS documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html))

2. [Python 3.12](https://www.python.org/downloads/) with pip package manager installed

### Optional (for Slack integration)
- A [Slack workspace](https://slack.com/) where you can create a new app

This can be deployed with or without Slack integration. If you choose to enable Slack integration during deployment, you'll need access to a Slack workspace where you can create a new app.

## Deployment

### 1. Slack App Setup (Optional)

This step is only necessary if you plan to enable Slack integration during deployment.

Create a Slack app and obtain the necessary credentials:

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click "Create New App" > "From scratch".
2. Name your app "aws-billing-agent" and select your workspace.
3. In the app settings, go to "OAuth & Permissions" and add the following Bot Token Scopes:
   - app_mentions:read
   - chat:write
   - chat:write.public
   - channels:read
4. Scroll up and click "Install to Workspace", then authorize the app.
5. After installation, copy the "Bot User OAuth Token" from the "OAuth & Permissions" page.
6. Go to "Basic Information" and copy the "Signing Secret" under "App Credentials".

Keep these values handy; you'll need them for the CloudFormation deployment.

### 2. CloudFormation Deployment

1. Clone this repository:
   ```
   git clone https://github.com/aws-samples/amazon-bedrock-samples.git 
   cd amazon-bedrock-samples/agents-for-bedrock/use-case-examples/cost-explorer-agent/
   ```

2. Run the deployment script:
   ```
   ./deploy.sh
   ```
   Follow the prompts to configure your deployment options.


3. After the stack is deployed, if Slack integration was enabled, note the API Gateway URL from the CloudFormation outputs. You'll need this to complete the Slack app setup.

### 3. Complete Slack App Configuration (Optional)

This section is only necessary if you chose to enable Slack integration during deployment.

1. Go back to your Slack app settings at [https://api.slack.com/apps](https://api.slack.com/apps).
2. Go to "Event Subscriptions" and toggle "Enable Events" to On.
3. Set the Request URL to the API Gateway URL from your CloudFormation stack outputs.
4. Under "Subscribe to bot events", add the `app_mention` event.
5. Save your changes.

### 4. Add the Bot to a Channel (Optional)

This section is only necessary if you chose to enable Slack integration during deployment.

1. In your Slack workspace, go to the channel where you want to use the bot.
2. Type `/invite @aws-billing-agent` to add the bot to the channel.

## Usage

### Slack Interaction (Optional)

If Slack integration is enabled, mention the bot in your Slack channel followed by your question:


```
@aws-billing-agent What were my AWS costs last month?
```


**Important Notes:**
1. The agent maintains conversation history within the reply thread of the initial message. This allows you to ask follow-up questions without repeating context.
2. The conversation history is valid for 1800 seconds (30 minutes) from the last message. After this time, a new mention will start a fresh conversation.
3. To ask follow-up questions, reply in the thread of the agent's response. You don't need to mention the bot again when replying in the thread.


This threaded conversation approach allows for more natural and context-aware interactions with the agent.

   ![Slack Demo](static/slack-demo.gif)


### Amazon Bedrock Console Interaction

Interact with the agent in the Amazon Bedrock console by asking questions about AWS costs and usage. The agent will generate cost reports and provide optimization recommendations.

   ![Agent Demo](static/agent-demo.gif)


## Clean Up

delete the Cloud Formation Stack resources:

```
aws cloudformation delete-stack --stack-name [STACK NAME]
```

Then, manually delete the S3 bucket created during deployment if it's no longer needed.

If you enabled Slack integration, remember to also delete your Slack app from [https://api.slack.com/apps](https://api.slack.com/apps) if it's no longer needed.

## Security

See [CONTRIBUTING](CONTRIBUTING.md) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.