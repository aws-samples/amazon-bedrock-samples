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
| Anthropic Claude | Opus 4.6/4.5/4.1/4, Sonnet 4.6/4.5/4, 3.7 Sonnet, 3.5 Haiku, 3.5 Sonnet v2 | Yes (`cachePoint`) | Yes (`cache_control`) |
| Amazon Nova | Micro, Lite, Pro, Premier, 2 Lite | Yes (`cachePoint`) | Yes (Nova-native format) |

### Not yet supported

| Model Family | Notes |
|---|---|
| Meta Llama 4 (Scout, Maverick) | Not listed in prompt caching supported models |
| Mistral (Large, Ministral) | Not listed in prompt caching supported models |
| DeepSeek (V3.2, R1) | Not listed in prompt caching supported models |
| OpenAI GPT OSS (20B, 120B) | Open-weight (Apache 2.0), supports Converse API, but not listed in prompt caching docs |

Check the [official supported models page](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) for the latest updates.

## Token Thresholds

Each cache checkpoint must meet the model's minimum token threshold:

| Model | Threshold |
|---|---|
| Claude Sonnet 4.6 | 2,048 tokens |
| Claude Opus 4.6 | 4,096 tokens |
| Claude Haiku 4.5 | 4,096 tokens |
| Nova Micro | 1,536 tokens |
| Nova Lite | 1,536 tokens |
| Nova 2 Lite | 1,536 tokens |
| Nova Pro | 1,024 tokens |

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
- Python 3.9+ with `boto3 >= 1.35.76`
- AWS credentials configured (default profile or environment variables)

## Additional Resources

- [Amazon Bedrock Prompt Caching documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
- [Bedrock pricing — prompt caching](https://aws.amazon.com/bedrock/pricing/)
