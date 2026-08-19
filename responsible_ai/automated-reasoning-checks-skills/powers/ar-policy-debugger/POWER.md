---
name: "ar-policy-debugger"
displayName: "Automated Reasoning: Debugger"
description: "Diagnoses failing Amazon Bedrock Automated Reasoning (AR) tests and repairs policies using annotations. Classifies the failure by result type, applies the two-step (translate vs. validate) triage, and fixes issues via REFINE_POLICY annotations, RESOLVE_POLICY_AMBIGUITIES, or ITERATIVELY_REFINE_POLICY."
keywords: ["debugger", "automated reasoning", "bedrock", "guardrail", "AR policy", "annotations", "test"]
author: "Adewale Akinfaderin"
---

<!-- GENERATED from skills/ar-policy-debugger/SKILL.md by scripts/sync_powers.py. Do not edit by hand; edit the SKILL.md and re-run the script. -->

# AR Policy Debugger

## Overview
This is the **iterative refinement** skill, the equivalent of AWS's documented "Kiro CLI" policy-repair
workflow. It loads the policy definition, quality report, and failing-test findings; explains *why* a test
fails using the **two-step model**; and applies targeted **annotations** so you don't hand-edit formal logic.

**⚠️ Golden rule: check the translation first.** The SMT validation step is mathematically sound. When a
result is wrong, look at the finding's `premises`/`claims`/`confidence`:
- Right variables, right values, wrong result → the issue is in your **rules**.
- Wrong/missing variable assignment → the issue is in your **variable descriptions** (cheaper, safer to fix).

**Reference:** `references/debugging-decisions.md` (the full decision table + annotation recipes),
`../../shared/references/findings-reference.md`, `smtlib-rules.md`, `ar-api-context.md`.

## Diagnosis by result type
| Actual result | First suspect | Fix |
|---|---|---|
| `TRANSLATION_AMBIGUOUS` | overlapping/vague variables | improve descriptions, merge overlaps (or last-resort lower threshold) |
| `NO_TRANSLATIONS` | missing variables / off-topic | add variables, or filter upstream |
| `TOO_COMPLEX` | policy/input too big, nonlinear arithmetic | shorten input, split policy, simplify rules |
| `IMPOSSIBLE` | contradictory input OR conflicting rules / bare assertions | fix input, or merge/delete conflicts; rewrite bare assertions |
| `VALID` but expected `INVALID` | missing/too-permissive rule | add or tighten a rule |
| `INVALID` but expected `VALID` | too-restrictive or misextracted rule | relax/fix the rule |
| `SATISFIABLE` but expected `VALID` | response incomplete OR extra rules | add missing conditions, or remove irrelevant rules |

## Key directives
1. **Translate-first triage** before touching rules.
2. **Prefer annotations over manual edits.** Use `addRuleFromNaturalLanguage` to describe a rule in plain
   English and let AR compile it. After REFINE_POLICY, review proposed changes, then `UpdateAutomatedReasoningPolicy`.
3. **Fix conflicts/bare assertions first.** They cause `IMPOSSIBLE` for all involved inputs.
4. **Re-review and re-test after every change** (hand back to reviewer/tester). Refinement is iterative.
5. **Build-slot cap is handled for you.** A policy allows at most 2 build workflows per pool; the scripts
   free a slot automatically (deleting the oldest terminal build) before each refine build.

## Workflow
```
# Apply a set of annotations (REFINE_POLICY). Build the annotations JSON per references/debugging-decisions.md
uv run scripts/apply_annotations.py --policy-arn <ARN> --annotations-file fixes.json

# Auto-resolve ambiguous variable descriptions / types
uv run scripts/resolve_ambiguities.py --policy-arn <ARN>

# Refine using an updated document + natural-language feedback
uv run scripts/iteratively_refine.py --policy-arn <ARN> --file updated_policy.pdf \
  --feedback "Change the parental-leave tenure requirement from 12 months to 6 months (section 3)."
```
After any of these complete, re-run `ar-policy-reviewer` and `ar-policy-tester`.

## Annotation verbs (in the annotations file)
- Variables: `addVariable`, `updateVariable`, `deleteVariable`
- Rules: `addRule`, `updateRule`, `deleteRule`, `addRuleFromNaturalLanguage`
- Types: `addType`, `updateType`, `deleteType`
- Feedback: `updateFromRulesFeedback`, `updateFromScenarioFeedback`
See `references/debugging-decisions.md` for ready-to-use annotation recipes (missing tenure rule,
overlapping variables, bare-assertion fix).

## Resources
- `references/debugging-decisions.md`: decision table + annotation recipes + worked examples.
- `scripts/apply_annotations.py`, `scripts/resolve_ambiguities.py`, `scripts/iteratively_refine.py`.
- `../../shared/references/findings-reference.md`, `smtlib-rules.md`, `ar-api-context.md`.

## Available Steering Files

- **debugging-decisions.md**: load on demand with `readSteering` (`steeringFile="debugging-decisions.md"`).
