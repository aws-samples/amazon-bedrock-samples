# 08 — Observability

Monitor, debug, and trace your BMKB and AgentCore Gateway.

| # | Notebook | Description | Status |
|---|----------|-------------|--------|
| 01 | `01-cloudwatch-metrics-TBD.ipynb` | KB metrics, dashboards, and alarms | TBD |
| 02 | `02-agentcore-observability.ipynb` | Capture Layers 1–5 (KB metrics, ingestion logs, retrieval quality, Gateway metrics, spans) + a KB-focused dashboard | ✅ |

### Already covered

The flagship notebook `06-end-to-end-patterns/01-bmkb-with-agentcore-gateway.ipynb` already demonstrates:
- **KB metrics** — `AWS/Bedrock/KnowledgeBases` namespace (Invocations, Errors, Throttles)
- **Gateway metrics** — `AWS/Bedrock-AgentCore` namespace (Invocations, Latency, Errors, Throttles)
- **OTEL spans** — `aws/spans` log group (per-operation traces with latency)
- **Vended logs** — `/aws/vendedlogs/bedrock-agentcore/{gateway_id}` (request processing)
- **Ingestion logs** — `/aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/{kb_id}`

These dedicated notebooks will provide deeper dives into dashboards, alarms, and advanced tracing patterns.

### Key namespaces

| Namespace | Metrics | Dimensions |
|-----------|---------|------------|
| `AWS/Bedrock/KnowledgeBases` | Invocations, ServerErrors, ClientErrors, Throttles, TotalIterationCount, RawDataSize | KnowledgeBaseId, Operation |
| `AWS/Bedrock-AgentCore` | Invocations, Latency, SystemErrors, UserErrors, Throttles | Operation, Protocol, Resource, Method |

> **Note:** `NumberOfVectors` appears in CloudWatch but is undocumented and always shows 0 — it is filtered out in the notebooks.

> **Note for contributors:** Reference the [AgentCore observability docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) for Gateway observability details.
