import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { S3Construct } from './constructs/s3-bucket-construct';
import { BedrockIamConstruct } from './constructs/bedrock-agent-iam-construct';
import { LambdaIamConstruct } from './constructs/lambda-iam-construct';
import { LambdaConstruct } from './constructs/lambda-construct';
import { CustomBedrockAgentConstruct } from './constructs/custom-bedrock-agent-construct';

export interface BedrockAgentCdkProps extends cdk.StackProps {
  readonly specFile: string;
  readonly lambdaFile: string;
}

export class BedrockAgentCdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BedrockAgentCdkProps) {
    super(scope, id, props);

    // Generate random number to avoid roles and lambda duplicates
    const randomPrefix = Math.floor(Math.random() * (10000 - 100) + 100);
    const collectionId = "BEDROCK_AGENT_CUSTOM_RESOURCE";
    const lambdaName = `bedrock-agent-lambda-${randomPrefix}`;
    const lambdaRoleName = `bedrock-agent-lambda-role-${randomPrefix}`;
    const agentResourceRoleName = `AmazonBedrockExecutionRoleForAgents_${randomPrefix}`; 
    const agentName = this.node.tryGetContext("agentName") || `cdk-agent-${randomPrefix}`;

    const lambdaRole = new LambdaIamConstruct(this, `LambdaIamConstruct-${randomPrefix}`, { roleName: lambdaRoleName });
    const s3Construct = new S3Construct(this, `agent-assets-${randomPrefix}`, {});
    const bedrockAgentRole = new BedrockIamConstruct(this, `BedrockIamConstruct-${randomPrefix}`, { 
      roleName: agentResourceRoleName,
      lambdaRoleArn: lambdaRole.lambdaRole.roleArn,
      s3BucketArn: s3Construct.bucket.bucketArn,
    });
    bedrockAgentRole.node.addDependency(lambdaRole);
    bedrockAgentRole.node.addDependency(s3Construct);
    const agentLambdaConstruct = new LambdaConstruct(this, `LambdaConstruct-${randomPrefix}`, {
      lambdaName: lambdaName,
      lambdaFile: props.lambdaFile,
      lambdaRoleName: lambdaRoleName,
      iamRole: lambdaRole.lambdaRole
    });
    agentLambdaConstruct.node.addDependency(lambdaRole);

    const customBedrockAgentConstruct = new CustomBedrockAgentConstruct(this, `custom-bedrock-agent-construct-${randomPrefix}`, {
      collectionId: collectionId,
      agentName: agentName,
      s3BucketName: s3Construct.bucketName,
      s3BucketArn: s3Construct.bucket.bucketArn,
      bedrockAgentRoleArn: bedrockAgentRole.roleArn,
      lambdaArn: agentLambdaConstruct.lambdaArn,
      s3BucketKey: props.specFile,
      bedrockAgentRoleName: agentResourceRoleName
    });
    customBedrockAgentConstruct.node.addDependency(bedrockAgentRole);
    customBedrockAgentConstruct.node.addDependency(agentLambdaConstruct);
  }
}
