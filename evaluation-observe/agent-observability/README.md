# Bedrock Agent Instrumentation

An OpenTelemetry instrumentation framework for AWS Bedrock Agents using OpenInference semantic convention.

## Files
- `main.py`: Core instrumentation wrapper for Bedrock Agent invocations using python file
- `example-notebook.ipynb`: Core instrumentation wrapper for Bedrock Agent invocations using a jupyter notebook
- `config.py`: Configuration for different tracing backends (Arize, Langfuse). Please configure your API keys here
- `processors.py`: Processes traces (preprocessing, orchestration, etc.)
- `handlers.py`: Handles trace events (LLM calls, tools, etc.) 
- `utils.py`: Utilities for timing and trace management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Decorate your invoke_agent api call:
```python
@instrument_agent_invocation
def invoke_bedrock_agent(inputText: str, agentId: str, agentAliasId: str, sessionId: str):
    bedrock_rt_client = boto3.client('bedrock-agent-runtime')
    response = bedrock_rt_client.invoke_agent(
        inputText=inputText,
        agentId=agentId,
        agentAliasId=agentAliasId,
        sessionId=sessionId,
        enableTrace=True
    )
    return response
```


3. Modify main.py:
```python
if __name__ == "__main__":
    try:
        agentId='agent-id',
        agentAliasId='agent-alias-is'
        sessionId='define-session-id'
        trace_collector="arize_cloud" # langfuse, and arize_local are other options
        userId = "Somename"
        questions = "your prompt goes here"

        invoke_bedrock_agent(
            inputText=question,
            agentId=agentId,
            agentAliasId=agentAliasId,
            sessionId=sessionId,
            userId=userId,
            provider=trace_collector,
            show_traces=True
        )
    except Exception as e:
        logger.error(f"Error invoking agent: {str(e)}")
```