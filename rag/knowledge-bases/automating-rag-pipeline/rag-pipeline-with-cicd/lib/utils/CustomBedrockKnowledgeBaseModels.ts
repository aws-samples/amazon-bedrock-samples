import { BedrockKnowledgeBaseModels } from '@aws/agents-for-amazon-bedrock-blueprints';

export class CustomBedrockKnowledgeBaseModels extends BedrockKnowledgeBaseModels {
    public static readonly TITAN_EMBED_TEXT_V2 = new CustomBedrockKnowledgeBaseModels("amazon.titan-embed-text-v2:0", 512);

    constructor(modelName: string, vectorDimension: number) {
        super(modelName, vectorDimension);
    }
}