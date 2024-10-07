# Function Calling (Tool usage)
With function calling, we can provide LLMs with descriptions of tools and functions it can use. An LLM is able to intelligently decide based on user query when and how to use those tools to help answer questions and complete tasks.

This repository contains examples and use-cases to get you started with Function Calling on Amazon Bedrock

## Contents
This folder contains information on how to use function calling with Amazon Bedrock capabilities.
The examples are divided as following:
* [Function calling with the Converse API](function_calling_with_converse): examples on how to set up function call with the [Bedrock Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
* [Function calling with Invoke Model](function_calling_with_invoke): examples on how to set up function call with the [Bedrock invoke model API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html)
* [Function calling with Bedrock Agents Return of Control functionality](return_of_control): In this folder we provide an example on how to make Bedrock Agents behave like the native LLM function calling using the [return of control](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-returncontrol.html) functionality
* [Function calling using LangChain tool binding functionality](tool_binding): in this folder we provide an example on how to provide tools descriptions to [LangChain framework](https://blog.langchain.dev/tool-calling-with-langchain/) using the `bind_tools` functionality 

## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
