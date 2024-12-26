# LLM Latency Benchmarking Framework

This tool helps you benchmark model latency metrics for Large Language Models (LLMs) on Amazon Bedrock. Openly available benchmarks may not reflect your specific dataset or task. By using this framework, you can benchmark models for your own use case, helping you select the most suitable model.

## What it does

1. Measures how quickly the model starts responding (Time to First Token)
2. Measures how many tokens the model generates per second (Output Tokens Per Second)
3. Tests different model versions and settings
4. Handles multiple API calls at once
5. Provides analysis and statistics that you can use to take decisions

## How to use it

1. Make sure you have:
   - AWS account with Amazon Bedrock access
   - A file with your prompts (in `JSONL format` check required format below)
   - Access to the AWS region you want to use

2. Set up your test:
   - Put your prompts in a JSONL file
   - Change settings in the first code cell (like file paths and test details)

3. Run the code:
   - All cells will run automatically
   - Results will be saved in your chosen folder
   - You'll get a log file with details about what happened

4. Check your results:
   - Look at the CSV files for detailed metrics
   - Review the final analysis for overall performance

## Required Dataset Format

Your input JSONL file should contain one JSON object per line with the following fields:

```json
{
    "text_prompt": "Your question or instruction here",
    "expected_output_tokens": 50,  // number of tokens expected in output
    "task_type": "Text-Generation",  // currently supports Text-Generation
    "model_id": "us.meta.llama3-1-70b-instruct-v1:0",  // model identifier
    "region": "us-west-2", // region where you want to benchmark model latency metrics
    "inference_profile": "optimized"  // optimization setting 
}
```

#### Example entries from the test dataset:

```json
{"text_prompt": "Summarize the key features of cloud computing in one sentence.", "expected_output_tokens": 50, "task_type": "Text-Generation", "model_id": "us.meta.llama3-1-70b-instruct-v1:0", "region": "us-east-2", "inference_profile": "optimized"}
{"text_prompt": "Explain the concept of machine learning in simple terms.", "expected_output_tokens": 50, "task_type": "Text-Generation", "model_id": "us.anthropic.claude-3-5-haiku-20241022-v1:0", "region": "us-east-2", "inference_profile": "optimized"}
{"text_prompt": "Explain the concept of machine learning in simple terms.", "expected_output_tokens": 50, "task_type": "Text-Generation", "model_id": "us.anthropic.claude-3-5-haiku-20241022-v1:0", "region": "us-east-2", "inference_profile": "standard"}
```

## Important notes

- Test results depend on your specific prompts and setup
- For best results, run tests for at least 24 hours during your busiest times
- More test runs give more accurate results

## Need help?
Check the comments in the code for more detailed information about each part of the framework or open an issue.