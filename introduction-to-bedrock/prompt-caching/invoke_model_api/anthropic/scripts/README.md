# InvokeModel API Test Scripts (Anthropic)

Standalone Python scripts for automated validation of prompt caching behavior using the InvokeModel and InvokeModelWithResponseStream APIs with Anthropic Claude's `cache_control` syntax. Each script tests cache write on the first request and cache read on the second, printing PASSED or FAILED for each API.

## Scripts

| Script | What it tests |
|---|---|
| `test_message_content_caching.py` | Caching user message content (simplified + multiple checkpoint modes) |
| `test_system_prompt_caching.py` | Caching system prompts |
| `test_tool_definition_caching.py` | Caching tool/function definitions |
| `test_mixed_ttl_caching.py` | Mixed TTL checkpoints (1h + 5m) via multiple `cache_control` blocks |

## How to Run

```bash
# Message content caching — simplified mode (default)
python test_message_content_caching.py

# Message content caching — multiple checkpoints
python test_message_content_caching.py --mode multiple

# System prompt caching
python test_system_prompt_caching.py

# Tool definition caching
python test_tool_definition_caching.py

# Mixed TTL caching
python test_mixed_ttl_caching.py
```

## Configuration

Each script has configuration constants at the top:

```python
MODEL_ID = "global.anthropic.claude-sonnet-4-6-v1:0"
AWS_PROFILE = "default"
AWS_REGION = "us-west-2"
CACHE_TTL = "5m"
```

Modify these values as needed before running.

## Requirements

- Python 3.9+
- `boto3 >= 1.35.76`
- AWS credentials configured for the specified profile
- Access to the specified model on Amazon Bedrock

## Interpreting Results

Each test function prints PASSED or FAILED:

- **PASSED**: First request showed cache activity (write or read), second request showed cache read
- **FAILED**: Cache was not written or not read as expected

The summary at the end lists all API results:

```
SUMMARY (simplified mode)
============================================================
✓ InvokeModelWithResponseStream: PASSED
✓ InvokeModel: PASSED
```

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| All tests FAILED | Model access not enabled | Enable the model in the Bedrock console |
| `cache_creation_input_tokens = 0` on first request | Content below token threshold | Ensure content exceeds 1,024 tokens for Sonnet 4.6 |
| `cache_read_input_tokens = 0` on second request | Cache expired or content changed | Run requests quickly; verify content is identical |
| `AccessDeniedException` | Profile lacks Bedrock permissions | Check IAM permissions for `bedrock-runtime:InvokeModel` |
