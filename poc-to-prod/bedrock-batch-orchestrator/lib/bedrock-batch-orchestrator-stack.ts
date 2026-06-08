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
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';


export interface BedrockBatchOrchestratorStackProps extends cdk.StackProps {
  maxSubmittedAndInProgressJobs: number;
  bedrockBatchInferenceTimeoutHours?: number;
  notificationEmails?: string[];
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
    // add permissions for additional models as needed
    bedrockServiceRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock:InvokeModel'],
      resources: [
        'arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0',
        'arn:aws:bedrock:*::inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0',
        'arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0',
        // Amazon Nova models
        'arn:aws:bedrock:*::foundation-model/amazon.nova-lite-v1:0',
        'arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0',
        'arn:aws:bedrock:*::foundation-model/amazon.nova-micro-v1:0',
      ],
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

    // SNS Topic for pipeline notifications
    const notificationTopic = new sns.Topic(this, 'pipelineNotificationTopic', {
      displayName: 'Bedrock Batch Pipeline Notifications',
      topicName: `bedrock-batch-pipeline-notifications-${this.account}`,
    });

    // Add email subscriptions if provided
    const notificationEmails = props.notificationEmails || [];
    notificationEmails.forEach((email, index) => {
      notificationTopic.addSubscription(
        new subscriptions.EmailSubscription(email)
      );
    });

    // Validation Lambda for pipeline configuration
    const validationFunction = new lambda.DockerImageFunction(this, 'validationFunction', {
      description: 'Validate pipeline configuration before execution',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../lambda'), {
        platform: assets.Platform.LINUX_AMD64,
        cmd: ['validate_pipeline_config.lambda_handler']
      }),
      timeout: cdk.Duration.seconds(30),
    });
    bucket.grantRead(validationFunction);

    // Transform Stage Lambda for column mappings
    const transformStageFunction = new lambda.DockerImageFunction(this, 'transformStageFunction', {
      description: 'Transform previous stage output for next stage input',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../lambda'), {
        platform: assets.Platform.LINUX_AMD64,
        cmd: ['transform_stage.lambda_handler']
      }),
      environment: {
        BUCKET_NAME: bucket.bucketName,
      },
      memorySize: 3008,
      timeout: cdk.Duration.minutes(5),
    });
    bucket.grantReadWrite(transformStageFunction);

    // Notification Lambda for pipeline completion
    const notificationFunction = new lambda.DockerImageFunction(this, 'notificationFunction', {
      description: 'Send pipeline completion notifications',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../lambda'), {
        platform: assets.Platform.LINUX_AMD64,
        cmd: ['send_notification.lambda_handler']
      }),
      environment: {
        SNS_TOPIC_ARN: notificationTopic.topicArn,
      },
      timeout: cdk.Duration.seconds(30),
    });
    bucket.grantRead(notificationFunction);
    notificationTopic.grantPublish(notificationFunction);

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
      maxConcurrency: props.maxSubmittedAndInProgressJobs,
      itemsPath: sfn.JsonPath.stringAt('$.completed_jobs'),
      resultPath: '$.output_paths',
    });

    const postprocessTask = new tasks.LambdaInvoke(this, 'postprocessTask', {
      lambdaFunction: postprocessFunction,
      outputPath: '$.Payload',
    });

    // step function
    const batchProcessingMap = new sfn.Map(this, 'batchProcessingMap', {
      maxConcurrency: props.maxSubmittedAndInProgressJobs,
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

    // Pipeline Orchestrator Step Function
    // This orchestrates multi-stage pipelines by chaining batch orchestrator executions

    // Validation task
    const validateConfigTask = new tasks.LambdaInvoke(this, 'validateConfigTask', {
      lambdaFunction: validationFunction,
      resultPath: '$.validation',
    });

    // Check validation result
    const checkValidation = new sfn.Choice(this, 'checkValidation')
      .when(
        sfn.Condition.booleanEquals('$.validation.Payload.valid', false),
        new sfn.Fail(this, 'validationFailed', {
          error: 'ValidationError',
          cause: 'Pipeline configuration validation failed',
        })
      );

    // Map iterator receives the stage directly - no need to wrap it
    // Just pass it through to maintain consistency with downstream references

    // Transform input task - pass all context so Lambda can determine previous stage output
    const transformInputTask = new tasks.LambdaInvoke(this, 'transformInputTask', {
      lambdaFunction: transformStageFunction,
      outputPath: '$.Payload',
    });

    // Add error handling for transform failures
    transformInputTask.addCatch(
      new sfn.Fail(this, 'transformFailed', {
        error: 'TransformError',
        cause: 'Failed to transform previous stage output for next stage',
      }),
      {
        resultPath: '$.error',
      }
    );

    // Prepare batch input for stages that used transform (use_previous_output: true)
    const prepareBatchInputFromTransform = new sfn.Pass(this, 'prepareBatchInputFromTransform', {
      parameters: {
        // Transform Lambda flattens the structure, so all fields are at root level
        'stage_name.$': '$.stage_name',
        's3_uri.$': '$.input_s3_uri',
        'job_name_prefix.$': '$.job_name_prefix',
        'model_id.$': '$.model_id',
        'prompt_config.$': '$.prompt_config',
        'input_type.$': '$.input_type',
        'max_num_jobs.$': '$.max_num_jobs',
        'max_records_per_job.$': '$.max_records_per_job',
      },
    });

    // Prepare batch input for stages with direct input_s3_uri
    const prepareBatchInput = new sfn.Pass(this, 'prepareBatchInput', {
      parameters: {
        'stage_name.$': '$.$.stage_name',
        's3_uri.$': '$.$.input_s3_uri',
        'job_name_prefix.$': '$.$.job_name_prefix',
        'model_id.$': '$.$.model_id',
        'prompt_config.$': '$.$.prompt_config',
        'input_type.$': '$.$.input_type',
        'max_num_jobs.$': '$.$.max_num_jobs',
        'max_records_per_job.$': '$.$.max_records_per_job',
      },
    });

    const executeBatchJob = new tasks.StepFunctionsStartExecution(this, 'executeBatchJob', {
      stateMachine: stepFunction,
      integrationPattern: sfn.IntegrationPattern.RUN_JOB,
      input: sfn.TaskInput.fromJsonPathAt('$'),
      resultPath: '$.batch_result',
    });

    // Add retry policy for transient errors
    executeBatchJob.addRetry({
      errors: ['States.TaskFailed'],
      interval: cdk.Duration.seconds(30),
      maxAttempts: 2,
      backoffRate: 2.0,
    });

    // Add catch for stage failures
    executeBatchJob.addCatch(
      new sfn.Fail(this, 'stageExecutionFailed', {
        error: 'StageExecutionError',
        cause: 'Batch job execution failed for stage',
      }),
      {
        resultPath: '$.error',
      }
    );

    // Extract output path from batch result
    const extractOutputPath = new sfn.Pass(this, 'extractOutputPath', {
      parameters: {
        'stage_name.$': '$.stage_name',
        'output_paths.$': '$.batch_result.Output.output_paths',
      },
    });

    // Check if we should use previous output
    const checkUsePreviousOutput = new sfn.Choice(this, 'checkUsePreviousOutput')
      .when(
        sfn.Condition.and(
          sfn.Condition.isPresent('$.$.use_previous_output'),
          sfn.Condition.booleanEquals('$.$.use_previous_output', true)
        ),
        transformInputTask.next(prepareBatchInputFromTransform)
      )
      .otherwise(prepareBatchInput);

    // Build stage iterator - stage object is passed directly as input
    const stageIterator = checkUsePreviousOutput;

    prepareBatchInput.next(executeBatchJob);
    prepareBatchInputFromTransform.next(executeBatchJob);
    executeBatchJob.next(extractOutputPath);

    // Map over stages
    const executeStages = new sfn.Map(this, 'executeStages', {
      maxConcurrency: 1,
      itemsPath: '$.stages',
      resultPath: '$.stage_results',
      parameters: {
        // Spread all stage fields (only includes fields that exist)
        '$.$': '$$.Map.Item.Value',
        // Add context fields
        'pipeline_name.$': '$$.Execution.Input.pipeline_name',
        'all_stages.$': '$$.Execution.Input.stages',
        'stage_index.$': '$$.Map.Item.Index',
      },
    });
    executeStages.itemProcessor(stageIterator);

    // Send notification
    const sendNotificationTask = new tasks.LambdaInvoke(this, 'sendNotificationTask', {
      lambdaFunction: notificationFunction,
      payload: sfn.TaskInput.fromObject({
        'pipeline_name.$': '$.pipeline_name',
        'stage_results.$': '$.stage_results',
        'validation.$': '$.validation',
        'presigned_url_expiry_days.$': '$.presigned_url_expiry_days',
        'status': 'SUCCESS',
      }),
      outputPath: '$.Payload',
    });

    // Build pipeline orchestrator chain
    checkValidation.otherwise(executeStages.next(sendNotificationTask));

    const pipelineChain = validateConfigTask.next(checkValidation);

    // Create Pipeline Orchestrator State Machine
    const pipelineOrchestrator = new sfn.StateMachine(this, 'pipelineOrchestratorSfn', {
      definitionBody: sfn.DefinitionBody.fromChainable(pipelineChain),
      stateMachineName: `bedrock-pipeline-orchestrator-${this.account}`,
    });

    // Grant permissions
    stepFunction.grantStartExecution(pipelineOrchestrator);
    stepFunction.grantRead(pipelineOrchestrator);

    // output the state machine names & bucket name
    new cdk.CfnOutput(this, 'stepFunctionName', {
      value: stepFunction.stateMachineName,
    });
    new cdk.CfnOutput(this, 'pipelineOrchestratorName', {
      value: pipelineOrchestrator.stateMachineName,
    });
    new cdk.CfnOutput(this, 'bucketName', {
      value: bucket.bucketName,
    });
    new cdk.CfnOutput(this, 'notificationTopicArn', {
      value: notificationTopic.topicArn,
    });
    new cdk.CfnOutput(this, 'validationFunctionName', {
      value: validationFunction.functionName,
    });
  }
}
