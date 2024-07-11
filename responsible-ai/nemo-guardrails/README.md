# NeMo Guardrails example

This is an example for implementing safeguards with NeMo Guardrails. [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) is an open-source toolkit for adding programmable guardrails to LLM-based conversational systems.

There is also [Guardrails for Amazon Bedrock](https://aws.amazon.com/bedrock/guardrails/) a native feature within Amazon Bedrock.

## Overview

NeMo Guardrails enables developers to add programmable safeguards to their LLM powered applications. The toolkit provides different mechanism to protect again common LLM vulnerabilities. Common vulnerabilities include jailbreaks, hallucination and toxcicity among others. By implementing different types of guardrails (or rails for short) these risks can be mitigated.

Programmable guardrails can be applied at the input, dialog, retrieval, execution or output level. This way developers can control each part of the application and interaction with the LLM, as well as if applicable interaction with knowledge bases and external tools or functions. Guardrails can reject or alter operations at the different levels. NeMo comes with certain built in guardrails, but also allows the creation of custom guardrails. Multiple guardrails can be implemented for holistic protection agains common vulnerabilities.

An example for an input rail could be to check if the user prompt is trying to jailbreak the system. Before calling the LLM with the actual user prompt first the prompt itself can be evaluated with a prompt by the LLM to see if it is harmful and should be rejected. You can find more examples and implementations below.

## Setup and config

Make sure to install `boto3`, `os` and all other required packages.

For detailed information on how to install `nemoguardrails` see their [Installation Guide](https://github.com/NVIDIA/NeMo-Guardrails/blob/develop/docs/getting_started/installation-guide.md).

```
python -m pip install nemoguardrails
```

NeMo expects certain configuration to be in place. At the very least a config.yml with the model to be used is needed. Additional you want to configue different rails. See [Guardrails Configuration](https://github.com/NVIDIA/NeMo-Guardrails/tree/develop?tab=readme-ov-file#guardrails-configuration) in the official repository.

## Contents

- [Hello World](hello-world/hello-world.py) - Minimal example of using NeMo Guardrails without any actual rails
- [Input Rail Jailbreak Check](input-rail-jailbreak-check/input-rail-jailbreak-check.py) - Minimal example of using NeMo Guardrails with an input check rail to prevent a simple jailbreak scenario
- [Output Rail Response Moderation](output-rail-response-moderation/output-rail-response-moderation.py) - Minimal example of using NeMo Guardrails with an output check rail to moderate generated responses

## Further content

- [NeMo Guardrails lab in Amazon Bedrock workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/a4bdb007-5600-4368-81c5-ff5b4154f518/en-US/110-guardrails/111-guardrails-nemo/) - Experiment wit NeMo Guardrails in this notebook to further uncover how they contribute to the safety, reliability, and ethical handling of LLMs
