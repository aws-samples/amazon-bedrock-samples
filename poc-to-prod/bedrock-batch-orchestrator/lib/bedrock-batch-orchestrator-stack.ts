import * as path from 'path';

import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as assets from "aws-cdk-lib/aws-ecr-assets";
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';


export interface BedrockBatchOrchestratorStackProps extends cdk.StackProps {
  bedrockBatchInferenceMaxConcurrency: number;
  bedrockBatchInferenceTimeoutHours?: number;
}


export class BedrockBatchOrchestratorStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BedrockBatchOrchestratorStackProps) {
    super(scope, id, props);

    // bucket
    const bucket = new s3.Bucket(this, 'bucket', {
      bucketName: `batch-inference-bucket-${this.account}`,
    });

    // dynamo table for job arn -> task tokens
    const taskTable = new dynamodb.TableV2(this, 'taskTable', {
      partitionKey: { name: 'job_arn', type: dynamodb.AttributeType.STRING },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // service role for bedrock batch inference
    const bedrockServiceRole = new iam.Role(this, 'bedrockServiceRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
    });
    bucket.grantReadWrite(bedrockServiceRole);

    // allow cross-region inference: https://docs.aws.amazon.com/bedrock/latest/userguide/batch-iam-sr.html#batch-iam-sr-identity
    bedrockServiceRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));

    // lambda functions
    const preprocessFunction = new lambda.DockerImageFunction(this, 'preprocessFunction', {
      description: 'Prepare the bedrock batch input files',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../lambda'), {
        platform: assets.Platform.LINUX_AMD64,
        cmd: ['preprocess.lambda_handler']
      }),
      environment: {
        BUCKET_NAME: bucket.bucketName,
        HF_HOME: '/tmp/huggingface'
      },
      timeout: cdk.Duration.minutes(15),
      memorySize: 10240,  // recommend a large amount of memory if using max. batch sizes (50k records)
      ephemeralStorageSize: cdk.Size.mebibytes(512),
    });
    bucket.grantReadWrite(preprocessFunction);

    const startBatchInferenceFunction = new lambda.DockerImageFunction(this, 'startBatchInferenceFunction', {
      description: 'Starts the bedrock batch inference jobs',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../lambda'), {
        platform: assets.Platform.LINUX_AMD64,
        cmd: ['start_batch_inference_job.lambda_handler']
      }),
      environment: {
        BEDROCK_ROLE_ARN: bedrockServiceRole.roleArn,
        TASK_TABLE: taskTable.tableName,
        JOB_TIMEOUT_HOURS: (props.bedrockBatchInferenceTimeoutHours ?? -1).toString(),
      },
      timeout: cdk.Duration.minutes(5),
    });
    taskTable.grantReadWriteData(startBatchInferenceFunction);
    startBatchInferenceFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:CreateModelInvocationJob', 'bedrock:GetModelInvocationJob'],
      effect: iam.Effect.ALLOW,
      resources: ['*'],
    }));
    startBatchInferenceFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['iam:PassRole'],
      resources: [bedrockServiceRole.roleArn], // Reference to your service role
      effect: iam.Effect.ALLOW,
    }));

    // event source for completed jobs
    const batchJobCompleteRule = new events.Rule(this, 'batchJobCompleteRule', {
      eventPattern: {
        source: ['aws.bedrock'],
        detailType: ['Batch Inference Job State Change'],
      },
    });

    const getBatchInferenceFunction = new lambda.DockerImageFunction(this, 'getBatchInferenceFunction', {
      description: 'Monitors the progress of bedrock batch inference jobs',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../lambda'), {
        platform: assets.Platform.LINUX_AMD64,
        cmd: ['get_batch_inference_job.lambda_handler']
      }),
      timeout: cdk.Duration.seconds(15),
      environment: {
        TASK_TABLE: taskTable.tableName,
      }
    });
    batchJobCompleteRule.addTarget(new targets.LambdaFunction(getBatchInferenceFunction));
    taskTable.grantReadWriteData(getBatchInferenceFunction);
    getBatchInferenceFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:GetModelInvocationJob'],
      effect: iam.Effect.ALLOW,
      resources: ['*'],
    }));

    const postprocessFunction = new lambda.DockerImageFunction(this, 'postprocessFunction', {
      description: 'Process the bedrock batch output files',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../lambda'), {
        platform: assets.Platform.LINUX_AMD64,
        cmd: ['postprocess.lambda_handler']
      }),
      memorySize: 10240,
      environment: {
        BUCKET_NAME: bucket.bucketName,
      },
      timeout: cdk.Duration.minutes(5),
    });
    bucket.grantReadWrite(postprocessFunction);

    // step function tasks
    const preprocessTask = new tasks.LambdaInvoke(this, 'preprocessTask', {
      lambdaFunction: preprocessFunction,
      outputPath: '$.Payload',
    });

    const startBatchInferenceTask = new tasks.LambdaInvoke(this, 'startBatchInferenceTask', {
      lambdaFunction: startBatchInferenceFunction,
      integrationPattern: sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      payload: sfn.TaskInput.fromObject({
        taskToken: sfn.JsonPath.taskToken,
        taskInput: sfn.JsonPath.stringAt('$'),
      }),
    });

    // explicit retries to handle throttling errors in particular
    startBatchInferenceTask.addRetry({
      maxAttempts: 3,
    });

    const postprocessMap = new sfn.Map(this, 'postprocessMap', {
      maxConcurrency: props.bedrockBatchInferenceMaxConcurrency,
      itemsPath: sfn.JsonPath.stringAt('$.completed_jobs'),
      resultPath: '$.output_paths',
    });

    const postprocessTask = new tasks.LambdaInvoke(this, 'postprocessTask', {
      lambdaFunction: postprocessFunction,
      outputPath: '$.Payload',
    });

    // step function
    const batchProcessingMap = new sfn.Map(this, 'batchProcessingMap', {
      maxConcurrency: props.bedrockBatchInferenceMaxConcurrency,
      itemsPath: sfn.JsonPath.stringAt('$.jobs'),
      resultPath: '$.completed_jobs',
    });

    const chain = preprocessTask
        .next(batchProcessingMap.itemProcessor(startBatchInferenceTask))
        .next(postprocessMap.itemProcessor(postprocessTask));

    // state machine
    const stepFunction = new sfn.StateMachine(this, 'bedrockBatchOrchestratorSfn', {
      definitionBody: sfn.DefinitionBody.fromChainable(chain),
    });

    stepFunction.grantTaskResponse(getBatchInferenceFunction);

    // output the state machine name & bucket name
    new cdk.CfnOutput(this, 'stepFunctionName', {
      value: stepFunction.stateMachineName,
    });
    new cdk.CfnOutput(this, 'bucketName', {
      value: bucket.bucketName,
    });
  }
}
