# InvokeModel API — Amazon Nova

Prompt caching examples for Amazon Nova models using the InvokeModel API. Nova uses `cachePoint` blocks in its native request format — the same syntax the Converse API uses across all model families.

## Notebook

| Notebook | Description |
|---|---|
| [01_nova_invoke_model_caching.ipynb](./notebooks/01_nova_invoke_model_caching.ipynb) | Document Q&A with cache points on system prompt and message content |

## Nova Cache Syntax (InvokeModel)

```python
native_request = {
    "system": [
        {"text": "<system prompt>", "cachePoint": {"type": "default"}}
    ],
    "messages": [
        {
            "role": "user",
            "content": [
                {"text": "<document>", "cachePoint": {"type": "default"}},
                {"text": "<user question>"}
            ]
        }
    ],
    "inferenceConfig": {"max_new_tokens": 300, "temperature": 0.7}
}

response = bedrock.invoke_model(
    body=json.dumps(native_request),
    modelId="us.amazon.nova-lite-v1:0"
)
```

## Prerequisites

- Python 3.9+
- `pip install -r ../../requirements.txt`
- AWS credentials configured
- Access to Amazon Nova models on Bedrock

## Additional Resources

- [Amazon Bedrock Prompt Caching documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
- For model-agnostic Converse API examples, see [converse_api/](../../converse_api/)
- For Anthropic-specific InvokeModel syntax, see [anthropic/](../anthropic/)
