# End-to-End Agentic RAG on a Fully-Managed Bedrock Knowledge Base — via AWS CloudFormation

Deploy a complete **agentic RAG** solution with nothing but CloudFormation: two fully-managed
Amazon Bedrock Knowledge Bases, an Amazon Bedrock AgentCore **Gateway** that exposes each KB's
`AgenticRetrieveStream` tool, an instrumented **Strands agent on AgentCore Runtime** that routes
questions to the right KB, and two **CloudWatch dashboards** covering seven layers of observability.

A companion notebook then drives traffic and lights the dashboards up.

> **About the data.** The two corpora have different provenance. The **financial** corpus (Octank
> Financial 10-K) is **synthetic** — Octank is a fictional company and the document is model-generated
> (CC0-licensed) sample data; it is not real financial data. The **weather** corpus (`tornadoes_report.pdf`)
> is a **real, publicly available** U.S. Congressional Research Service report
> ([IF12695](https://sgp.fas.org/crs/misc/IF12695.pdf)) — a public-domain U.S. Government work. Swap in
> your own S3 corpus by changing the data source in `templates/01-knowledge-bases.yaml`.

## Architecture

```
                          ┌── Layer 1: AWS/Bedrock/KnowledgeBases (metrics)
  data/ ─▶ Managed KB ×2 ─┼── Layer 2: ingestion job + APPLICATION_LOGS
  (financial, weather)    └── Layer 3: AgenticRetrieveStream payload (chunks + cited answer)
       ▲
       │ MCP (AgenticRetrieveStream, per-KB connector target)
  AgentCore Gateway ─────── Layer 4: AWS/Bedrock-AgentCore (metrics)
       ▲
       │ MCP (SigV4 / AWS_IAM)
  Strands agent  ┌───────── Layer 5: OTEL span tree ─▶ aws/spans
  on AgentCore ──┼───────── Layer 6: gen_ai.usage tokens on spans → usage
  RUNTIME        └───────── Layer 7: AgentCore Evaluate scores the session
       ▲
  invoke_agent_runtime(session_id)   ← session id is the join key across every layer
```

Everything above the `data/` line is deployed by CloudFormation. The agentic retrieval tool is a
**native Gateway connector** (`ConnectorId: bedrock-knowledge-bases`) — no Lambda or extra container
is needed for retrieval; only the agent itself runs in a container (built by CodeBuild at deploy).

## Layout

```
templates/
  01-knowledge-bases.yaml   S3 + 2 managed KBs + data sources + IAM + ingest custom resource
  02-agentic-gateway.yaml   Gateway (AWS_IAM/MCP) + per-KB AgenticRetrieveStream targets
  03-agent-runtime.yaml     ECR + CodeBuild + instrumented Strands agent on Runtime + vended logs/traces
  04-dashboards.yaml        2 CloudWatch dashboards (agentic + per-KB observability)
lambdas/ingest_sync/        custom resource: upload corpora + StartIngestionJob
utils/                      self-contained copy of the observability helpers (no repo-root deps)
notebooks/
  01-drive-and-observe.ipynb  post-deploy driver: drives traffic, emits L3/L6/L7, opens dashboards
data/                       the two corpora: financial/ (synthetic, CC0) + weather/ (public CRS report)
scripts/deploy.sh           deploy all four stacks in order (outputs wired forward)
scripts/cleanup.sh          tear everything down in reverse order
```

## Prerequisites

- AWS credentials with permissions for Bedrock, AgentCore (Runtime + Gateway), IAM, CloudWatch,
  X-Ray, ECR, CodeBuild, S3, Lambda, CloudFormation.
- Model access enabled for the agent's model (default `us.anthropic.claude-haiku-4-5-20251001-v1:0`).
- **CloudWatch Transaction Search** enabled (so OTEL spans land in `aws/spans` for Layers 5–7).
- AWS CLI v2 and (for the notebook) Python 3.13 with `boto3>=1.43`, `pandas`, `pyyaml`,
  `mcp-proxy-for-aws`.
- No local Docker required — the agent image is built by CodeBuild (ARM64).

## Deploy

```bash
./scripts/deploy.sh [region] [project-name]
```

**Both arguments are optional** — run `./scripts/deploy.sh` with no arguments and it uses the
defaults below. Pass them positionally (region first, then project name); to set the project name you
must also pass the region before it.

| Arg | Meaning | Default | Notes |
|-----|---------|---------|-------|
| 1 · `region` | AWS region to deploy into | `us-west-2` | Must be a region where Bedrock Managed KB + AgentCore are available. |
| 2 · `project-name` | Name prefix for **every** resource and stack | `bmkb-obs` | Drives the four stack names: `<project>-kb`, `<project>-gateway`, `<project>-agent`, `<project>-dashboards`, plus KB/gateway/bucket names. |

Examples:

```bash
./scripts/deploy.sh                          # us-west-2, project "bmkb-obs" (defaults)
./scripts/deploy.sh us-east-1                # us-east-1, default project name
./scripts/deploy.sh us-west-2 my-rag-demo    # custom project name → stacks my-rag-demo-kb, -gateway, …
```

> **Changing the project name** gives you an isolated, independently-named copy of the whole stack —
> useful for running two deployments side by side. Whatever value you use here, **use the same value
> for `cleanup.sh`**, or cleanup won't find the stacks it needs to delete.

This deploys, in order, wiring outputs forward automatically:

| # | Stack | What it creates | Note |
|---|-------|-----------------|------|
| 01 | `…-kb` | S3 bucket, two `Type: MANAGED` KBs, data sources, IAM, ingest custom resource | KBs reach `ACTIVE`, corpora ingested |
| 02 | `…-gateway` | Gateway (AWS_IAM/MCP), per-KB `AgenticRetrieveStream` targets | no Cognito needed |
| 03 | `…-agent` | ECR, CodeBuild, instrumented Strands agent on Runtime, vended logs/traces | **~8–10 min** (image build) |
| 04 | `…-dashboards` | agentic-observability + kb-observability dashboards | empty until you drive traffic |

## Drive traffic & observe

Open `notebooks/01-drive-and-observe.ipynb` and run it top to bottom. It reads the stack outputs,
sends financial + weather prompts to the deployed agent (per-KB sessions), then publishes the three
custom-metric layers the dashboards read:

- **Layer 3** — reference-free agentic retrieval quality → `BMKB/RetrievalQuality`
- **Layer 6** — per-session token usage from span `gen_ai.usage.*` → `BMKB/Cost`
- **Layer 7** — AgentCore Evaluate scores → `BMKB/Evaluation`

Then open the two dashboards (URLs are printed, and are stack outputs). Set a **3-hour** range and
refresh — CloudWatch metric values lag emission by 1–5 minutes.

## The two dashboards

- **`…-agentic-observability`** — the end-to-end 7-layer view: KB metrics (L1), agentic retrieval
  quality per KB (L3), Gateway calls + latency (L4), token usage (L6), eval scores (L7), and the
  span table (L5).
- **`…-kb-observability`** — the per-KB operational signals that also determine spend: index size
  (MB), retrieve volume, agentic tool-calls, session token usage, and generation token usage by model.

## Evaluation: on-demand and continuous

Layer 7 is covered two ways:

- **On-demand** — the driver notebook calls `evaluate()` over each session's spans and publishes to
  `BMKB/Evaluation` (feeds the L7 dashboard widget).
- **Continuous (online)** — the `03-agent-runtime` stack provisions an
  `AWS::BedrockAgentCore::OnlineEvaluationConfig` that samples live sessions and scores them
  automatically; results appear in the console under **CloudWatch → GenAI Observability → Bedrock
  AgentCore → Evaluations**.

> **⚠️ Sampling disclaimer.** This stack sets **`SamplingPercentage: 100`** *purely for the blog
> experiment*, so every session is scored and the results are immediately visible. **This is not a
> production recommendation.** Online evaluation invokes an LLM-as-judge per sampled session, which
> **incurs cost that scales with the sampling rate and traffic volume**. For any real deployment,
> choose a sampling percentage (`N%`) that reflects your quality-monitoring needs and budget, and
> **align the configuration with your organization's own policies and cost-governance requirements**
> before enabling it. Tune `SamplingPercentage` in `templates/03-agent-runtime.yaml`
> (`OnlineEvaluationConfig.Rule.SamplingConfig`).

## Cleanup

```bash
./scripts/cleanup.sh [region] [project-name] [--purge-staging]
```

Same first two arguments as `deploy.sh` (both optional, same defaults) — **they must match what you
deployed with**, because `cleanup.sh` deletes stacks by exact name (`<project>-dashboards`, `-agent`,
`-gateway`, `-kb`).

> **🔒 Safety:** cleanup only ever touches stacks named `<project>-*`. It deletes them **by exact
> name**, so a wrong or mistyped `project-name` **silently deletes nothing** (missing stacks are
> skipped) — it will never remove a stack it didn't create, and unrelated stacks in the account are
> never affected.

| Arg | Meaning | Default |
|-----|---------|---------|
| 1 · `region` | AWS region the stacks live in | `us-west-2` |
| 2 · `project-name` | The prefix you deployed with | `bmkb-obs` |
| 3 · `--purge-staging` | Also delete the `<project>-cfn-staging-<account>-<region>` bucket that held packaged artifacts | *(off)* — omit to keep the staging bucket |

Examples:

```bash
./scripts/cleanup.sh                                        # tear down the default deployment
./scripts/cleanup.sh us-west-2 my-rag-demo                  # tear down a custom-named deployment
./scripts/cleanup.sh us-west-2 bmkb-obs --purge-staging # also remove the CFN staging bucket
```

Stacks are deleted in **reverse** order (dashboards → agent → gateway → kb); the `01` stack's ingest
custom resource empties the KB source bucket on delete so it can be removed.
