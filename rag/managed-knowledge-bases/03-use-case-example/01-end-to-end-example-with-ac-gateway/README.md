# End-to-End: Managed KB + AgentCore Gateway

Production-ready pattern combining Managed KB with AgentCore Gateway, Strands Agent, and full-stack observability.

| # | Notebook | Description |
|---|----------|-------------|
| 01 | [01-bmkb-with-agentcore-gateway.ipynb](01-bmkb-with-agentcore-gateway.ipynb) | ⭐ Flagship — KB + Gateway + Strands Agent + CloudWatch observability |
| 02 | 02-multi-kb-agentic-retrieval-TBD.ipynb | Multiple KBs with agentic retrieval |
| 03 | 03-gateway-with-cedar-policies-TBD.ipynb | Gateway + Cedar authorization policies |

## What this demonstrates

1. Create a Managed KB with S3 data source
2. Create an AgentCore Gateway (MCP protocol, IAM auth)
3. Connect KB as a Gateway Target
4. Configure observability (vended logs + OTEL traces)
5. Create a Strands Agent that queries the KB through the Gateway
6. View CloudWatch metrics, OTEL spans, vended logs, and ingestion logs
