# **RAG Pipeline with CI/CD**

This project implements a robust **CI/CD pipeline** for an end-to-end **Retrieval-Augmented Generation (RAG)** system powered by **Amazon Bedrock Knowledge Bases** and **AWS CDK**. The pipeline automates the deployment and management of key AWS resources critical for the RAG architecture. At its core, the solution integrates **Amazon Bedrock's foundation models and Knowledge Bases** with essential AWS services such as S3, Lambda, DynamoDB, and Step Functions to manage data ingestion, transformation, and retrieval. Through predefined stages spanning **QA and Production environments**, raw data flows through transformation pipelines, where it is processed, evaluated, and optimized for enhanced knowledge retrieval.

The solution leverages **AWS CodePipeline** to streamline multi-stage deployments, automating infrastructure updates from code commits to production rollouts. RAG evaluations act as critical checkpoints to ensure system integrity by validating both **data and code changes**. Promotions from QA to Production are only allowed after successful RAG evaluations, ensuring that only validated changes make it to production. The architecture offers **fine-grained control** over the deployment lifecycle, with **manual/automatic approvals** and **state machine-driven workflows** managing critical decisions. By combining **CI/CD best practices with RAG workflows**, the project provides a scalable and automated framework to continuously deploy GenAI-powered applications, leveraging real-time external knowledge. This solution accelerates time-to-market by providing a production-ready framework for enterprises building AI-powered applications with Amazon Bedrock.

---

## **cdk.json: Configuration for Your CDK Project**

The **`cdk.json`** file defines the configuration settings and context values for the CDK project. It ensures the CDK framework knows how to execute the app and what environment-specific settings to apply. Below is the content of the `cdk.json` file:

```json
{
    "app": "npx ts-node bin/main.ts",
    "context": {
        "defaultProject": "rag-project",
        "defaultRegion": "us-east-1",
        "defaultAccount": "xxxxxxx",
        "defaultEnvironment": "QA",
        "prodAccount": "xxxxxxx",
        "prodRegion": "us-west-2",
        "bedrockModelID": "anthropic.claude-3-haiku-20240307-v1:0",
        "@aws-cdk/customresources:installLatestAwsSdkDefault": false
    }
}
```

### **Explanation of Key Fields in `cdk.json`:**

- **`app`**: Specifies the command to run the CDK app. Here, **`npx ts-node bin/main.ts`** runs the TypeScript entry point directly using `ts-node`.
- **`context`**: Stores environment-specific configurations and variables:
  - **`defaultProject`**: Name of the project
  - **`defaultRegion`**: The AWS region for QA deployments 
  - **`defaultAccount`**: The AWS account ID used for deployments.
  - **`defaultEnvironment`**: Indicates the default environment as **QA**.
  - **`prodAccount`** and **`prodRegion`**: AWS account and region for production 
  - **`bedrockModelID`**: The foundation model ID used in Amazon Bedrock.
  - **`installLatestAwsSdkDefault`**: Controls whether the latest AWS SDK is installed for custom resources.

The `cdk.json` file ensures the CDK app deploys correctly across different stages by centralizing environment variables and configurations. This makes the pipeline flexible and easy to extend for multiple environments (e.g., QA, Prod).

---

## **Prerequisites**

Ensure the following tools are installed:

1. **Node.js**: [Download here](https://nodejs.org).
2. **AWS CDK CLI**: Install the AWS CDK CLI globally:
   ```bash
   npm install -g aws-cdk
   ```
3. **AWS CLI**: [Install and configure](https://aws.amazon.com/cli/) the AWS CLI.

---

## **Installation**

1. **Navigate to the Project Folder**:
   ```bash
   cd path/to/RAG-PIPELINE-WITH-CICD
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Build the Project**:
   ```bash
   npm run build
   ```

4. **Synthesize the CDK App**:
   ```bash
   npx cdk synth
   ```

5. **Deploy the CDK App**:
   ```bash
   npx cdk deploy --all
   ```

---

## **Project Structure**

- **`bin/`**: Contains the entry point for the CDK app.
- **`lib/`**: Contains the core CDK stack definitions.
  - **`constructs/`**: Custom reusable components.
  - **`stacks/`**: Defines the various AWS resources.
  - **`stages/`**: Pipeline stages (e.g., QA, Prod).
- **`src/`**: Lambda function source code.
- **`cdk.json`**: CDK configuration file.
- **`package.json`**: Node.js dependencies and scripts.
- **`tsconfig.json`**: TypeScript configuration.

---

## **Troubleshooting Tips**

- **AWS CLI Credentials**: Ensure AWS credentials are configured:
   ```bash
   aws configure
   ```
- **TypeScript Issues**: Install TypeScript if needed:
   ```bash
   npm install -D typescript
   ```
- **Permissions Errors**: Verify IAM permissions for your user or role.

---

## **Useful Commands**

- **Build**: `npm run build`
- **Synthesize**: `npx cdk synth`
- **Deploy**: `npx cdk deploy`
- **Destroy**: `npx cdk destroy`

---

This RAG pipeline enables fast and efficient management of GenAI applications, ensuring smooth integration of data and code changes into production with the power of **Amazon Bedrock** and AWS CDK.