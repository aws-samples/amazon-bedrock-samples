// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
// External Dependencies:
import * as cdk from "aws-cdk-lib";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as cloudfront_origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cr from "aws-cdk-lib/custom-resources";
import { NagSuppressions } from "cdk-nag";
import { Construct } from "constructs";

export interface IPublicVpcLoadBalancerProps {
  vpc: ec2.IVpc;
  /**
   * Provide an S3 bucket if you want to enable access logging for the load balancer.
   *
   * (PublicVpcLoadBalancer.loadBalancer fail CDK-Nag 'AwsSolutions-ELB2' check if not provided)
   *
   * @default undefined Access logging will not be enabled
   */
  accessLogBucket?: s3.IBucket;
  /**
   * S3 Key prefix for load balancer access logs, if `accessLogBucket` was provided.
   * @default 'access-logs'
   */
  accessLogPrefix?: string;
  /**
   * Use this option to *skip* deploying AWS CloudFront in front of the Load Balancer
   *
   * Without CloudFront, users will need to connect directly to your ALB which won't support HTTPS
   * (unless you set up a domain and ACM certificate separate from this construct). Leave the
   * default (false) for users to connect over HTTPS via CloudFront (and benefit from caching on
   * the static website assets!)
   *
   * @default false
   */
  disableCloudFront?: boolean;
  /**
   * AWS Tags to apply to created resources (cluster, security groups, etc)
   */
  tags?: cdk.Tag[];
}

/**
 * A VPC-based HTTP(S) load balancer with CloudFront CDN *OR* direct public access (configurable)
 *
 * Includes security group and listener setup.
 */
export class PublicVpcLoadBalancer extends Construct {
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  /**
   * Security group associated with the load balancer (for granting access to your servers)
   */
  public readonly securityGroup: ec2.SecurityGroup;

  private cloudFrontDistribution?: cloudfront.Distribution;
  private listeners: {
    [protocol in elbv2.ApplicationProtocol]?: elbv2.ApplicationListener;
  };

  constructor(
    scope: Construct,
    id: string,
    props: IPublicVpcLoadBalancerProps,
  ) {
    super(scope, id);

    this.listeners = {};

    this.securityGroup = new ec2.SecurityGroup(this, "SG", {
      allowAllOutbound: false,
      description: "Security group for Langfuse load balancer",
      vpc: props.vpc,
    });
    cdk.Tags.of(this.securityGroup).add("Name", "web-alb-sg");
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.securityGroup).add(tag.key, tag.value),
      );
    }

    this.loadBalancer = new elbv2.ApplicationLoadBalancer(
      this,
      "LoadBalancer",
      {
        internetFacing: !!props.disableCloudFront,
        securityGroup: this.securityGroup,
        vpc: props.vpc,
      },
    );
    if (props.accessLogBucket) {
      this.loadBalancer.logAccessLogs(
        props.accessLogBucket,
        props.accessLogPrefix || "access-logs",
      );
    }
    if (props.tags) {
      props.tags.forEach((tag) =>
        cdk.Tags.of(this.loadBalancer).add(tag.key, tag.value),
      );
    }

    this.loadBalancer.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);

    if (!props.disableCloudFront) {
      const cfOrigin = cloudfront_origins.VpcOrigin.withApplicationLoadBalancer(
        this.loadBalancer,
        {
          // (Can't support HTTPS-to-ALB without a domain name & ACM cert)
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        },
      );

      const cfDist = new cloudfront.Distribution(this, "CloudFront", {
        comment: "Langfuse CloudFront distribution",
        defaultBehavior: {
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          origin: cfOrigin,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          viewerProtocolPolicy:
            cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        },
        additionalBehaviors: {
          "/api/*": {
            allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
            cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
            origin: cfOrigin,
            originRequestPolicy:
              cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            viewerProtocolPolicy:
              cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          },
        },
        priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      });
      if (props.tags) {
        props.tags.forEach((tag) =>
          cdk.Tags.of(cfDist).add(tag.key, tag.value),
        );
      }
      this.cloudFrontDistribution = cfDist;
      NagSuppressions.addResourceSuppressions(
        cfDist,
        [
          {
            id: "AwsSolutions-CFR3",
            reason: "Ignore CloudFront access logging",
          },
          // (If we were able to terminate HTTPS at ALB, we probably wouldn't need CloudFront in
          // the first place here)
          {
            id: "AwsSolutions-CFR4",
            reason: "Can't support HTTPS-to-ALB without domain+ACM",
          },
        ],
        true,
      );

      // We need to open the ALB SG to requests from CloudFront, it's not super straightforward
      // because CloudFront creates its own VPC SG, and the alternative IP prefix list is
      // region-dependent... So look up the created SG dynamically as documented at:
      // https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront_origins-readme.html#restrict-traffic-coming-to-the-vpc-origin
      const getCloudFrontSg = new cr.AwsCustomResource(this, "GetCFSG", {
        onCreate: {
          service: "ec2",
          action: "describeSecurityGroups",
          parameters: {
            Filters: [
              { Name: "vpc-id", Values: [props.vpc.vpcId] },
              // (The name is hard-wired by CloudFront itself:)
              {
                Name: "group-name",
                Values: ["CloudFront-VPCOrigins-Service-SG"],
              },
            ],
          },
          physicalResourceId: cr.PhysicalResourceId.of(
            "CloudFront-VPCOrigins-Service-SG",
          ),
        },
        policy: cr.AwsCustomResourcePolicy.fromSdkCalls({ resources: ["*"] }),
      });
      NagSuppressions.addResourceSuppressions(
        getCloudFrontSg,
        [
          {
            id: "AwsSolutions-IAM5",
            reason: "Policy defined in cdk-lib Lambda",
          },
        ],
        true,
      );
      const stack = cdk.Stack.of(this);
      NagSuppressions.addResourceSuppressionsByPath(
        stack,
        `${stack.node.path}/AWS679f53fac002430cb0da5b7982bd2287/ServiceRole/Resource`,
        [
          {
            id: "AwsSolutions-IAM4",
            reason: "Policy defined in cdk-lib Lambda",
          },
        ],
      );
      NagSuppressions.addResourceSuppressionsByPath(
        stack,
        `${stack.node.path}/AWS679f53fac002430cb0da5b7982bd2287/Resource`,
        [
          {
            id: "AwsSolutions-L1",
            reason: "Can't control runtime of upstream aws-cdk-lib Lambda",
          },
        ],
      );
      // The security group will only be available after the distributon is deployed:
      getCloudFrontSg.node.addDependency(cfDist);
      // Now we can specify the rule, without creating a circular dependency with .addIngressRule:
      new ec2.CfnSecurityGroupIngress(this, "CloudFrontIngress", {
        ipProtocol: "tcp",
        fromPort: 80,
        toPort: 80,
        groupId: this.securityGroup.securityGroupId,
        sourceSecurityGroupId: getCloudFrontSg.getResponseField(
          "SecurityGroups.0.GroupId",
        ),
      });
    } else {
      this.securityGroup.addIngressRule(
        ec2.Peer.ipv4("0.0.0.0/0"),
        ec2.Port.tcp(80),
      );
      this.securityGroup.addIngressRule(
        ec2.Peer.ipv4("0.0.0.0/0"),
        ec2.Port.tcp(443),
      );
      // This'll cause a high CDK Nag finding if configured, but we won't suppress it because it's
      // a deliberate user choice so they should be made aware of the finding.
    }
  }

  /**
   * The (http:// or https://) URL through which the service can be accessed
   */
  public get url() {
    return this.cloudFrontDistribution
      ? `https://${this.cloudFrontDistribution.distributionDomainName}`
      : `http://${this.loadBalancer.loadBalancerDnsName}`;
  }

  /**
   * Simplified mechanism to add targets to the load balancer and automatically create listeners
   *
   * Creates an application listener for the target protocol (with default settings) if one doesn't
   * already exist, and adds the target to that listener.
   *
   * @see https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_elasticloadbalancingv2.ApplicationListener.html#addwbrtargetsid-props
   */
  public addTargets(
    id: string,
    props: elbv2.AddApplicationTargetsProps & {
      protocol: elbv2.ApplicationProtocol;
      targets: elbv2.IApplicationLoadBalancerTarget[];
    },
  ): elbv2.IApplicationTargetGroup {
    if (!this.listeners[props.protocol]) {
      this.listeners[props.protocol] = this.loadBalancer.addListener(id, {
        open: !this.cloudFrontDistribution,
        protocol: props.protocol,
      });
    }
    const listener = this.listeners[props.protocol]!;
    return listener.addTargets(id, props);
  }
}
