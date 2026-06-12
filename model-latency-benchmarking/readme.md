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
   - Some models (for example Amazon Nova and the latest Claude models) reject `temperature` and `topP` in the same request, so the tool sends only one. Set `INFERENCE_SAMPLING` in the configuration cell to `'temperature'` (default) or `'topP'` to choose which one.

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

Prompt caching lets you cache a static prompt prefix (the `cached_context`) so that repeated requests reusing that prefix skip reprocessing it. This reduces Time to First Token and lowers input-token cost for workloads that send a large, stable context on every request, such as a system prompt, a long instruction set, a knowledge document, or few-shot examples.

How it works in the tool:

- Set `prompt_caching` to `true` on a scenario and supply the static prefix in `cached_context`. The tool places the cached context first and inserts a cache checkpoint immediately after it, then appends your `text_prompt`.
- Set `cache_ttl` to `5m` (default) or `1h` to control how long the cache entry lives. The `1h` extended TTL is only supported on Anthropic models; other models use the default `5m`.
- When `prompt_caching` is `false` or absent, the request is sent without any cache checkpoint, exactly as before.
- If `prompt_caching` is `true` but `cached_context` is empty, or `cache_ttl` is not `5m` or `1h`, the tool records an error status with a descriptive message for that invocation and continues with the remaining scenarios.

A global prompt caching toggle in the configuration cell sets the default. A scenario's `prompt_caching` field always wins when present.

### Supported models, regions, and minimum token thresholds

Prompt caching is available for **on-demand invocation only**. It is not supported with provisioned throughput.

Caching only triggers when the cached prefix meets or exceeds a per-model minimum token threshold. Below the threshold, the request still runs but no cache write or read occurs. The thresholds and the list of caching-capable models and supported regions change over time, so confirm the current values in the [Amazon Bedrock prompt caching documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) for your model and region before authoring a dataset.

The models demonstrated by this tool and their minimum cached-prefix token thresholds:

| Model | Inference profile ID | Minimum tokens to trigger caching |
|-------|----------------------|-----------------------------------|
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 4,096 |
| Amazon Nova Pro | `us.amazon.nova-pro-v1:0` | 1,000 (1K) |

Only reference caching-capable models for any scenario where `prompt_caching` is `true`.

## Cache metrics in output

When prompt caching is active, the tool captures cache usage from the Converse response and adds these columns to the per-invocation output. When a response omits the cache fields, the tool records zero for both token counts so the output schema stays stable.

| Metric | Description |
|--------|-------------|
| `cache_read_input_tokens` | Input tokens served from cache on a cache hit. `0` when absent. |
| `cache_write_input_tokens` | Input tokens written to the cache when it is populated. `0` when absent. |
| `Cache_Hit_Rate` | Fraction of input tokens served from cache, derived per invocation as cache read input tokens divided by total input tokens. |

The analysis cell reports Time to First Token for cached invocations separately from uncached invocations and includes the cache token columns and Cache_Hit_Rate in the aggregated output. All existing per-invocation columns and aggregated metrics are preserved; the cache columns are added rather than replacing anything.

## Caching demonstration dataset

The repository ships a dedicated demo dataset, `caching-demo-prompts-for-benchmarking.jsonl`, alongside the sample dataset. Its purpose is to let you observe the cache effect directly without authoring your own data.

It demonstrates prompt caching on two models, Claude Haiku 4.5 and Amazon Nova Pro. For each model it pairs a cached scenario (`prompt_caching: true`) with a matching uncached baseline (`prompt_caching: false`) that uses the same model and prompt, so cached and uncached results compare directly. The cached context in each scenario meets the per-model minimum token threshold so caching is triggered.

To run it, point the dataset file path in the configuration cell at `caching-demo-prompts-for-benchmarking.jsonl` and run the notebook as usual. No tool changes are needed. After the run, compare the cached scenarios against their baselines: cached invocations should report non-zero `cache_read_input_tokens` or `cache_write_input_tokens` and lower Time to First Token. Because the first request pays the cache write cost while later requests benefit from the read, run enough invocations per scenario to warm the cache before comparing cache-hit latency.

## Important notes

- Test results depend on your specific prompts and setup
- For best results, run tests for at least 24 hours during your busiest times
- More test runs give more accurate results

## Need help?
Check the comments in the code for more detailed information about each part of the framework or open an issue.
