## Migration from Text Completions API to the new Messages API

The text completions API for Claude is now in legacy mode and it is recommended to migrate to 
the new Messages API. The Messages API is backward compatible with current Claude Models on Bedrock and requires that a modified JSON body be passed to the invoke methods.

This folder contains examples of the new Messages API and compares it with the legacy Text completions API.

## Contents

- [Single and Mult-turn text generation with Messages API](./Claude-MessagesAPI-Examples.ipynb) - Examples to illustrate the new Claude Messages API


## Contributing

We welcome community contributions! Please ensure your sample aligns with AWS [best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.