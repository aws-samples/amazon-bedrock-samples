# LLM Latency Benchmarking Framework

This tool helps you benchmark model latency metrics for Large Language Models (LLMs) on Amazon Bedrock. Openly available benchmarks may not reflect your specific dataset or task. By using this framework, you can benchmark models for your own use case, helping you select the most suitable model.

## What it does

1. Measures how quickly the model starts responding (Time to First Token)
2. Measures how many tokens the model generates per second (Output Tokens Per Second)
3. Tests different model versions and settings
4. Handles multiple API calls at once
5. Supports optional, opt-in prompt caching per scenario and captures cache metrics
6. Provides analysis and statistics that you can use to take decisions

## Prerequisites

- AWS account with Amazon Bedrock access.
- Model access enabled for every model you reference. The latest models (Claude Opus 4.5, Claude Sonnet 4.5, Claude Haiku 4.5, Claude 3.7 Sonnet, and Amazon Nova Pro) require model access to be enabled in the account and region where you run the benchmark. Enable access in the Amazon Bedrock console under Model access before running the tool.
- A recent `boto3` version. The notebook declares a minimum required `boto3` version that supports the latest Bedrock models and prompt caching through the Converse API. If your installed version is below that minimum, the notebook reports the requirement before invoking any model. Upgrade with `pip install -U boto3`.
- A file with your prompts in `JSONL` format (see the required format below).
- Access to the AWS region you want to use.

## How to use it

1. Set up your test:
   - Put your prompts in a JSONL file
   - Change settings in the first code cell (like file paths and test details)
   - Some models reject `temperature` and `topP` together; set `INFERENCE_SAMPLING` in the configuration cell to `'temperature'` (default) or `'topP'`.

2. Run the code:
   - All cells will run automatically
   - Results will be saved in your chosen folder
   - You'll get a log file with details about what happened

3. Check your results:
   - Look at the CSV files for detailed metrics
   - Review the final analysis for overall performance

## Required Dataset Format

Your input JSONL file should contain one JSON object per line. The following fields are supported. Existing datasets keep working unchanged: the caching fields are optional and additive, and a scenario without them behaves exactly as before.

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `text_prompt` | string | yes | - | The user prompt. |
| `expected_output_tokens` | int | no | 100 | Maximum output tokens for the request. |
| `task_type` | string | no | - | Currently supports `Text-Generation`. |
| `model_id` | string | yes | - | Model ID or cross-region inference profile ID. |
| `region` | string | yes | - | AWS region where the model is invoked. |
| `inference_profile` | string | no | `optimized` | Latency setting passed via Converse `performanceConfig`, either `optimized` or `standard`. |
| `prompt_caching` | bool | no | `false` | Opt-in prompt caching for the scenario. When omitted, caching is off. |
| `cache_ttl` | string | no | `5m` | Cache checkpoint time-to-live. Allowed values are `5m` and `1h`. The `1h` extended TTL is only supported on Anthropic models; on other models the tool falls back to the default `5m`. |
| `cached_context` | string | no | none | The long, static prompt prefix to cache. Required when `prompt_caching` is `true`. |

```json
{
    "text_prompt": "Your question or instruction here",
    "expected_output_tokens": 50,
    "task_type": "Text-Generation",
    "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "region": "us-east-1",
    "inference_profile": "optimized"
}
```

#### Example entries from the test dataset:

```json
{"text_prompt": "Explain the concept of machine learning in simple terms.", "expected_output_tokens": 50, "task_type": "Text-Generation", "model_id": "us.anthropic.claude-opus-4-5-20251101-v1:0", "region": "us-east-1", "inference_profile": "standard"}
{"text_prompt": "Explain the concept of machine learning in simple terms.", "expected_output_tokens": 50, "task_type": "Text-Generation", "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "region": "us-east-1", "inference_profile": "optimized"}
{"text_prompt": "Explain the concept of machine learning in simple terms.", "expected_output_tokens": 50, "task_type": "Text-Generation", "model_id": "us.amazon.nova-pro-v1:0", "region": "us-east-1", "inference_profile": "standard"}
```

#### Example entry with prompt caching enabled:

```json
{"text_prompt": "Using the reference document above, summarize the key points.", "expected_output_tokens": 200, "task_type": "Text-Generation", "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0", "region": "us-east-1", "inference_profile": "standard", "prompt_caching": true, "cache_ttl": "5m", "cached_context": "<your long static context here>"}
```

## Prompt caching

Prompt caching reuses a static prompt prefix (`cached_context`) across requests to lower Time to First Token and input-token cost. Set `prompt_caching` to `true` and provide the prefix in `cached_context`; the optional fields are described in the dataset table above. Caching is off by default, so existing datasets are unaffected.

- Available for on-demand invocation only.
- Caching only triggers when the cached prefix meets the model's minimum token threshold (for example, 4,096 tokens for Claude Haiku 4.5). Confirm current thresholds and supported models in the [Amazon Bedrock prompt caching documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html).
- Output adds `cache_read_input_tokens`, `cache_write_input_tokens`, and `Cache_Hit_Rate`, and the analysis reports Time to First Token for cached and uncached calls separately. Existing columns are unchanged.

To see it in action, point the dataset path at `caching-demo-prompts-for-benchmarking.jsonl`, which pairs cached and uncached scenarios for Claude Haiku 4.5 and Amazon Nova Pro.

## Important notes

- Test results depend on your specific prompts and setup
- For best results, run tests for at least 24 hours during your busiest times
- More test runs give more accurate results

## Need help?
Check the comments in the code for more detailed information about each part of the framework or open an issue.
