# Amazon Bedrock Prompt Flows

[Amazon Bedrock Prompt Flows](https://aws.amazon.com/bedrock/prompt-flows/) is a visual builder tool that allows developers to quickly create, test, and deploy workflows by seamlessly linking foundation models (FMs), prompts, and various AWS services and tools together. It is designed to accelerate the development process of generative AI applications by providing an intuitive, low-code/no-code environment.

Key features of Amazon Bedrock Prompt Flows:

1. **Visual Builder**: Developers can use a drag-and-drop interface to create flows by connecting different components (nodes) such as prompts, AWS services, and business logic.

2. **Testing and Iteration**: Prompt Flows allows developers to test their flows directly in the console for faster iteration and refinement.

3. **Versioning and Deployment**: Once a flow is ready, developers can version it, enabling easy rollback and the ability to conduct A/B testing by splitting traffic between different versions. Versioned flows can be integrated into generative AI applications through API calls.

4. **Collaboration**: Prompt Flows is available in Amazon Bedrock Studio, an SSO-enabled web interface, allowing developers across an organization to experiment and collaborate on workflow creation.

5. **Integration with AWS Services**: Developers can incorporate various AWS services, such as Amazon Lex, into their flows by linking them as nodes within the visual builder.

6. **Code Hooks**: Prompt Flows supports the use of Lambda functions (code hooks) to process the output from nodes within the flow.


## Contents

This repository contains examples of usage for Amazon Bedrock Prompt Flow:
* [Getting Started](Getting_started_with_Prompt_Management_Flows.ipynb): Basic example of how to get started with Amazon Bedrock Prompt Flows


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
