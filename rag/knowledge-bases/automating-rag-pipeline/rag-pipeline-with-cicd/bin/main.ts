import { App } from "aws-cdk-lib";
import { CodePipelineStack } from "../lib/stacks/CodePipelineStack";


const app = new App();


new CodePipelineStack(app, "CodePipelineStack", {
    env: {
        account: process.env.CDK_DEFAULT_ACCOUNT as string,
        region: process.env.CDK_DEFAULT_REGION as string,
    },
    codePipelineName: "RAGPipeline",
});


