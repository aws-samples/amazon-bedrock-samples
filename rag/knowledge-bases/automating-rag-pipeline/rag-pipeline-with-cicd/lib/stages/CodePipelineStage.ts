import { Stage, StageProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import { WebApplicationStack } from "../stacks/WebApplicationStack";
import { BedrockStack } from "../stacks/BedrockStack";
import { RAGEvaluationStack } from "../stacks/RAGEvaluationStack";
import { DataIngestionStack } from "../stacks/DataIngestionStack";
import { MoveFilesStack } from "../stacks/MoveFilesStack";
import { S3BucketStack } from "../stacks/S3BucketStack";


export interface CodePipelineStageProps extends StageProps {
  stageName: string;
  codePipelineName: string;
}

export class CodePipelineStage extends Stage {

  constructor(scope: Construct, id: string, props: CodePipelineStageProps) {
    super(scope, id, props);

    if (props.stageName === "PreQABucketSetupStage" || props.stageName === "PreProdBucketSetupStage") {

      new S3BucketStack(this, "S3BucketStack", {
        codePipelineName: props.codePipelineName as string,
        stageName: props.stageName as string,
      });
    }

    if (props.stageName === "QA") {

      const bedrockKnowledgeBaseStack = new BedrockStack(this, "BedrockStack", {
        stageName: props.stageName,
        codePipelineName: props.codePipelineName,
      });

      new DataIngestionStack(this, "DataIngestionStack", {
        stageName: props.stageName as string,
        codePipelineName: props.codePipelineName as string,
        knowledgeBaseId: bedrockKnowledgeBaseStack.knowledgeBaseId,
        dataSourceId: bedrockKnowledgeBaseStack.dataSourceId,
      });

      new WebApplicationStack(this, "WebAppStack", {
        stageName: props.stageName,
        knowledgeBaseId: bedrockKnowledgeBaseStack.knowledgeBaseId,
      });

    }

    // New PostQAApproval stage
    if (props.stageName === "PostQAApproval") {
      // Create only the RAG evaluation stack in this stage
      new RAGEvaluationStack(this, "RAGEvaluationStack", {
        stageName: props.stageName as string,
        codePipelineName: props.codePipelineName as string,
      });

      // This stage will handle the Manual Approval and the actual RAG evaluation trigger
      // LambdaInvoke for RAG evaluation would trigger here based on the KB ingestion step machine.
    }

    if (props.stageName === "Prod") {
      const bedrockKnowledgeBaseStack = new BedrockStack(this, "BedrockStack", {
        stageName: props.stageName,
        codePipelineName: props.codePipelineName,
      });

      const dataIngestionStack = new DataIngestionStack(this, "DataIngestionStack", {
        stageName: props.stageName as string,
        codePipelineName: props.codePipelineName as string,
        knowledgeBaseId: bedrockKnowledgeBaseStack.knowledgeBaseId,
        dataSourceId: bedrockKnowledgeBaseStack.dataSourceId,
      });

      new MoveFilesStack(this, "MoveFilesStack", {
        codePipelineName: props.codePipelineName as string,
        prodRawS3DataSourceBucketName: dataIngestionStack.rawS3DataSourceBucketName,
      });

      new WebApplicationStack(this, "WebAppStack", {
        stageName: props.stageName,
        knowledgeBaseId: bedrockKnowledgeBaseStack.knowledgeBaseId,
      });

    }

  }
}