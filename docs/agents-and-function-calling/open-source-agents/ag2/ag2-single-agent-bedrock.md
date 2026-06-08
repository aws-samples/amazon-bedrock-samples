---
tags:
    - Agents/ Function Calling
    - Open Source/ AG2
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-single-agent-bedrock.ipynb){:target="_blank"}"

<h2>AG2 Single Agent with Amazon Bedrock</h2>

<h3>Overview</h3>

[AG2](https://ag2.ai/) (formerly AutoGen) is an open-source multi-agent framework with **native Amazon Bedrock support** — no wrapper libraries or OpenAI API keys required.

In this notebook, we'll create a simple conversational agent using AG2 with Amazon Bedrock as the LLM backend.

<h3>Context</h3>

AG2 is a community-driven fork of AutoGen with 400K+ monthly PyPI downloads. Its key differentiator for Bedrock users is `LLMConfig(api_type="bedrock")` — native integration without wrapper libraries like LangChain's ChatBedrock.

This means you can use any Bedrock-supported model (Claude, Llama, Mistral, Titan, Command R+) with the standard AWS credential chain — IAM roles, environment variables, or `~/.aws/credentials`.

<h3>Prerequisites</h3>

- An AWS account with Amazon Bedrock model access enabled
- Python 3.10+
- AWS credentials configured (IAM role, environment variables, or `~/.aws/credentials`)
- Model access granted for `anthropic.claude-3-sonnet-20240229-v1:0` in your AWS region

<h2>Setup</h2>

Install the AG2 package. The `[openai]` extra includes the required dependencies for LLM integration.

```python
%pip install -q ag2[openai]
```

<h2>Code</h2>

<h3>Configure AG2 with Amazon Bedrock</h3>

AG2 supports Bedrock natively via `LLMConfig(api_type="bedrock")`. This uses the default AWS credential chain — IAM roles, environment variables, or `~/.aws/credentials` — so no API keys need to be hardcoded.

```python
from autogen import AssistantAgent, UserProxyAgent, LLMConfig

# Native Bedrock support — no OpenAI key needed
# ---- ⚠️ Update region for your AWS setup ⚠️ ----
llm_config = LLMConfig(
    api_type="bedrock",
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    aws_region="us-east-1",
)
```

<h3>Create Agents</h3>

AG2 uses a two-agent pattern: an `AssistantAgent` (LLM-powered reasoning) and a `UserProxyAgent` (executes tools, provides human input).

The `with llm_config:` context manager applies the Bedrock configuration to all agents created within it.

```python
with llm_config:
    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful AI assistant. Answer questions concisely.",
    )
    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
    )
```

<h3>Run the Conversation</h3>

The `initiate_chat` method sends a message from the `UserProxyAgent` to the `AssistantAgent` and starts the conversation loop. The assistant will use Amazon Bedrock (Claude) to generate its response.

```python
result = user_proxy.initiate_chat(
    assistant,
    message="What are the main benefits of using Amazon Bedrock for enterprise AI?",
)
```

<h2>Best Practices</h2>

- **Use IAM roles** over hardcoded credentials for production deployments
- **Set `max_consecutive_auto_reply`** to prevent infinite conversation loops
- **Use `human_input_mode="NEVER"`** for automated pipelines, `"TERMINATE"` for interactive use
- **Region selection**: Choose the AWS region closest to your workload for lower latency
- **Model selection**: AG2 supports all Bedrock models — use Claude for complex reasoning, Llama for open-source flexibility, Mistral for multilingual tasks

<h2>Next Steps</h2>

- **Tool use**: See [ag2-tool-use-bedrock.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-tool-use-bedrock.ipynb) for function calling with Bedrock
- **Multi-agent**: See [ag2-multi-agent-bedrock.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-multi-agent-bedrock.ipynb) for GroupChat orchestration
- **AG2 Documentation**: [docs.ag2.ai](https://docs.ag2.ai/)
- **AG2 GitHub**: [github.com/ag2ai/ag2](https://github.com/ag2ai/ag2)
- **AG2 Bedrock Guide**: [docs.ag2.ai/docs/user-guide/models/amazon-bedrock](https://docs.ag2.ai/docs/user-guide/models/amazon-bedrock)

<h2>Cleanup</h2>

No resources to clean up — this notebook uses only local compute and Bedrock API calls. To stop incurring Bedrock charges, simply stop running the notebook.
