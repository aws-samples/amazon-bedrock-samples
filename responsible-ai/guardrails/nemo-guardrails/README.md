# NeMo Guardrails example

This is an example for implementing safeguards with NeMo Guardrails. [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) is an open-source toolkit for adding programmable guardrails to LLM-based conversational systems.

There is also [Guardrails for Amazon Bedrock](https://aws.amazon.com/bedrock/guardrails/) a native feature within Amazon Bedrock.

## Setup

Make sure to install `boto3`, `json` and all other required packages.

```
python -m pip install boto3
```

For detailed information on how to install `nemoguardrails` see their [Installation Guide](https://github.com/NVIDIA/NeMo-Guardrails/blob/develop/docs/getting_started/installation-guide.md).

## Contents

- [Hello World](hello-world.py) - Minimal example of using NeMo Guardrails without any actual rails
