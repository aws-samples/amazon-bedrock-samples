import { App } from "aws-cdk-lib";
import { CodePipelineStack } from "../lib/stacks/CodePipelineStack";
// import { BedrockStack } from "../lib/stacks/BedrockStack";
// import { RAGEvaluationStack } from "../lib/stacks/RAGEvaluationStack";
// import { DataIngestionStack } from "../lib/stacks/DataIngestionStack";



const app = new App();

// const evaluationStack = new RAGEvaluationStack(app, "RAGEvaluationStack", {
//     stageName: 'QA',
// });


new CodePipelineStack(app, "CodePipelineStack", {
    env: {
        account: process.env.CDK_DEFAULT_ACCOUNT as string,
        region: process.env.CDK_DEFAULT_REGION as string,
    },
    codePipelineName: "MultimodalRAG",
});

// const bedrockKnowledgeBaseStack = new BedrockStack(app, "BedrockStack", {
//     stageName: "QA",
// });

// const ragEvaluationStack = new RAGEvaluationStack(app, "RAGEvaluationStack", {
//     stageName: "QA",
//     // kbDataIngestionStateMachineArn: dataIngestionStack.kbDataIngestionStateMachineArn,
// });


// const dataIngestionStack = new DataIngestionStack(app, "DataIngestionStack", {
//     stageName: "QA",
//     codePipelineName: "MultimodalRAG",
//     knowledgeBaseId: bedrockKnowledgeBaseStack.knowledgeBaseId,
//     dataSourceId: bedrockKnowledgeBaseStack.dataSourceId,
//     ragEvaluationStateMachineArn: ragEvaluationStack.ragEvaluationStateMachineArn,
// });


