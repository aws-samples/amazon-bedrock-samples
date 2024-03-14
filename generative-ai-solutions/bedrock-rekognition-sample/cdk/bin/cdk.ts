#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { MultiModal } from '../lib/multi-modal-stack';

const app = new cdk.App();
const stack = new MultiModal(app, 'MultiModalLLMStack');