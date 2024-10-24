Here’s how to set up and start the project

### Prerequisites
1. **Node.js**: Ensure you have Node.js installed. You can download it from [nodejs.org](https://nodejs.org).
2. **AWS CDK**: Install the AWS CDK CLI globally, if you don’t have it already:
   ```bash
   npm install -g aws-cdk
   ```

### Installation
1. **Navigate to the Project Folder**: Open your terminal or command prompt and navigate to the project folder.
   ```bash
   cd path/to/RAG-PIPELINE-WITH-CICD
   ```

2. **Install Dependencies**: 
   The `package.json` file contains the dependencies. Use the following command to install them:
   ```bash
   npm install
   ```


### Troubleshooting Tips
- If the CDK CLI prompts for credentials, make sure you have the AWS CLI configured with:
   ```bash
   aws configure
   ```

- If you encounter TypeScript issues, ensure the TypeScript compiler is installed:
   ```bash
   npm install -D typescript
   ```

This setup will get your AWS CDK project running. 