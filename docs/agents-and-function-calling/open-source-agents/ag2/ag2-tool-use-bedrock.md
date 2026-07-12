---
tags:
    - Agents/ Function Calling
    - Open Source/ AG2
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-tool-use-bedrock.ipynb){:target="_blank"}"

<h2>AG2 Tool Use with Amazon Bedrock</h2>

<h3>Overview</h3>

[AG2](https://ag2.ai/) (formerly AutoGen) supports tool/function calling with Amazon Bedrock models natively. This notebook demonstrates AG2's dual registration pattern — `register_for_llm` (the LLM decides **when** to call a tool) and `register_for_execution` (the UserProxy **executes** it).

<h3>Context</h3>

AG2's tool calling approach separates **tool selection** from **tool execution**:
- The `AssistantAgent` (backed by a Bedrock model) decides which tool to call and with what arguments
- The `UserProxyAgent` actually executes the function and returns the result

This separation gives full control over tool execution — you can add sandboxing, logging, approval flows, or rate limiting at the execution layer without modifying the LLM configuration.

<h3>Prerequisites</h3>

- An AWS account with Amazon Bedrock model access enabled
- Python 3.10+
- AWS credentials configured (IAM role, environment variables, or `~/.aws/credentials`)
- Model access granted for `anthropic.claude-3-sonnet-20240229-v1:0` in your AWS region

<h2>Setup</h2>

Install the AG2 package.

```python
%pip install -q ag2[openai]
```

<h2>Code</h2>

<h3>Configure Bedrock</h3>

Set up the native Bedrock connection using AG2's `LLMConfig`.

```python
from typing import Annotated
from autogen import AssistantAgent, UserProxyAgent, LLMConfig

# Native Bedrock support — no OpenAI key needed
# ---- ⚠️ Update region for your AWS setup ⚠️ ----
llm_config = LLMConfig(
    api_type="bedrock",
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    aws_region="us-east-1",
)
```

<h3>Define Tools</h3>

Define Python functions that will be available to the agent. Use `Annotated` type hints to provide parameter descriptions — Bedrock models use these to understand the tool schema.

```python
def get_stock_price(
    symbol: Annotated[str, "Stock ticker symbol (e.g., AMZN, GOOGL)"],
) -> dict:
    """Look up the current stock price for a given ticker symbol."""
    # Simulated data for demo purposes
    prices = {
        "AMZN": {"price": 186.45, "change": "+2.3%"},
        "GOOGL": {"price": 175.20, "change": "-0.8%"},
        "MSFT": {"price": 420.15, "change": "+1.1%"},
    }
    return prices.get(symbol.upper(), {"error": f"Unknown symbol: {symbol}"})


def get_company_info(
    company: Annotated[str, "Company name to look up"],
) -> str:
    """Get brief information about a company."""
    info = {
        "amazon": "Amazon.com, Inc. — e-commerce, cloud computing (AWS), AI, streaming.",
        "google": "Alphabet Inc. — search, advertising, cloud, AI research.",
        "microsoft": "Microsoft Corp. — software, cloud (Azure), gaming, AI.",
    }
    return info.get(company.lower(), f"No info available for {company}")
```

<h3>Create Agents and Register Tools</h3>

AG2 uses a **dual registration** pattern:
1. `register_for_llm` — tells the AssistantAgent (LLM) that this tool exists and how to call it
2. `register_for_execution` — tells the UserProxyAgent to execute the function when the LLM requests it

This separation means the LLM decides **when** to call a tool, but the UserProxy controls **how** it's executed.

```python
with llm_config:
    assistant = AssistantAgent(
        name="FinanceAssistant",
        system_message="You are a financial assistant. Use the available tools to look up stock data and company information. Provide clear analysis based on the data.",
    )
    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
    )

# Register tools for the LLM (tool schema) and for execution (function call)
assistant.register_for_llm(description="Look up current stock price")(get_stock_price)
assistant.register_for_llm(description="Get company information")(get_company_info)
user_proxy.register_for_execution()(get_stock_price)
user_proxy.register_for_execution()(get_company_info)
```

<h3>Run the Conversation</h3>

The assistant will use Bedrock (Claude) to decide which tools to call, and the user proxy will execute them.

```python
result = user_proxy.initiate_chat(
    assistant,
    message="Compare Amazon and Google — show me their stock prices and company info.",
)
```

<h2>Best Practices</h2>

- **Use `Annotated` type hints** for parameter descriptions — Bedrock models use these for tool schemas
- **Keep tools simple and focused** — one function per responsibility
- **Use `max_consecutive_auto_reply`** to limit tool call loops and prevent runaway execution
- **Return structured data** (dict/JSON) from tools for consistent parsing
- **Add docstrings** to tool functions — the LLM uses these to understand when to call each tool
- **Error handling**: Return error messages as data (not exceptions) so the LLM can reason about failures

<h2>Next Steps</h2>

- **Multi-agent**: See [ag2-multi-agent-bedrock.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-multi-agent-bedrock.ipynb) for GroupChat orchestration with tools
- **Single agent**: See [ag2-single-agent-bedrock.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-single-agent-bedrock.ipynb) for the basic setup
- **AG2 Tool Use Guide**: [docs.ag2.ai/docs/user-guide/basic-concepts/tools](https://docs.ag2.ai/docs/user-guide/basic-concepts/tools)
- **AG2 Documentation**: [docs.ag2.ai](https://docs.ag2.ai/)

<h2>Cleanup</h2>

No resources to clean up — this notebook uses only local compute and Bedrock API calls. To stop incurring Bedrock charges, simply stop running the notebook.
