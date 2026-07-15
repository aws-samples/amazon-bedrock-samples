# Observability

Monitor and observe your Managed Knowledge Base and AgentCore Gateway.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01-cloudwatch-metrics.ipynb` | CloudWatch metrics for Managed KBs (ingestion, retrieval, errors) |
| 02 | `02-agentcore-observability.ipynb` | AgentCore Gateway observability — OTEL spans, vended logs |

## Observability components

| Component | What it provides |
|-----------|-----------------|
| **KB CloudWatch Metrics** | Ingestion success/failure, retrieval latency, document counts |
| **KB Vended Logs** | Detailed ingestion logs per document |
| **Gateway OTEL Spans** | Tool invocation traces (Initialize, ListTools, InvokeTool) |
| **Gateway Vended Logs** | Request/response logs for each MCP call |

## Key metric dimensions

- KB metrics namespace: `AWS/Bedrock/KnowledgeBases`
- KB dimension: `knowledge-base/{kb_id}`
- Gateway metrics namespace: `AWS/Bedrock-AgentCore`

## Documentation

- [Observability for managed KBs](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-observability.html)
- [AgentCore observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
