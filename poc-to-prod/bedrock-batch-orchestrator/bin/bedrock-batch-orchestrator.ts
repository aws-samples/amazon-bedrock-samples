#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { BedrockBatchOrchestratorStack } from '../lib/bedrock-batch-orchestrator-stack';

const app = new cdk.App();
new BedrockBatchOrchestratorStack(app, 'BedrockBatchOrchestratorStack', {
    bedrockBatchInferenceMaxConcurrency: app.node.tryGetContext('bedrockBatchInferenceMaxConcurrency')!,  // required in cdk.json
    bedrockBatchInferenceTimeoutHours: app.node.tryGetContext('bedrockBatchInferenceTimeoutHours'),
});
