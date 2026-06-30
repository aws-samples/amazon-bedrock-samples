#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3>=1.35.0"]
# ///
"""Audit an AR policy: fetch QUALITY_REPORT + FIDELITY_REPORT + POLICY_DEFINITION from the latest
COMPLETED build and print a prioritized findings report.

This is heuristic and defensive about response shapes (the exact asset JSON can evolve): it surfaces
whatever quality/fidelity signals are present and falls back to dumping the raw asset if keys differ.

Usage:
    uv run audit_policy.py --policy-arn <ARN> [--build-workflow-id <id>] [--json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import ar_common as ar  # noqa: E402


def _dig(d: dict, *keys):
    """Return the first present key's value from a dict (case-insensitive-ish)."""
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return None


def summarize_quality(q: dict) -> list[str]:
    """q is the unwrapped qualityReport payload."""
    issues: list[str] = []
    pairs = [
        ("conflicting rules", _dig(q, "conflictingRules", "conflicting_rules")),
        ("unused variables", _dig(q, "unusedVariables", "unused_variables")),
        ("unused type values", _dig(q, "unusedTypeValues", "unused_type_values")),
        ("disjoint rule sets", _dig(q, "disjointRuleSets", "disjoint_rule_sets")),
    ]
    for label, val in pairs:
        if val:
            n = len(val) if isinstance(val, list) else val
            sev = "HIGH" if "conflict" in label else "MEDIUM"
            issues.append(f"[{sev}] {label}: {n}")
    # disjoint rule sets are informational, not always a problem — note separately
    return issues


def summarize_fidelity(f: dict) -> list[str]:
    """f is the unwrapped fidelityReport payload (may be empty if not produced)."""
    out: list[str] = []
    if not f:
        return ["not produced for this build type (e.g. REFINE_POLICY) — run GENERATE_FIDELITY_REPORT"]
    cov = _dig(f, "coverageScore", "coverage_score", "coverage")
    acc = _dig(f, "accuracyScore", "accuracy_score", "accuracy")
    if cov is not None:
        flag = " [LOW]" if isinstance(cov, (int, float)) and cov < 0.7 else ""
        out.append(f"coverage score: {cov}{flag}")
    if acc is not None:
        flag = " [LOW]" if isinstance(acc, (int, float)) and acc < 0.7 else ""
        out.append(f"accuracy score: {acc}{flag}")
    return out or ["present, but no coverage/accuracy scores found"]


def summarize_definition(d: dict) -> list[str]:
    """d is the unwrapped policyDefinition payload."""
    out: list[str] = []
    rules = d.get("rules", []) if isinstance(d, dict) else []
    variables = d.get("variables", []) if isinstance(d, dict) else []
    types = d.get("types", []) if isinstance(d, dict) else []
    out.append(f"rules: {len(rules)}, variables: {len(variables)}, types: {len(types)}")

    # Heuristic for the docs' "bare assertion" trap: a rule that unconditionally fixes a
    # BOOLEAN value (e.g. `(= eligible true)` or a lone `eligible`) becomes an always-true
    # axiom and causes spurious IMPOSSIBLE results. Arithmetic definitions like
    # `(= revenueGrowthRate (* ...))` are legitimate and must NOT be flagged.
    bool_names = {v.get("name") for v in variables if isinstance(v, dict) and v.get("type") == "BOOL"}
    suspicious: list[str] = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        expr = " ".join((r.get("expression") or "").split())
        if "=>" in expr:
            continue  # conditional — fine
        # lone boolean var, or (= boolVar true/false), or (not boolVar)
        flagged = (
            expr in bool_names
            or any(expr == f"(= {b} true)" or expr == f"(= {b} false)" or expr == f"(not {b})" for b in bool_names)
        )
        if flagged:
            suspicious.append(str(r.get("id", "?")))
    if suspicious:
        out.append(f"[HIGH] bare boolean assertions (always-true axioms): {len(suspicious)} -> {', '.join(suspicious[:10])}")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy-arn", required=True)
    p.add_argument("--build-workflow-id", help="Defaults to the latest COMPLETED build.")
    p.add_argument("--json", action="store_true", help="Emit raw assets as JSON instead of a summary.")
    ar.add_common_args(p)
    args = p.parse_args()

    ctx = ar.ctx_from_args(args)
    build_id = args.build_workflow_id or ar.latest_completed_build_id(ctx, args.policy_arn)
    if not build_id:
        sys.exit("No COMPLETED build workflow found. Build the policy first.")

    # Each asset is optional and nested under buildWorkflowAssets.<key>.
    quality_raw = ar.try_get_result_asset(ctx, args.policy_arn, build_id, "QUALITY_REPORT")
    fidelity_raw = ar.try_get_result_asset(ctx, args.policy_arn, build_id, "FIDELITY_REPORT")
    definition_raw = ar.try_get_result_asset(ctx, args.policy_arn, build_id, "POLICY_DEFINITION")

    if args.json or args.dry_run:
        ar.emit({"quality": quality_raw, "fidelity": fidelity_raw, "definition": definition_raw})
        return

    quality = ar.asset_payload(quality_raw, "qualityReport") if quality_raw else {}
    fidelity = ar.asset_payload(fidelity_raw, "fidelityReport") if fidelity_raw else {}
    definition = ar.asset_payload(definition_raw, "policyDefinition") if definition_raw else {}

    print(f"# AR Policy Audit\nPolicy: {args.policy_arn}\nBuild:  {build_id}\n")
    print("## Definition")
    for line in summarize_definition(definition):
        print(f"- {line}")
    print("\n## Quality report")
    qissues = summarize_quality(quality)
    print("\n".join(f"- {i}" for i in qissues) if qissues else "- no structural issues detected")
    print("\n## Fidelity report")
    for line in summarize_fidelity(fidelity):
        print(f"- {line}")
    print("\n## Recommendation")
    print("- Fix HIGH items first (conflicts/bare assertions cause IMPOSSIBLE), then variable noise.")
    print("- Apply fixes with ar-policy-debugger (annotations), then re-audit.")


if __name__ == "__main__":
    main()
