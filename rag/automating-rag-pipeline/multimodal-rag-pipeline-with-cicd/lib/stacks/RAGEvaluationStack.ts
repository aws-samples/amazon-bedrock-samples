import { Duration, Stack, StackProps } from 'aws-cdk-lib';
import { StringParameter } from 'aws-cdk-lib/aws-ssm';
import { LambdaInvoke } from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Choice, Condition, DefinitionBody, JsonPath, Pass, StateMachine, TaskInput } from 'aws-cdk-lib/aws-stepfunctions';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { join } from 'path';
import { Runtime } from 'aws-cdk-lib/aws-lambda';

export interface RAGEvaluationStackProps extends StackProps {
    stageName: string;
    codePipelineName: string;
}

export class RAGEvaluationStack extends Stack {
    constructor(scope: Construct, id: string, props: RAGEvaluationStackProps) {
        super(scope, id, props);

        // Read the DynamoDB table name from SSM Parameter Store
        const fileMetadataTableNameParam = StringParameter.fromStringParameterName(this,
            'FileMetadataTableName', `/${props.codePipelineName}/QA/fileMetadataTableName`
        );

        // Lambda to evaluate new data ingestion
        const ingestionEvaluationLambda = this.createLambdaFunction('RAGEvaluationLambda', 'evaluate-new-data-ingestion.ts', 5, {
            STAGE_NAME: props.stageName,
            FILE_METADATA_TABLE_NAME: fileMetadataTableNameParam.stringValue,
        });

        // Construct the ARN for the DynamoDB table
        const fileMetadataTableArn = `arn:aws:dynamodb:${Stack.of(this).region}:${Stack.of(this).account}:table/${fileMetadataTableNameParam.stringValue}`;

        // Add necessary permissions for ingestionEvaluationLambda
        const allowDynamoDBAccess = new PolicyStatement({
            actions: ['dynamodb:Scan', 'dynamodb:UpdateItem'],
            resources: [fileMetadataTableArn],
        });
        ingestionEvaluationLambda.addToRolePolicy(allowDynamoDBAccess);


        const triggerApprovalLambda = this.createLambdaFunction('TriggerApprovalLambda', 'trigger-approval.ts', 5, {
            STAGE_NAME: props.stageName,
            PIPELINE_NAME: props.codePipelineName,
        });

        // Add necessary permissions for triggerApprovalLambda
        triggerApprovalLambda.addToRolePolicy(new PolicyStatement({
            actions: ['codepipeline:GetPipelineState', 'codepipeline:PutApprovalResult', 'ssm:GetParameter'],
            resources: [
                `arn:aws:codepipeline:${this.region}:${this.account}:${props.codePipelineName}`,
                `arn:aws:ssm:us-west-2:${this.account}:parameter/${props.codePipelineName}/Prod/move-files-state-machine-arn`,
                `arn:aws:codepipeline:${this.region}:${this.account}:${props.codePipelineName}/${props.stageName}/ManualApprovalForProduction`,  // The manual approval action resource
            ],
        }));


        // Step 1: Invoke RAG evaluation lambda
        const evaluationLambdaInvokeTask = new LambdaInvoke(this, 'EvaluationLambdaInvokeTask', {
            lambdaFunction: ingestionEvaluationLambda,
            outputPath: '$.Payload',
        });

        // Step 2: Invoke QA to Prod Approval Lambda
        const invokeQAToProdPipelineApprovalLambdaTask = new LambdaInvoke(this, 'InvokeQAToProdPipelineApprovalLambda', {
            lambdaFunction: triggerApprovalLambda,
            payload: TaskInput.fromObject({
                success: JsonPath.stringAt('$.success'),
                message: JsonPath.stringAt('$.message'),
            }),
            outputPath: '$.Payload',
        });

        // StepFunctionsStartExecution construct in AWS CDK does not have a region property as part of its API. Instead, you need to manage cross-region invocations using AWS SDK calls within a Lambda function that runs in the region where the Step Function is located.
        // Create a new Lambda to start the Step Function in us-west-2
        const startMoveFilesLambda = this.createLambdaFunction('StartMoveFilesLambda', 'start-move-files-state-machine.ts', 5, {
            PIPELINE_NAME: props.codePipelineName,
        });

        // Add necessary permissions to start Step Function in us-west-2
        startMoveFilesLambda.addToRolePolicy(new PolicyStatement({
            actions: ['states:StartExecution', 'ssm:GetParameter'],
            resources: [
                `arn:aws:states:us-west-2:${this.account}:stateMachine:*`,
                `arn:aws:ssm:us-west-2:${this.account}:parameter/${props.codePipelineName}/Prod/move-files-state-machine-arn`,
            ],
        }));

        // Create the Lambda task to invoke the Step Function in us-west-2
        const invokeMoveFilesLambdaTask = new LambdaInvoke(this, 'InvokeMoveFilesLambdaTask', {
            lambdaFunction: startMoveFilesLambda,
            outputPath: '$.Payload',
        });

        // Step 4: Choice state to handle different outcomes from the approval lambda
        const checkApprovalStatus = new Choice(this, 'CheckApprovalStatus')
            .when(Condition.numberEquals('$.statusCode', 500), invokeMoveFilesLambdaTask)
            .otherwise(new Pass(this, 'GoAheadAndEndTheStateMachine'));  // Default success path

        // Define the state machine
        const ragEvaluationStateMachineDefinition = evaluationLambdaInvokeTask
            .next(invokeQAToProdPipelineApprovalLambdaTask)
            .next(checkApprovalStatus);

        const ragEvaluationStateMachine = new StateMachine(this, 'RAGEvaluationStateMachine', {
            definitionBody: DefinitionBody.fromChainable(ragEvaluationStateMachineDefinition),
            timeout: Duration.minutes(20),
        });

        // Store the ARN in SSM
        new StringParameter(this, 'RAGEvaluationStateMachineArnParameter', {
            parameterName: `/${props.codePipelineName}/PostQAApproval/rag-evaluation-state-machine-arn`,
            stringValue: ragEvaluationStateMachine.stateMachineArn,
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
