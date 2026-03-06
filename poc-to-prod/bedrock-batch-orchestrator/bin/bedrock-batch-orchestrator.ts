#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { BedrockBatchOrchestratorStack } from '../lib/bedrock-batch-orchestrator-stack';

const app = new cdk.App();
new BedrockBatchOrchestratorStack(app, 'BedrockBatchOrchestratorStack', {
    maxSubmittedAndInProgressJobs: app.node.tryGetContext('maxSubmittedAndInProgressJobs')!,  // required in cdk.json
    bedrockBatchInferenceTimeoutHours: app.node.tryGetContext('bedrockBatchInferenceTimeoutHours'),
    notificationEmails: app.node.tryGetContext('notificationEmails'),
});
