// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

// Local Dependencies:
import { PublicVpcLoadBalancer } from "./load-balancer";
import {
  ILangfuseServiceSharedProps,
  LangfuseServiceBase,
} from "./service-base";

const LANGFUSE_WEB_PORT = 3000;

interface ILangfuseWebServiceProps extends ILangfuseServiceSharedProps {
  /**
   * (STRONGLY RECOMMENDED) Load balancer infrastructure to connect through
   *
   * We provide the ability to set 'null' here mainly in order to simplify temporarily removing the
   * LB from the stack to work through debugging or failed updates. If you don't have a load
   * balancer, the ECS service will be deployed with a global publicly accessible (internet)
   * security group.
   */
  loadBalancer: PublicVpcLoadBalancer | null;
  /**
   * Secrets Manager Secret to use for Langfuse NEXTAUTH_SECRET configuration
   *
   * See: https://langfuse.com/self-hosting/configuration
   */
  nextAuthSecret: secretsmanager.ISecret;
  /**
   * Optional Secrets Manager Secret storing Cognito authentication parameters
   *
   * Providing this parameter will set up Langfuse environment variables to use Cognito and disable
   * open user sign-up. The secret should be a key-value format containing at least
   * `clientId`, `clientSecret`, and `issuer` fields.
   *
   * @default None
   */
  authCognitoSecret?: secretsmanager.ISecret;
  /**
   * Source container image name for the worker
   *
   * @default 'langfuse/langfuse'
   */
  imageName?: string;
}

/**
 * Construct for an ECS-based service to run Langfuse's primary web server
 */
export class LangfuseWebService extends LangfuseServiceBase {
  constructor(scope: Construct, id: string, props: ILangfuseWebServiceProps) {
    super(scope, id, {
      ...props,
      environment: {
        NEXTAUTH_URL: props.loadBalancer
          ? props.loadBalancer.url
          : `http://0.0.0.0:${LANGFUSE_WEB_PORT}`,
        ...(props.authCognitoSecret && {
          AUTH_COGNITO_ALLOW_ACCOUNT_LINKING: "true",
          AUTH_DISABLE_SIGNUP: "false",
          AUTH_DISABLE_USERNAME_PASSWORD: "true",
        }),
        ...(props.environment || {}),
      },
      healthCheck: {
        command: [
          "CMD-SHELL",
          // >> to capture health check in task/service logs as described at:
          // https://docs.aws.amazon.com/AmazonECS/latest/developerguide/view-container-health.html
          `wget --no-verbose --tries=1 --spider http://localhost:${LANGFUSE_WEB_PORT}/api/public/health >> /proc/1/fd/1 2>&1  || exit 1`,
        ],
        interval: cdk.Duration.minutes(2),
        retries: 3,
        startPeriod: cdk.Duration.minutes(3),
        timeout: cdk.Duration.seconds(15),
      },
      imageName: props.imageName || "langfuse/langfuse",
      portMappings: [
        {
          containerPort: LANGFUSE_WEB_PORT,
          hostPort: LANGFUSE_WEB_PORT,
          protocol: ecs.Protocol.TCP,
        },
      ],
      secrets: {
        NEXTAUTH_SECRET: ecs.Secret.fromSecretsManager(props.nextAuthSecret),
        ...(props.authCognitoSecret && {
          AUTH_COGNITO_CLIENT_ID: ecs.Secret.fromSecretsManager(
            props.authCognitoSecret,
            "clientId",
          ),
          AUTH_COGNITO_CLIENT_SECRET: ecs.Secret.fromSecretsManager(
            props.authCognitoSecret,
            "clientSecret",
          ),
          AUTH_COGNITO_ISSUER: ecs.Secret.fromSecretsManager(
            props.authCognitoSecret,
            "issuer",
          ),
        }),
      },
      serviceName: "web",
    });

    if (props.authCognitoSecret)
      props.authCognitoSecret.grantRead(
        this.fargateService.taskDefinition.taskRole,
      );

    const securityGroup = new ec2.SecurityGroup(this, "WebSG", {
      vpc: props.vpc,
      allowAllOutbound: false,
      description: "Langfuse web container tasks",
    });
    cdk.Tags.of(securityGroup).add("Name", "langfuse-web");
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(securityGroup).add(tag.key, tag.value),
      );
    }

    this.fargateService.connections.addSecurityGroup(securityGroup);

    if (props.loadBalancer) {
      securityGroup.addIngressRule(
        ec2.Peer.securityGroupId(
          props.loadBalancer.securityGroup.securityGroupId,
        ),
        ec2.Port.tcp(LANGFUSE_WEB_PORT),
        "Inbound access from ALB",
      );
      props.loadBalancer.addTargets("HTTP", {
        healthCheck: {
          enabled: true,
          path: "/api/public/health",
        },
        port: 3000,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targets: [this.fargateService],
      });
    } else {
      // (This will raise a CDK Nag error if selected, but we don't suppress it because it's an
      // explicit user configuration choice and they should be made aware of the risk)
      securityGroup.addIngressRule(
        ec2.Peer.ipv4("0.0.0.0/0"),
        ec2.Port.tcp(LANGFUSE_WEB_PORT),
        "PUBLIC inbound web access",
      );
    }

    // Auto-scaling:
    const scalableTarget = this.fargateService.autoScaleTaskCount({
      maxCapacity: 2,
    });
    scalableTarget.scaleOnCpuUtilization("LfAutoscaling", {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(120),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });
  }
}
