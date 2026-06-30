---
name: ar-policy-builder
description: >
  Creates an Amazon Bedrock Automated Reasoning (AR) policy from a source document (HR handbook,
  compliance manual, refund/loan/leave policy, product spec) by extracting formal logic rules and a
  variable schema. Handles policy-resource creation, the INGEST_CONTENT build workflow, base64 document
  encoding, build polling, and optional LLM rule pre-extraction.

  Use this skill whenever the user wants to:
  - "Create an Automated Reasoning policy" / "build an AR policy from this PDF / handbook / doc"
  - Turn a natural-language policy document into formal rules and variables
  - Call CreateAutomatedReasoningPolicy or StartAutomatedReasoningPolicyBuildWorkflow / INGEST_CONTENT
  - Bootstrap a Bedrock Guardrails Automated Reasoning policy from scratch
  Also trigger when the user pastes a policy/handbook and asks to "validate LLM answers against this"
  or "make rules from this", even if they don't say "Automated Reasoning" explicitly.
license: Apache-2.0
---

# AR Policy Builder

## Overview
An Automated Reasoning policy encodes business rules as **formal logic** (rules + a typed variable
schema) extracted from a natural-language **source document**. Creating one is a **two-step API flow**:
(1) create the policy resource, (2) run an `INGEST_CONTENT` build workflow to extract rules from the doc.
This skill drives both, then hands off to `ar-policy-reviewer` to inspect the result.

**API/operator reference:** `../../shared/references/ar-api-context.md` and `smtlib-rules.md`.
Read those when you need exact arg shapes or rule syntax.

## When to use
- Starting a brand-new AR policy from a document.
- Adding a new document's rules into an existing policy (merge via `INGEST_CONTENT` with the full
  current definition — see Step 4).

## Key directives
1. **⚠️ Source doc limit is 5 MB AND 50,000 characters** (images/tables count). If larger, split into
   focused single-domain sections and build incrementally — do NOT try to ingest a whole complex doc at once.
2. **One policy = one focused domain** (e.g. parental leave), not a whole handbook.
3. **Always write `instructions`** at build time — they materially improve extraction. Cover three
   things: the use case, example user questions, and which sections to focus on / ignore.
4. **`policyDefinition.version` must be `"1.0"`** in `sourceContent` (schema version, ≠ resource version).
5. **⚠️ Max 2 build workflows per policy, 1 IN_PROGRESS.** Delete an old one before a third.
6. After the build COMPLETES, **do not assume it's correct** — extraction is non-deterministic. Hand off
   to `ar-policy-reviewer` to check the quality + fidelity reports.

## Workflow

### Step 1 — (Optional) Pre-extract rules with an LLM
For narrative/legal/complex docs, convert prose into clean if-then rules first. This yields higher-quality
policies with fewer junk variables.
```
uv run scripts/extract_rules_with_llm.py --file handbook.pdf --mode structured --region us-east-1
```
`--mode plain` = numbered if-then rules; `--mode structured` = JSON with confidence/ruleType/ambiguities
plus auto-generated sanity (boundary) rules. **Always review the output against the original** before using.

### Step 2 — Create the policy resource
```
uv run scripts/create_policy.py --name "MyHRPolicy" \
  --description "Validates HR chatbot answers about leave eligibility"
```
Returns `policyArn` + `version: DRAFT`. Add `--kms-key-id <arn>` for a customer-managed key.

### Step 3 — Build from the document (INGEST_CONTENT)
```
uv run scripts/build_from_document.py --policy-arn <ARN> --file leave_policy.pdf \
  --doc-name "HR Leave Policy" \
  --doc-description "Validates HR answers about leave eligibility" \
  --instructions "This policy validates HR questions about leave eligibility. Users ask things like
  'Am I eligible for parental leave if I've worked here 9 months?'. Focus on eligibility criteria;
  ignore the company overview."
```
The script base64-encodes the doc, starts the workflow, and polls to `COMPLETED`.

### Step 4 — Merge another document into an existing policy
Pass the **full current** policy definition so new rules merge instead of replacing:
```
uv run scripts/build_from_document.py --policy-arn <ARN> --file benefits.pdf \
  --doc-name "Benefits Rules" --merge
```
`--merge` fetches and includes the existing definition automatically.

### Step 5 — Hand off
Tell the user to run `ar-policy-reviewer` on the policy ARN to check for unused/duplicate variables,
bare assertions, and conflicting rules before testing.

## Prerequisites
- ✅ AWS credentials with `bedrock:CreateAutomatedReasoningPolicy` + `:StartAutomatedReasoningPolicyBuildWorkflow`.
- ✅ A source document ≤ 5 MB / 50K chars, in a focused domain.
- ✅ `boto3` (scripts declare it via PEP 723; `uv run` installs automatically).

## Resources
- `references/doc-preparation.md` — clear-vs-vague rules, splitting, preprocessing, writing instructions.
- `scripts/create_policy.py`, `scripts/build_from_document.py`, `scripts/extract_rules_with_llm.py`
  — all support `--help` and `--dry-run`.
- `../../shared/references/ar-api-context.md` — full API surface. `smtlib-rules.md` — rule syntax.
