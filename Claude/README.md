## Claude 3 Features and New Messages API

The text completions API for Claude is now in legacy mode and it is recommended to migrate to 
the new Messages API. The Messages API is backward compatible with current Claude Models on Bedrock and requires that a modified JSON body be passed to the invoke methods.

The multi-modal capability of Claude 3 allows for input of not only text but also an image that you can 
ask questions about.

This folder contains examples of the new Messages API and compares it with the legacy Text completions API. In addition, we provide an example of the new mulimodal capability of the Claude 3 model.

For Claude 3 Integration with Bedrock please visit [Claude on Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html)

Please see [Claude 3](https://www.anthropic.com/news/claude-3-family) for more details on Claude 3 from Anthropic. Please follow this link for more details on the [Messages API](https://docs.anthropic.com/claude/reference/messages_post).


## Contents

- [Single and Mult-turn text generation with Messages API](./Claude-MessagesAPI-Examples.ipynb) - Examples to illustrate the new Claude Messages API
- [Claude3-Sonnet Multi-Modal input](./Claude3-Sonnet-Multimodal-Example.ipynb) - Example to illustrate the multmodal capabilties of Claude 3-Sonnet



## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.