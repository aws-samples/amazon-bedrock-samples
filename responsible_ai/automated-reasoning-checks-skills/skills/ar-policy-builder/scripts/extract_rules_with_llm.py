#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Optional pre-processing: use an LLM (via Bedrock Converse) to rewrite a narrative document
as clean logical rules before ingesting it into an AR policy.

Two modes (the prompts come straight from the Bedrock User Guide):
  --mode plain      -> a numbered list of if-then rules (good for short, clear docs)
  --mode structured -> JSON with conditions/consequence/confidence/ruleType/source + an
                       `ambiguities` array, plus auto-generated sanity (boundary) rules.

ALWAYS review the output against the original document before using it as AR source text.

Usage:
    uv run extract_rules_with_llm.py --file handbook.txt --mode structured \
        [--model-id anthropic.claude-3-5-sonnet-20241022-v2:0] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402

DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

PLAIN_PROMPT = """You are a logical reasoning expert. Your task is to analyze the provided source text \
and rewrite it as a set of clear, logical rules using if-then statements.

Instructions:
1. Extract the key relationships, conditions, and outcomes from the source text.
2. Convert these into logical implications using "if-then" format.
3. Use clear, precise language that captures the original meaning.
4. Number each rule for easy reference.
5. Ensure rules are mutually consistent and non-contradictory.

Format:
- Rule [N]: If [condition], then [consequence].
- Use "and" to combine multiple conditions.
- Use "or" for alternative conditions.
- Include negations when relevant: If not [condition], then [consequence].

Source Text:
{source}"""

STRUCTURED_PROMPT = """You are a logical reasoning expert. Extract formal logical rules from the provided text.

Output Format:
For each rule, provide:
- Rule ID: [unique identifier]
- Conditions: [ALL preconditions - preserve compound conditions with AND/OR/NOT]
- Consequence: [the outcome/action]
- Confidence: [high/medium/low based on text clarity]
- Source Reference: [quote or paraphrase from source]
- Rule Type: [explicit/implicit/sanity]

Critical Guidelines:
1. PRESERVE ALL CONDITIONS: Do not drop or simplify conditions.
2. PRESERVE LOGICAL OPERATORS: Maintain AND, OR, NOT relationships exactly.
3. PRESERVE QUANTIFIERS: Keep "all", "any", "at least", numeric thresholds.
4. PRESERVE EXCEPTIONS: Include "unless", "except when" clauses.
5. Make implicit conditions explicit only when clearly implied by context.
6. Use consistent terminology across rules.
7. Flag ambiguities such as unclear, incomplete, or contradictory statements.
8. Add sanity rules for common-sense constraints:
   - Numeric ranges (e.g., "age must be between 0 and 150")
   - Temporal constraints (e.g., "start date must be before end date")
   - Physical limits (e.g., "quantity cannot be negative")
   - Mutual exclusivity (e.g., "status cannot be both active and inactive")

Output Requirements:
- Produce final JSON only (no text or markdown).
- Use the following JSON keys:
  - "rules" for the rules array
  - "ambiguities" for the ambiguities array

Source Text:
{source}"""


def read_source(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        sys.exit("PDF input: extract text first (e.g. with pypdf), then pass a .txt/.md file.")
    return path.read_text(errors="replace")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", required=True, help="Text/markdown source document.")
    p.add_argument("--mode", choices=["plain", "structured"], default="structured")
    p.add_argument("--model-id", default=DEFAULT_MODEL, help=f"Bedrock model id (default: {DEFAULT_MODEL}).")
    p.add_argument("--max-tokens", type=int, default=4000)
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    source = read_source(Path(args.file))
    if len(source) > 50_000:
        sys.stderr.write(f"[warn] source is {len(source)} chars; AR ingest limit is 50,000. Consider splitting.\n")
    template = PLAIN_PROMPT if args.mode == "plain" else STRUCTURED_PROMPT
    prompt = template.format(source=source)

    params = {
        "modelId": args.model_id,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": args.max_tokens, "temperature": 0},
    }
    resp = ctx.call("bedrock-runtime", "converse", **params)
    if args.dry_run:
        return
    text = ""
    for block in resp.get("output", {}).get("message", {}).get("content", []):
        text += block.get("text", "")
    print(text)
    sys.stderr.write("\n[reminder] Review this against the original document before using as AR source.\n")


if __name__ == "__main__":
    main()
