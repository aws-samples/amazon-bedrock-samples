import { DynamoDB } from "aws-sdk";
import { BedrockAgentClient, StartIngestionJobCommand, GetIngestionJobCommand } from "@aws-sdk/client-bedrock-agent";

const dynamodbClient = new DynamoDB.DocumentClient();
const bedrockClient = new BedrockAgentClient({ region: process.env.AWS_REGION });

// const DYNAMODB_TABLE = process.env.PROCESSED_FILES_TABLE;
// const STAGE_NAME = process.env.STAGE_NAME;
const FILE_METADATA_TABLE = process.env.FILE_METADATA_TABLE;

// if (!FILE_METADATA_TABLE_NAME) {
//     throw new Error('DYNAMODB_TABLE environment variable is not set');
// }

export const handler = async (event: any, context: any): Promise<any> => {
    // console.log(`Hello KB Data Ingestion Lambda for ${STAGE_NAME} environment!`);
    console.log('Event:', event);
    console.log('From kb-data-ingestion Lambda');

    const kbS3ProcessedDataSource = process.env.PROCESSED_S3;
    const knowledgeBaseId = process.env.KNOWLEDGE_BASE_ID;
    const dataSourceId = process.env.DATA_SOURCE_ID;

    if (!kbS3ProcessedDataSource || !knowledgeBaseId || !dataSourceId) {
        throw new Error('Environment variables KB_S3_PROCESSED_DATA_SOURCE, KNOWLEDGE_BASE_ID, and DATA_SOURCE_ID must be defined');
    }

    console.log('KB S3 Processed Data Source: ', kbS3ProcessedDataSource);
    console.log('Knowledge Base ID: ', knowledgeBaseId);
    console.log('Data Source ID: ', dataSourceId);

    // const newFilesAvailable = await areNewFilesAvailableForKbIngestion();
    // if (!newFilesAvailable) {
    //     console.log('No new files detected. Skipping data ingestion.');
    //     return {
    //         // dataingestionStatus: 'No new files to ingest',
    //         newFilesAvailable: false,
    //     };
    // }

    // console.log('New files detected. Proceeding with data ingestion...');
    console.log('Starting data ingestion job...');
    const jobInfo = await startIngestionJob(knowledgeBaseId, dataSourceId, context.awsRequestId);

    // Return job information
    return {
        // dataingestionStatus: 'Started data ingestion job successfully',
        // newFilesAvailable: true,
        // fileModificationsExist: true,
        JobId: jobInfo.JobId,
        KnowledgeBaseId: knowledgeBaseId,
        DataSourceId: dataSourceId,
    };
};

const startIngestionJob = async (knowledgeBaseId: string, dataSourceId: string, clientToken: string): Promise<{ JobId: string }> => {
    const input = {
        knowledgeBaseId: knowledgeBaseId,
        dataSourceId: dataSourceId,
        clientToken: clientToken,
    };
    const command = new StartIngestionJobCommand(input);

    const startJobResponse = await bedrockClient.send(command);
    const job = startJobResponse.ingestionJob;
    console.log('Ingestion Job started:', job);

    return {
        JobId: job?.ingestionJobId as string,
    };
};

// // Function to check if new files are marked in DynamoDB
// const checkForNewFiles = async (): Promise<boolean> => {
//     const params = {
//         TableName: DYNAMODB_TABLE as string,
//         Key: { fileName: 'newFilesFlag', environment: STAGE_NAME },
//     };
//     console.log(`Checking DynamoDB for new files in ${STAGE_NAME} environment...`);

//     const data = await dynamodbClient.get(params).promise();
//     console.log(`DynamoDB response for checkForNewFiles in ${STAGE_NAME} environment:`, data);

//     if (data.Item && data.Item.hasNewFiles) {
//         console.log('New files found in DynamoDB.');
//         return true;
//     }

//     console.log('No new files found in DynamoDB.');
//     return false;
// };


async function areNewFilesAvailableForKbIngestion(): Promise<boolean> {
    try {
        // Query the DynamoDB GSI for processed files with pending KB ingestion status and active status
        const result = await dynamodbClient.query({
            TableName: FILE_METADATA_TABLE as string,
            IndexName: 'fileType-kbIngestionStatus-index', // Specify the GSI name
            KeyConditionExpression: '#fileType = :processed and #kbIngestionStatus = :pending',
            FilterExpression: '#status = :active and #fileFormat = :PDF',
            ExpressionAttributeNames: {
                '#fileType': 'fileType',
                '#kbIngestionStatus': 'kbIngestionStatus',
                '#status': 'status',
                '#fileFormat': 'fileFormat',
            },
            ExpressionAttributeValues: {
                ':processed': 'processed',
                ':pending': 'pending',
                ':active': 'active',
                ':PDF': 'PDF', // Match the FilterExpression placeholder
            },
        }).promise();

        // Return true if there are any matching items, otherwise false
        return result.Items !== undefined && result.Items.length > 0;
    } catch (error) {
        console.error('Error checking for new files for KB ingestion:', error);
        throw error;
    }
}



