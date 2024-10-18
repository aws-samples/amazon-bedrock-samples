// Import necessary AWS CDK modules and constructs.
import { CfnOutput, Duration, RemovalPolicy, Stack, StackProps } from "aws-cdk-lib";
import { NodejsFunction } from "aws-cdk-lib/aws-lambda-nodejs";
import { Construct } from "constructs";
import { join } from "path";
import { Runtime } from "aws-cdk-lib/aws-lambda";
import { SSMParameterReader } from "./ssm-parameter-reader";
import { PolicyStatement } from "aws-cdk-lib/aws-iam";
import { LambdaInvoke } from "aws-cdk-lib/aws-stepfunctions-tasks";
import { DefinitionBody, StateMachine } from "aws-cdk-lib/aws-stepfunctions";
import { StringParameter } from "aws-cdk-lib/aws-ssm";


export interface MoveFilesStackProps extends StackProps {
    codePipelineName: string;
    prodRawS3DataSourceBucketName: string; // Name of the Production raw S3 bucket.
}

/**
 * ## MoveFilesStack Overview
 * 
 * ### Usage:
 * This stack orchestrates the file transfer process between QA and Production environments. 
 * Once the RAG evaluation is complete, this stack copies raw files from the QA S3 bucket to the Production S3 bucket.
 * 
 * ### Key Features:
 * - Lambda function: Copies raw files from the QA raw S3 bucket to the Production raw S3 bucket.
 * - Step Function State Machine: Automates the copying process.
 * - SSM Parameter Store Integration: Stores and retrieves bucket names and the ARN of the state machine.
 * - IAM Policies: Ensures the Lambda function has the required permissions to interact with S3.
 * 
 * 
 */

export class MoveFilesStack extends Stack {

    constructor(scope: Construct, id: string, props: MoveFilesStackProps) {
        super(scope, id, props);

        // Retrieve QA Bucket Name from SSM Parameter Store.
        const qaRawS3DataSourceBucketParameter = new SSMParameterReader(this, 'QARawS3DataSourceBucketParameter', {
            parameterName: `/${props.codePipelineName}/QA/raw-s3-data-source`,
            region: 'us-east-1', // SSM parameter region.
        });

        // Resolve QA and Production Bucket Names.
        const qaRawS3DataSourceBucketName = qaRawS3DataSourceBucketParameter.getParameterValue();
        const prodRawS3DataSourceBucketName = props.prodRawS3DataSourceBucketName;

        // Create Lambda Function for Copying Files from QA to Production.
        const copyfilesFromQAToProdLambda = new NodejsFunction(this, 'FileCopyLambda', {
            runtime: Runtime.NODEJS_18_X,
            entry: join(__dirname, '..', '..', 'src', 'services', 'copy-files.ts'),
            handler: 'handler',
            timeout: Duration.minutes(15),
            environment: {
                RAW_S3_QA: qaRawS3DataSourceBucketName, // QA raw bucket as environment variable.
                RAW_S3_PROD: prodRawS3DataSourceBucketName, // Production raw bucket as environment variable.
            },
        });

        // Define S3 Bucket ARNs.
        const qaRawS3DataSourceBucketArn = `arn:aws:s3:::${qaRawS3DataSourceBucketName}`;
        const prodRawS3DataSourceBucketArn = `arn:aws:s3:::${prodRawS3DataSourceBucketName}`;

        // Grant Lambda Function Permissions to Access QA and Production Buckets.
        copyfilesFromQAToProdLambda.addToRolePolicy(
            new PolicyStatement({
                actions: ['s3:ListBucket', 's3:GetObject', 's3:PutObject'], // Required S3 actions.
                resources: [
                    qaRawS3DataSourceBucketArn, `${qaRawS3DataSourceBucketArn}/*`,
                    prodRawS3DataSourceBucketArn, `${prodRawS3DataSourceBucketArn}/*`
                ],
            })
        );

        // Define a Step Function Task to Invoke the Copy Files Lambda.
        const copyFilesTask = new LambdaInvoke(this, 'CopyDataLambdaInvokeTask', {
            lambdaFunction: copyfilesFromQAToProdLambda,
            outputPath: '$.Payload', // Output Lambda response.
        });

        // Define the Step Function State Machine to Automate File Movement.
        const moveFilesStateMachineDefinition = copyFilesTask;

        const moveFilesStateMachine = new StateMachine(this, 'MoveFilesStateMachine', {
            definitionBody: DefinitionBody.fromChainable(moveFilesStateMachineDefinition),
            timeout: Duration.minutes(20), // State machine timeout.
        });

        // Store State Machine ARN in SSM Parameter Store for Future Reference.
        new StringParameter(this, 'MoveFilesStateMachineArnParameter', {
            parameterName: `/${props.codePipelineName}/Prod/move-files-state-machine-arn`,
            stringValue: moveFilesStateMachine.stateMachineArn,
        });

        // // Output State Machine ARN to CloudFormation for Debugging and Reference.
        // new CfnOutput(this, 'MoveFilesStateMachineArnOutput', {
        //     value: moveFilesStateMachine.stateMachineArn,
        //     description: 'ARN of the Move Files State Machine',
        // });
    }
}

