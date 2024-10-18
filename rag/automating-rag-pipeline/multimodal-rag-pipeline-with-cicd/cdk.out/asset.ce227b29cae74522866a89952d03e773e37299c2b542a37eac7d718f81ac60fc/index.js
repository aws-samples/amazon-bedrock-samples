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

// src/services/trigger-approval.ts
var trigger_approval_exports = {};
__export(trigger_approval_exports, {
  handler: () => handler
});
module.exports = __toCommonJS(trigger_approval_exports);
var import_client_codepipeline = require("@aws-sdk/client-codepipeline");
var codePipelineClient = new import_client_codepipeline.CodePipelineClient({ region: process.env.AWS_REGION });
var handler = async (event) => {
  console.log("Event received to approve pipeline: ", event);
  try {
    const pipelineName = process.env.PIPELINE_NAME;
    const stageName = "PostQAApproval";
    const actionName = "ManualApprovalForProduction";
    const evaluationResult = event.success;
    if (!pipelineName) {
      throw new Error("Pipeline name is not defined");
    }
    const getPipelineStateCommand = new import_client_codepipeline.GetPipelineStateCommand({
      name: pipelineName
    });
    const pipelineStateResponse = await codePipelineClient.send(getPipelineStateCommand);
    console.log("Pipeline state response: ", pipelineStateResponse);
    const pipelineVersion = pipelineStateResponse.pipelineVersion;
    const lastUpdated = pipelineStateResponse.updated;
    console.log(`Pipeline Version: ${pipelineVersion}, Last Updated: ${lastUpdated}`);
    const stages = pipelineStateResponse.stageStates;
    if (!stages) {
      throw new Error("Pipeline stages are not available.");
    }
    let postQAApprovalExecutionId;
    const postQAStageName = "PostQAApproval";
    for (const stage of stages) {
      if (stage.stageName === postQAStageName && stage.latestExecution) {
        postQAApprovalExecutionId = stage.latestExecution.pipelineExecutionId;
        console.log(`PostQAApproval Stage Execution ID: ${postQAApprovalExecutionId}`);
        break;
      }
    }
    if (!postQAApprovalExecutionId) {
      throw new Error("PostQAApproval execution ID not found.");
    }
    let approvalAlreadySucceeded = false;
    let approvalToken;
    for (const stage of stages) {
      if (stage.stageName === stageName) {
        console.log(`Processing PostQAApproval stage with execution ID: ${stage.latestExecution?.pipelineExecutionId}`);
        if (stage.actionStates) {
          console.log("Stage action states: ", stage.actionStates);
          for (const action of stage.actionStates) {
            if (action.actionName === actionName) {
              if (action.latestExecution?.status === "Succeeded") {
                approvalAlreadySucceeded = true;
                console.log("Manual approval already succeeded. Resetting approval.");
              } else if (action.latestExecution?.status === "InProgress") {
                approvalToken = action.latestExecution.token;
                console.log(`Found approval token: ${approvalToken}`);
              }
              break;
            }
          }
        }
      }
    }
    if (approvalAlreadySucceeded) {
      const resetApprovalCommand = new import_client_codepipeline.PutApprovalResultCommand({
        pipelineName,
        stageName,
        actionName,
        result: {
          summary: "Manual approval reset due to new changes.",
          status: "Rejected"
          // Reject the previous approval to force re-triggering
        },
        token: approvalToken
      });
      await codePipelineClient.send(resetApprovalCommand);
      console.log("Previous approval was reset.");
      return {
        statusCode: 200,
        body: "Manual approval reset successfully. Waiting for new approval."
      };
    }
    if (!approvalToken) {
      console.warn("Approval token not found for current execution. Trying fallback to the latest execution.");
      for (const stage of stages) {
        if (stage.stageName === stageName) {
          if (stage.actionStates) {
            console.log("Stage action states: ", stage.actionStates);
            for (const action of stage.actionStates) {
              if (action.actionName === actionName && action.latestExecution?.status === "InProgress") {
                approvalToken = action.latestExecution.token;
                console.log(`Fallback approval token found: ${approvalToken}`);
                break;
              }
            }
          }
        }
      }
      if (!approvalToken) {
        throw new Error("Approval token not found or no manual approval in progress.");
      }
    }
    if (evaluationResult === true) {
      const putApprovalResultCommand = new import_client_codepipeline.PutApprovalResultCommand({
        pipelineName,
        stageName,
        actionName,
        result: {
          summary: "Evaluation passed. Proceeding to production.",
          status: "Approved"
        },
        token: approvalToken
        // Use the approval token retrieved
      });
      const response = await codePipelineClient.send(putApprovalResultCommand);
      console.log(`Pipeline ${pipelineName} manual approval successfully completed.`);
      return {
        statusCode: 200,
        body: "Manual approval approved, pipeline continues to production."
      };
    } else {
      console.log(`Evaluation failed. Production deployment will not proceed.`);
      return {
        statusCode: 400,
        body: "Evaluation failed. Pipeline not promoted to production."
      };
    }
  } catch (error) {
    console.error("Error during pipeline approval: ", error);
    return {
      statusCode: 500,
      body: "Failed to approve pipeline"
    };
  }
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  handler
});
