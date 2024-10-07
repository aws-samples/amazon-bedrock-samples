// Regular expressions for parsing model responses
const REGEX = {
    PRE_PROCESSING_RATIONALE: "<thinking>(.*?)</thinking>",
    PREPROCESSING_CATEGORY: "<category>(.*?)</category>",
    ANSWER_PART: /<answer>(.*?)<\/answer>/gs,
    ANSWER_TEXT_PART: /<text>(.*?)<\/text>/,
    ANSWER_REFERENCE_PART: /<reference>(.*?)<\/reference>/gs,
    FINAL_RESPONSE: /<final_response>([\s\S]*?)<\/final_response>/g,
};

// Compiled patterns for global and multiline matching
const PATTERNS = {
    PRE_PROCESSING_RATIONALE: new RegExp(REGEX.PRE_PROCESSING_RATIONALE, 'gs'),
    PREPROCESSING_CATEGORY: new RegExp(REGEX.PREPROCESSING_CATEGORY, 'gs'),
};

// Utility functions
function sanitizeResponse(text: string | undefined): string {
    console.log('Sanitizing response');
    if (text === undefined) {
        console.error('Received undefined text in sanitizeResponse');
        return '';
    }
    return text.replace(/\\n/g, "\n");
}

function getIsValidInput(category: string | null): boolean {
    console.log('Determining if input is valid based on category');
    return category !== null && ["D", "E"].includes(category.trim().toUpperCase());
}

function parseReferences(answerPart: string) {
    console.log('Parsing references from answer part');
    const references = [];
    for (const match of answerPart.matchAll(REGEX.ANSWER_REFERENCE_PART)) {
        references.push({ sourceId: match[1].trim() });
    }
    return references;
}

// Parsing functions
function parseGeneratedResponse(sanitizedLlmResponse: string) {
    console.log('Parsing generated response');
    const results = [];
    for (const match of sanitizedLlmResponse.matchAll(REGEX.ANSWER_PART)) {
        const text = match[1].trim().match(REGEX.ANSWER_TEXT_PART)?.[1].trim();
        if (!text) throw new Error("Could not parse generated response");
        const references = parseReferences(match[1]);
        results.push({ text, references });
    }
    return { generatedResponseParts: results };
}

function parsePreProcessing(modelResponse: string) {
    console.log('Parsing pre-processing part of model response');
    const category = [...modelResponse.matchAll(PATTERNS.PREPROCESSING_CATEGORY)].map(m => m[1])[0] || null;
    const rationale = [...modelResponse.matchAll(PATTERNS.PRE_PROCESSING_RATIONALE)].map(m => m[1])[0] || null;
    return {
        promptType: "PRE_PROCESSING",
        preProcessingParsedResponse: { rationale, isValidInput: getIsValidInput(category) },
    };
}

function parseKnowledgeBaseResponse(modelResponse: string) {
    console.log('Parsing knowledge base response generation part of model response');
    return {
        promptType: 'KNOWLEDGE_BASE_RESPONSE_GENERATION',
        knowledgeBaseResponseGenerationParsedResponse: { generatedResponse: parseGeneratedResponse(modelResponse) }
    };
}

function parseFinalResponse(input: string): string {
    console.log('Parsing final response');
    const match = [...input.matchAll(REGEX.FINAL_RESPONSE)][0];
    if (!match) throw new Error("No final response found.");
    return match[1].trim();
}

function parsePostProcessing(modelResponse: string) {
    console.log('Parsing post-processing part of model response');
    const finalResponse = parseFinalResponse(modelResponse);
    console.log('Final response:', finalResponse);

    return {
        promptType: "POST_PROCESSING",
        postProcessingParsedResponse: {
            responseText: finalResponse,
        },
    };
}

// Main processing function
function processPrompt(promptType: string, modelResponse: string) {
    console.log(`Processing prompt of type: ${promptType}`);
    switch (promptType) {
        case "PRE_PROCESSING": return parsePreProcessing(modelResponse);
        case "KNOWLEDGE_BASE_RESPONSE_GENERATION": return parseKnowledgeBaseResponse(modelResponse);
        case "POST_PROCESSING": return parsePostProcessing(modelResponse);
        default: return { statusCode: 400, body: JSON.stringify({ message: 'Unsupported prompt type' }) };
    }
}

// Lambda handler
export const handler = async (event: any, _context: unknown) => {
    console.log('Received input event for Lambda Parser:', event);
    if (!event || !event.invokeModelRawResponse || !event.promptType) {
        console.error('Invalid event structure:', event);
        return { statusCode: 400, body: JSON.stringify({ message: 'Invalid event structure' }) };
    }

    const modelResponse = sanitizeResponse(event.invokeModelRawResponse);
    const response = processPrompt(event.promptType, modelResponse);

    console.log('Lambda Parser response that will be sent to the agent:', response);
    return { ...response, messageVersion: "1.0", overrideType: "OUTPUT_PARSER", promptType: event.promptType };
};

