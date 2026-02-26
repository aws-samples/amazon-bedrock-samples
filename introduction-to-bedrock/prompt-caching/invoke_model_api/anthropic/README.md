# Prompt Caching — InvokeModel API (Anthropic Claude)

Prompt caching for Anthropic Claude models on Amazon Bedrock using the InvokeModel and InvokeModelWithResponseStream APIs with Anthropic's native `cache_control` syntax.

## Model IDs

| Model | Global Inference Endpoint |
|---|---|
| Claude Sonnet 4.6 (default) | `global.anthropic.claude-sonnet-4-6-v1:0` |
| Claude Opus 4.6 | `global.anthropic.claude-opus-4-6-v1:0` |
| Claude Haiku 4.5 | `global.anthropic.claude-haiku-4-5-20251001-v1:0` |

## Notebooks

| # | Notebook | APIs | Description |
|---|---|---|---|
| 01 | [Message Content Caching](./notebooks/01_message_content_caching.ipynb) | InvokeModel, InvokeModelWithResponseStream | Simplified + multiple checkpoints |
| 02 | [System Prompt Caching](./notebooks/02_system_prompt_caching.ipynb) | InvokeModel, InvokeModelWithResponseStream | Caching system prompts/persona definitions |
| 03 | [Tool Definition Caching](./notebooks/03_tool_definition_caching.ipynb) | InvokeModel, InvokeModelWithResponseStream | `cache_control` on last tool, schema format comparison |

## Scripts

Standalone test scripts in [scripts/](./scripts/) for automated validation. See [scripts/README.md](./scripts/README.md) for usage.

| Script | Caching Location | APIs Tested |
|---|---|---|
| `test_message_content_caching.py` | User message content | InvokeModelWithResponseStream, InvokeModel |
| `test_system_prompt_caching.py` | System prompt | InvokeModelWithResponseStream, InvokeModel |
| `test_tool_definition_caching.py` | Tool definitions | InvokeModelWithResponseStream, InvokeModel |
| `test_mixed_ttl_caching.py` | Mixed TTL (1h + 5m) | InvokeModelWithResponseStream, InvokeModel |

## Anthropic `cache_control` Syntax

```python
# Message content caching
content = [
    {"type": "text", "text": "<static content>", "cache_control": {"type": "ephemeral", "ttl": "5m"}},
    {"type": "text", "text": "<user question>"}
]

# System prompt caching
system = [
    {"type": "text", "text": "<system prompt>", "cache_control": {"type": "ephemeral", "ttl": "5m"}}
]

# Tool definition caching — cache_control on the last tool
tools = [
    {"name": ..., "input_schema": ...},
    {"name": ..., "input_schema": ..., "cache_control": {"type": "ephemeral", "ttl": "5m"}}
]
```

## Streaming Response Parsing

InvokeModelWithResponseStream returns cache metrics across multiple chunk types:

```python
for event in response["body"]:
    chunk = json.loads(event["chunk"]["bytes"])
    if chunk["type"] == "message_start":
        # chunk["message"]["usage"] → cache_creation_input_tokens, cache_read_input_tokens
    elif chunk["type"] == "message_delta":
        # chunk["usage"] → output_tokens
```

## Configuration

All notebooks and scripts default to:
- **Model**: `global.anthropic.claude-sonnet-4-6-v1:0`
- **Region**: `us-west-2`
- **Profile**: `default`
- **Cache TTL**: `5m`

Modify the constants at the top of each file to change these values.
