---
name: ar-policy-reviewer
description: >
  Inspects an extracted Amazon Bedrock Automated Reasoning (AR) policy for quality and fidelity before
  testing or deployment. Fetches the POLICY_DEFINITION, QUALITY_REPORT, and FIDELITY_REPORT build assets
  and flags unused/duplicate variables, bare assertions, conflicting rules, disjoint rule sets, and low
  coverage/accuracy scores, producing a prioritized fix list.

  Use this skill whenever the user wants to:
  - "Review / audit / sanity-check my Automated Reasoning policy"
  - "Check the quality report" or "fidelity report" for an AR policy
  - Understand whether an extracted policy is good before testing or deploying
  - Inspect a policy's rules and variables after a build completes
  Trigger right after ar-policy-builder finishes a build, or whenever a policy ARN needs a health check.
license: Apache-2.0
---

# AR Policy Reviewer

## Overview
After a build completes, the extracted policy is **not guaranteed correct** — extraction is
non-deterministic. This skill pulls the build's **quality report** (structural issues) and **fidelity
report** (how faithfully the policy represents the source) plus the **policy definition**, and turns them
into a prioritized list of fixes. It diagnoses; `ar-policy-debugger` applies the fixes.

**Reference:** `../../shared/references/ar-api-context.md` (asset types), `findings-reference.md`,
`smtlib-rules.md` (what good rules look like).

## When to use
- Immediately after `ar-policy-builder` builds or merges a policy.
- Before testing or deploying, as a health check.

## Key directives
1. **Pull the build assets:** `POLICY_DEFINITION` + `QUALITY_REPORT` are produced by every build.
   ⚠️ `FIDELITY_REPORT` is **not** auto-produced by `INGEST_CONTENT`/`REFINE_POLICY` — run a
   `GENERATE_FIDELITY_REPORT` build to get it. `audit_policy.py` tolerates a missing one and says so.
2. **Triage by severity:** conflicting rules + bare assertions (cause `IMPOSSIBLE`) first; then
   unused/duplicate variables (cause `TRANSLATION_AMBIGUOUS`); then low fidelity scores.
3. **Don't auto-edit.** Report findings and recommend specific annotations; hand off to `ar-policy-debugger`.
4. The fidelity report is **SME-friendly** — share its grounding (rule → source statement) with the
   document author to confirm intent without reading formal logic.

## What to flag
- **Conflicting rules** — contradictory conclusions for the same conditions → `IMPOSSIBLE` for all
  involved inputs. Merge or delete one.
- **Bare assertions** — rules not in if-then form (e.g. `(= eligible true)`) → unexpected `IMPOSSIBLE`.
  Rewrite as implications (acceptable only for boundary conditions like `(>= balance 0)`).
- **Unused variables** — referenced by no rule → noise → `TRANSLATION_AMBIGUOUS`. Delete or add rules.
- **Duplicate/near-duplicate variables** (`tenureMonths` vs `monthsOfService`) → inconsistent
  translation. Merge.
- **Unused type values** — enum values no rule references. Add rules or remove the value.
- **Disjoint rule sets** — groups sharing no variables. Fine if domains are independent; otherwise a
  signal that connecting variables are missing.
- **Low coverage score** — source content not captured (look for source statements with 0 rules/0 vars).
- **Low per-rule accuracy** — rule may misrepresent the source; compare to its grounding statements.

## Workflow
```
# Audit everything at once (fetches assets, prints a structured report)
uv run scripts/audit_policy.py --policy-arn <ARN>

# Or fetch a single asset to inspect manually
uv run scripts/get_assets.py --policy-arn <ARN> --asset-type QUALITY_REPORT
uv run scripts/get_assets.py --policy-arn <ARN> --asset-type POLICY_DEFINITION
uv run scripts/get_assets.py --policy-arn <ARN> --asset-type FIDELITY_REPORT   # only after GENERATE_FIDELITY_REPORT
```
`audit_policy.py` resolves the latest COMPLETED build automatically (override with `--build-workflow-id`).

## Resources
- `scripts/get_assets.py` — fetch one build asset (`--asset-type`, valid types listed in `--help`).
- `scripts/audit_policy.py` — fetch + summarize quality/fidelity/definition into a prioritized report.
- `../../shared/references/ar-api-context.md`, `findings-reference.md`, `smtlib-rules.md`.
