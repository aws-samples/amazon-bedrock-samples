import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { BedrockRuntimeClient, InvokeModelCommand, InvokeModelCommandInput, InvokeModelCommandOutput } from "@aws-sdk/client-bedrock-runtime";
import { BedrockAgentRuntimeClient, RetrieveAndGenerateCommand, RetrieveAndGenerateCommandInput, RetrieveAndGenerateCommandOutput } from "@aws-sdk/client-bedrock-agent-runtime";

const awsRegion = process.env.AWS_REGION
const modelID = process.env.MODEL_ID;
// Knowledge base ID for BedrockAgentRuntimeClient
const knowledgeBaseId = process.env.KNOWLEDGE_BASE_ID;
console.log("Knowledge Base ID:", knowledgeBaseId);

if (!modelID) throw new Error('MODEL_ID environment variable is missing.');
if (!knowledgeBaseId) throw new Error('KNOWLEDGE_BASE_ID environment variable is missing.');

// Create instances of both Bedrock clients
const runtimeClient = new BedrockRuntimeClient({ region: awsRegion });
const agentClient = new BedrockAgentRuntimeClient({ region: awsRegion });


interface Reference {
    content: {
        text: string;
    };
    location: {
        s3Location: {
            bucket: string;
            key: string;
        };
        type: string;
    };
    metadata: {
        'x-amz-bedrock-kb-source-uri': string;
        'x-amz-bedrock-kb-chunk-id': string;
        'x-amz-bedrock-kb-data-source-id': string;
    };
}

interface Citation {
    generatedResponsePart: string;
    retrievedReferences: Reference[];
}


// Function to query the knowledge base
async function queryKnowledgeBase(prompt: string): Promise<string> {
    const input: RetrieveAndGenerateCommandInput = {
        input: {
            text: prompt,
        },
        retrieveAndGenerateConfiguration: {
            type: "KNOWLEDGE_BASE",
            knowledgeBaseConfiguration: {
                knowledgeBaseId: knowledgeBaseId,
                modelArn: `arn:aws:bedrock:${awsRegion}::foundation-model/${modelID}`,
                retrievalConfiguration: {
                    vectorSearchConfiguration: {
                        numberOfResults: 5,
                    },
                },
            },
        },
    };

    console.log("Input to Retrieve and Generate:", JSON.stringify(input));
    const command: RetrieveAndGenerateCommand = new RetrieveAndGenerateCommand(input);
    const response: RetrieveAndGenerateCommandOutput = await agentClient.send(command);
    console.log("Response generated after sending the command:", response);
    return response.output?.text as string;
}

// Function to query the knowledge base with citation extraction
async function queryKnowledgeBaseWithCitations(prompt: string): Promise<{ responseText: string, citations: any[] }> {
    const input: RetrieveAndGenerateCommandInput = {
        input: {
            text: prompt,
        },
        retrieveAndGenerateConfiguration: {
            type: "KNOWLEDGE_BASE",
            knowledgeBaseConfiguration: {
                knowledgeBaseId: knowledgeBaseId,
                modelArn: `arn:aws:bedrock:${awsRegion}::foundation-model/${modelID}`,
                retrievalConfiguration: {
                    vectorSearchConfiguration: {
                        numberOfResults: 5,
                    },
                },
            },
        },
    };

    console.log("Input to Retrieve and Generate:", JSON.stringify(input));
    const command: RetrieveAndGenerateCommand = new RetrieveAndGenerateCommand(input);
    const response: RetrieveAndGenerateCommandOutput = await agentClient.send(command);
    console.log("Response generated after sending the command:", response);

    // Extract citations and response text
    const responseText = response.output?.text || '';
    const citations = response.citations || [];

    return { responseText, citations };
}


// Function to invoke a model using BedrockRuntimeClient
async function invokeModel(prompt: string): Promise<string> {
    const payload: InvokeModelCommandInput = {
        modelId: modelID,
        contentType: "application/json",
        accept: "application/json",
        body: JSON.stringify({
            anthropic_version: "bedrock-2023-05-31",
            max_tokens: 1000,
            messages: [
                {
                    role: "user",
                    content: [{ type: "text", text: prompt }],
                },
            ],
        }),
    };

    console.log("Payload for model invocation:", JSON.stringify(payload));

    const apiResponse = await runtimeClient.send(new InvokeModelCommand(payload));
    const decodedResponseBody = new TextDecoder().decode(apiResponse.body);  // Decode the response body
    const responseBody = JSON.parse(decodedResponseBody);  // Parse the response
    const finalResponse = responseBody.content[0].text;  // Extract the final response text

    console.log("Model Response:", finalResponse);

    return finalResponse;
}

// Main Lambda handler
export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    console.log("Event received:", JSON.stringify(event, null, 2));

    // Extract input parameters from query string or body
    const queryStringParameters = event.queryStringParameters || {};
    let prompt = queryStringParameters.prompt || 'Hi';
    let action = queryStringParameters.action || 'knowledge';  // Default to 'knowledge' if no action is provided

    // If the HTTP method is POST, parse the body
    if (event.httpMethod === 'POST' && event.body) {
        try {
            const body = JSON.parse(event.body);
            prompt = body.prompt || prompt;
            action = body.action || action;
        } catch (error) {
            console.error('Error parsing body:', error);
        }
    }

    console.log(`Action: ${action}`);
    console.log(`Prompt: ${prompt}`);

    try {
        let result: string;
        let citations: any[] = [];

        // Choose the correct function based on the action
        if (action === 'knowledge') {
            console.log("Querying the knowledge base...");
            // result = await queryKnowledgeBase(prompt);
            const knowledgebaseResult = await queryKnowledgeBaseWithCitations(prompt);
            console.log("Knowledge Result:", knowledgebaseResult);

            result = knowledgebaseResult.responseText;
            citations = knowledgebaseResult.citations;

            console.log("knowledgebaseResult response:", result);
            console.log("knowledgebaseResult citations:", citations);

            // Unpack and log citations
            citations.forEach((citation: Citation, index: number) => {
                console.log(`Citation ${index + 1}:`);
                console.log("Generated Response Part:", citation.generatedResponsePart);

                // Unpack and log retrieved references
                citation.retrievedReferences.forEach((reference: Reference, refIndex: number) => {
                    console.log(`  Retrieved Reference ${refIndex + 1}:`);
                    console.log("    Content Text:", reference.content.text);
                    console.log("    Location:", reference.location);
                    console.log("    Metadata:", reference.metadata);
                });
            });

        } else {
            console.log("Invoking the model...");
            result = await invokeModel(prompt);
        }

        return {
            statusCode: 200,
            body: JSON.stringify({
                generatedResponse: result,
                citations: citations,  // Return citations if available
            }),
        };

    } catch (err) {
        console.error("Error occurred:", err);

        return {
            statusCode: 500,
            body: JSON.stringify({
                generatedResponse: 'An error occurred',
                error: err instanceof Error ? err.message : 'Unknown error',
            }),
        };
    }
};
