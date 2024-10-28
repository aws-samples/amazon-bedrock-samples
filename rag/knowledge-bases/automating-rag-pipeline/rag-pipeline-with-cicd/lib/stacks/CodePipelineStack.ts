
import { Duration, Fn, Stack, StackProps } from "aws-cdk-lib";
import { CodeBuildStep, CodePipeline, CodePipelineSource, ManualApprovalStep, ShellStep } from "aws-cdk-lib/pipelines";
import { Construct } from "constructs";
import { CodePipelineStage } from "../stages/CodePipelineStage";
import { ManagedPolicy, PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam";
import { LinuxBuildImage } from "aws-cdk-lib/aws-codebuild";
import { NodejsFunction } from "aws-cdk-lib/aws-lambda-nodejs";
import { Runtime } from "aws-cdk-lib/aws-lambda";
import { join } from "path";
import { AwsCustomResource, AwsCustomResourcePolicy, PhysicalResourceId } from "aws-cdk-lib/custom-resources";

interface CodePipelineStackProps extends StackProps {
  env: {
    account: string;
    region: string;
  };
  codePipelineName: string;
}

/** 
 * ## CodePipelineStack Overview
 *
 * ### Usage:
 * This stack defines the CI/CD pipeline that automates the deployment of the RAG system across multiple environments (QA and Production).
 * It uses AWS CodePipeline, CodeBuild, and approval steps to manage infrastructure updates and deployments.
 *
 * ### Key Features:
 * - CodePipeline Integration: Automates the build, test, and deployment process for each environment.
 * - CodeBuild Step: Packages Lambda functions and builds the infrastructure using CDK.
 * - Manual Approval Workflow: Ensures that only validated code and data changes are promoted to production.
 * - SSM Parameter Store: Stores configuration values like bucket names and pipeline parameters.
 * - Multi-Environment Support: Deploys and promotes resources across QA and Production environments.
 */


export class CodePipelineStack extends Stack {
  constructor(scope: Construct, id: string, props: CodePipelineStackProps) {
    super(scope, id, props);

    // Initialize the pipeline
    const cicdPipeline = new CodePipeline(this, "MultimodalRAGPipeline", {
      pipelineName: props.codePipelineName,
      selfMutation: true,
      role: new Role(this, "CodePipelineRole", {
        assumedBy: new ServicePrincipal("codepipeline.amazonaws.com"),
        managedPolicies: [
          ManagedPolicy.fromAwsManagedPolicyName("AdministratorAccess"),
        ],
      }),
      synth: new ShellStep("Synth", {
        input: CodePipelineSource.gitHub(
          "manoj-selvakumar5/amazon-bedrock-samples",
          "rag-cicd-without-image-processing",
        ),
        commands: [
          "echo 'Current working directory:' $(pwd)",
          "ls -ltr",
          "cd rag/automating-rag-pipeline/rag-pipeline-with-cicd",
          "echo 'New working directory:' $(pwd)",
          "ls -ltr",
          "npm ci",
          "npm run build",
          "npx cdk synth"
        ],
        primaryOutputDirectory: 'rag/automating-rag-pipeline/rag-pipeline-with-cicd/cdk.out'  // Updated to reflect the correct project root directory
      }),
      dockerEnabledForSynth: true,
    });

    // Define the role with required policies
    const codeBuildRole = new Role(this, 'CodeBuildRole', {
      assumedBy: new ServicePrincipal('codebuild.amazonaws.com'),
      managedPolicies: [ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess')],
    });

    // Add specific permission for SSM GetParameter
    codeBuildRole.addToPolicy(new PolicyStatement({
      actions: ['ssm:GetParameter'],
      resources: [
        // `arn:aws:ssm:${this.region}:${this.account}:parameter/${props.codePipelineName}/PreQABucketSetupStage/lambda-package-bucket-name`,
        `arn:aws:ssm:${this.region}:${this.account}:parameter/${props.codePipelineName}/*`,
      ],
    }));


    // Add the S3 Bucket Stage
    const preQABucketSetupStage = cicdPipeline.addStage(
      new CodePipelineStage(this, 'PreQABucketSetupStage', {
        stageName: 'PreQABucketSetupStage',
        env: {
          account: this.node.tryGetContext('defaultAccount'),  // Retrieve a value from the CDK application context
          region: this.node.tryGetContext('defaultRegion'),
        },
        codePipelineName: props.codePipelineName,
      })
    );



    // Add Lambda Build Step to QA Stage
    const qaStage = cicdPipeline.addStage(
      new CodePipelineStage(this, "QA", {
        stageName: "QA",
        env: {
          account: this.node.tryGetContext("defaultAccount"),
          region: this.node.tryGetContext("defaultRegion"),
        },
        codePipelineName: props.codePipelineName,
      }),
      {
        pre: [
          // Pre-deployment Step: Build Lambda Package using CodeBuild required for Custom Lambda parser used in Bedrock 
          new CodeBuildStep("BuildLambdaPackage", {
            commands: [
              "echo 'Current working directory:' $(pwd)",
              "ls -R",
              "chmod +x rag/automating-rag-pipeline/rag-pipeline-with-cicd/src/app/build_lambda.sh",  // Make the script executable
              "./rag/knowledge-bases/automating-rag-pipeline/rag-pipeline-with-cicd/src/app/build_lambda.sh"            // Run the script
            ],

            role: codeBuildRole,
            buildEnvironment: {
              buildImage: LinuxBuildImage.STANDARD_5_0, // Use standard CodeBuild image
              environmentVariables: {
                CODE_PIPELINE_NAME: { value: props.codePipelineName },
                STAGE_NAME: { value: "PreQABucketSetupStage" },  // To retrieve the bucket name from SSM 
                AWS_REGION: { value: this.node.tryGetContext("defaultRegion") },  // Pass the region as an environment variable
              },
            },
          }),
        ],
      }
    );


    // New Post-QA Stage: Handles RAG evaluation and manual approval
    const postQAApprovalStage = cicdPipeline.addStage(
      new CodePipelineStage(this, "PostQAApproval", {
        stageName: "PostQAApproval",
        env: {
          account: this.node.tryGetContext("defaultAccount"),
          region: this.node.tryGetContext("defaultRegion"),
        },
        codePipelineName: props.codePipelineName,
      })
    );

    postQAApprovalStage.addPost(
      new CodeBuildStep("TriggerRAGEvaluationAfterQADeployment", {
        commands: [
          // Retrieve the state machine ARN from SSM in the us-east-1 region
          `aws stepfunctions start-execution --region ${this.node.tryGetContext("defaultRegion")} --state-machine-arn $(aws ssm get-parameter --name /${props.codePipelineName}/PostQAApproval/rag-evaluation-state-machine-arn --region ${this.node.tryGetContext("defaultRegion")} --query "Parameter.Value" --output text) --input '{}'`,
        ],
        buildEnvironment: {
          buildImage: LinuxBuildImage.STANDARD_5_0,
        },
        rolePolicyStatements: [
          new PolicyStatement({
            actions: ['ssm:GetParameter', 'states:StartExecution'],
            resources: [
              `arn:aws:ssm:${this.node.tryGetContext("defaultRegion")}:${this.account}:parameter/${props.codePipelineName}/PostQAApproval/rag-evaluation-state-machine-arn`,
              `arn:aws:states:${this.node.tryGetContext("defaultRegion")}:${this.account}:stateMachine:*`,
            ],
          }),
        ],
      })
    );

    postQAApprovalStage.addPost(new ManualApprovalStep("ManualApprovalForProduction"));




    // Add the S3 Bucket Stage
    const preProdBucketSetupStage = cicdPipeline.addStage(
      new CodePipelineStage(this, 'PreProdBucketSetupStage', {
        stageName: 'PreProdBucketSetupStage',
        env: {
          account: this.node.tryGetContext('prodAccount'),
          region: this.node.tryGetContext('prodRegion'),
        },
        codePipelineName: props.codePipelineName,
      })
    );


    // Prod Stage
    const prodStage = cicdPipeline.addStage(
      new CodePipelineStage(this, "Prod", {
        stageName: "Prod",
        env: {
          account: this.node.tryGetContext("prodAccount"),
          region: this.node.tryGetContext("prodRegion"),
        },
        codePipelineName: props.codePipelineName,
      }),
      {
        pre: [
          // Pre-deployment Step: Build Lambda Package for Prod Stage
          new CodeBuildStep("BuildLambdaPackageForProd", {
            commands: [
              "echo 'Current working directory:' $(pwd)",
              "ls -R",
              "chmod +x rag/automating-rag-pipeline/rag-pipeline-with-cicd/src/app/build_lambda.sh",     // Make the script executable
              "./rag/knowledge-bases/automating-rag-pipeline/rag-pipeline-with-cicd/src/app/build_lambda.sh"            // Run the script
            ],
            role: codeBuildRole,  // Use the shared CodeBuild role
            buildEnvironment: {
              buildImage: LinuxBuildImage.STANDARD_5_0, // Use standard CodeBuild image
              environmentVariables: {
                CODE_PIPELINE_NAME: { value: props.codePipelineName },
                STAGE_NAME: { value: "PreProdBucketSetupStage" },  // Specify the stage name for prod
                AWS_REGION: { value: this.node.tryGetContext("prodRegion") },  // Pass the region as an environment variable
              },
            },
          }),
        ],
        post: [
          // Post-deployment step: Trigger Copy Files State Machine
          new CodeBuildStep("TriggerCopyFilesFromQAToProdStateMachine", {
            commands: [
              `aws stepfunctions start-execution --region ${this.node.tryGetContext("prodRegion")} --state-machine-arn $(aws ssm get-parameter --name /${props.codePipelineName}/Prod/move-files-state-machine-arn --region ${this.node.tryGetContext("prodRegion")} --query "Parameter.Value" --output text) --input '{}'`,
            ],
            buildEnvironment: {
              buildImage: LinuxBuildImage.STANDARD_5_0,
            },
            rolePolicyStatements: [
              new PolicyStatement({
                actions: ["ssm:GetParameter", "states:StartExecution"],
                resources: [
                  `arn:aws:ssm:${this.node.tryGetContext("prodRegion")}:${this.account}:parameter/${props.codePipelineName}/Prod/move-files-state-machine-arn`,
                  `arn:aws:states:${this.node.tryGetContext("prodRegion")}:${this.account}:stateMachine:*`,
                ],
              }),
            ],
          }),
        ],
      }
    );



    // Create the cleanup Lambda function
    const cleanUpFunction = new NodejsFunction(this, 'CleanUpFunction', {
      runtime: Runtime.NODEJS_18_X,
      entry: join(__dirname, '..', '..', 'src', 'services', 'delete-stacks.ts'),
      handler: 'handler',
      timeout: Duration.minutes(15),
    });

    // Grant permissions to list and delete CloudFormation stacks
    cleanUpFunction.addToRolePolicy(
      new PolicyStatement({
        actions: ['cloudformation:ListStacks', 'cloudformation:DeleteStack'],
        resources: ['*'],
      })
    );

    // Create a custom resource to trigger the cleanup Lambda function on stack deletion
    // When the CodePipelineStack is deleted using cdk destroy, the CleanupTrigger resource is triggered, which then invokes the cleanUpFunction asynchronously.
    new AwsCustomResource(this, 'CleanupTrigger', {
      onDelete: {
        service: 'Lambda',
        action: 'invoke',
        parameters: {
          FunctionName: cleanUpFunction.functionName,
          InvocationType: 'Event',
        },
        physicalResourceId: PhysicalResourceId.of('CleanupTrigger'),
      },
      policy: AwsCustomResourcePolicy.fromStatements([
        new PolicyStatement({
          actions: ['lambda:InvokeFunction'],
          resources: [cleanUpFunction.functionArn],
        }),
      ]),
    });


  }
}

