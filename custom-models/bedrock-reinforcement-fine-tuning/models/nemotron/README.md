# Codeforces Competitive Programming — Nemotron Nano 3 30B RFT

This use case demonstrates reinforcement fine-tuning (RFT) of **NVIDIA Nemotron Nano 3 30B** on competitive programming problems from the [Codeforces-Python-Submissions](https://huggingface.co/datasets/MatrixStudio/Codeforces-Python-Submissions) dataset.

## Overview

The model learns to write correct Python solutions to Codeforces problems through reinforcement learning. A Lambda reward function executes the model's generated code against test cases and provides a score based on how many tests pass.

## Files

| File | Description |
|------|-------------|
| `nemotron_codeforces_rft.ipynb` | Main notebook — end-to-end RFT workflow |
| `../../reward-functions/codeforces_rew_func.py` | Lambda reward function that scores code by running test cases |

## Reward Function

The reward function (`codeforces_rew_func.py`) scores model responses as follows:

- **1.0** — All test cases pass
- **Partial credit** — Fraction of test cases passed (e.g., 3/5 = 0.6)
- **0.1** — Code was extracted but no tests passed (format reward)
- **0.0** — No Python code could be extracted from the response

## Data Preprocessing

The notebook handles the full data pipeline:

1. Downloads the dataset from HuggingFace (~621K rows)
2. Filters for accepted solutions on problems rated 800–1600
3. Deduplicates by problem (one solution per unique problem)
4. Builds structured prompts from problem descriptions, I/O specs, and examples
5. Exports as OpenAI-compatible JSONL with test cases in `metadata`

## Prerequisites

- AWS credentials with IAM, Lambda, and Bedrock permissions
- Bedrock model access for `nvidia.nemotron-nano-3-30b`
- Python 3.11+
