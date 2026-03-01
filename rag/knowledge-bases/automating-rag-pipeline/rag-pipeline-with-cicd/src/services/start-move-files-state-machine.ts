import { SSM, StepFunctions } from 'aws-sdk';
import { Handler } from 'aws-lambda';

const ssm = new SSM({ region: 'us-west-2' });
const stepfunctions = new StepFunctions({ region: 'us-west-2' });

export const handler: Handler = async (event) => {
    try {
        // Get the state machine ARN from SSM Parameter Store
        const param = await ssm.getParameter({
            Name: `/${process.env.PIPELINE_NAME}/Prod/move-files-state-machine-arn`,
        }).promise();

        const stateMachineArn = param.Parameter?.Value;

        if (!stateMachineArn) {
            throw new Error('State Machine ARN not found in SSM');
        }

        // Start the Step Function execution
        const result = await stepfunctions.startExecution({
            stateMachineArn,
            input: JSON.stringify(event),
        }).promise();

        console.log('Step Function Execution started:', result);

        return {
            statusCode: 200,
            body: 'Step Function execution started successfully',
        };
    } catch (error) {
        console.error('Error starting Step Function:', error);
        return {
            statusCode: 500,
            body: 'Failed to start Step Function',
        };
    }
};
