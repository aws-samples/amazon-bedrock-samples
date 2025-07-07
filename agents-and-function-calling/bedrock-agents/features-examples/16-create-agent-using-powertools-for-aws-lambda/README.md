# Bedrock Agent with Powertools for AWS

This sample demonstrates how to create an Amazon Bedrock Agent using Powertools for AWS (TypeScript) Event Handler for Bedrock Agent Functions.

## Prerequisites

Before you can deploy this sample, you must request access to a foundation model in Amazon Bedrock. Please refer to [this page](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) for more information.

Once you have access, take a note of the model ID (i.e. `amazon.nova-pro-v1:0`) and AWS Region (i.e. `us-west-2`) as you will need them to deploy the sample.

Finally, please make sure to review the IAM role and permissions defined in `lib/bedrockagents-stack.ts`, especially the one for the Bedrock Agent (search for `agentRole` in the file). Currently, the sample uses a `bedrock:*` permission to allow you to test the agent and experiment with it.

Before deploying an agent in production, review the [Bedrock Agent documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_id-based-policy-examples-agent.html) to ensure you have the right permissions in place.

## Deploy

After cloning this repository, you can deploy the sample using the AWS CDK.

```bash
npm ci
npm run cdk deploy -- --context modelId=amazon.nova-pro-v1:0 --region us-west-2
```

The sample will create a Bedrock Agent with a single AWS Lambda function that uses the Powertools for AWS Lambda [Event Handler for Bedrock Agent Functions](https://s12d.com/bedrock-agents-sample-github-link). The function is written in TypeScript, but you can adapt it to your preferred language using the same Powertools for AWS feature available in [Python](https://docs.powertools.aws.dev/lambda/python/latest/core/event_handler/bedrock_agents/) and [.NET](https://docs.powertools.aws.dev/lambda/dotnet/core/event_handler/bedrock_agent_function/).

## Test

Use the Bedrock Console to test the agent, try asking it questions like:

- What's the weather in Seattle?
- What's the weather like in Madrid and in Rome?

You can then go in CloudWatch Log Insights and run the following query to see the logs:

```sql
fields message, level, timestamp, requestId, correlation_id as sessionId, tool
| filter sessionId = "536254204126922" # Replace with your session ID
# | filter city = "city_name" # Uncomment to filter by city
| sort timestamp asc
| limit 10000
```

## Cleanup

```bash
npm run cdk destroy
```

## License

MIT-0
