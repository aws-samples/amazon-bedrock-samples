# Prompt Caching — Amazon Nova Models

Prompt caching for Amazon Nova models on Bedrock.

## Notebook

| Notebook | Description |
|---|---|
| [prompt_caching_with_nova_models.ipynb](./prompt_caching_with_nova_models.ipynb) | Getting started with prompt caching using Amazon Nova models |

## Converse API Syntax

The Converse API `cachePoint` syntax is **identical across all model families**, including Nova:

```python
content = [
    {"text": "<static content>"},
    {"cachePoint": {"type": "default"}},
    {"text": "<user question>"}
]
```

For more Converse API examples (system prompts, tools, mixed TTL, streaming), see [converse_api/](../converse_api/).

For Anthropic-specific InvokeModel syntax, see [invoke_model_api/anthropic/](../invoke_model_api/anthropic/).

## Additional Resources

- [Amazon Bedrock Prompt Caching documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
