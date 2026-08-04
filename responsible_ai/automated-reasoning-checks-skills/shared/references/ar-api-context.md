# Automated Reasoning Checks: API Context Reference

> The authoritative API surface for Amazon Bedrock Automated Reasoning (AR) checks. Every AR skill
> points here to keep a single source of truth. boto3 method = the CLI verb shown, snake_cased.
> Clients: `boto3.client("bedrock")` (control plane), `boto3.client("bedrock-runtime")` (validation).

## The two-step model (read first)
AR validates in two steps. **(1) Translate**: multiple FMs convert NL question+answer into formal
logic over your variables (fallible; reliability = `confidence` = % of models agreeing). **(2) Validate**:
an SMT solver checks the logic against your rules (mathematically sound). **When a result is wrong,
suspect the translation first** (fix variable descriptions); only then suspect the rules.

## Policy lifecycle (control plane)

| Job | API / CLI verb | Key args |
|---|---|---|
| Create policy resource | `CreateAutomatedReasoningPolicy` | `name`(req), `description`, `policyDefinition`, `kmsKeyId`, `tags`(≤200), `clientRequestToken` → returns `policyArn`, `version:DRAFT`, `definitionHash` |
| Build from doc / merge | `StartAutomatedReasoningPolicyBuildWorkflow` | `policyArn`, `buildWorkflowType`, `sourceContent`, `clientRequestToken` |
| Poll build | `GetAutomatedReasoningPolicyBuildWorkflow` | `policyArn`, `buildWorkflowId` → `status` |
| List builds | `ListAutomatedReasoningPolicyBuildWorkflows` | `policyArn` |
| Cancel / delete build | `Cancel...` / `DeleteAutomatedReasoningPolicyBuildWorkflow` | delete needs `lastUpdatedAt` |
| Fetch build assets | `GetAutomatedReasoningPolicyBuildWorkflowResultAssets` | `policyArn`, `buildWorkflowId`, `assetType`, `assetId`(for SOURCE_DOCUMENT) |
| Get / update DRAFT | `GetAutomatedReasoningPolicy` / `UpdateAutomatedReasoningPolicy` | update needs `policyDefinition` |
| Delete policy | `DeleteAutomatedReasoningPolicy` | delete dependents FIRST (build workflows w/ `lastUpdatedAt`, numbered versions via the `:N` ARN, test cases), then the DRAFT. `--force` exists in newer API versions but is NOT available everywhere, so don't rely on it. |
| List policies | `ListAutomatedReasoningPolicies` | optional `policyArn` filter |
| Snapshot version | `CreateAutomatedReasoningPolicyVersion` | needs `lastUpdatedDefinitionHash` (concurrency token) |
| Export version JSON | `ExportAutomatedReasoningPolicyVersion` | `policyArn`, version |
| Next scenario | `GetAutomatedReasoningPolicyNextScenario` | `policyArn`, `buildWorkflowId` |
| Get/update annotations | `Get/UpdateAutomatedReasoningPolicyAnnotations` | `buildWorkflowId`, `annotations`(≤10), concurrency hash |

### `buildWorkflowType` values
`INGEST_CONTENT` (extract/merge from doc) · `REFINE_POLICY` (apply annotations) ·
`IMPORT_POLICY` (load JSON as-is) · `GENERATE_FIDELITY_REPORT` · `GENERATE_POLICY_SCENARIOS` ·
`RESOLVE_POLICY_AMBIGUITIES` · `ITERATIVELY_REFINE_POLICY` (doc + NL feedback).

### Build status enum
`SCHEDULED → PREPROCESSING → BUILDING → TESTING → COMPLETED` (+ `CANCEL_REQUESTED`, `FAILED`, `CANCELLED`).
⚠️ **Max 2 build workflows per policy, only 1 IN_PROGRESS.** Builds split into two pools counted
separately: fidelity-report builds (`GENERATE_FIDELITY_REPORT`) vs. everything else. The scripts call
`ar_common.start_build`, which frees a slot first by deleting the oldest terminal build when a pool is at
capacity (never an in-progress one), so you do not manage this by hand. It raises only if every slot in
the pool is busy with an in-progress build.

### Asset types (`assetType`)
`BUILD_LOG` · `QUALITY_REPORT` · `POLICY_DEFINITION` · `GENERATED_TEST_CASES` · `POLICY_SCENARIOS` ·
`FIDELITY_REPORT` · `ASSET_MANIFEST` · `SOURCE_DOCUMENT` (needs `assetId` from the manifest).
⚠️ The payload nests under **`response["buildWorkflowAssets"][<camelCaseKey>]`** (e.g.
`buildWorkflowAssets.policyDefinition`, `.qualityReport`, `.fidelityReport`, `.buildLog`). Not every
asset exists for every build type, so a missing one raises `ResourceNotFoundException`; treat as optional.
Quality-report fields: `ruleCount`, `variableCount`, `typeCount`, `conflictingRules`, `unusedVariables`,
`unusedTypes`, `unusedTypeValues`, `disjointRuleSets`. Rule fields: `id`, `expression`, `alternateExpression`.

### `sourceContent` shapes
- **INGEST_CONTENT:** `{ policyDefinition:{version:"1.0", types:[], rules:[], variables:[]}, workflowContent:{ documents:[{document:<bytes>, documentContentType:"pdf"|"txt", documentName, documentDescription}] } }`. To **merge**, pass the **full current** `policyDefinition`.
  ⚠️ `policyDefinition.version` MUST be `"1.0"` (schema version, not the resource version).
  ⚠️ `document` is a **blob**. In **boto3 pass RAW BYTES** (boto3 base64-encodes blobs for you; a base64 string double-encodes and the build silently extracts **0 rules**). In the **AWS CLI**, pass base64. `documentContentType` enum is exactly `pdf` | `txt`.
  ⚠️ A successful INGEST does **not** auto-produce a `FIDELITY_REPORT` asset. Run a `GENERATE_FIDELITY_REPORT` build for that. `QUALITY_REPORT`, `POLICY_DEFINITION`, and `GENERATED_TEST_CASES` are present.
- **IMPORT_POLICY:** `{ policyDefinition:{version:"1.0", variables:[...], rules:[{id, expression}], types:[...]} }`.
- **ITERATIVELY_REFINE_POLICY:** `{ policyDefinition:<current>, workflowContent:{ iterativeRefinementContent:{ documents:[...], feedback:"..." } } }`.
- **REFINE_POLICY (annotations):** `{ policyDefinition:<current>, workflowContent:{ policyRepairAssets:{ annotations:[...] } } }`.
- **GENERATE_POLICY_SCENARIOS / RESOLVE_POLICY_AMBIGUITIES:** `{ policyDefinition:<current> }`.

### Annotation verbs (inside `policyRepairAssets.annotations[]`)
- Variables: `addVariable`, `updateVariable`, `deleteVariable`
- Rules: `addRule`, `updateRule`, `deleteRule`, `addRuleFromNaturalLanguage`
- Types: `addType`, `updateType`, `deleteType`
- Feedback: `updateFromRulesFeedback`, `updateFromScenarioFeedback`

## Tests (control plane)

| Job | API verb | Key args |
|---|---|---|
| Create QnA test | `CreateAutomatedReasoningPolicyTestCase` | `guardContent`(req=answer), question param is `query` (boto3 ~1.40) or `queryContent` (1.43+), `expectedAggregatedFindingsResult`, `confidenceThreshold` |
| Get/Update/Delete/List test | `.../TestCase(s)` | update/delete need `lastUpdatedAt` |
| Run tests | `StartAutomatedReasoningPolicyTestWorkflow` | `policyArn`, `buildWorkflowId`(COMPLETED build), optional `testCaseIds` |
| Get/List results | `Get/ListAutomatedReasoningPolicyTestResult(s)` | `buildWorkflowId` (+ `testCaseId`) |

Test result = `expected` vs **`actual`** (worst-severity aggregated) + pass/fail + `findings`.

## Runtime validation (`bedrock-runtime`)

### `ApplyGuardrail` (standalone)
Args: `guardrailIdentifier`, `guardrailVersion` (use a **number**, not DRAFT in prod), `source`
(`OUTPUT` for answers, `INPUT` for prompts), `content=[{text:{text, qualifiers}}]`, `outputScope`.
- Each block defaults to **agent-side (`guard_content` / claim)**. Mark user-side with `qualifiers:["query"]`.
- ⚠️ **No model response is appended**, so you must include ≥1 claim block or you get `ValidationException`.
- Findings: `response["assessments"][].automatedReasoningPolicy.findings[]` (union, one of
  `valid/invalid/satisfiable/impossible/translationAmbiguous/tooComplex/noTranslations`).

### `Converse` / `InvokeModel` / `InvokeAgent` / `RetrieveAndGenerate`
AR runs **only if** there's a `guardContent` block. The **model response is auto-appended as a claim**,
so query-only blocks still trigger AR.
- ⚠️ **`Converse` qualifiers are snake_case** (`query`, `guard_content`, `grounding_source`);
  **`InvokeModel` XML tags are camelCase** (`query`, `guardContent`, `groundingSource`).
- Precedence: `guard_content > query > grounding_source`. `grounding_source` is ignored by AR.

### ⚠️ Silent-skip guard
An untagged request still **succeeds** but returns `automatedReasoningPolicyUnits: 0` → AR never ran.
**Always assert `usage.automatedReasoningPolicyUnits > 0`** (`ar_common.assert_ar_ran`).

## Deployment
`CreateAutomatedReasoningPolicyVersion` → numbered immutable version. Attach to a Guardrail via
`create_guardrail(automatedReasoningPolicyConfig={"policies":[arn|policyIdentifier+version], "confidenceThreshold":1.0}, crossRegionConfig={"guardrailProfileIdentifier": "...us.guardrail.v1:0"})`.
⚠️ AR guardrails **require a cross-region guardrail profile**. **Max 2 AR policies per guardrail.**

## Constraints (docs-authoritative)
- Source document: **≤ 5 MB and ≤ 50,000 characters** (images/tables count). Split larger docs.
- English (US) only. GA in select Regions. Uses cross-region inference internally.
- Variable/type/enum-value names share **one namespace**, so all must be unique.
- Use deterministic code for char-by-char validation (e.g. passwords); AR does not cover that.

## IAM (least privilege)
`bedrock:CreateAutomatedReasoningPolicy`, `:StartAutomatedReasoningPolicyBuildWorkflow`,
`:StartAutomatedReasoningPolicyTestWorkflow`, `:GetAutomatedReasoningPolicy*`, `:CreateGuardrail`,
`:ApplyGuardrail`, `:Converse`, `:InvokeModel`. Resources: `automated-reasoning-policy/*`, `guardrail/*`.
KMS (customer key): `kms:Decrypt/DescribeKey/GenerateDataKey` with encryption-context key
`aws:bedrock:automated-reasoning-policy` = policy ARN.
