#!/usr/bin/env node
import 'source-map-support/register';
import * as path from 'path';
import * as glob from 'glob';
import * as cdk from 'aws-cdk-lib';
import { BedrockAgentCdkStack } from '../lib/bedrock-agent-cdk-stack';

const app = new cdk.App();

// Get the spec file found in lambda dir
const specDir = 'lib/assets/api-schema'; 
const jsonOrYmlFile = glob.sync('**/*', { cwd: specDir });
const specFilePath = jsonOrYmlFile[0];
const specFile = path.basename(specFilePath)  

// Get the .py file found in lambda dir
const lambdaDir = 'lib/assets/lambdas/agent'; 
const pyFile = glob.sync('**/*.py', { cwd: lambdaDir });
const lambdaFilePath = pyFile[0];
const lambdaFile = path.basename(lambdaFilePath.replace(/\.py$/, '')) 

const appStack = new BedrockAgentCdkStack(app, `BedrockAgentCDKStack`, {
  specFile: specFile,
  lambdaFile: lambdaFile,
});