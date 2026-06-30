#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Validate an LLM answer against an AR guardrail with ApplyGuardrail.

Sends the question as a query-qualified block and the answer as a claim block, asserts that AR actually
ran (automatedReasoningPolicyUnits > 0), and prints the findings + aggregated result.

Usage:
    uv run validate_response.py --guardrail-id <ID> --guardrail-version 1 \
        --question "..." --answer "..." [--source OUTPUT] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402


def build_content(question: str | None, answer: str) -> list[dict]:
    content: list[dict] = []
    if question:
        content.append({"text": {"text": question, "qualifiers": ["query"]}})
    # The answer is the claim. (Default qualifier is guard_content, but we set it explicitly.)
    content.append({"text": {"text": answer, "qualifiers": ["guard_content"]}})
    return content


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--guardrail-id", required=True)
    p.add_argument("--guardrail-version", required=True)
    p.add_argument("--answer", required=True, help="The LLM answer (claim) to validate.")
    p.add_argument("--question", help="The user question (query context).")
    p.add_argument("--source", default="OUTPUT", choices=["OUTPUT", "INPUT"])
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    resp = ctx.call(
        "bedrock-runtime",
        "apply_guardrail",
        guardrailIdentifier=args.guardrail_id,
        guardrailVersion=args.guardrail_version,
        source=args.source,
        content=build_content(args.question, args.answer),
    )
    if args.dry_run:
        ar.emit(resp)
        return

    units = ar.assert_ar_ran(resp)  # raises if AR didn't run
    findings = ar.parse_findings(resp)
    ar.emit(
        {
            "automatedReasoningPolicyUnits": units,
            "aggregatedResult": ar.aggregate_result(findings),
            "findings": [{"result": f.result, "detail": f.raw} for f in findings],
        }
    )


if __name__ == "__main__":
    main()
