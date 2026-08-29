import { DynamoDB } from 'aws-sdk';
const dynamodbClient = new DynamoDB.DocumentClient();
const tableName = process.env.FILE_METADATA_TABLE_NAME!;

export const handler = async (): Promise<any> => {
    console.log('Evaluate Batch RAG Ingestion Lambda!');

    // Placeholder for ingestion result (simulating a success rate of 85%)
    const ingestionResult = { successRate: 85 };
    console.log('Ingestion Result:', JSON.stringify(ingestionResult, null, 2));

    const threshold = 80; // Threshold for passing evaluation

    // Determine the RAG evaluation status
    const ragStatus = ingestionResult.successRate >= threshold ? 'PASSED' : 'FAILED';
    const evaluationTimestamp = new Date().toISOString();

    try {
        // Step 1: Fetch all files with 'pending' RAG evaluation status
        const pendingFiles = await getPendingRAGEvaluations();
        console.log(`Found ${pendingFiles.length} files with pending RAG evaluation.`);

        // Step 2: Update all pending files with the batch evaluation result
        const updatePromises = pendingFiles.map((file) => {
            const { fileId, fileType } = file;
            console.log(`Updating ${fileId} with RAG status: ${ragStatus}`);
            return updateRAGEvaluation(fileId, fileType, ragStatus, evaluationTimestamp);
        });

        // Step 3: Wait for all updates to complete
        await Promise.all(updatePromises);
        console.log('All pending evaluations processed successfully.');

        return {
            success: true,
            message: `Batch RAG evaluation completed with status: ${ragStatus}.`,
        };
    } catch (error) {
        console.error('Error processing batch RAG evaluation:', error);
        return {
            success: false,
            message: 'Failed to process batch RAG evaluation.',
        };
    }
};

// Function to fetch all files with 'pending' RAG evaluation status
async function getPendingRAGEvaluations(): Promise<any[]> {
    const params = {
        TableName: tableName,
        FilterExpression: 'ragEvaluationStatus = :pending',
        ExpressionAttributeValues: { ':pending': 'pending' },
    };

    const result = await dynamodbClient.scan(params).promise();
    return result.Items || [];
}

// Function to update RAG evaluation status and timestamp in DynamoDB
async function updateRAGEvaluation(
    fileId: string,
    fileType: string,
    ragStatus: string,
    evaluationTimestamp: string
): Promise<void> {
    try {
        await dynamodbClient.update({
            TableName: tableName,
            Key: {
                fileId: fileId,  // Partition key
                fileType: fileType, // Sort key
            },
            UpdateExpression: 'set ragEvaluationStatus = :ragStatus, ragEvaluationTimestamp = :timestamp',
            ExpressionAttributeValues: {
                ':ragStatus': ragStatus,
                ':timestamp': evaluationTimestamp,
            },
        }).promise();

        console.log(`Updated RAG evaluation to '${ragStatus}' for fileId: ${fileId}`);
    } catch (error) {
        console.error(`Error updating RAG evaluation for ${fileId}:`, error);
        throw error;
    }
}

