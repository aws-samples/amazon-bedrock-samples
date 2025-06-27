#!/usr/bin/env node
import 'source-map-support/register';
import { App, Aspects } from 'aws-cdk-lib';
import { BedrockAgentsStack } from '../lib/bedrockagents-stack.js';
import { AwsSolutionsChecks } from 'cdk-nag';

const app = new App();
new BedrockAgentsStack(app, 'BedrockAgentsStack', {});
Aspects.of(app).add(new AwsSolutionsChecks());
