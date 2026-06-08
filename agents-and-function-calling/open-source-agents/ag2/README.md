# AG2 with Amazon Bedrock

[AG2](https://ag2.ai/) (formerly AutoGen) is an open-source multi-agent framework with
**native Amazon Bedrock support**. Unlike other frameworks that require wrapper libraries,
AG2 connects to Bedrock directly via `LLMConfig(api_type="bedrock")`.

## Examples

| Notebook | Description |
|----------|-------------|
| [ag2-single-agent-bedrock.ipynb](ag2-single-agent-bedrock.ipynb) | Basic single agent with Bedrock |
| [ag2-tool-use-bedrock.ipynb](ag2-tool-use-bedrock.ipynb) | Function calling with `register_for_llm` |
| [ag2-multi-agent-bedrock.ipynb](ag2-multi-agent-bedrock.ipynb) | Multi-agent GroupChat orchestration |

## Why AG2 + Bedrock?

- **Native support**: `LLMConfig(api_type="bedrock")` — no LangChain or wrapper needed
- **AWS credential chain**: IAM roles, environment variables, or `~/.aws/credentials`
- **All Bedrock models**: Claude, Llama, Mistral, Titan, Command R+
- **Multi-agent**: GroupChat with automatic speaker selection
- **500K+ monthly PyPI downloads**: Active community with frequent releases

## Quick Start

```bash
pip install ag2[openai]
```

```python
from autogen import AssistantAgent, UserProxyAgent, LLMConfig

llm_config = LLMConfig(
    api_type="bedrock",
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    aws_region="us-east-1",
)
```

## Resources

- [AG2 Documentation](https://docs.ag2.ai/)
- [AG2 GitHub](https://github.com/ag2ai/ag2)
- [AG2 Bedrock Guide](https://docs.ag2.ai/docs/user-guide/models/amazon-bedrock)
