# Responsible AI Samples 

This repository contains pre-built examples to help customers get started with Responsible AI on Amazon Bedrock.

## Contents

### [bedrock-guardrails](./bedrock-guardrails)

Examples highlighting how Amazon Bedrock Guardrails can be used to implement safeguards for generative AI applications.

| Notebook | Description |
|----------|-------------|
| [guardrails-api.ipynb](./bedrock-guardrails/guardrails-api.ipynb) | Create, update, version, and test guardrails using the Bedrock Python SDK. Covers topic policies, content filters, word filters, PII detection, and contextual grounding. |
| [bedrock_guardrails_apply_guardrail_api.ipynb](./bedrock-guardrails/bedrock_guardrails_apply_guardrail_api.ipynb) | Use the ApplyGuardrail API to evaluate text independently of model invocation. Demonstrates topic-based blocking and contextual grounding for hallucination detection. |
| [Apply_Guardrail_with_Streaming_and_Long_Context.ipynb](./bedrock-guardrails/Apply_Guardrail_with_Streaming_and_Long_Context.ipynb) | Apply guardrails with streaming responses and long-context documents, including chunked evaluation strategies. |
| [Guardrails with LangChain.ipynb](./bedrock-guardrails/Guardrails%20with%20LangChain.ipynb) | Integrate Bedrock Guardrails with LangChain chat chains and tool-calling agents. |
| [guardrails_image_content_filters_api.ipynb](./bedrock-guardrails/guardrails_image_content_filters_api.ipynb) | Configure and test image content filters to detect harmful visual content (violence, hate, etc.) using the Converse API and ApplyGuardrail API. Also demonstrates guardrails with image generation models. |

### [tdd-guardrail](./tdd-guardrail)

A test-driven development approach to iteratively building and improving guardrails using automated evaluations.

| Notebook | Description |
|----------|-------------|
| [testing_refactoring_guardrails.ipynb](./tdd-guardrail/testing_refactoring_guardrails.ipynb) | Build a guardrail, create a test suite, evaluate results, then use an LLM to iteratively refine the guardrail's denied topics based on test failures — demonstrating measurable improvement over iterations. |

## Contributing

We welcome community contributions! Please ensure your sample aligns with [AWS best practices](https://aws.amazon.com/architecture/well-architected/), and please update the **Contents** section of this README file with a link to your sample, along with a description.
