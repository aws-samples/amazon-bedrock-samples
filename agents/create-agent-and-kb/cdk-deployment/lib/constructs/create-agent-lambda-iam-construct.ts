import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface CreateAgentLambdaIamProps extends cdk.StackProps {
  readonly roleName: string;
  readonly s3AgentArtifactsBucketArn: string;
  readonly s3KnowledgeBaseDataSourceBucketArn: string;
  readonly lambdaAllowPolicyName: string;
  readonly s3AllowPolicyName: string;
  readonly bedrockAllowPolicyName: string;
  readonly iamAllowPolicyName: string;
}

const defaultProps: Partial<CreateAgentLambdaIamProps> = {};

export class CreateAgentLambdaIamConstruct extends Construct {
  public lambdaRole: cdk.aws_iam.Role;

  constructor(scope: Construct, name: string, props: CreateAgentLambdaIamProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const lambdaRole = new cdk.aws_iam.Role(this, "CreateAgentLambdaRole", {
      roleName: props.roleName,
      assumedBy: new cdk.aws_iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [cdk.aws_iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess')]
    });

    const lambdaAllowPolicy = new cdk.aws_iam.Policy(this, "lambdaAllowPolicy", {
      policyName: props.lambdaAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'lambda:CreateFunction',
            'lambda:AddPermission'
          ],
        })
      ]
    });

    const iamAllowPolicy = new cdk.aws_iam.Policy(this, "iamCreateAgentAllowPolicy", {
      policyName: props.iamAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'iam:PassRole',
            'iam:CreateRole',
            'iam:AttachRolePolicy',
            'iam:GetRole',
            'iam:CreatePolicy'
          ],
        })
      ]
    });

    const s3AllowPolicy = new cdk.aws_iam.Policy(this, "s3CreateAgentAllowPolicy", {
      policyName: props.s3AllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: [props.s3AgentArtifactsBucketArn, `${props.s3AgentArtifactsBucketArn}/*`,
                      props.s3KnowledgeBaseDataSourceBucketArn, `${props.s3KnowledgeBaseDataSourceBucketArn}/*`],
          actions: [
            's3:PutObject',
            's3:GetObject*',
            's3:ListBucket',
          ],
        })
      ]
    });

    const bedrockAllowPolicy = new cdk.aws_iam.Policy(this, "bedrockCreateAgentAllowPolicy", {
      policyName: props.bedrockAllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: ['*'],
          actions: [
            'bedrock:*'
          ],
        })
      ]
    });

    lambdaRole.attachInlinePolicy(lambdaAllowPolicy);
    lambdaRole.attachInlinePolicy(s3AllowPolicy);
    lambdaRole.attachInlinePolicy(bedrockAllowPolicy);
    lambdaRole.attachInlinePolicy(iamAllowPolicy);

    this.lambdaRole = lambdaRole;
  }
}