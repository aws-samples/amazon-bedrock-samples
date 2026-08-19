# Prompt Caching in Amazon Bedrock

Prompt caching stores portions of your conversation context so that subsequent requests skip reprocessing cached tokens, reducing Time-To-First-Token (TTFT) and input token costs.

## Directory Structure

| Folder | Description |
|---|---|
| [converse_api/](./converse_api/) | Model-agnostic `cachePoint` examples — Converse + ConverseStream APIs |
| [invoke_model_api/](./invoke_model_api/) | Model-family-specific examples — InvokeModel + InvokeModelWithResponseStream APIs |

## Model Support Status

### Supported

| Model Family | Models | Converse API | InvokeModel API |
|---|---|---|---|
| Anthropic Claude | Opus 4.6/4.5/4.1/4, Sonnet 4.6/4.5/4, Haiku 4.5, 3.7 Sonnet, 3.5 Haiku, 3.5 Sonnet v2 | Yes (`cachePoint`) | Yes (`cache_control`) |
| Amazon Nova | Micro, Lite, Pro, Premier, 2 Lite | Yes (`cachePoint`) | Yes (Nova-native format) |

### Not yet supported

| Model Family | Models |
|---|---|
| Meta Llama 4 | Scout, Maverick |
| Mistral | Large, Ministral |
| DeepSeek | V3.2, R1 |
| OpenAI GPT OSS | 20B, 120B |

Check the [official supported models page](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) for the latest updates.

## Token Thresholds

Each cache checkpoint must meet the model's minimum token threshold:

| Model | Threshold |
|---|---|
| Claude Sonnet 4.6 | 2,048 tokens |
| Claude Opus 4.6 | 4,096 tokens |
| Claude Sonnet 4.5 | 1,024 tokens |
| Claude Opus 4.5 | 4,096 tokens |
| Claude Haiku 4.5 | 4,096 tokens |
| Claude 3.7 Sonnet | 1,024 tokens |
| Claude 3.5 Sonnet v2 | 1,024 tokens |
| Claude 3.5 Haiku | 2,048 tokens |
| Nova Micro | 1,536 tokens |
| Nova Lite | 1,536 tokens |
| Nova 2 Lite | 1,536 tokens |
| Nova Pro | 1,024 tokens |
| Nova Premier | 1,024 tokens |

## TTL Support

All models default to a **5-minute** cache TTL. The following models also support a **1-hour** TTL:

| Model | 5m TTL | 1h TTL |
|---|---|---|
| Claude Haiku 4.5 | Yes | Yes |
| Claude Sonnet 4.5 | Yes | Yes |
| Claude Opus 4.5 | Yes | Yes |
| Claude Sonnet 4.6 | Yes | Yes |
| Claude Opus 4.6 | Yes | Yes |

When mixing TTLs in a single request, longer TTL checkpoints must appear **before** shorter ones (e.g., a `1h` cache point before a `5m` cache point). See the mixed TTL notebooks and scripts for working examples:

- `converse_api/notebooks/04_mixed_ttl_caching.ipynb`
- `converse_api/scripts/demo_mixed_ttl_caching.py`
- `invoke_model_api/anthropic/scripts/demo_mixed_ttl_caching.py`

## Simplified Cache Management (Claude Models)

Claude models support simplified cache management: you can place a single `cachePoint` (or `cache_control`) marker, and Bedrock automatically checks for cache hits on all prefixes up to approximately 20 content blocks before that marker. This means you don't need to manually place multiple cache checkpoints to get cache hits on earlier portions of your conversation.

## Converse API vs InvokeModel API

The **Converse API** `cachePoint` syntax is identical across all model families. Differences only appear in the **InvokeModel API**, where each model family uses its native request format.

| Feature | Converse API (all models) | InvokeModel API (Anthropic) |
|---|---|---|
| Cache marker | `{"cachePoint": {"type": "default"}}` | `"cache_control": {"type": "ephemeral", "ttl": "5m"}` |
| Placement | Standalone content block after cached content | Inside the content block being cached |
| TTL support | `{"cachePoint": {"type": "default", "ttl": "1h"}}` | `"ttl"` field inside `cache_control` |
| TTL ordering | Longer TTL checkpoints must appear before shorter ones (e.g., `1h` before `5m`) | Same constraint |
| `cacheDetails` response | Yes | No |
| Usage key format | `cacheWriteInputTokens` | `cache_creation_input_tokens` |

## Prerequisites

- AWS account with Amazon Bedrock access
- Model access enabled for the target model
- Python 3.9+ with dependencies: `pip install -r requirements.txt`
- AWS credentials configured (default profile or environment variables)

## Additional Resources

- [Amazon Bedrock Prompt Caching documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
- [Bedrock pricing — prompt caching](https://aws.amazon.com/bedrock/pricing/)
