import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { S3Construct } from './constructs/s3-bucket-construct'
import { BedrockIamConstruct } from './constructs/bedrock-agent-iam-construct';
import { LambdaIamConstruct } from './constructs/lambda-iam-construct';
import { LambdaConstruct } from './constructs/lambda-construct';
import { CustomBedrockAgentConstruct } from './constructs/custom-bedrock-agent-construct';
import { LambdaLayerConstruct } from './constructs/lambda-layer-construct';
import { S3 } from 'aws-cdk-lib/aws-ses-actions';

export interface BedrockAgentCdkProps extends cdk.StackProps {
  readonly specFile: string;
  readonly randomPrefix: number;
  readonly modelName: string;
  readonly agentInstruction: string;
}

export class BedrockAgentCdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BedrockAgentCdkProps) {
    super(scope, id, props);

    const resourceId = "BEDROCK_AGENT_CUSTOM_RESOURCE";
    const lambdaName = `bedrock-agent-lambda-${props.randomPrefix}`;
    const lambdaRoleName = `bedrock-agent-lambda-role-${props.randomPrefix}`;
    const agentResourceRoleName = `AmazonBedrockExecutionRoleForAgents_${props.randomPrefix}`; 
    const bedrockAgentLambdaPolicyName = `BedrockAgentLambdaPolicy-${props.randomPrefix}`;
    const bedrockAgentS3BucketPolicyName = `BedrockAgentS3BucketPolicy-${props.randomPrefix}`;
    const bedrockAgentBedrockModelPolicyName = `BedrockAgentBedrockModelPolicy-${props.randomPrefix}`;
    const lambdaAllowPolicyName = `LambdaAllowPolicy-${props.randomPrefix}`;
    const s3AllowPolicyName = `s3AllowPolicy-${props.randomPrefix}`;
    const bedrockAllowPolicyName = `BedrockAllowPolicy-${props.randomPrefix}`;
    const iamAllowPolicyName = `IamAllowPolicy-${props.randomPrefix}`;

    const agentName = new cdk.CfnParameter(this, "AgentName", {
      type: "String",
      description: "Name of the agent to be created.",
      default: `cdk-agent-${props.randomPrefix}`
    });

    // Create S3 bucket for new agent artifcats
    const s3CreateAgentConstruct = new S3Construct(this, `agent-${props.randomPrefix}`, {});

    // Create S3 bucket with Open API schema for create-agent
    const s3OpenApiConstruct = new S3Construct(this, `openapi-${props.randomPrefix}`, {
      assetFullPath: '../../assets/openapi-schema'
    });

    // Create Lambda layer
    const lambdaLayerConstruct = new LambdaLayerConstruct(this, `lambda-layer-construct-${props.randomPrefix}`, {});

    // Create IAM role for create-agent Lambda
    const lambdaRole = new LambdaIamConstruct(this, `LambdaIamConstruct-${props.randomPrefix}`, { 
      roleName: lambdaRoleName,
      s3BucketArn: s3CreateAgentConstruct.bucket.bucketArn,
      lambdaAllowPolicyName: lambdaAllowPolicyName,
      s3AllowPolicyName: s3AllowPolicyName,
      bedrockAllowPolicyName: bedrockAllowPolicyName,
      iamAllowPolicyName: iamAllowPolicyName
    });
    lambdaRole.node.addDependency(s3OpenApiConstruct);

    // Create IAM role for create-agent agent
    const bedrockAgentRole = new BedrockIamConstruct(this, `BedrockIamConstruct-${props.randomPrefix}`, { 
      roleName: agentResourceRoleName,
      lambdaRoleArn: lambdaRole.lambdaRole.roleArn,
      s3BucketArn: s3OpenApiConstruct.bucket.bucketArn,
      bedrockAgentLambdaPolicy: bedrockAgentLambdaPolicyName,
      bedrockAgentS3BucketPolicy: bedrockAgentS3BucketPolicyName,
      bedrockAgentBedrockModelPolicy: bedrockAgentBedrockModelPolicyName
    });
    bedrockAgentRole.node.addDependency(lambdaRole);
    bedrockAgentRole.node.addDependency(s3OpenApiConstruct);

    // Create Lambda function for create-agent agent
    const agentLambdaConstruct = new LambdaConstruct(this, `LambdaConstruct-${props.randomPrefix}`, {
      lambdaName: lambdaName,
      iamRole: lambdaRole.lambdaRole,
      lambdaLayer: lambdaLayerConstruct.lambdaLayer,
    });
    agentLambdaConstruct.node.addDependency(lambdaRole);
    agentLambdaConstruct.node.addDependency(lambdaLayerConstruct);

    // Create custom resource for deploying agent
    const customBedrockAgentConstruct = new CustomBedrockAgentConstruct(this, `custom-bedrock-agent-construct-${props.randomPrefix}`, {
      resourceId: resourceId,
      agentName: agentName.valueAsString,
      s3BucketName: s3OpenApiConstruct.bucketName,
      s3BucketArn: s3OpenApiConstruct.bucket.bucketArn,
      s3BucketKey: props.specFile,
      bedrockAgentRoleArn: bedrockAgentRole.roleArn,
      lambdaArn: agentLambdaConstruct.lambdaArn,
      bedrockAgentRoleName: agentResourceRoleName,
      modelName: props.modelName,
      instruction: props.agentInstruction,
      lambdaLayer: lambdaLayerConstruct.lambdaLayer,
    });
    customBedrockAgentConstruct.node.addDependency(bedrockAgentRole);
    customBedrockAgentConstruct.node.addDependency(agentLambdaConstruct);

    new cdk.CfnOutput(this, 'S3BucketNameForNewAgentArtifacts', {
      value: `${s3CreateAgentConstruct.bucketName}`
    });

    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: `${lambdaName}`
    });
  }
}
