# RLVR for Tool-Calling with BFCL

Train a model to make better function calls using Reinforcement Fine-Tuning on the [Berkeley Function Calling Leaderboard (BFCL)](https://gorilla.cs.berkeley.edu/leaderboard.html) dataset.

## Overview

This use-case walks through the full RLVR workflow for tool-calling:

1. **Curate** — Pull BFCL data from HuggingFace, format for Bedrock RFT
2. **Evaluate locally** — Test the reward function against sample data before deploying
3. **Deploy** — Package and deploy the reward function as an AWS Lambda
4. **Train** — Kick off an RFT job on Amazon Bedrock (you handle this part)

The reward function scores model outputs by parsing function calls at the AST level and comparing function names, parameter names, and parameter values against ground truth — with type coercion so `"5"` matches `5`.

## Prerequisites

- Python 3.10+
- AWS account with Bedrock access
- S3 bucket for training data
- IAM permissions for Lambda, IAM, Bedrock, and S3

## Quick Start

### Install llm-eval-kit

```bash
git clone <this-repo>
cd llm-eval-kit
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,datasets,deploy]"
```

### Run the notebook

Open `bfcl_tool_calling_rft.ipynb` and follow along. The notebook covers:

| Step | What happens |
|------|-------------|
| 0. Install deps | Installs datasets, boto3 |
| 1. Data prep | Pulls BFCL from HuggingFace, formats for RFT, uploads to S3 |
| 2. Local eval | Runs the tool_call grader over sample data to verify scoring |
| 3. Deploy Lambda | Packages reward function and deploys to AWS Lambda |
| 4. Test Lambda | Invokes the deployed function with test payloads |
| 5. Start RFT job | Creates a Bedrock model customization job |
| 6. Monitor | Checks job status |

## How the Reward Function Works

The reward function (`bfcl_tool_call_rew_func.py`) receives batches of samples from Bedrock during training:

```json
[
  {
    "id": "bfcl_train_0",
    "messages": [
      {"role": "user", "content": "Calculate the area of a triangle..."},
      {"role": "assistant", "content": "calculate_area(base=10, height=5)"}
    ],
    "metadata": {
      "ground_truth": ["calculate_area(base=10, height=5)"]
    }
  }
]
```

It returns scores:

```json
[
  {
    "id": "bfcl_train_0",
    "aggregate_reward_score": 1.0,
    "reward_components": {"tool_call_accuracy": 1.0}
  }
]
```

### Scoring breakdown (per function call)

| Component | Weight | What it checks |
|-----------|--------|---------------|
| Function name | 33% | Did the model call the right function? |
| Parameter names | 33% | Did it use the correct parameter names? |
| Parameter values | 34% | Are the values correct (with type coercion)? |

Multiple calls are averaged. Missing or extra calls score 0 for unmatched positions.

## Files

```
use-cases/bfcl-tool-calling/
├── README.md                      # This file
└── bfcl_tool_calling_rft.ipynb    # End-to-end notebook

reward-functions/
└── bfcl_tool_call_rew_func.py     # Lambda reward function (standalone, no deps)
```

## Dataset: BFCL v3

The [BFCL dataset](https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard) contains ~2,000 samples across categories:

| File | Description | Samples |
|------|-------------|---------|
| `BFCL_v3_simple.json` | Single function calls | 400 |
| `BFCL_v3_multiple.json` | Choose from multiple functions | 200 |
| `BFCL_v3_parallel.json` | Multiple calls needed | 200 |
| `BFCL_v3_exec_simple.json` | Executable simple calls | 100 |
| `BFCL_v3_live_simple.json` | Real-world API calls | varies |

The notebook uses `BFCL_v3_exec_simple.json` by default since it has ground truth function calls included. You can swap to other files by changing the `BFCL_FILE` config.

## Adapting for Your Use Case

To use a different dataset or scoring logic:

1. Write a new reward function following the Lambda contract (receives list, returns list with `id` and `aggregate_reward_score`)
2. Place it in `reward-functions/`
3. Update the notebook's config section to point to your function and data

## Resources

- [llm-eval-kit README](../../../../llm-eval-kit/README.md) — Full SDK documentation
- [BFCL Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [Bedrock RFT docs](https://docs.aws.amazon.com/bedrock/latest/userguide/reinforcement-fine-tuning.html)
- [BFCL Paper](https://arxiv.org/abs/2402.15671)
