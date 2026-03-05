# Prompt Caching — Converse API

Model-agnostic prompt caching examples using the Converse and ConverseStream APIs. The `cachePoint` syntax shown here works identically with Anthropic Claude, Amazon Nova, and any future Bedrock model that supports prompt caching.

## Notebooks

| # | Notebook | APIs | Description |
|---|---|---|---|
| 01 | [Message Content Caching](./notebooks/01_message_content_caching.ipynb) | Converse, ConverseStream | Simplified + multiple checkpoints, TTFT benchmark |
| 02 | [System Prompt Caching](./notebooks/02_system_prompt_caching.ipynb) | Converse, ConverseStream | Caching system prompts/persona definitions |
| 03 | [Tool Definition Caching](./notebooks/03_tool_definition_caching.ipynb) | Converse, ConverseStream | Caching tool schemas for agentic workflows |
| 04 | [Mixed TTL Caching](./notebooks/04_mixed_ttl_caching.ipynb) | Converse, ConverseStream | Mixed TTL (1h + 5m), `cacheDetails` per-TTL breakdown |
| 05 | [Tenant Isolation](./notebooks/05_tenant_isolation.ipynb) | Converse | SHA-256 hash prefix for per-tenant cache isolation |
| 06 | [LangChain Integration](./notebooks/06_langchain_integration.ipynb) | Converse (via LangChain) | `ChatBedrockConverse.create_cache_point()`, LCEL chains |

## Scripts

Standalone demo scripts in [scripts/](./scripts/) for automated validation. See [scripts/README.md](./scripts/README.md) for usage.

| Script | Caching Location | APIs Tested |
|---|---|---|
| `demo_message_content_caching.py` | User message content | ConverseStream, Converse |
| `demo_system_prompt_caching.py` | System prompt | ConverseStream, Converse |
| `demo_tool_definition_caching.py` | Tool definitions | ConverseStream, Converse |
| `demo_mixed_ttl_caching.py` | Mixed TTL (1h + 5m) | ConverseStream, Converse |

## ConverseStream Response Parsing

ConverseStream returns cache metrics in the `metadata` event at the end of the stream:

```python
for event in response["stream"]:
    if "contentBlockDelta" in event:
        text += event["contentBlockDelta"]["delta"].get("text", "")
    elif "metadata" in event:
        usage = event["metadata"]["usage"]
        # usage["cacheWriteInputTokens"]
        # usage["cacheReadInputTokens"]
```

The Converse (non-streaming) API returns usage directly in `response["usage"]`.

## Converse API Syntax

```python
# Message content caching
content = [
    {"text": "<static content>"},
    {"cachePoint": {"type": "default"}},
    {"text": "<user question>"}
]

# System prompt caching
system = [
    {"text": "<system prompt>"},
    {"cachePoint": {"type": "default"}}
]

# Tool definition caching
tools = [
    {"toolSpec": {"name": ..., "inputSchema": {"json": ...}}},
    {"cachePoint": {"type": "default"}}
]

# Mixed TTL
content = [
    {"text": "<core content>"},
    {"cachePoint": {"type": "default", "ttl": "1h"}},
    {"text": "<session content>"},
    {"cachePoint": {"type": "default", "ttl": "5m"}},
    {"text": "<question>"}
]
```

## Configuration

All notebooks and scripts default to:
- **Model**: `global.anthropic.claude-sonnet-4-6`
- **Region**: `us-west-2`
- **Profile**: `default`

Modify the constants at the top of each file to change these values. The `cachePoint` syntax works with any supported model — change `MODEL_ID` to use Nova or other supported models.
