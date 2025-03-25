# PoC to Prod

This folder includes resources and examples to assist organizations in transitioning Amazon Bedrock-powered applications from proof-of-concept (PoC) to production-ready solutions. It offers tools, best practices, and sample code to guide the effective implementation, testing, validation, and operationalization of Bedrock applications.

### Key Resources

- **[Inference Profiles](./inference-profiles/inference-profile-basics.ipynb):** This notebook provides a comprehensive guide to:
  1. **Create and Configure Inference Profiles**: Understand and apply profile options for optimal application performance.
  2. **Invoke Models with Inference Profiles**: Validate model invocation with real-time response streaming.
  3. **Operationalize Tagging and Cleanup**: Implement organized tagging for resource management and automate profile cleanup as needed.

- **[Bedrock Batch Orchestrator](./bedrock-batch-orchestrator/README.md)**: This CDK stack helps facilitate large-scale [batch inference](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html) tasks by automating end-to-end processing with Step Functions and EventBridge.

## Contributing
We welcome community contributions! Please ensure that your sample aligns with AWS best practices. Update the **Contents** section of this README file with a link to your sample, along with a brief description.
