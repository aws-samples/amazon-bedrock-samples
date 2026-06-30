# Automated Reasoning (AR) Checks — Research Summary

> Consolidated notes for building **Agent Skills** around Amazon Bedrock Automated Reasoning checks.
> **Primary source:** the Bedrock User Guide AR chapter (`bedrock_AR_section.pdf`, ~120 pages,
> extracted text in `AR_section_text.txt`). Secondary: aws-samples GitHub (AR checks notebooks +
> rewriting chatbot), 4 AWS ML blogs, AR workshop, Nova / Hugging Face skills repos.
> Where the docs and blogs disagree (e.g. document size limits), **the User Guide wins** and the
> correction is flagged ⚠️.

---

## 1. What Automated Reasoning Checks Are

A safeguard policy type within **Amazon Bedrock Guardrails** that uses **formal logic + SMT solvers**
to mathematically verify whether an LLM answer is consistent with an encoded **policy**. Unlike
LLM-as-a-judge (one probabilistic system checking another), AR gives a **sound, auditable** verdict.

AR does **not** simply block content — it returns structured **findings** (with the rules and variable
assignments behind each verdict) that you use to **rewrite / steer / caveat** the answer.

Status: **GA** in select Regions, **English (US) only**, uses **cross-region inference** internally.
Charged per **automated reasoning policy unit**.

---

## 2. The Two-Step Model (the single most important concept)

AR validates content in two distinct steps. **Almost all debugging hinges on knowing which step failed.**

1. **Translate** — multiple foundation models independently convert the natural-language input
   (question + answer) into formal logic, mapping phrases to your policy's **variables**. This step
   *can* be wrong; its reliability is captured by a **confidence** score (= % of models that agreed).
2. **Validate** — an **SMT solver** checks the translated logic against your **rules**. This step is
   **mathematically sound**: if the translation is correct, the result is correct.

> Debugging rule of thumb: **check the translation first.** If the right variables got the right values
> but the result is wrong → fix **rules**. If the variables/values are wrong → fix **variable descriptions**.

---

## 3. Core Building Blocks

### Policy
A resource in your account (identified by an **ARN**, Region-scoped) holding **rules + a variable
schema + optional custom types**. Has a **DRAFT** version ("Working Draft") you edit, and **numbered
immutable versions** you snapshot for deployment. Each policy should cover **one focused domain**.

Pipeline: `Source Document (NL) → AR Policy (rules+vars+types) → Guardrail (refs a version) → Your App (calls guardrail APIs)`

### Rules
Formal-logic expressions in a **subset of SMT-LIB**. Should be **if-then (implicative)** form.

| Operator | Meaning | Example |
|---|---|---|
| `=>` | implication (if-then) | `(=> isFullTime eligibleForBenefits)` |
| `and` | logical AND | `(and isFullTime (> tenure 12))` |
| `or` | logical OR | `(or isVeteran isTeacher)` |
| `not` | logical NOT | `(not isTerminated)` |
| `=` | equality | `(= employmentType FULL_TIME)` |
| `>` `<` `>=` `<=` | comparison | `(>= creditScore 700)` |

**Bare assertions** (rules with no if-then, e.g. `eligibleForParentalLeave`) become **axioms** — always
true — and are a top cause of unexpected `IMPOSSIBLE` results. Only acceptable for boundary conditions
like `(>= accountBalance 0)`.

### Variables
Each has a **name, type, description**. Types: **BOOL**, **INT**, **NUMBER** (decimal), **custom enum**.
- ⚠️ **Variable descriptions are the #1 factor in translation accuracy.** Good ones state what the
  variable means, the unit/format, synonyms/alt-phrasings users use, and boundary conditions
  (e.g. "convert years to months: 2 years = 24; set 0 for new hires").
- **Namespace rule:** variable names, type names, and enum values share **one namespace** — all must
  be unique (prefix collisions like `LeaveType_OTHER` / `Severity_OTHER`).
- AR is **not** for char-by-char/string validation (e.g. password rules) — use deterministic code there.

### Custom types (enums)
Fixed value sets. **Use enums for mutually-exclusive states; use separate booleans for co-existing
states** (a person can be veteran AND teacher → two booleans, not one enum). Include an `OTHER`/`NONE`
value when input might not match.

### Fidelity report (auto-generated on build)
Measures how faithfully the policy represents the source doc. Two scores (0.0–1.0): **coverage**
(how much of the source is captured) and **accuracy** (how faithfully rules match intent). Provides
per-rule / per-variable **grounding** back to numbered atomic statements in the source — built for
**SME review without reading formal logic**. Regenerate with `GENERATE_FIDELITY_REPORT`.

### Quality report (auto-generated on build)
Flags structural issues: **conflicting rules** (→ cause `IMPOSSIBLE` for all involved inputs),
**unused variables** (→ noise, cause `TRANSLATION_AMBIGUOUS`), **unused type values**, **disjoint
rule sets** (groups sharing no variables — may signal missing connections). Asset type `QUALITY_REPORT`.

---

## 4. Findings & Validation Results

Each **finding** = one factual claim extracted from the input + its result + variable assignments +
the rules behind it. Most findings carry a `translation` object: `premises`, `claims`, `confidence`
(0–1), `untranslatedPremises`, `untranslatedClaims`, plus a `logicWarning` when the translation is
trivially always-true/always-false.

The **aggregated** result = the **worst** finding by severity. Severity (worst→best):
**`TRANSLATION_AMBIGUOUS → IMPOSSIBLE → INVALID → SATISFIABLE → VALID`**.
(`TOO_COMPLEX` and `NO_TRANSLATIONS` sit outside this ordering — handle separately.)

| Result (API key) | Meaning | Key fields | Recommended action |
|---|---|---|---|
| **VALID** (`valid`) | Claims provably true given premises + rules | `supportingRules`, `claimsTrueScenario` | Serve. Log proof for audit. Check untranslated* for unvalidated parts. |
| **INVALID** (`invalid`) | Claims contradict rules | `contradictingRules` | Don't serve. Feed contradicting rules + claims to LLM to rewrite. |
| **SATISFIABLE** (`satisfiable`) | True under some conditions, not all (incomplete) | `claimsTrueScenario` + `claimsFalseScenario` | Compare scenarios → add missing conditions, ask user, or caveat. |
| **IMPOSSIBLE** (`impossible`) | Premises self-contradict, or policy rules conflict | `contradictingRules` | Check input for contradictions; else fix policy (quality report). |
| **TRANSLATION_AMBIGUOUS** (`translationAmbiguous`) | Models disagreed on interpretation | `options` (≤2), `differenceScenarios` | Improve variable descriptions / merge overlaps / ask user. Last resort: lower threshold. |
| **TOO_COMPLEX** (`tooComplex`) | Exceeded processing/latency capacity | none | Shorten input; simplify policy; avoid nonlinear arithmetic; split policy. |
| **NO_TRANSLATIONS** (`noTranslations`) | Couldn't map input to any variable (off-topic or missing vars) | none | Add variables if relevant; else filter off-topic upstream (topic policy). |

> ⚠️ **`VALID` only covers translated claims.** Untranslated content is NOT validated (e.g. "I have a
> fake doctor's note" may pass if no variable models it). Treat `untranslated*` and `NO_TRANSLATIONS`
> as warning signals.

### Confidence threshold
Value 0.0–1.0; the **minimum fraction of translation models that must agree** for a translation to
yield a definitive result. Higher (e.g. 0.9) = fewer, more-accurate findings, more `TRANSLATION_AMBIGUOUS`.
Lower (e.g. 0.5) = more findings, higher risk. Below-threshold translations surface as an extra
`TRANSLATION_AMBIGUOUS` finding. **Prefer fixing variable descriptions over lowering the threshold.**

---

## 5. End-to-End Lifecycle + API/CLI Surface

`boto3.client('bedrock')` for control plane; `boto3.client('bedrock-runtime')` for validation.
CLI verbs shown; boto3 method = same name in snake_case.

### 1. Create the policy resource
`CreateAutomatedReasoningPolicy` → returns `policyArn`, `version: DRAFT`, `definitionHash`.
Args: `name` (req), `description`, `policyDefinition` (optional pre-seeded schema), `kmsKeyId`,
`tags` (≤200), `clientRequestToken`.

### 2. Build from a document
`StartAutomatedReasoningPolicyBuildWorkflow` with `buildWorkflowType=INGEST_CONTENT`.
`sourceContent = { policyDefinition: {version:"1.0", types:[], rules:[], variables:[]}, workflowContent:{documents:[{document:<base64>, documentContentType:"pdf", documentName, documentDescription}]} }`.
⚠️ `policyDefinition.version` must be `"1.0"` (schema version, ≠ resource version).
Poll `GetAutomatedReasoningPolicyBuildWorkflow` (status: `SCHEDULED → PREPROCESSING → BUILDING → TESTING → COMPLETED`; also `CANCEL_REQUESTED/FAILED/CANCELLED`).
⚠️ **Max 2 build workflows per policy; only 1 `IN_PROGRESS`.** Delete old ones first.

**`buildWorkflowType` values:** `INGEST_CONTENT`, `REFINE_POLICY`, `IMPORT_POLICY`,
`GENERATE_FIDELITY_REPORT`, `GENERATE_POLICY_SCENARIOS`, `RESOLVE_POLICY_AMBIGUITIES`,
`ITERATIVELY_REFINE_POLICY`.

### 3. Review extracted policy
`GetAutomatedReasoningPolicyBuildWorkflowResultAssets --asset-type <T>`.
**Asset types:** `BUILD_LOG`, `QUALITY_REPORT`, `POLICY_DEFINITION`, `GENERATED_TEST_CASES`,
`POLICY_SCENARIOS`, `FIDELITY_REPORT`, `ASSET_MANIFEST`, `SOURCE_DOCUMENT` (needs `--asset-id`).
Check for: unused vars, duplicate/near-duplicate vars, bare assertions, conflicting rules, missing rules.

### 4. Refine / merge / import
- **Merge a new doc** → `INGEST_CONTENT` again, passing the **full current `policyDefinition`** + new doc.
- **Import existing JSON** → `IMPORT_POLICY` (skips extraction).
- **Refine with feedback** → `ITERATIVELY_REFINE_POLICY` (doc as context + NL `feedback`).
- **Apply annotations** → `REFINE_POLICY` with `workflowContent.policyRepairAssets.annotations[]`.
  **Annotation types:** `addVariable/updateVariable/deleteVariable`,
  `addRule/updateRule/deleteRule/addRuleFromNaturalLanguage`, `addType/updateType/deleteType`,
  `updateFromRulesFeedback/updateFromScenarioFeedback`.
- **Auto-fix ambiguity** → `RESOLVE_POLICY_AMBIGUITIES`.
- Apply changes to DRAFT with `UpdateAutomatedReasoningPolicy` (`--policy-definition` req).

### 5. Test
- **Scenarios** (test *rule correctness*): `GENERATE_POLICY_SCENARIOS` →
  `GetAutomatedReasoningPolicyNextScenario` (fetch one at a time). Thumbs-up → save as `SATISFIABLE`
  test; thumbs-down → annotate with NL feedback.
- **QnA tests** (test *translation accuracy* end-to-end): `CreateAutomatedReasoningPolicyTestCase`
  (`guardContent` req = the answer; `queryContent` optional = the question;
  `expectedAggregatedFindingsResult`; `confidenceThreshold`).
- Run: `StartAutomatedReasoningPolicyTestWorkflow` (needs `buildWorkflowId` of a COMPLETED build;
  optional `testCaseIds`). Read: `GetAutomatedReasoningPolicyTestResult` /
  `ListAutomatedReasoningPolicyTestResults`. Result = expected vs **actual** (worst-severity) + pass/fail.

### 6. Version + deploy
`CreateAutomatedReasoningPolicyVersion` (needs `--last-updated-definition-hash` concurrency token) →
immutable numbered version. `ExportAutomatedReasoningPolicyVersion` to get the JSON. Attach to a
**Guardrail** via `automatedReasoningPolicyConfig` (policy ARN + version + `confidenceThreshold`).
⚠️ **Max 2 AR policies per guardrail.** Guardrail can reference `DRAFT` or a numbered version.

### 7. Validate at runtime
- **`ApplyGuardrail`** (standalone): `guardrailIdentifier`, `guardrailVersion` (use a number, not DRAFT),
  `source="OUTPUT"` (or `INPUT`), `content=[{text:{text:...}}]`.
  ⚠️ Each block defaults to **agent-side (`guard_content`/claim)**; set `qualifiers:["query"]` to mark
  user-side. **No model response is appended**, so you must include ≥1 claim block or you get a
  `ValidationException`. Read findings: `response["assessments"][].automatedReasoningPolicy.findings[]`
  (union — exactly one of `valid/invalid/satisfiable/impossible/translationAmbiguous/tooComplex/noTranslations`).
- **`Converse` / `InvokeModel` / `InvokeAgent` / `RetrieveAndGenerate`**: AR runs **only if** there's a
  `guardContent` block. The **model response is auto-appended as a claim**, so query-only blocks still work.
  ⚠️ **`Converse` uses snake_case qualifiers** (`query`, `guard_content`, `grounding_source`);
  `InvokeModel` XML tags use **camelCase** (`query`, `guardContent`, `groundingSource`).
  Qualifier precedence: `guard_content > query > grounding_source`.
- ⚠️ **Silent-skip gotcha:** a misconfigured (untagged) request still **succeeds** but returns
  `automatedReasoningPolicyUnits: 0` — AR didn't run. **Always assert this value is > 0.**

### Management / misc
`Get/Update/Delete/ListAutomatedReasoningPolicies` (`--force` delete cascades versions/tests).
KMS: optional customer-managed key; needs `kms:Decrypt/DescribeKey/GenerateDataKey` with encryption
context key `aws:bedrock:automated-reasoning-policy` = policy ARN.
IAM actions: `bedrock:CreateAutomatedReasoningPolicy`, `:StartAutomatedReasoningPolicyBuildWorkflow`,
`:StartAutomatedReasoningPolicyTestWorkflow`, `:CreateGuardrail`, `:ApplyGuardrail`, `:Converse`, etc.

---

## 6. Authoring Good Policies (docs best practices)

- **Start simple & iterate** — one focused section first, test, then merge more via iterative building.
  (The #1 mistake is trying to ingest a whole complex document at once.)
- **Prepare the source doc:** clear if-then rules, no boilerplate/legal/TOC. ⚠️ **Limits: 5 MB and
  50,000 characters** (images/tables count). (Blogs' "120K tokens / 100 pages" is **superseded** by docs.)
- **(Optional) LLM-preprocess** narrative docs into rules first — the docs give two ready prompts:
  (1) *plain-text if-then extraction*, (2) *structured JSON extraction* (with `confidence`,
  `ruleType: explicit/implicit/sanity`, an `ambiguities` array, and auto-generated **sanity/boundary
  rules** like "age 0–150"). **Review LLM output against the original before using.**
- **Write effective `instructions`** at build time, covering 3 things: (1) the use case,
  (2) example user questions, (3) which sections to focus on / ignore.
- **Rule style:** use implications `=>`; booleans for non-exclusive states; enums for exclusive
  categories; validate numeric ranges with boundary rules; intermediate variables for abstraction;
  describe *what is true*, not *how to compute*; avoid contradictions, unused vars, circular deps.

---

## 7. AWS's own agent workflow = strong signal for our skills

The User Guide documents **using "Kiro CLI" (an agent) to refine AR policies via natural language** —
it loads the policy definition + quality report + test findings, explains failures, proposes rule/variable
changes, and applies **annotations** through the control-plane + test APIs. Prereqs include saving an
**"Automated Reasoning policy API context prompt"** (a markdown file of API usage guidance) into the
project so the agent calls the APIs correctly, and using a **large model (e.g. Sonnet 4.5)** for the
logical reasoning. **This is essentially the product we're building** — our skills should bundle that
same API-context guidance as `references/`, and cover the same jobs (explore, diagnose, refine, test).

---

## 8. Reference Implementations to Lift (aws-samples GitHub)

### `bedrock-automated-reasoning-checks/` (notebooks + helpers)
- `policy_definition.py` → `get_policy_definition(client, policy_arn)`
- `findings_utils.py` → `extract_reasoning_findings(...)` (raw findings → readable markdown, rule-enriched)
- `rewrite.py` → `FindingType` enum, `TemplateManager`, `FindingProcessor`, `ResponseRewriter`, priority sort
- `response_rewriting_prompts/` → `ambiguity.md`, `impossible.md`, `invalid.md`, `no-translations.md`, `satisfiable.md`
- Notebooks: policy creator, refinement, test creator, guardrail validation, rewrite, **valid@N**.

### `automated-reasoning-rewriting-chatbot/` (Flask + React, auditable rewrite loop)
- `config_manager.ensure_guardrail(policy_arn)` — idempotent create-or-update; derives required
  `crossRegionConfig` profile from the policy ARN.
- `validation_service` — `apply_guardrail` shape + `_extract_finding_type` union parsing + priority sort.
- `policy_service` — load policy definition **without a saved version** from the latest COMPLETED build's
  `POLICY_DEFINITION` asset; `format_policy_context()` → `{{policy_context}}` injection.
- `llm_service` — model-agnostic invoke (Claude/Nova/default) + cross-region inference prefixing;
  `retry_handler.retry_api_call(max_retries=3, base_delay=1.0)`.
- Per-type rewrite templates + clarification/fallback templates; `ThreadProcessor` state machine
  (`GENERATE_INITIAL → VALIDATE → CHECK_QUESTIONS → HANDLE_RESULT → REWRITING_LOOP`), `AuditLogger`.

**Caveats:** notebooks use `converse`; chatbot uses `invoke_model` (pick one). Extraction is
**non-deterministic** (rule/var counts vary) → human/SME review expected.

### Use cases demonstrated
HR leave eligibility (the docs' running example), hospital readmission risk (enum LOW/INT/HIGH),
mortgage approval (workshop/blog), homework submission (console sample policy), customer-support refund,
S3 pricing, insurance coverage.

---

## 9. Skill-Authoring Conventions (Nova + HF repos)

**Unit:** one `kebab-case` folder per skill with a required `SKILL.md` (only always-loaded file).
Optional `references/` (deep-dive `.md`, loaded on demand), `scripts/` (PEP 723 + `uv run`, support `--help`),
`assets/`, `.claude-plugin/plugin.json` (per-skill, Nova) or repo-level `.claude-plugin/marketplace.json` (HF).

**Frontmatter:** required `name` + `description`; optional `license`, `tags`, `metadata`, `allowed-tools`.
The **`description` is the trigger** — third-person, lead with what it does, then concrete trigger signals
(keywords, API/model names, literal user phrasings): "Use this skill whenever the user mentions … Also
trigger when …, even if they don't say 'X' explicitly."

**Body shape (convergent):** `# Title` → `## Overview` → `## When to Use` → `## Key Directives`
(bold MUST/ALWAYS) → numbered `## Step N` workflow w/ code → `## Prerequisites/Checklist` →
`## Troubleshooting/Resources` → `## Key Takeaways`. Keep `SKILL.md` lean; push depth to `references/`,
runnable work to `scripts/` (progressive disclosure).
