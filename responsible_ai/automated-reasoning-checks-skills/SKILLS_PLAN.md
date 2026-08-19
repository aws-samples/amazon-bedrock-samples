# Automated Reasoning Checks: Agent Skills Plan

> Design for a **suite of focused skills**, each with **runnable boto3 scripts + guidance**,
> packaged as a **Claude Code plugin/marketplace**. Decisions confirmed with the user.
> Grounded in `RESEARCH_SUMMARY.md` (docs-authoritative).

---

## Design principles

1. **One skill per lifecycle job**, so the right one triggers and `SKILL.md` stays lean.
2. **Scripts do the boto3; SKILL.md teaches the judgment.** Each script is PEP-723
   (`uv run`), supports `--help`, prints JSON, and is also pasteable inline.
3. **Shared knowledge lives in a `references/` core** (the "API context prompt" pattern AWS
   uses for Kiro CLI) so every skill can point to one authoritative reference and avoid
   duplicating the finding/operator/asset tables.
4. **The two-step model (Translate→Validate) is the spine** of all diagnostic guidance.
5. **Safety rails baked in:** assert `automatedReasoningPolicyUnits > 0`, warn on `DRAFT` in
   prod, respect "max 2 build workflows / max 2 AR policies" limits, never delete without confirm.

---

## Repo layout

```
Automated_Reasoning_Skills/
├── RESEARCH_SUMMARY.md            # done, docs-authoritative reference
├── SKILLS_PLAN.md                 # this file
├── README.md                      # marketplace overview + install instructions
├── .claude-plugin/
│   └── marketplace.json           # lists all skills as installable plugins (HF style)
├── shared/
│   ├── ar_common.py               # boto3 client factory, build-workflow poller, asset fetch,
│   │                              #   finding parser, automatedReasoningPolicyUnits guard, retry
│   └── references/
│       ├── ar-api-context.md      # THE API context prompt (verbs, args, ARNs, asset/annotation enums)
│       ├── findings-reference.md  # 7 result types: fields + recommended action + severity order
│       ├── smtlib-rules.md        # operators, if-then form, bare-assertion trap, modeling patterns
│       └── glossary.md            # policy/rule/variable/type/fidelity/quality/confidence
└── skills/
    ├── ar-policy-builder/
    ├── ar-policy-reviewer/
    ├── ar-policy-tester/
    ├── ar-policy-debugger/
    ├── ar-guardrail-deployer/
    └── ar-runtime-validator/
```

*(Each skill folder carries its own `SKILL.md`, `scripts/`, and small `references/`. The big
shared references are symlinked or referenced by relative path from `shared/references/`.)*

---

## The 6 skills

### 1. `ar-policy-builder`: create a policy from a document
**Triggers:** "create an automated reasoning policy", "build AR policy from this PDF/handbook",
"turn this doc into rules", mentions of `CreateAutomatedReasoningPolicy` / `INGEST_CONTENT`.
**Workflow:** prepare source (5 MB / 50K char limit; optional LLM rule-extraction prompt) →
`CreateAutomatedReasoningPolicy` → `StartAutomatedReasoningPolicyBuildWorkflow INGEST_CONTENT`
with good `instructions` → poll → hand off to reviewer.
**Scripts:**
- `create_policy.py --name --description [--kms-key-id]`
- `build_from_document.py --policy-arn --file --doc-name --doc-description [--instructions]` (base64 + poll)
- `extract_rules_with_llm.py --file [--mode plain|structured]` (the two doc-preprocessing prompts)
**References:** doc-prep checklist, the two extraction prompts, effective-instructions guide.

### 2. `ar-policy-reviewer`: inspect & sanity-check an extracted policy
**Triggers:** "review my AR policy", "check the quality report", "is my policy good", post-build.
**Workflow:** pull `POLICY_DEFINITION` + `QUALITY_REPORT` + `FIDELITY_REPORT` assets →
flag unused/duplicate vars, bare assertions, conflicting rules, disjoint sets, low
coverage/accuracy → produce a prioritized fix list (defers actual fixes to debugger).
**Scripts:**
- `get_assets.py --policy-arn [--build-workflow-id] --asset-type ...`
- `audit_policy.py --policy-arn` (fetches assets, prints a structured findings report + score summary)
**References:** quality-report interpretation, fidelity-report interpretation.

### 3. `ar-policy-tester`: generate scenarios + author/run QnA tests
**Triggers:** "test my AR policy", "generate test scenarios", "add a QnA test", "validate all tests".
**Workflow:** `GENERATE_POLICY_SCENARIOS` → `Get...NextScenario` (review SATISFIABLE/thumbs-down) →
`CreateAutomatedReasoningPolicyTestCase` (guard/query content, expected result, confidence) →
`StartAutomatedReasoningPolicyTestWorkflow` → `Get/ListTestResult` → summarize pass/fail.
**Scripts:**
- `generate_scenarios.py --policy-arn` (start workflow + fetch scenarios)
- `create_test.py --policy-arn --output [--input] --expected --confidence`
- `run_tests.py --policy-arn [--build-workflow-id] [--test-case-ids]` (run + collect results)
**References:** scenarios-vs-QnA strategy, expected-result severity logic.

### 4. `ar-policy-debugger`: diagnose failures & apply annotation repairs
**Triggers:** "my test is failing", "getting IMPOSSIBLE / TRANSLATION_AMBIGUOUS / unexpected VALID",
"fix my AR policy rules". *This is the Kiro-CLI-equivalent flagship skill.*
**Workflow:** classify by actual result → **check translation first** (premises/claims/confidence) →
decide rules-vs-descriptions → propose annotations → `REFINE_POLICY` with
`policyRepairAssets.annotations` (or `RESOLVE_POLICY_AMBIGUITIES` / `ITERATIVELY_REFINE_POLICY`) →
re-review → `UpdateAutomatedReasoningPolicy`.
**Scripts:**
- `apply_annotations.py --policy-arn --annotations-file` (REFINE_POLICY)
- `resolve_ambiguities.py --policy-arn`
- `iteratively_refine.py --policy-arn --file --feedback`
**References:** the **debugging decision table** (result → likely cause → fix), annotation-type
catalog with before/after examples, translate-vs-validate triage.

### 5. `ar-guardrail-deployer`: version the policy & attach to a guardrail
**Triggers:** "deploy my AR policy", "create a guardrail with my policy", "version this policy",
"attach AR policy to guardrail".
**Workflow:** `CreateAutomatedReasoningPolicyVersion` (with `definitionHash`) →
`CreateGuardrail`/`UpdateGuardrail` with `automatedReasoningPolicyConfig` (ARN+version+threshold) +
required `crossRegionConfig` → create guardrail version → return guardrail id/version.
**Scripts:**
- `create_version.py --policy-arn` (snapshots DRAFT, handles concurrency hash)
- `deploy_guardrail.py --policy-arn --policy-version [--guardrail-name] [--confidence]`
  (idempotent ensure-guardrail; derives cross-region profile from ARN)
**References:** versioning model, 2-policies-per-guardrail limit, DRAFT-vs-numbered guidance.

### 6. `ar-runtime-validator`: validate LLM outputs + rewrite loop
**Triggers:** "validate this answer with AR", "call ApplyGuardrail", "set up a rewrite loop",
"check my chatbot response", mentions of `apply_guardrail` / `automatedReasoningPolicy.findings`.
**Workflow:** `ApplyGuardrail` (or `Converse`) with correct qualifiers → parse findings (union) →
**assert `automatedReasoningPolicyUnits > 0`** → on non-VALID, render per-finding rewrite template +
rule context → regenerate → re-validate (Valid@N loop, default 5) → log audit trail.
**Scripts:**
- `validate_response.py --guardrail-id --guardrail-version --question --answer [--source OUTPUT]`
- `rewrite_loop.py --guardrail-id --guardrail-version --question --answer --model-id [--max-iter 5]`
**References:** ApplyGuardrail-vs-Converse qualifier rules (snake vs camel), the silent-skip gotcha,
per-result-type rewrite templates (lifted from aws-samples `response_rewriting_prompts/`).

---

## Shared `references/ar-api-context.md`

A single markdown file every skill points to (the "context prompt" AWS recommends for agents):
all control-plane + runtime verbs with required/optional args, ARN formats, the 7
`buildWorkflowType`s, 8 asset types, annotation verbs, status enums, severity ordering, and the
runtime qualifier/units rules. Keeps each `SKILL.md` lean.

---

## Build order (proposed)

1. **Scaffold** repo + `shared/` + `marketplace.json` + `README.md`.
2. **`shared/ar_common.py`** (clients, poller, asset fetch, finding parser, units-guard, retry). Every script imports it.
3. **`shared/references/`** core docs (distilled from RESEARCH_SUMMARY).
4. Skills in lifecycle order: **builder → reviewer → tester → debugger → deployer → runtime-validator.**
5. **Dry-run validation** of each script (`--help` + arg parsing) with no live AWS calls; note where real creds are needed.

## Open questions before scaffolding
- **boto3 availability / AWS creds:** do you want scripts that actually call Bedrock (you run them
  with creds), or also a `--dry-run`/mock mode for offline testing? (Plan assumes real calls + `--help`.)
- **Region default:** `us-east-1` ok as the scripts' default?
- **LLM convention for rewrite/extraction scripts:** standardize on `Converse` (cleaner). Agree?
