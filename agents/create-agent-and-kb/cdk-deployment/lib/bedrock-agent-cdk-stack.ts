import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { S3Construct } from './constructs/s3-bucket-construct'
import { BedrockIamConstruct } from './constructs/bedrock-agent-iam-construct';
import { CreateAgentLambdaIamConstruct } from './constructs/create-agent-lambda-iam-construct';
import { LambdaConstruct } from './constructs/lambda-construct';
import { CustomBedrockAgentConstruct } from './constructs/custom-bedrock-agent-construct';
import { LambdaLayerConstruct } from './constructs/lambda-layer-construct';
import { InvokeKbLambdaIamConstruct } from './constructs/invoke-kb-lambda-iam-construct';
import { CreateKbLambdaIamConstruct } from './constructs/create-kb-lambda-iam-construct';
import { EventBridgeConstruct } from './constructs/event-bridge-construct';


export interface BedrockAgentCdkProps extends cdk.StackProps {
  readonly specCreateAgentFile: string;
  readonly specCreateKbFile: string;
  readonly randomPrefix: number;
  readonly modelName: string;
  readonly agentInstruction: string;
}

export class BedrockAgentCdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BedrockAgentCdkProps) {
    super(scope, id, props);

    const resourceId = "BEDROCK_AGENT_CUSTOM_RESOURCE";
    const createAgentLambdaName = `bedrock-agent-lambda-${props.randomPrefix}`;
    const createKbLambdaName = `bedrock-kb-lambda-${props.randomPrefix}`;
    const invokeKbLambdaName = `invoke-kb-lambda-${props.randomPrefix}`;
    const createAgentLambdaRoleName = `bedrock-agent-lambda-role-${props.randomPrefix}`;
    const createKbLambdaRoleName = `bedrock-kb-lambda-role-${props.randomPrefix}`;
    const invokeKbLambdaRoleName = `bedrock-invoke-lambda-role-${props.randomPrefix}`;
    const agentResourceRoleName = `AmazonBedrockExecutionRoleForAgents_${props.randomPrefix}`; 
    const bedrockAgentLambdaPolicyName = `BedrockAgentLambdaPolicy-${props.randomPrefix}`;
    const bedrockAgentS3BucketPolicyName = `BedrockAgentS3BucketPolicy-${props.randomPrefix}`;
    const bedrockAgentBedrockModelPolicyName = `BedrockAgentBedrockModelPolicy-${props.randomPrefix}`;
    const createAgentLambdaAllowPolicyName = `CreateAgentLambdaAllowPolicy-${props.randomPrefix}`;
    const createAgentS3AllowPolicyName = `CreateAgentS3AllowPolicy-${props.randomPrefix}`;
    const createAgentBedrockAllowPolicyName = `CreateAgentBedrockAllowPolicy-${props.randomPrefix}`;
    const createAgentIamAllowPolicyName = `CreateAgentIamAllowPolicy-${props.randomPrefix}`;
    const createKbLambdaAllowPolicyName = `CreateKbLambdaAllowPolicy-${props.randomPrefix}`;
    const createKbBedrockAllowPolicyName = `CreateKbBedrockAllowPolicy-${props.randomPrefix}`;
    const createKbIamAllowPolicyName = `CreateKbIamAllowPolicy-${props.randomPrefix}`;
    const createKbOpensearchAllowPolicyName = `CreateKbOpensearchAllowPolicy-${props.randomPrefix}`;
    const invokeCreateKbEventBusAllowPolicyName = `InvokeCreateKbEventBusAllowPolicy-${props.randomPrefix}`;

    const agentName = new cdk.CfnParameter(this, "AgentName", {
      type: "String",
      description: "Name of the agent to be created.",
      default: `cdk-agent-${props.randomPrefix}`
    });

    // Create S3 bucket for new agent artifcats
    const s3CreateAgentConstruct = new S3Construct(this, `agent-${props.randomPrefix}-artifacts`, {});

    // Create S3 bucket for knowledge base datasource
    const s3KnowledgeBaseDataSourceConstruct = new S3Construct(this, `agent-${props.randomPrefix}-knowledgebase`, {});

    // Create S3 bucket with Open API schema for create-agent
    const s3OpenApiConstruct = new S3Construct(this, `openapi-${props.randomPrefix}`, {
      assetFullPath: '../../assets/openapi-schemas'
    });

    // Create Lambda layer
    const lambdaLayerConstruct = new LambdaLayerConstruct(this, `lambda-layer-construct-${props.randomPrefix}`, {});

    // Create IAM role for create-agent Lambda
    const createAgentLambdaRole = new CreateAgentLambdaIamConstruct(this, `CreateAgentLambdaIamConstruct-${props.randomPrefix}`, { 
      roleName: createAgentLambdaRoleName,
      s3AgentArtifactsBucketArn: s3CreateAgentConstruct.bucket.bucketArn,
      s3KnowledgeBaseDataSourceBucketArn: s3KnowledgeBaseDataSourceConstruct.bucket.bucketArn,
      lambdaAllowPolicyName: createAgentLambdaAllowPolicyName,
      s3AllowPolicyName: createAgentS3AllowPolicyName,
      bedrockAllowPolicyName: createAgentBedrockAllowPolicyName,
      iamAllowPolicyName: createAgentIamAllowPolicyName
    });
    createAgentLambdaRole.node.addDependency(s3OpenApiConstruct);

    // Create IAM role for create-kb Lambda
    const createKbLambdaRole = new CreateKbLambdaIamConstruct(this, `CreateKbLambdaIamConstruct-kb-${props.randomPrefix}`, {
      roleName: createKbLambdaRoleName,
      lambdaAllowPolicyName: createKbLambdaAllowPolicyName,
      bedrockAllowPolicyName: createKbBedrockAllowPolicyName,
      iamAllowPolicyName: createKbIamAllowPolicyName,
      opensearchAllowPolicyName: createKbOpensearchAllowPolicyName
    });
    createKbLambdaRole.node.addDependency(s3OpenApiConstruct);

    // Create Lambda function for create-agent agent
    const createAgentLambdaConstruct = new LambdaConstruct(this, `LambdaAgentConstruct-${props.randomPrefix}`, {
      lambdaName: createAgentLambdaName,
      iamRole: createAgentLambdaRole.lambdaRole,
      lambdaLayer: lambdaLayerConstruct.lambdaLayer,
      handler: 'create_agent.lambda_handler',
      functionPath: '../../assets/lambda-function-create-agent',
      grantInvokeService: "bedrock.amazonaws.com",
      timeout: cdk.Duration.seconds(600)
    });
    createAgentLambdaConstruct.node.addDependency(createAgentLambdaRole);
    createAgentLambdaConstruct.node.addDependency(lambdaLayerConstruct);

    const createKnowledgeBaseConstruct = new LambdaConstruct(this, `LambdaKbConstruct-${props.randomPrefix}`, {
      lambdaName: createKbLambdaName,
      iamRole: createKbLambdaRole.lambdaRole,
      lambdaLayer: lambdaLayerConstruct.lambdaLayer,
      handler: 'create_knowledge_base.lambda_handler',
      functionPath: '../../assets/lambda-function-create-kb',
      grantInvokeService: "events.amazonaws.com",
      timeout: cdk.Duration.seconds(600)
    })
    createKnowledgeBaseConstruct.node.addDependency(createKbLambdaRole);
    createKnowledgeBaseConstruct.node.addDependency(lambdaLayerConstruct);

    // Create an EventBridge EventBus
    const eventBridgeConstruct = new EventBridgeConstruct(this, `event-bridge-construct-${props.randomPrefix}`, {
      createKbLambda: createKnowledgeBaseConstruct.lambda
    });
    eventBridgeConstruct.node.addDependency(createKnowledgeBaseConstruct);

    // Create IAM role for invoke-lambda 
    const invokeCreateKbLambdaRole = new InvokeKbLambdaIamConstruct(this, `InvokeKbLambdaIamConstruct-kb-${props.randomPrefix}`, {
      roleName: invokeKbLambdaRoleName,
      eventBusAllowPolicyName: invokeCreateKbEventBusAllowPolicyName,
      eventBusArn: eventBridgeConstruct.eventBusArn
    });
    invokeCreateKbLambdaRole.node.addDependency(eventBridgeConstruct);

    const invokeKnowledgeBaseLambdaConstruct = new LambdaConstruct(this, `LambdaInvokeCreateKbLambdaConstruct-${props.randomPrefix}`, {
      lambdaName: invokeKbLambdaName,
      iamRole: invokeCreateKbLambdaRole.lambdaRole,
      lambdaLayer: lambdaLayerConstruct.lambdaLayer,
      handler: 'invoke_create_knowledge_base_lambda.lambda_handler',
      functionPath: '../../assets/lambda-function-invoke-create-kb',
      grantInvokeService: 'bedrock.amazonaws.com',
      timeout: cdk.Duration.seconds(900)
    })
    invokeKnowledgeBaseLambdaConstruct.node.addDependency(invokeCreateKbLambdaRole);

    // Create IAM role for create-agent agent
    const bedrockAgentRole = new BedrockIamConstruct(this, `BedrockIamConstruct-${props.randomPrefix}`, { 
      roleName: agentResourceRoleName,
      createLambdaArn: createAgentLambdaConstruct.lambdaArn,
      invokeLambdaArn: invokeKnowledgeBaseLambdaConstruct.lambdaArn,
      s3BucketArn: s3OpenApiConstruct.bucket.bucketArn,
      bedrockAgentLambdaPolicy: bedrockAgentLambdaPolicyName,
      bedrockAgentS3BucketPolicy: bedrockAgentS3BucketPolicyName,
      bedrockAgentBedrockModelPolicy: bedrockAgentBedrockModelPolicyName
    });
    bedrockAgentRole.node.addDependency(createAgentLambdaConstruct);
    bedrockAgentRole.node.addDependency(invokeKnowledgeBaseLambdaConstruct);

    // Create custom resource for deploying agent
    const customBedrockAgentConstruct = new CustomBedrockAgentConstruct(this, `custom-bedrock-agent-construct-${props.randomPrefix}`, {
      resourceId: resourceId,
      agentName: agentName.valueAsString,
      s3BucketName: s3OpenApiConstruct.bucketName,
      s3BucketArn: s3OpenApiConstruct.bucket.bucketArn,
      s3BucketCreateAgentKey: props.specCreateAgentFile,
      s3BucketCreateKbKey: props.specCreateKbFile,
      bedrockAgentRoleArn: bedrockAgentRole.roleArn,
      createAgentLambdaArn: createAgentLambdaConstruct.lambdaArn,
      invokeCreateKbLambdaArn: invokeKnowledgeBaseLambdaConstruct.lambdaArn,
      bedrockAgentRoleName: agentResourceRoleName,
      modelName: props.modelName,
      instruction: props.agentInstruction,
      lambdaLayer: lambdaLayerConstruct.lambdaLayer,
    });
    customBedrockAgentConstruct.node.addDependency(bedrockAgentRole);
    customBedrockAgentConstruct.node.addDependency(createAgentLambdaConstruct);
    customBedrockAgentConstruct.node.addDependency(invokeKnowledgeBaseLambdaConstruct);

    new cdk.CfnOutput(this, 'S3BucketNameForNewAgentArtifacts', {
      value: `${s3CreateAgentConstruct.bucketName}`
    });

    new cdk.CfnOutput(this, 'S3BucketNameForKnowledgeBaseDataSource', {
      value: `${s3KnowledgeBaseDataSourceConstruct.bucketName}`,
    })
  }
}
