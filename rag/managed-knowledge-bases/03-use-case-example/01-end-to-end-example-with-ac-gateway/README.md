# End-to-End Example with AgentCore Gateway

A complete production-ready pattern: Managed KB + AgentCore Gateway + Strands Agent + observability.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01-bmkb-with-agentcore-gateway.ipynb` | Full end-to-end: create KB, Gateway, connect agent, query, observe |

## What this notebook covers

1. Create a Managed KB with S3 data source
2. Ingest documents and verify retrieval
3. Create an AgentCore Gateway (MCP protocol, IAM auth)
4. Connect KB as a Gateway target
5. Configure observability (vended logs + OTEL traces)
6. Create a Strands Agent that queries the KB through the Gateway
7. Examine KB and Gateway observability (metrics, spans, logs)
8. Cleanup all resources

## Also in this section (`03-use-case-example/`)

| # | Notebook | Description |
|---|----------|-------------|
| 02 | `../02-multi-kb-semantic-routing.ipynb` | Multi-KB routing via Gateway with transparent tool selection |
| 03 | `../03-gateway-with-cedar-policies.ipynb` | Gateway + Cedar policies for multi-tenant access control |

## Documentation

- [Connect through AgentCore Gateway](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-gateway-target.html)
- [Managed KB as Gateway connector target](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-managed-kb.html)
- [Strands Agents SDK](https://strandsagents.com/latest/)
