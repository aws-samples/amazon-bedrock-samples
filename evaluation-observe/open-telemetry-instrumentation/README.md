# Amazon Bedrock Agent Observability with OpenTelemetry

This package provides OpenTelemetry instrumentation for Amazon Bedrock Agents that sends trace data to any OpenTelemetry-compatible observability platform. It creates a complete observability solution for Bedrock Agents, supporting both streaming and non-streaming modes.

## Overview

OpenTelemetry integration enables tracing, monitoring, and analyzing the performance and behavior of your Bedrock Agents. This observability solution helps in understanding agent interactions, debugging issues, and optimizing performance. It works with single agents, multi-agent collaboration (MAC), or with inline agents.

As the field of AI observability is still maturing, this implementation adheres to OpenTelemetry semantics as much as possible and will evolve as industry standards become more established.

## Features

- Complete span hierarchy with proper parent-child relationships (L1-L4 levels)
- Token usage tracking for LLM operations
- Standardized attribute naming following OpenLLMetry conventions
- Compatible with any OpenTelemetry-compatible observability platform (e.g., Langfuse, Grafana, Datadog)
- Support for both cloud-hosted and self-hosted options
- Streaming and non-streaming response support
- Detailed trace and performance metrics

## Setup

### Prerequisites
1. AWS account with appropriate IAM permissions for Amazon Bedrock Agents
2. An existing Amazon Bedrock Agent (or follow AWS documentation to create one)
3. An OpenTelemetry-compatible observability platform (examples include Langfuse, Grafana, Jaeger, etc.)

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
1. Add the following information in `config.json`
2. Fill in your OpenTelemetry endpoint credentials, agent details, and other settings

```json
{
    "langfuse": {
        "project_name": "Your Project",
        "environment": "development",
        "langfuse_public_key": "your-public-key",
        "langfuse_secret_key": "your-secret-key",
        "langfuse_api_url": "your-otel-endpoint"
    },
    "agent": {
        "agentId": "your-agent-id", 
        "agentAliasId": "your-agent-alias-id"
    },
    "user": {
        "userId": "user123",
        "agent_model_id": "claude-3-5-sonnet-20241022-v2:0"
    },
    "question": {
        "question": "Your prompt to the agent"
    }
}
```

## Quick Start
Run the main script to test your agent integration:

```bash
python main.py
```

Or use the integration in your own code:

```python
from core import instrument_agent_invocation, flush_telemetry

@instrument_agent_invocation
def invoke_bedrock_agent(inputText, agentId, agentAliasId, sessionId, **kwargs):
    bedrock_rt_client = boto3.client('bedrock-agent-runtime')
    response = bedrock_rt_client.invoke_agent(
        inputText=inputText,
        agentId=agentId,
        agentAliasId=agentAliasId,
        sessionId=sessionId,
        enableTrace=True  # Required for instrumentation
    )
    return response

# Example usage with config
response = invoke_bedrock_agent(
    inputText="What's the weather in Seattle?",
    agentId="your-agent-id",
    agentAliasId="your-agent-alias-id",
    sessionId="user-session-123",
    streaming=False,  # Toggle streaming mode
    # OpenTelemetry endpoint configuration (using Langfuse as an example)
    langfuse_public_key="your-public-key",
    langfuse_secret_key="your-secret-key",
    langfuse_api_url="your-otel-endpoint",
    userId="user-123",
    tags=["bedrock-agent", "weather-demo"]
)

# Always flush telemetry before exiting
flush_telemetry()
```

## Deployment Options

### Cloud-Hosted Observability Platforms
Configure the integration using the cloud endpoint of your preferred OpenTelemetry-compatible observability platform.

### Self-Hosted Option
1. Deploy an OpenTelemetry collector or a compatible observability platform (like Langfuse, Jaeger, etc.) using Docker containers
2. Configure the integration using your self-hosted endpoint
3. Ideal for keeping all data within your AWS environment

## Trace Hierarchy

The integration creates a detailed span hierarchy:

```
L1: Root span "Bedrock Agent: [agent_id]"
  L2: "guardrail_pre"
  L2: "orchestrationTrace"
    L3: "llm" 
      L4: "OrchestrationModelInvocationOutput"
    L3: "rationale"
    L3: "code_interpreter"
      L4: "code_interpreter_result" 
    L3: "action_group"
      L4: "action_result"
    L3: "knowledgeBaseLookupInput"
      L4: "knowledgeBaseLookupOutput"
  L2: "postProcessingTrace"
    L3: "llm"
      L4: "PostProcessingModelInvocationOutput" 
  L2: "guardrail_post"
```

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `langfuse_public_key` | API key for OTEL endpoint | Environment variable |
| `langfuse_secret_key` | Secret key for OTEL endpoint | Environment variable |
| `langfuse_api_url` | OTEL API endpoint URL | https://us.cloud.langfuse.com/api/public/otel |
| `project_name` | Project name | Amazon Bedrock Agents |
| `environment` | Environment name | development |
| `userId` | User ID for tracking | anonymous |
| `tags` | Tags for filtering | [] |
| `streaming` | Enable streaming mode | False |

## Attribute Naming

This integration follows OpenTelemetry and OpenLLMetry attribute naming conventions as the standard evolves:

- `gen_ai.prompt` - Prompt text
- `gen_ai.completion` - Generated completion
- `gen_ai.usage.prompt_tokens` - Input tokens used
- `gen_ai.usage.completion_tokens` - Output tokens used
- `gen_ai.usage.total_tokens` - Total tokens used
- `session.id` - Session ID
- `customer_id` - User ID

## Known Issues and WIP for next release on 2025/4/10:
- Guardrail post processing creates duplicate when streaming for certain input types
- Change to OpenTelemetry meters for latency. Top level numbers on spans show incorrect but correct latency is published in the metadata for now
- Release instrumentor for Amazon Bedrock multi-agent-collaboration agents
- Add more standard gen AI semantics from OpenTelemetry