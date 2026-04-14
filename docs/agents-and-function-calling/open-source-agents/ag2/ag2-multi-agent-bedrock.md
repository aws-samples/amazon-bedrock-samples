---
tags:
    - Agents/ Function Calling
    - Open Source/ AG2
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-multi-agent-bedrock.ipynb){:target="_blank"}"

<h2>AG2 Multi-Agent GroupChat with Amazon Bedrock</h2>

<h3>Overview</h3>

[AG2](https://ag2.ai/) (formerly AutoGen) provides a powerful **GroupChat** feature for multi-agent orchestration. The `GroupChatManager` uses the LLM to automatically select the next speaker based on conversation context — no hardcoded routing graphs or handoff logic required.

In this notebook, we'll create a multi-agent research team using AG2's GroupChat with Amazon Bedrock as the LLM backend.

<h3>Context</h3>

AG2's GroupChat is its flagship multi-agent feature. Unlike frameworks that require explicit handoff definitions or routing graphs, AG2's `GroupChatManager` uses the LLM itself to determine which agent should speak next based on:
- Each agent's name and system message
- The current conversation history
- The task at hand

This makes it easy to add or remove agents without rewriting orchestration code. Combined with native Bedrock support, you get enterprise-grade multi-agent systems with AWS IAM authentication, VPC endpoints, and CloudTrail logging — all without wrapper libraries.

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

Set up the native Bedrock connection.

```python
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager, LLMConfig

# Native Bedrock support — no OpenAI key needed
# ---- ⚠️ Update region for your AWS setup ⚠️ ----
llm_config = LLMConfig(
    api_type="bedrock",
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    aws_region="us-east-1",
)
```

<h3>Create Specialist Agents</h3>

We'll create a team of three specialist agents, each with a distinct role:
- **Researcher**: Gathers information and provides factual analysis
- **Writer**: Creates clear, well-structured content from research findings
- **Critic**: Reviews content for accuracy and completeness, and terminates when satisfied

```python
with llm_config:
    researcher = AssistantAgent(
        name="Researcher",
        system_message=(
            "You are a research analyst. Search for information and provide "
            "factual analysis. Focus on key data points and trends. "
            "Cite sources when possible."
        ),
    )
    writer = AssistantAgent(
        name="Writer",
        system_message=(
            "You are a technical writer. Take research findings and create "
            "clear, well-structured summaries for business stakeholders. "
            "Use bullet points and concise language."
        ),
    )
    critic = AssistantAgent(
        name="Critic",
        system_message=(
            "You review content for accuracy, completeness, and clarity. "
            "Provide constructive feedback. When the output meets quality "
            "standards, say TERMINATE to end the conversation."
        ),
    )
    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
    )
```

<h3>Set Up GroupChat</h3>

The `GroupChat` collects agents into a group, and the `GroupChatManager` orchestrates the conversation. The `speaker_selection_method="auto"` setting lets the LLM decide which agent speaks next based on context.

```python
groupchat = GroupChat(
    agents=[user_proxy, researcher, writer, critic],
    messages=[],
    max_round=8,
    speaker_selection_method="auto",
)
manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
```

<h3>Run the Multi-Agent Conversation</h3>

The user proxy sends the initial request to the GroupChatManager, which then automatically routes messages to the appropriate agents.

```python
result = user_proxy.initiate_chat(
    manager,
    message=(
        "Research the current state of generative AI adoption in enterprise. "
        "Write a brief executive summary with key trends and challenges."
    ),
)
```

<h3>Understanding the Output</h3>

The GroupChatManager automatically routed the conversation through the agents:
- The **Researcher** provided data points and analysis
- The **Writer** structured the findings into an executive summary
- The **Critic** reviewed the output and said TERMINATE when satisfied

The key advantage of AG2's GroupChat: the `GroupChatManager` uses the LLM to automatically select the next speaker based on conversation context. You don't need to define explicit routing logic or handoff patterns.

<h2>Best Practices</h2>

- **Speaker selection**: Use `"auto"` for LLM-based routing, `"round_robin"` for predictable sequential flow
- **Max rounds**: Set `max_round` to prevent runaway conversations — 6-10 is a good starting range
- **Termination**: Include `TERMINATE` in one agent's system message to end gracefully
- **Agent count**: 3-5 agents works well; more agents increases speaker selection complexity
- **Distinct roles**: Give each agent a clear, non-overlapping system message for better routing
- **Native Bedrock advantages**: No OpenAI key, AWS IAM auth, supports Claude/Llama/Mistral/Titan, enterprise-grade security with VPC endpoints and CloudTrail logging

<h2>Next Steps</h2>

- **Single agent**: See [ag2-single-agent-bedrock.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-single-agent-bedrock.ipynb) for the basic setup
- **Tool use**: See [ag2-tool-use-bedrock.ipynb](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/agents-and-function-calling/open-source-agents/ag2/ag2-tool-use-bedrock.ipynb) for function calling with Bedrock
- **AG2 GroupChat Guide**: [docs.ag2.ai/docs/user-guide/basic-concepts/orchestration/group-chat](https://docs.ag2.ai/docs/user-guide/basic-concepts/orchestration/group-chat)
- **AG2 Documentation**: [docs.ag2.ai](https://docs.ag2.ai/)
- **AG2 Bedrock Guide**: [docs.ag2.ai/docs/user-guide/models/amazon-bedrock](https://docs.ag2.ai/docs/user-guide/models/amazon-bedrock)

<h2>Cleanup</h2>

No resources to clean up — this notebook uses only local compute and Bedrock API calls. To stop incurring Bedrock charges, simply stop running the notebook.
