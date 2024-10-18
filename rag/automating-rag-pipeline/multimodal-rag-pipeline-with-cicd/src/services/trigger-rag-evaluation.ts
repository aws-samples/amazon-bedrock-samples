
import { StepFunctions, SSM } from 'aws-sdk';
import { APIGatewayProxyHandler } from 'aws-lambda';

const stepfunctions = new StepFunctions();
const ssm = new SSM();

export const handler: APIGatewayProxyHandler = async (event: any): Promise<any> => {
    // Define the parameter name that stores the RAG Evaluation State Machine ARN
    const ragEvaluationSsmParameter = `/${process.env.CODE_PIPELINE_NAME}/PostQAApproval/rag-evaluation-state-machine-arn`;

    try {
        // Fetch the RAG evaluation state machine ARN from SSM
        const ssmResponse = await ssm.getParameter({
            Name: ragEvaluationSsmParameter,
            // WithDecryption: true // If the parameter is encrypted
        }).promise();

        const ragEvaluationStateMachineArn = ssmResponse.Parameter?.Value;

        if (!ragEvaluationStateMachineArn) {
            throw new Error('RAG Evaluation State Machine ARN not found in SSM');
        }

        // Prepare Step Functions parameters
        const params = {
            stateMachineArn: ragEvaluationStateMachineArn,  // Use the fetched ARN from SSM
            input: JSON.stringify(event),  // Pass the input from the kbDataIngestionStateMachine
        };

        // Start the execution of the RAG evaluation state machine
        const data = await stepfunctions.startExecution(params).promise();
        console.log('Successfully started RAG Evaluation State Machine:', data);

        return {
            statusCode: 200,
            body: JSON.stringify('RAG Evaluation triggered successfully'),
        };
    } catch (error) {
        console.error('Error triggering RAG Evaluation State Machine:', error);
        return {
            statusCode: 500,
            body: JSON.stringify('Failed to start RAG Evaluation')
        };
    }
};
