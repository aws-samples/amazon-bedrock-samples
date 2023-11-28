import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface LambdaIamProps extends cdk.StackProps {
  readonly roleName: string;
  readonly s3BucketArn: string;
  readonly lambdaAllowPolicyName: string;
  readonly s3AllowPolicyName: string;
  readonly bedrockAllowPolicyName: string;
  readonly iamAllowPolicyName: string;
}

const defaultProps: Partial<LambdaIamProps> = {};

export class LambdaIamConstruct extends Construct {
  public lambdaRole: cdk.aws_iam.Role;

  constructor(scope: Construct, name: string, props: LambdaIamProps) {
    super(scope, name);

    props = { ...defaultProps, ...props };

    const lambdaRole = new cdk.aws_iam.Role(this, "LambdaRole", {
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

    const iamAllowPolicy = new cdk.aws_iam.Policy(this, "iamAllowPolicy", {
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

    const s3AllowPolicy = new cdk.aws_iam.Policy(this, "s3AllowPolicy", {
      policyName: props.s3AllowPolicyName,
      statements: [
        new cdk.aws_iam.PolicyStatement({
          effect: cdk.aws_iam.Effect.ALLOW,
          resources: [props.s3BucketArn, `${props.s3BucketArn}/*`],
          actions: [
            's3:PutObject'
          ],
        })
      ]
    });

    const bedrockAllowPolicy = new cdk.aws_iam.Policy(this, "bedrockAllowPolicy", {
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