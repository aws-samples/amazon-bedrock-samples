import { CfnOutput, Duration, RemovalPolicy, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import { bedrock } from "@cdklabs/generative-ai-cdk-constructs";
import { BlockPublicAccess, Bucket, IBucket } from "aws-cdk-lib/aws-s3";
import { Runtime, Code, Function, LayerVersion } from "aws-cdk-lib/aws-lambda";
import { CustomS3DataSource } from "../constructs/custom-s3-data-source";
import { join } from "path";
import { Effect, ManagedPolicy, Policy, PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam";
import { StringParameter } from "aws-cdk-lib/aws-ssm";
import { SSMParameterReader } from "./ssm-parameter-reader";

export interface BedrockStackProps extends StackProps {
  stageName: string;
  codePipelineName: string;
}

export class BedrockStack extends Stack {
  public knowledgeBaseId!: string; // Store the Knowledge Base ID
  public dataSourceId!: string;    // Store the Data Source ID
  private s3AccessPolicy!: Policy; // Store the S3 access policy as a class property

  constructor(scope: Construct, id: string, props: BedrockStackProps) {
    super(scope, id, props);

    // Create a Lambda execution role with basic execution permissions
    const customLambdaRole = new Role(this, "CustomChunkingLambdaRole", {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"), // Lambda service principal
      managedPolicies: [ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole")],
    });

    // Retrieve account number and region from environment variables
    const accountNumber = process.env.CDK_DEFAULT_ACCOUNT;
    const region = this.region;

    // Ensure account number and region are provided, otherwise throw an error
    if (!accountNumber || !region) {
      throw new Error("CDK_DEFAULT_ACCOUNT or AWS_REGION environment variable is not set");
    }

    // Set the foundation model ID
    const foundationModelID = "anthropic.claude-3-sonnet-20240229-v1:0";

    // Determine the appropriate S3 bucket name based on the stage (QA or Prod)
    let docBucketName = props?.stageName === "QA"
      ? "processed-data-source-bucket-533267284022-qa"
      : "processed-data-source-bucket-533267284022-prod";

    // Reference an existing S3 bucket by name
    const docBucket = Bucket.fromBucketName(this, "DocBucket", docBucketName);
    console.log("Processed Files S3 Data Source: ", docBucketName); // Log the selected bucket name


    // // Read the S3 bucket name from the SSM parameter store (the buckets are created as part of the data ingestion stack)
    // const docBucketName = StringParameter.fromStringParameterName(this, 'ProcessedS3BucketName', `/${props.codePipelineName}/${props.stageName}/processed-s3-data-source`).stringValue;

    // // Reference an existing S3 bucket by name
    // const docBucket = Bucket.fromBucketName(this, "DocBucket", docBucketName);

    // Create a new S3 bucket to store intermediate data
    const intermediateBucket = new Bucket(this, "IntermediateBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL, // Ensure no public access
      removalPolicy: RemovalPolicy.DESTROY, // Remove the bucket when the stack is deleted
      autoDeleteObjects: true, // Automatically delete objects when bucket is removed
    });

    // Initialize the S3 access policy with permissions to access specific S3 buckets
    this.s3AccessPolicy = new Policy(this, "AmazonBedrockS3PolicyForKnowledgeBase", {
      policyName: "AmazonBedrockS3PolicyForKnowledgeBase",
      statements: [
        new PolicyStatement({
          sid: "S3ListBucketStatement", // Allow listing objects in the bucket
          effect: Effect.ALLOW,
          actions: ["s3:ListBucket"],
          resources: [docBucket.bucketArn],
          conditions: { StringEquals: { "aws:ResourceAccount": accountNumber } },
        }),
        new PolicyStatement({
          sid: "S3GetObjectStatement", // Allow reading objects from buckets
          effect: Effect.ALLOW,
          actions: ["s3:GetObject"],
          resources: [
            docBucket.bucketArn, `${docBucket.bucketArn}/*`,
            intermediateBucket.bucketArn, `${intermediateBucket.bucketArn}/*`
          ],
          conditions: { StringEquals: { "aws:ResourceAccount": accountNumber } },
        }),
        new PolicyStatement({
          sid: "S3PutObjectStatement", // Allow writing objects to intermediate bucket
          effect: Effect.ALLOW,
          actions: ["s3:PutObject"],
          resources: [`${intermediateBucket.bucketArn}/*`],
          conditions: { StringEquals: { "aws:ResourceAccount": accountNumber } },
        }),
      ],
    });

    // Retrieve the custom Lambda package bucket name from the SSM parameter store
    let bedrockCustomLambdaBucketName: string;
    if (props.stageName === "QA") {
      bedrockCustomLambdaBucketName = StringParameter.valueForStringParameter(this, '/MultimodalRAG/PreQABucketSetupStage/lambda-package-bucket-name');
      console.log("Bedrock Custom Lambda Package Bucket Name: ", bedrockCustomLambdaBucketName); // Log the bucket name
    } else {
      bedrockCustomLambdaBucketName = StringParameter.valueForStringParameter(this, '/MultimodalRAG/PreProdBucketSetupStage/lambda-package-bucket-name');
      console.log("Bedrock Custom Lambda Package Bucket Name: ", bedrockCustomLambdaBucketName); // Log the bucket name
    }



    // Add logging to capture the parameter value
    new CfnOutput(this, 'BedrockCustomLambdaPackageBucketNameOutput', {
      value: bedrockCustomLambdaBucketName,
      description: 'The name of the S3 bucket for the custom Lambda package',
    });

    const bedrockCustomLambdaPackageBucket = Bucket.fromBucketName(this, 'BedrockCustomLambdaPackageBucket', bedrockCustomLambdaBucketName);


    // Create the Lambda function responsible for transforming data
    const transformationLambda = this.createTransformationLambda(customLambdaRole, bedrockCustomLambdaPackageBucket);

    // Configure policies and link the resources created above
    this.configurePolicies(transformationLambda, accountNumber, region, foundationModelID, docBucket, intermediateBucket);
  }

  // Method to create the Lambda function for data transformation
  private createTransformationLambda(customLambdaRole: Role, bedrockCustomLambdaPackageBucket: IBucket): Function {
    // const lambdaCodePath = join(__dirname, "..", "..", "src", "services", "tmp", "custom_chunking_lambda_package.zip");
    // console.log(`Using Lambda code from: ${lambdaCodePath}`);

    // Define the Lambda function with necessary properties
    const transformationLambda = new Function(this, "CustomChunkingLambda", {
      runtime: Runtime.PYTHON_3_12, // Use Python 3.12 runtime
      // code: Code.fromAsset(lambdaCodePath), // Reference the pre-packaged Lambda code
      code: Code.fromBucket(bedrockCustomLambdaPackageBucket, 'custom_chunking_lambda_package.zip'),
      handler: "custom_chunking_python.lambda_handler", // Lambda function handler
      role: customLambdaRole, // Assign the Lambda execution role
      timeout: Duration.minutes(15), // Set timeout to 15 minutes
      memorySize: 10240, // Allocate 10 GB memory
      layers: [
        LayerVersion.fromLayerVersionArn(
          this, "PillowLayer", `arn:aws:lambda:${this.region}:770693421928:layer:Klayers-p312-pillow:1`
        ),
      ],
    });

    return transformationLambda;
  }

  // Method to configure policies and link Lambda with other resources
  private configurePolicies(
    transformationLambda: Function, accountNumber: string, region: string, foundationModelID: string,
    docBucket: IBucket, intermediateBucket: Bucket
  ) {
    // Policy to allow invoking the Lambda function
    const lambdaInvokePolicy = new Policy(this, "AmazonBedrockLambdaPolicyForKnowledgeBase", {
      policyName: "AmazonBedrockLambdaPolicyForKnowledgeBase",
      statements: [
        new PolicyStatement({
          sid: "LambdaInvokeFunctionStatement",
          effect: Effect.ALLOW,
          actions: ["lambda:InvokeFunction"],
          resources: [`${transformationLambda.functionArn}:*`],
          conditions: { StringEquals: { "aws:ResourceAccount": accountNumber } },
        }),
      ],
    });

    // Policy to allow invoking Bedrock foundation models
    const foundationalModelInvokePolicy = new Policy(this, "AmazonBedrockFoundationalModelInvokePolicy", {
      policyName: "AmazonBedrockFoundationalModelInvokePolicy",
      statements: [
        new PolicyStatement({
          sid: "BedrockInvokeModelStatement",
          effect: Effect.ALLOW,
          actions: ["bedrock:InvokeModel"],
          resources: [`arn:aws:bedrock:${region}::foundation-model/${foundationModelID}`],
        }),
      ],
    });

    // Policy to allow retrieving Lambda layer versions
    const layerArn = `arn:aws:lambda:${region}:770693421928:layer:Klayers-p312-pillow:1`;
    const getLayerVersionPolicy = new Policy(this, "GetLayerVersionPolicy", {
      policyName: "GetLayerVersionPolicy",
      statements: [
        new PolicyStatement({
          sid: "GetLayerVersionStatement",
          effect: Effect.ALLOW,
          actions: ["lambda:GetLayerVersion"],
          resources: [layerArn],
        }),
      ],
    });

    // Attach policies to the Lambda function role
    transformationLambda.role?.attachInlinePolicy(lambdaInvokePolicy);
    transformationLambda.role?.attachInlinePolicy(this.s3AccessPolicy);
    transformationLambda.role?.attachInlinePolicy(foundationalModelInvokePolicy);
    transformationLambda.role?.attachInlinePolicy(getLayerVersionPolicy);

    // Create a KnowledgeBase and attach necessary policies
    const kb = new bedrock.KnowledgeBase(this, "KnowledgeBase", {
      embeddingsModel: bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
      instruction: "Use this knowledge base to answer questions about a wide range of topics.",
    });

    kb.role.attachInlinePolicy(lambdaInvokePolicy);
    kb.role.attachInlinePolicy(this.s3AccessPolicy);
    kb.role.attachInlinePolicy(foundationalModelInvokePolicy);

    // Create a custom data source linked to the knowledge base
    const kbS3DataSource = new CustomS3DataSource(this, "KBS3DataSource", {
      bucket: docBucket,
      knowledgeBase: kb,
      dataSourceName: "finance",
      chunkingStrategy: bedrock.ChunkingStrategy.NONE,
      intermediateBucket: intermediateBucket,
      transformationLambda: transformationLambda,
    });

    // Store the IDs for further reference
    this.knowledgeBaseId = kb.knowledgeBaseId;
    this.dataSourceId = kbS3DataSource.dataSourceId;
  }
}
