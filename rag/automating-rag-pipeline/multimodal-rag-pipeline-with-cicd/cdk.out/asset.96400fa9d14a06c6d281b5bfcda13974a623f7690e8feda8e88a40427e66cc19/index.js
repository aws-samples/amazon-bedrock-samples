"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/services/main-lambda.ts
var main_lambda_exports = {};
__export(main_lambda_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(main_lambda_exports);
var import_client_bedrock_runtime = require("@aws-sdk/client-bedrock-runtime");
var import_client_bedrock_agent_runtime = require("@aws-sdk/client-bedrock-agent-runtime");
var awsRegion = process.env.AWS_REGION;
var modelID = "anthropic.claude-3-haiku-20240307-v1:0";
var runtimeClient = new import_client_bedrock_runtime.BedrockRuntimeClient({ region: awsRegion });
var agentClient = new import_client_bedrock_agent_runtime.BedrockAgentRuntimeClient({ region: awsRegion });
var knowledgeBaseId = process.env.KNOWLEDGE_BASE_ID;
console.log("Knowledge Base ID:", knowledgeBaseId);
async function queryKnowledgeBaseWithCitations(prompt) {
  const input = {
    input: {
      text: prompt
    },
    retrieveAndGenerateConfiguration: {
      type: "KNOWLEDGE_BASE",
      knowledgeBaseConfiguration: {
        knowledgeBaseId,
        modelArn: `arn:aws:bedrock:${awsRegion}::foundation-model/${modelID}`,
        retrievalConfiguration: {
          vectorSearchConfiguration: {
            numberOfResults: 5
          }
        }
      }
    }
  };
  console.log("Input to Retrieve and Generate:", JSON.stringify(input));
  const command = new import_client_bedrock_agent_runtime.RetrieveAndGenerateCommand(input);
  const response = await agentClient.send(command);
  console.log("Response generated after sending the command:", response);
  const responseText = response.output?.text || "";
  const citations = response.citations || [];
  return { responseText, citations };
}
async function invokeModel(prompt) {
  const payload = {
    modelId: "anthropic.claude-3-haiku-20240307-v1:0",
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 1e3,
      messages: [
        {
          role: "user",
          content: [{ type: "text", text: prompt }]
        }
      ]
    })
  };
  console.log("Payload for model invocation:", JSON.stringify(payload));
  const apiResponse = await runtimeClient.send(new import_client_bedrock_runtime.InvokeModelCommand(payload));
  const decodedResponseBody = new TextDecoder().decode(apiResponse.body);
  const responseBody = JSON.parse(decodedResponseBody);
  const finalResponse = responseBody.content[0].text;
  console.log("Model Response:", finalResponse);
  return finalResponse;
}
var handler = async (event) => {
  console.log("Event received:", JSON.stringify(event, null, 2));
  const queryStringParameters = event.queryStringParameters || {};
  let prompt = queryStringParameters.prompt || "Hi";
  let action = queryStringParameters.action || "knowledge";
  if (event.httpMethod === "POST" && event.body) {
    try {
      const body = JSON.parse(event.body);
      prompt = body.prompt || prompt;
      action = body.action || action;
    } catch (error) {
      console.error("Error parsing body:", error);
    }
  }
  console.log(`Action: ${action}`);
  console.log(`Prompt: ${prompt}`);
  try {
    let result;
    let citations = [];
    if (action === "knowledge") {
      console.log("Querying the knowledge base...");
      const knowledgebaseResult = await queryKnowledgeBaseWithCitations(prompt);
      console.log("Knowledge Result:", knowledgebaseResult);
      result = knowledgebaseResult.responseText;
      citations = knowledgebaseResult.citations;
      console.log("knowledgebaseResult response:", result);
      console.log("knowledgebaseResult citations:", citations);
      citations.forEach((citation, index) => {
        console.log(`Citation ${index + 1}:`);
        console.log("Generated Response Part:", citation.generatedResponsePart);
        citation.retrievedReferences.forEach((reference, refIndex) => {
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
        citations
        // Return citations if available
      })
    };
  } catch (err) {
    console.error("Error occurred:", err);
    return {
      statusCode: 500,
      body: JSON.stringify({
        generatedResponse: "An error occurred",
        error: err instanceof Error ? err.message : "Unknown error"
      })
    };
  }
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
