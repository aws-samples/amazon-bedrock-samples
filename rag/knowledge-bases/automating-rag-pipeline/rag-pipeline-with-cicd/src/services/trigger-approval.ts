import { CodePipelineClient, GetPipelineStateCommand, PutApprovalResultCommand } from "@aws-sdk/client-codepipeline";
import { Handler } from "aws-lambda";

// Initialize the CodePipeline client
const codePipelineClient = new CodePipelineClient({ region: process.env.AWS_REGION });

export const handler: Handler = async (event: any) => {
    console.log("Event received to approve pipeline: ", event);

    try {
        // Extract necessary environment variables
        const pipelineName = process.env.PIPELINE_NAME;
        const stageName = "PostQAApproval"; // Now the manual approval is in the PostQAApproval stage
        const actionName = "ManualApprovalForProduction"; // Name of the manual approval action
        const evaluationResult = event.success; // Get the evaluation result

        if (!pipelineName) {
            throw new Error("Pipeline name is not defined");
        }

        // Get the current state of the pipeline
        const getPipelineStateCommand = new GetPipelineStateCommand({
            name: pipelineName,
        });

        const pipelineStateResponse = await codePipelineClient.send(getPipelineStateCommand);
        console.log("Pipeline state response: ", pipelineStateResponse);

        // Check the latest pipeline version and timestamp
        const pipelineVersion = pipelineStateResponse.pipelineVersion;
        const lastUpdated = pipelineStateResponse.updated;
        console.log(`Pipeline Version: ${pipelineVersion}, Last Updated: ${lastUpdated}`);

        // Retrieve the stages from the pipeline
        const stages = pipelineStateResponse.stageStates;
        if (!stages) {
            throw new Error("Pipeline stages are not available.");
        }

        // Find the pipelineExecutionId from the PostQAApproval stage (ensure it's the latest one)
        let postQAApprovalExecutionId: string | undefined;
        const postQAStageName = "PostQAApproval"; // Ensure this matches the exact stage name for PostQAApproval

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

        // Check for previous approval status
        let approvalAlreadySucceeded = false;
        let approvalToken: string | undefined;

        for (const stage of stages) {
            if (stage.stageName === stageName) {
                console.log(`Processing PostQAApproval stage with execution ID: ${stage.latestExecution?.pipelineExecutionId}`);

                if (stage.actionStates) {
                    console.log("Stage action states: ", stage.actionStates);
                    for (const action of stage.actionStates) {
                        if (action.actionName === actionName) {
                            // Check if approval has already succeeded
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

        // Reset manual approval if it was already marked as succeeded
        if (approvalAlreadySucceeded) {
            const resetApprovalCommand = new PutApprovalResultCommand({
                pipelineName: pipelineName,
                stageName: stageName,
                actionName: actionName,
                result: {
                    summary: "Manual approval reset due to new changes.",
                    status: "Rejected", // Reject the previous approval to force re-triggering
                },
                token: approvalToken,
            });

            await codePipelineClient.send(resetApprovalCommand);
            console.log("Previous approval was reset.");
            return {
                statusCode: 200,
                body: "Manual approval reset successfully. Waiting for new approval.",
            };
        }

        if (!approvalToken) {
            console.warn("Approval token not found for current execution. Trying fallback to the latest execution.");

            // Fallback mechanism to find any manual approval token in the PostQAApproval stage
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

        // Perform the approval if the evaluation succeeded
        if (evaluationResult === true) {
            const putApprovalResultCommand = new PutApprovalResultCommand({
                pipelineName: pipelineName,
                stageName: stageName,
                actionName: actionName,
                result: {
                    summary: "Evaluation passed. Proceeding to production.",
                    status: "Approved",
                },
                token: approvalToken, // Use the approval token retrieved
            });

            const response = await codePipelineClient.send(putApprovalResultCommand);
            console.log(`Pipeline ${pipelineName} manual approval successfully completed.`);
            return {
                statusCode: 200,
                body: "Manual approval approved, pipeline continues to production.",
            };
        } else {
            console.log(`Evaluation failed. Production deployment will not proceed.`);
            return {
                statusCode: 400,
                body: "Evaluation failed. Pipeline not promoted to production.",
            };
        }
    } catch (error) {
        console.error("Error during pipeline approval: ", error);
        return {
            statusCode: 500,
            body: 'Failed to approve pipeline',
        };
    }
};
