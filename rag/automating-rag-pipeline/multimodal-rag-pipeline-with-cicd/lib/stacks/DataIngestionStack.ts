
import { Construct } from 'constructs';
import { Duration, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import { BlockPublicAccess, Bucket, EventType, IBucket } from 'aws-cdk-lib/aws-s3';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { AttributeType, GlobalSecondaryIndexProps, GlobalSecondaryIndexPropsV2, TableV2 } from 'aws-cdk-lib/aws-dynamodb';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { join } from 'path';
import { LambdaDestination } from 'aws-cdk-lib/aws-s3-notifications';
import { Rule } from 'aws-cdk-lib/aws-events';
import { LambdaInvoke, SqsSendMessage } from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Queue } from 'aws-cdk-lib/aws-sqs';
import { Choice, Condition, DefinitionBody, Fail, JsonPath, Pass, Result, StateMachine, TaskInput, Wait, WaitTime } from 'aws-cdk-lib/aws-stepfunctions';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { SfnStateMachine } from 'aws-cdk-lib/aws-events-targets';
import { CfnSchedule } from "aws-cdk-lib/aws-scheduler";
import { PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { LogGroup, RetentionDays } from 'aws-cdk-lib/aws-logs';
import { LogLevel } from 'aws-cdk-lib/aws-stepfunctions';


export interface DataIngestionStackProps extends StackProps {
    stageName: string;
    codePipelineName: string;
    knowledgeBaseId: string;
    dataSourceId: string;
}

export class DataIngestionStack extends Stack {
    public readonly kbDataIngestionStateMachineArn: string;
    public readonly rawS3DataSourceBucketName: string;

    constructor(scope: Construct, id: string, props: DataIngestionStackProps) {
        super(scope, id, props);


        // ================================Create S3 Buckets================================
        // Create a s3 bucket that will be used as the organization's data source
        // const rawS3DataSource = new Bucket(this, 'RawDataSourceBucket', {
        //     bucketName: 'raw-data-source-bucket-' + process.env.CDK_DEFAULT_ACCOUNT + '-' + props?.stageName?.toLowerCase(),
        //     blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
        //     autoDeleteObjects: true,
        //     removalPolicy: RemovalPolicy.DESTROY,
        //     eventBridgeEnabled: true,
        // });

        const rawS3DataSource = this.createBucket('RawDataSourceBucket', 'raw-data-source-bucket', props.stageName);

        // Store the bucket name in SSM Parameter Store
        new StringParameter(this, 'rawS3DataSource', {
            parameterName: `/${props.codePipelineName}/${props.stageName}/raw-s3-data-source`,
            stringValue: rawS3DataSource.bucketName,
        });

        this.rawS3DataSourceBucketName = rawS3DataSource.bucketName;

        // Create a s3 bucket that will be used as the organization's processed data source (KB s3 source)
        // const processedS3DataSource = new Bucket(this, 'ProcessedDataSourceBucket', {
        //     bucketName: 'processed-data-source-bucket-' + process.env.CDK_DEFAULT_ACCOUNT + '-' + props?.stageName?.toLowerCase(),
        //     blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
        //     autoDeleteObjects: true,
        //     removalPolicy: RemovalPolicy.DESTROY,
        //     eventBridgeEnabled: true,
        // });

        const processedS3DataSource = this.createBucket('ProcessedDataSourceBucket', 'processed-data-source-bucket', props.stageName);

        // Store the bucket name in SSM Parameter Store
        new StringParameter(this, 'processedS3DataSource', {
            parameterName: `/${props.codePipelineName}/${props.stageName}/processed-s3-data-source`,
            stringValue: processedS3DataSource.bucketName,
        });


        // ================================Create DynamoDB Table================================

        // Create a DynamoDB table - a unfied table to track both raw and processed files metadata
        // Since there is a need to query the table based on the fileType and kbIngestionStatus to decide to start the KB ingestion process, 
        // a GSI is created on the fileType and kbIngestionStatus attributes; a query on GSI is faster than a scan on the entire table
        const fileMetadataTable = new TableV2(this, 'FileMetadataTable', {
            partitionKey: { name: 'fileId', type: AttributeType.STRING }, // Unique file identifier across raw/processed files
            sortKey: { name: 'fileType', type: AttributeType.STRING }, // Sort key to differentiate raw vs processed files
            removalPolicy: RemovalPolicy.DESTROY, // Change to RETAIN for production
            tableName: `file-metadata-for-${props.codePipelineName}-${props.stageName}`,
            globalSecondaryIndexes: [
                {
                    indexName: 'fileType-kbIngestionStatus-index',
                    partitionKey: { name: 'fileType', type: AttributeType.STRING },
                    sortKey: { name: 'kbIngestionStatus', type: AttributeType.STRING },
                    projectionType: 'ALL', // Include all attributes in the index
                } as GlobalSecondaryIndexPropsV2,
            ],
        });

        // Store the table name in SSM Parameter Store
        new StringParameter(this, 'FileMetadataTableNameParameter', {
            parameterName: `/${props.codePipelineName}/${props.stageName}/fileMetadataTableName`,
            stringValue: fileMetadataTable.tableName,
        });


        // Lambda function to mark the new files in the DynamoDB table
        // const metadataTrackingLambda = new NodejsFunction(this, 'MetadataTrackingLambda', {
        //     runtime: Runtime.NODEJS_18_X,
        //     entry: join(__dirname, '..', '..', 'src', 'services', 'metadata-tracking.ts'),
        //     handler: 'handler',
        //     environment: {
        //         FILE_METADATA_TABLE_NAME: fileMetadataTable.tableName,
        //     },
        // });

        const metadataTrackingLambda = this.createLambdaFunction('MetadataTrackingLambda', 'metadata-tracking.ts', 5, {
            FILE_METADATA_TABLE_NAME: fileMetadataTable.tableName,
        });

        // Grant permissions to the Lambda function for the unified metadata table and S3 buckets
        fileMetadataTable.grantReadWriteData(metadataTrackingLambda); // Allow Lambda to read/write to the table
        rawS3DataSource.grantRead(metadataTrackingLambda); // Read access for raw bucket
        processedS3DataSource.grantRead(metadataTrackingLambda); // Read access for processed bucket

        // Trigger the Lambda function on object creation and deletion in the raw bucket
        rawS3DataSource.addEventNotification(
            EventType.OBJECT_CREATED,
            new LambdaDestination(metadataTrackingLambda),
        );
        rawS3DataSource.addEventNotification(
            EventType.OBJECT_REMOVED,
            new LambdaDestination(metadataTrackingLambda),
        );

        // Trigger the Lambda function on object creation and deletion in the processed bucket
        processedS3DataSource.addEventNotification(
            EventType.OBJECT_CREATED,  //Use the s3:ObjectCreated:* event type to request notification regardless of the API that was used to create an object.
            new LambdaDestination(metadataTrackingLambda),
        );

        processedS3DataSource.addEventNotification(
            EventType.OBJECT_REMOVED,
            new LambdaDestination(metadataTrackingLambda),
        );


        // ===============================EventBridge Rule================================
        // Create an EventBridge rule to capture specific S3 events - Object Created and Object Deleted
        // The rule is configured to capture events from the specified bucket and send it to Step Functions as a target
        const s3EventRule = new Rule(this, 'S3EventRule', {
            eventPattern: {
                source: ['aws.s3'],
                detailType: ['Object Created', 'Object Deleted'],
                detail: {
                    bucket: {
                        name: [rawS3DataSource.bucketName],
                    }
                },
            },
        });


        // ===============================ETL Step Function Workflow================================

        // Create a Lambda function to process s3 events and extract the file name and event type
        const s3EventProcessor = new NodejsFunction(this, 'S3EventProcessorLambda', {
            runtime: Runtime.NODEJS_18_X,
            entry: (join(__dirname, '..', '..', 'src', 'services', 's3-event-processor.ts')),
            handler: 'handler',
        });

        // Step 1: Create a Step Functions task to invoke the Lambda function
        const lambdaInvokeTask = new LambdaInvoke(this, 'S3EventProcessorLambdaInvokeTask', {
            lambdaFunction: s3EventProcessor,
            outputPath: '$.Payload', // The outputPath property is set to $.Payload, which means that the output of the Lambda function will be extracted from the Payload field of the Lambda's response.
        });

        // Create SQS queue to send file upload events
        const fileUploadQueue = new Queue(this, 'FileUploadQueue', {
            queueName: 'file-upload-queue-org-data-source',
            visibilityTimeout: Duration.seconds(300),
        });

        // Create another SQS queue to send file deletion events
        const fileDeletionQueue = new Queue(this, 'FileDeletionQueue', {
            queueName: 'file-deletion-queue-org-data-source',
            visibilityTimeout: Duration.seconds(300),
        });

        // Step 3: Create a Step Functions task to add file upload message to the queue
        const addFileUploadMessageToQueueTask = new SqsSendMessage(this, 'AddFileUploadMessageToQueueTask', {
            queue: fileUploadQueue,
            messageBody: TaskInput.fromObject({
                fileName: JsonPath.stringAt('$.fileName'),
                eventType: JsonPath.stringAt('$.eventType'),
            }),
        });

        // Step 4: Create a Step Functions task to add file deletion message to the queue
        const addFileDeletionMessageToQueueTask = new SqsSendMessage(this, 'AddFileDeletionMessageToQueueTask', {
            queue: fileDeletionQueue,
            messageBody: TaskInput.fromObject({
                fileName: JsonPath.stringAt('$.fileName'),
                eventType: JsonPath.stringAt('$.eventType'),
            }),
        });

        // Create a Lambda function to process the added file by picking up the message from the FileUploadQueue
        const fileProcessor = new NodejsFunction(this, 'FileProcessorLambda', {
            runtime: Runtime.NODEJS_18_X,
            entry: (join(__dirname, '..', '..', 'src', 'services', 'file-upload-processor.ts')),
            handler: 'handler',
            environment: {
                RAW_S3: rawS3DataSource.bucketArn,
                PROCESSED_S3: processedS3DataSource.bucketArn
            },
        });

        // Add permissions to the Lambda function to access the S3 buckets
        rawS3DataSource.grantRead(fileProcessor);
        processedS3DataSource.grantWrite(fileProcessor);

        // Add the file upload SQS queue as an event source for the Lambda function
        fileProcessor.addEventSource(new SqsEventSource(fileUploadQueue, {
            batchSize: 1,
        }));

        // Also add the file deletion SQS queue as an event source for the Lambda function
        // This is to handle the case where the file is deleted from the raw S3 bucket, and we need to delete the corresponding file from the processed S3 bucket
        // Same Lambda function can be used to handle both file upload and file deletion events
        fileProcessor.addEventSource(new SqsEventSource(fileDeletionQueue, {
            batchSize: 1,
        }));


        // Step 5: Create a Step Functions task to invoke the Lambda function to process the added file by picking up the message from the FileUploadQueue
        const fileProcessorTask = new LambdaInvoke(this, 'FileProcessorLambdaInvokeTask', {
            lambdaFunction: fileProcessor,
            outputPath: '$.Payload',
        });

        // Step 2: Create a Choice state to determine the s3 event type based on the Lambda's response
        const choiceState = new Choice(this, 'S3EventType');

        // Define the states to transition to based on the eventType
        const objectCreatedState = new Pass(this, 'ObjectCreated'); // Placeholder for actual state
        const objectDeletedState = new Pass(this, 'ObjectDeleted'); // Placeholder for actual state
        const defaultState = new Fail(this, 'UnknownEventType', {
            error: 'UnknownEventType',
            cause: 'The event type is not recognized.',
        });

        // Add conditions to the Choice state
        choiceState
            // .when(Condition.stringEquals('$.lambdaResult.eventType', 'Object Created'), objectCreatedState)
            .when(Condition.stringEquals('$.eventType', 'Object Created'), objectCreatedState.next(addFileUploadMessageToQueueTask).next(fileProcessorTask))
            .when(Condition.stringEquals('$.eventType', 'Object Deleted'), objectDeletedState.next(addFileDeletionMessageToQueueTask).next(fileProcessorTask))
            .otherwise(defaultState);


        // Define the state machine
        const etlStateMachine = new StateMachine(this, 'ETLStateMachine', {
            definition: lambdaInvokeTask.next(choiceState),
            timeout: Duration.minutes(5),
        });

        // Add the state machine as a target to the EventBridge rule
        s3EventRule.addTarget(new SfnStateMachine(etlStateMachine));


        // ===============================Bedrock Knowledge Base Ingestion Workflow================================

        // =======================Step 1: Check for new files in the processed S3 bucket=======================
        // Create a Lambda function to check for new files in the processed S3 bucket.
        const checkForNewFileModificationsLambda = new NodejsFunction(this, 'CheckForNewFileModificationsLambda', {
            runtime: Runtime.NODEJS_18_X,
            entry: join(__dirname, '..', '..', 'src', 'services', 'check-for-new-files.ts'),
            handler: 'handler',
            environment: {
                FILE_METADATA_TABLE: fileMetadataTable.tableName,
            },
        });

        // Grant read permissions to the DynamoDB table for the CheckForNewFiles Lambda.
        fileMetadataTable.grantReadData(checkForNewFileModificationsLambda);

        // Create a Step Functions task to invoke the CheckForNewFiles Lambda.
        const checkForNewFileModificationsTask = new LambdaInvoke(this, 'checkForNewFileModificationsTask', {
            lambdaFunction: checkForNewFileModificationsLambda,
            outputPath: '$.Payload', // Extract Lambda response payload.
        });






        // =======================Step 2: Evaluate the result from CheckForNewFilesTask=======================
        // Define a Choice state to evaluate the result from CheckForNewFiles.
        const choiceStateTocheckForNewFileModifications = new Choice(this, 'CheckForNewFileModifications');

        // Define the condition when new files are available.
        // const newFilesAvailableCondition = Condition.booleanEquals('$.newFilesAvailable', true);
        const filesModifiedCondition = Condition.booleanEquals('$.fileModificationsExist', true);






        // =======================Step 3: Start the KB ingestion process if new files are available=======================

        // Create a Lambda function to start the KB ingestion process
        const startKBIngestionLambda = new NodejsFunction(this, 'StartKBIngestionLambda', {
            runtime: Runtime.NODEJS_18_X,
            entry: (join(__dirname, '..', '..', 'src', 'services', 'kb-data-ingestion.ts')),
            handler: 'handler',
            timeout: Duration.minutes(10),
            environment: {
                FILE_METADATA_TABLE: fileMetadataTable.tableArn,
                PROCESSED_S3: processedS3DataSource.bucketArn,
                KNOWLEDGE_BASE_ID: props.knowledgeBaseId,
                DATA_SOURCE_ID: props.dataSourceId,
            },
        });


        // Grant permissions to the Lambda function to access the DynamoDB table and start the KB ingestion
        fileMetadataTable.grantReadData(startKBIngestionLambda);
        // processedS3DataSource.grantRead(startKBIngestionLambda);

        // Allow the Lambda function to start the KB ingestion process
        const allowKnowledgeBaseDataIngestion = new PolicyStatement({
            actions: ['bedrock:StartIngestionJob'],
            resources: [`arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/${props.knowledgeBaseId}`],
            sid: 'AllowKnowledgeBaseDataIngestion',
        });
        startKBIngestionLambda.addToRolePolicy(allowKnowledgeBaseDataIngestion);

        // Create a Step Functions task to invoke the Lambda function to start the KB ingestion
        const startKBIngestionTask = new LambdaInvoke(this, 'StartKBIngestionLambdaInvokeTask', {
            lambdaFunction: startKBIngestionLambda,
            outputPath: '$.Payload',
        });


        // =======================Step 4: Get the KB ingestion job status=======================

        // Create a Lambda function to get the KB ingestion job status
        const getIngestionJobStatusLambda = new NodejsFunction(this, 'GetIngestionJobStatusLambda', {
            runtime: Runtime.NODEJS_18_X,
            entry: (join(__dirname, '..', '..', 'src', 'services', 'get-ingestion-job-status.ts')),
            handler: 'handler',
            timeout: Duration.minutes(5),
            environment: {
                FILE_METADATA_TABLE: fileMetadataTable.tableArn,
            },
        });

        // Allow the Lambda function to get the ingestion job status
        const allowGetIngestionJobStatus = new PolicyStatement({
            actions: ['bedrock:GetIngestionJob'],
            resources: [`arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/${props.knowledgeBaseId}`],
            sid: 'AllowGetIngestionJobStatus',
        });
        getIngestionJobStatusLambda.addToRolePolicy(allowGetIngestionJobStatus);

        // Create a Step Functions task to invoke the Lambda function to get the ingestion job status
        // The payload property is set to a JSON object that contains the KnowledgeBaseId, DataSourceId, and IngestionJobId
        // payload property specifies the input to the Lambda function
        // The resultPath property is set to $.GetIngestionJobResult, which means that the output of the Lambda function will be extracted from the GetIngestionJobResult field of the Lambda's response.
        // The result of the Lambda function will be stored in the $.GetIngestionJobResult field of the state's output
        const getIngestionJobStatusTask = new LambdaInvoke(this, 'GetIngestionJobStatusLambdaInvokeTask', {
            lambdaFunction: getIngestionJobStatusLambda,
            payload: TaskInput.fromObject({
                KnowledgeBaseId: JsonPath.stringAt("$.KnowledgeBaseId"),
                DataSourceId: JsonPath.stringAt("$.DataSourceId"),
                IngestionJobId: JsonPath.stringAt("$.JobId"),
            }),
            resultPath: "$.GetIngestionJobResult",
        });

        // =======================Step 4.1: Wait for the KB ingestion job to complete=======================
        // Wait state to pause before polling the job status again
        const waitState = new Wait(this, "Wait", {
            time: WaitTime.duration(Duration.seconds(10)), // Adjust the wait time as needed
        });


        // =======================Step 6: Update the file metadata table with the KB ingestion status=======================
        // Create a Lambda function to update the file metadata table with the KB ingestion status
        const updateFileMetadataLambda = new NodejsFunction(this, 'UpdateFileMetadataLambda', {
            runtime: Runtime.NODEJS_18_X,
            entry: (join(__dirname, '..', '..', 'src', 'services', 'update-file-metadata.ts')),
            handler: 'handler',
            environment: {
                FILE_METADATA_TABLE: fileMetadataTable.tableArn,
            },
        });

        // Grant the Lambda function permissions to read and write to the DynamoDB table
        fileMetadataTable.grantReadWriteData(updateFileMetadataLambda);


        // Create a Step Functions task to invoke the Lambda function to update the file metadata table with the KB ingestion status
        const updateFileMetadataTask = new LambdaInvoke(this, 'UpdateFileMetadataLambdaInvokeTask', {
            lambdaFunction: updateFileMetadataLambda,
            outputPath: '$.Payload',
            // outputPath: '$.Payload',  // The outputPath property is set to $.Payload, which means that the output of the Lambda function will be extracted from the Payload field of the Lambda's response.
        });





        // =======================Step 5: Check the status of the ingestion job=======================
        // Create a choice state to check the status of the ingestion job
        const choiceStateForJobStatus = new Choice(this, 'CheckIngestionJobStatus');


        // Define the states to transition to based on the job status
        const jobInProgressState = Condition.or(
            Condition.stringEquals('$.GetIngestionJobResult.Payload.status', 'IN_PROGRESS'),
            Condition.stringEquals('$.GetIngestionJobResult.Payload.status', 'STARTING')
        );
        const jobCompletedState = Condition.stringEquals('$.GetIngestionJobResult.Payload.status', 'COMPLETE');

        const jobFailedState = Condition.stringEquals('$.GetIngestionJobResult.Payload.status', 'FAILED');

        const jobCompletedPassState = new Pass(this, `IngestionJobCompleted-${props.stageName}`, {
            result: Result.fromObject({
                message: `The ingestion job completed successfully in -${props.stageName} stage.`,
            }),
        });



        // Pass states to indicate that the ingestion job failed
        const jobFailedPassState = new Pass(this, 'IngestionJobFailed', {
            result: Result.fromObject({
                message: 'The ingestion job failed.',
            }),
        });

        // Fail state to indicate that the job status is not recognized
        const unknownJobStatus = new Fail(this, 'UnknownJobStatus', {
            error: 'UnknownJobStatus',
            cause: 'The job status is not recognized.',
        });





        if (props.stageName === 'QA') {
            // Lambda function to trigger the ragEvaluationStateMachine using the AWS SDK's StartExecution API,
            const triggerRAGEvalLambda = new NodejsFunction(this, 'TriggerRAGEvaluationLambda', {
                runtime: Runtime.NODEJS_18_X,
                entry: join(__dirname, '..', '..', 'src', 'services', 'trigger-rag-evaluation.ts'),
                handler: 'handler',
                timeout: Duration.minutes(5),
                environment: {
                    CODE_PIPELINE_NAME: props.codePipelineName,
                },
                // environment: {
                //     RAG_EVALUATION_STATE_MACHINE_ARN: ragEvaluationStateMachineArn.getParameterValue(),
                // },
            });


            // Add permissions for the Lambda to start executions on Step Functions
            triggerRAGEvalLambda.addToRolePolicy(new PolicyStatement({
                actions: ['states:StartExecution', 'ssm:GetParameter'],
                resources: [`arn:aws:states:${this.region}:${this.account}:stateMachine:*`, // Allow starting execution of any state machine in this account
                `arn:aws:ssm:${this.region}:${this.account}:parameter/${props.codePipelineName}/PostQAApproval/rag-evaluation-state-machine-arn`] // Allow fetching parameters for RAG evaluation
            }));


            // Create the Lambda invoke task to trigger the RAG evaluation state machine
            const invokeTriggerRAGLambdaTask = new LambdaInvoke(this, 'InvokeTriggerRAGLambda', {
                lambdaFunction: triggerRAGEvalLambda,
                outputPath: '$.Payload',
            });


            choiceStateForJobStatus
                .when(jobInProgressState, waitState.next(getIngestionJobStatusTask))
                .when(jobCompletedState, jobCompletedPassState.next(updateFileMetadataTask.next(invokeTriggerRAGLambdaTask)))
                .when(jobFailedState, jobFailedPassState)
                .otherwise(unknownJobStatus);

        } else {
            choiceStateForJobStatus
                .when(jobInProgressState, waitState.next(getIngestionJobStatusTask))
                .when(jobCompletedState, jobCompletedPassState.next(updateFileMetadataTask))
                .when(jobFailedState, jobFailedPassState)
                .otherwise(unknownJobStatus);
        }



        // Configure the Choice state to transition to the appropriate state based on the new files availability
        choiceStateTocheckForNewFileModifications
            .when(filesModifiedCondition, startKBIngestionTask.next(getIngestionJobStatusTask).next(choiceStateForJobStatus))
            .otherwise(new Pass(this, 'No new file modifications to sync'));



        // Define the state machine for the KB data ingestion process
        const stateMachineDefinition = checkForNewFileModificationsTask.next(choiceStateTocheckForNewFileModifications);

        const logGroup = new LogGroup(this, 'KBDataIngestionLogGroup', {
            retention: RetentionDays.ONE_WEEK,
            removalPolicy: RemovalPolicy.DESTROY,
        });

        // Create a Step Functions state machine to orchestrate the KB data ingestion process
        const kbDataIngestionStateMachine = new StateMachine(this, 'KBDataIngestionStateMachine', {
            definitionBody: DefinitionBody.fromChainable(stateMachineDefinition),
            timeout: Duration.minutes(300),
            logs: {
                destination: logGroup,
                includeExecutionData: true,
                level: LogLevel.ALL,
            },
        });

        this.kbDataIngestionStateMachineArn = kbDataIngestionStateMachine.stateMachineArn;



        const kbIngestionSchedulerRole = new Role(this, 'KBIngestionSchedulerRole', {
            assumedBy: new ServicePrincipal('scheduler.amazonaws.com'),
        });

        // Allow the scheduler to invoke the Step Functions state machine
        kbDataIngestionStateMachine.grantStartExecution(kbIngestionSchedulerRole);



        //Create an EventBridge scheduler to invoke the Step Functions state machine every 2 minutes
        new CfnSchedule(this, "KBDataIngestionSchedule", {
            flexibleTimeWindow: {
                mode: "OFF",
            },
            scheduleExpression: "cron(*/2 * * * ? *)",
            target: {
                arn: kbDataIngestionStateMachine.stateMachineArn,
                roleArn: kbIngestionSchedulerRole.roleArn,
                input: JSON.stringify({
                    scheduleTime: "<aws.scheduler.scheduled-time>",
                }),
            },
            description:
                "Schedule to start the Knowledge Bases data ingestion process",
            name: "KnowledgeBasesDataIngestionSchedule",
            state: "ENABLED",
        });




    }

    private createBucket(id: string, namePrefix: string, stageName: string): Bucket {
        return new Bucket(this, id, {
            bucketName: `${namePrefix}-${process.env.CDK_DEFAULT_ACCOUNT}-${stageName.toLowerCase()}`,
            blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
            autoDeleteObjects: true,
            removalPolicy: RemovalPolicy.DESTROY,
            eventBridgeEnabled: true,
        });
    }

    private createLambdaFunction(id: string, entryPath: string, timeoutMinutes: number, environment: Record<string, string> = {}): NodejsFunction {
        return new NodejsFunction(this, id, {
            runtime: Runtime.NODEJS_18_X,
            entry: join(__dirname, '..', '..', 'src', 'services', entryPath),
            handler: 'handler',
            environment,
            timeout: Duration.minutes(timeoutMinutes),
        });

    }

}

