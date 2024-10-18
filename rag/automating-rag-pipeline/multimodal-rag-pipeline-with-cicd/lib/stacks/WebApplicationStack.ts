import { CfnOutput, Duration, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { join } from 'path';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { PolicyStatement } from 'aws-cdk-lib/aws-iam';

export interface WebAppStackProps extends StackProps {
    readonly knowledgeBaseId: string;
    stageName?: string;

}

export class WebApplicationStack extends Stack {
    constructor(scope: Construct, id: string, props: WebAppStackProps) {
        super(scope, id, props);

        // Create a new VPC with a specific CIDR range, 2 Availability Zones, and 1 NAT Gateway.
        const vpc = new ec2.Vpc(this, 'MyVpc', {
            maxAzs: 2,  // Use two Availability Zones
            ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),  // CIDR block for the VPC
            natGateways: 1,  // Number of NAT Gateways
        });

        // Create a security group for the ECS service that allows all outbound traffic.
        const ecsSecurityGroup = new ec2.SecurityGroup(this, 'EcsSecurityGroup', {
            vpc,
            allowAllOutbound: true,  // Allow all outbound traffic
        });

        // Create a security group for the ALB that allows all outbound traffic.
        const albSecurityGroup = new ec2.SecurityGroup(this, 'AlbSecurityGroup', {
            vpc,
            allowAllOutbound: true,  // Allow all outbound traffic
        });

        // Allow incoming HTTP traffic (port 80) from the ALB security group to the ECS security group.
        ecsSecurityGroup.addIngressRule(albSecurityGroup, ec2.Port.tcp(80), 'Allow traffic from ALB');

        // Create an ECS cluster within the VPC, enabling Fargate capacity providers.
        const ecsCluster = new ecs.Cluster(this, 'MyEcsCluster', {
            vpc,
            enableFargateCapacityProviders: true,  // Enable Fargate capacity providers
        });

        // Define a Fargate task with specific CPU and memory limits.
        const fargateTaskDefinition = new ecs.FargateTaskDefinition(this, 'MyFargateTaskDefinition', {
            memoryLimitMiB: 512,  // Memory limit for the task
            cpu: 256,  // CPU units for the task
        });

        // Create the Lambda function
        const mainLambdaFunction = new NodejsFunction(this, 'MainLambdaFunction', {
            runtime: Runtime.NODEJS_18_X,
            entry: (join(__dirname, '..', '..', 'src', 'services', 'main-lambda.ts')),
            handler: 'handler',
            timeout: Duration.minutes(5),
            environment: {
                STAGE_NAME: props?.stageName!,
                KNOWLEDGE_BASE_ID: props.knowledgeBaseId,
            },
        });

        // Grant the Lambda function permission to invoke Bedrock
        mainLambdaFunction.addToRolePolicy(
            new PolicyStatement({
                actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
                resources: ['*'],  // TODO CRITICAL: Restrict to specific models
            }),
        );

        // Grant the Lambda function permission to access KnowledgeBase for Amazon Bedrock to retrieve and generate responses
        const kbRetrieveAndGeneratePolicy = new PolicyStatement({
            actions: ['bedrock:RetrieveAndGenerate', 'bedrock:Retrieve'],
            resources: ['*'],  // TODO CRITICAL: Restrict to specific knowledge bases
            sid: 'KnowledgebaseRetrieveAndGeneratePolicy',
        });

        mainLambdaFunction.addToRolePolicy(kbRetrieveAndGeneratePolicy);

        // Define the API Gateway to trigger the Lambda function
        const chatAPI = new apigateway.RestApi(this, 'InvokeBedrock', {
            restApiName: 'InvokeBedrock API',
            description: 'This service invokes the Bedrock Main Lambda function',
            deployOptions: {
                stageName: props?.stageName!,
                loggingLevel: apigateway.MethodLoggingLevel.INFO,
                dataTraceEnabled: true,
            },
        });

        // Create a new API Gateway resource with the path /invoke
        const invokeResource = chatAPI.root.addResource('invoke');

        // Define the Lambda integration for the API Gateway resource
        const invokeIntegration = new apigateway.LambdaIntegration(mainLambdaFunction);

        // Add the Lambda integration to the API Gateway resource
        invokeResource.addMethod('POST', invokeIntegration);

        // Output the API Gateway endpoint URL
        new CfnOutput(this, 'ApiGatewayEndpoint', {
            value: chatAPI.url,
        });

        // Build the container image from the local Dockerfile and push it to Amazon ECR.
        // const containerImage = ecs.ContainerImage.fromAsset('./src/app');
        const containerImage = ecs.ContainerImage.fromAsset('./src');

        // Add a container to the Fargate task definition, using the local container image.
        const container = fargateTaskDefinition.addContainer('MyContainer', {
            image: containerImage,  // Container image
            memoryLimitMiB: 512,  // Memory limit for the container
            cpu: 256,  // CPU units for the container
            logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'WebContainerLogs' }),  // Enable logging
            environment: {
                STAGE_NAME: props?.stageName!,
                APIGATEWAY_ENDPOINT: chatAPI.url,
            },
            // entryPoint: ["app.handler"],
            // command: ["streamlit", "run", "app.py"],
        });

        // Map port 8501 of the container to the host.
        container.addPortMappings({
            containerPort: 8501,  // Port on the container
            protocol: ecs.Protocol.TCP,  // TCP protocol
        });

        // Create a Fargate service for the task definition, placing tasks in private subnets.
        const fargateService = new ecs.FargateService(this, 'MyFargateService', {
            cluster: ecsCluster,  // The ECS cluster where the service will run
            taskDefinition: fargateTaskDefinition,  // The task definition to use
            securityGroups: [ecsSecurityGroup],  // Security group for the service
            vpcSubnets: {
                subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,  // Subnets for the service
            },
        });

        // Create an Application Load Balancer (ALB) that is internet-facing.
        const alb = new elbv2.ApplicationLoadBalancer(this, 'MyAlb', {
            vpc,
            internetFacing: true,  // ALB is internet-facing
            securityGroup: albSecurityGroup,  // Security group for the ALB
            vpcSubnets: {
                subnetType: ec2.SubnetType.PUBLIC,  // Subnets for the ALB
            },
        });

        // Add a listener on the ALB that listens for HTTP (port 80) traffic.
        const httpListener = alb.addListener('HttpListener', {
            port: 80,  // Listening on port 80
            open: true,  // Allow anyone to connect
        });

        // Forward incoming requests to the Fargate service on port 80.
        httpListener.addTargets('FargateServiceTarget', {
            port: 8501,  // Forward to the container's port 8501
            protocol: elbv2.ApplicationProtocol.HTTP,  // HTTP protocol
            targets: [fargateService],  // Target the Fargate service
        });

        // Output the DNS name of the ALB.
        new CfnOutput(this, 'AlbDnsName', {
            value: alb.loadBalancerDnsName,  // DNS name of the ALB
        });
    }
}




// // Add a container to the Fargate task definition, using the 'amazon/amazon-ecs-sample' image.
// const container = fargateTaskDefinition.addContainer('MyContainer', {
//     image: ecs.ContainerImage.fromRegistry('amazon/amazon-ecs-sample'),  // Container image
//     memoryLimitMiB: 512,  // Memory limit for the container
//     cpu: 256,  // CPU units for the container
//     logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'WebContainerLogs' }),  // Enable logging
// });

// // Map port 80 of the container to the host.
// container.addPortMappings({
//     containerPort: 80,  // Port on the container
// });
