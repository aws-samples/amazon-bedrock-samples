import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {BedrockAgentBlueprintsConstruct, AgentDefinitionBuilder, BedrockKnowledgeBaseModels} from '@aws/agents-and-function-calling-for-amazon-bedrock-blueprints';

export class AgentWithSimpleClassificationStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        const agentDef = new AgentDefinitionBuilder(this, 'ClassificationAgent', {})
            .withAgentName('custom-classification-agent')  
            .withInstruction(
            'You are an agent that classifies customer emails into 4 main categories:'+
            '* CUSTOMER_SUPPORT: when customers require the support of a service specialist that solve '+
            'an existing pain point' +
            '* COMPLAINT: when customer wants to submit a complain about a certain service or employee' + 
            '* FEEDBACK: when the customer is providing feedback about a service that he/she received'+
            '* OTHERS: any other topic'+
            'You ALWAYS answer with the email classification only, without adding any other text to it.'
                )
            .withFoundationModel('anthropic.claude-3-sonnet-20240229-v1:0');
           

            const agent = new BedrockAgentBlueprintsConstruct(this, 'AgentWithSimpleClassificationStack', {
                agentDefinition: agentDef.build(),
            });
    }
}