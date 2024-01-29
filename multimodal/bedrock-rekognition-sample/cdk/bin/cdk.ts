#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { MultiModal } from '../lib/multi-modal-stack';
import { AwsSolutionsChecks } from 'cdk-nag';


const app = new cdk.App();
new MultiModal(app, 'MultiModalLLMStack');
cdk.Aspects.of(app).add(new AwsSolutionsChecks());