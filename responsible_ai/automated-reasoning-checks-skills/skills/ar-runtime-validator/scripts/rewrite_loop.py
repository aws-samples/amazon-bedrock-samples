#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.40.0"]
# ///
"""Iterative rewrite loop (Valid@N) for AR-validated answers.

Validate -> on a non-VALID worst finding, render the matching rewrite template with the finding's rules
-> regenerate via Converse -> re-validate. Repeat up to --max-iter. Logs each iteration's result.

TOO_COMPLEX and TRANSLATION_AMBIGUOUS short-circuit (they need user action, not blind rewriting).

Usage:
    uv run rewrite_loop.py --guardrail-id <ID> --guardrail-version 1 \
        --question "..." --answer "<initial>" --model-id <id> [--max-iter 5] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402

DEFAULT_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

# Minimal inline templates (the SKILL's references/rewrite-templates.md has the full prose set).
TEMPLATES = {
    "INVALID": (
        "The previous answer CONTRADICTS the policy. Rewrite it to comply.\n"
        "Question: {question}\nRejected answer: {answer}\nContradicting rules: {rules}\n"
        "Reply ONLY with the corrected answer."
    ),
    "SATISFIABLE": (
        "The previous answer is correct only under some conditions. Make it complete.\n"
        "Question: {question}\nAnswer: {answer}\nRelevant rules/scenarios: {rules}\n"
        "Rewrite it to state the missing conditions. Reply ONLY with the corrected answer."
    ),
    "IMPOSSIBLE": (
        "The premises create a contradiction under the policy.\n"
        "Question: {question}\nAnswer: {answer}\nConflicting rules: {rules}\n"
        "If the contradiction is in the user's input, ask one clarifying question; otherwise rewrite to avoid it."
    ),
}
SHORT_CIRCUIT = {"TOO_COMPLEX", "TRANSLATION_AMBIGUOUS", "NO_TRANSLATIONS"}


def validate(ctx: ar.ARContext, gid: str, gver: str, question: str, answer: str) -> tuple[str, list[ar.Finding], dict]:
    resp = ctx.call(
        "bedrock-runtime",
        "apply_guardrail",
        guardrailIdentifier=gid,
        guardrailVersion=gver,
        source="OUTPUT",
        content=[
            {"text": {"text": question, "qualifiers": ["query"]}},
            {"text": {"text": answer, "qualifiers": ["guard_content"]}},
        ],
    )
    if ctx.dry_run:
        return "VALID", [], resp
    ar.assert_ar_ran(resp)
    findings = ar.parse_findings(resp)
    return ar.aggregate_result(findings), findings, resp


def rules_text(findings: list[ar.Finding], result: str) -> str:
    """Pull a readable rule list from the worst finding of the given result."""
    for f in findings:
        if f.result == result:
            key = ar._result_to_key(result)
            body = f.raw.get(key, {})
            rules = body.get("contradictingRules") or body.get("supportingRules") or []
            return "; ".join(r.get("identifier", str(r)) for r in rules) or "(no rules listed)"
    return "(no rules)"


def regenerate(ctx: ar.ARContext, model_id: str, prompt: str) -> str:
    resp = ctx.call(
        "bedrock-runtime",
        "converse",
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 500, "temperature": 0},
    )
    if ctx.dry_run:
        return "(dry-run rewrite)"
    out = ""
    for block in resp.get("output", {}).get("message", {}).get("content", []):
        out += block.get("text", "")
    return out.strip()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--guardrail-id", required=True)
    p.add_argument("--guardrail-version", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--answer", required=True, help="Initial answer to validate/rewrite.")
    p.add_argument("--model-id", default=DEFAULT_MODEL)
    p.add_argument("--max-iter", type=int, default=5)
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    answer = args.answer
    log: list[dict] = []

    for n in range(1, args.max_iter + 1):
        result, findings, _ = validate(ctx, args.guardrail_id, args.guardrail_version, args.question, answer)
        log.append({"iteration": n, "result": result, "answer": answer})
        sys.stderr.write(f"[iter {n}] {result}\n")
        if result == "VALID":
            break
        if result in SHORT_CIRCUIT:
            sys.stderr.write(f"[stop] {result} needs user action, not rewriting. See SKILL guidance.\n")
            break
        template = TEMPLATES.get(result)
        if not template:
            break
        prompt = template.format(question=args.question, answer=answer, rules=rules_text(findings, result))
        answer = regenerate(ctx, args.model_id, prompt)
        if ctx.dry_run:
            break

    ar.emit({"finalResult": log[-1]["result"] if log else "UNKNOWN", "finalAnswer": answer, "n": len(log), "log": log})


if __name__ == "__main__":
    main()
