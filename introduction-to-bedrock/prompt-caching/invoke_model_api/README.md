# Prompt Caching — InvokeModel API

Model-family-specific prompt caching examples using the InvokeModel and InvokeModelWithResponseStream APIs. Each model family uses its own native request format for cache control.

## Model Families

| Folder | Model Family | Cache Syntax |
|---|---|---|
| [anthropic/](./anthropic/) | Anthropic Claude | `"cache_control": {"type": "ephemeral", "ttl": "5m"}` |
| [nova/](./nova/) | Amazon Nova | `"cachePoint": {"type": "default"}` |

## InvokeModelWithResponseStream Response Parsing

Streaming cache metrics are split across multiple chunk types:

```python
for event in response["body"]:
    chunk = json.loads(event["chunk"]["bytes"])

    if chunk["type"] == "message_start":
        # Initial usage: cache_creation_input_tokens, cache_read_input_tokens, input_tokens
        usage = chunk["message"]["usage"]

    elif chunk["type"] == "content_block_delta":
        # Response text
        text += chunk["delta"].get("text", "")

    elif chunk["type"] == "message_delta":
        # Final usage: output_tokens
        usage.update(chunk["usage"])
```

The InvokeModel (non-streaming) API returns all usage in `response["usage"]`.

## InvokeModel vs Converse

For model-agnostic examples using the Converse API (`cachePoint` syntax), see [converse_api/](../converse_api/). The Converse API is recommended for new applications since its syntax is identical across all model families.

| Feature | InvokeModel API | Converse API |
|---|---|---|
| Syntax | Model-family-specific | Model-agnostic `cachePoint` |
| `cacheDetails` per-TTL breakdown | No | Yes |
| Streaming usage location | `message_start` + `message_delta` chunks | `metadata` event |
| Usage key format | `cache_creation_input_tokens` | `cacheWriteInputTokens` |
