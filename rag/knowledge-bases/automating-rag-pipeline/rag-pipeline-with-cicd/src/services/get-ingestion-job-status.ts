
import { BedrockAgentClient, GetIngestionJobCommand } from "@aws-sdk/client-bedrock-agent";

const bedrockClient = new BedrockAgentClient({ region: process.env.AWS_REGION });

export const handler = async (event: any): Promise<any> => {
    const { KnowledgeBaseId, DataSourceId, IngestionJobId } = event;

    const command = new GetIngestionJobCommand({
        knowledgeBaseId: KnowledgeBaseId,
        dataSourceId: DataSourceId,
        ingestionJobId: IngestionJobId,
    });

    try {
        const response = await bedrockClient.send(command);
        const job = response.ingestionJob;
        console.log('Ingestion Job status:', job?.status);
        return {
            status: job?.status,
            ingestionJob: job,
        };
    } catch (error) {
        console.error('Error getting ingestion job status:', error);
        throw error;
    }
};
