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

// src/services/get-ingestion-job-status.ts
var get_ingestion_job_status_exports = {};
__export(get_ingestion_job_status_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(get_ingestion_job_status_exports);
var import_client_bedrock_agent = require("@aws-sdk/client-bedrock-agent");
var bedrockClient = new import_client_bedrock_agent.BedrockAgentClient({ region: process.env.AWS_REGION });
var handler = async (event) => {
  const { KnowledgeBaseId, DataSourceId, IngestionJobId } = event;
  const command = new import_client_bedrock_agent.GetIngestionJobCommand({
    knowledgeBaseId: KnowledgeBaseId,
    dataSourceId: DataSourceId,
    ingestionJobId: IngestionJobId
  });
  try {
    const response = await bedrockClient.send(command);
    const job = response.ingestionJob;
    console.log("Ingestion Job status:", job?.status);
    return {
      status: job?.status,
      ingestionJob: job
    };
  } catch (error) {
    console.error("Error getting ingestion job status:", error);
    throw error;
  }
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
