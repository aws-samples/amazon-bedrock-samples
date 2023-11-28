#!/usr/bin/env node
import 'source-map-support/register';
import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import { BedrockAgentCdkStack } from '../lib/bedrock-agent-cdk-stack';

const app = new cdk.App();

// Generate random number to avoid roles and lambda duplicates
const randomPrefix = Math.floor(Math.random() * (1000 - 100) + 100);

const specCreateAgentFile = "create-agent-schema.json";
const specCreateKbFile = "invoke-create-kb-lambda-schema.json";  
const modelName = "anthropic.claude-v2";
const agentInstruction = `
You are an assistant for solution architects (SA) to create code for Agents for Amazon Bedrock.
When creating an agent, consider the following: 1. The user may tell you where to save the artifacts, and they may not tell you that it is an s3 bucket. 
Assume that the destination they provide is indeed the name of the s3 bucket. If they provide the bucket name, use it instead of prompting them for the bucket name.
2. The user may describe an entire list of actions or api's 3.
They may refer to the api in various terms like method, function, tool, action
4. Feel free to come up with an agent name based on the description when returning results of creation of an agent but always keep it under 20 characters long. 
After you create an agent and return the response from "Create-Agent", ask user if they want to create a knowledge base and associate it to the newly created agent. If the user answers affirmative, inquire for S3 bucket name with files. 
Don't create random S3 bucket name. Once they do, use "Create-Knowledge-Base" action group and create a knowledge base. 
If the answer is negative, i.e. they said "no" or similar to the knowledge base creation request - do not do anything.
`;

new BedrockAgentCdkStack(app, 'BedrockAgentCdkStack', {
  specCreateAgentFile: specCreateAgentFile,
  specCreateKbFile: specCreateKbFile,
  randomPrefix: randomPrefix,
  modelName: modelName,
  agentInstruction: agentInstruction,
  synthesizer: new cdk.DefaultStackSynthesizer({
    generateBootstrapVersionRule: false
  })
});