"""Amazon Bedrock AgentCore Runtime entrypoint for the AnyCompany travel assistant.

AgentCore Runtime routes invocations with the same session ID to the session's dedicated microVM
and preserves context between them, so one agent per session retains the conversation history.
"""

from collections import OrderedDict

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from travel_agent import create_agent, tool_call_counts

app = BedrockAgentCoreApp()

MAX_SESSIONS = 100
agents_by_session = OrderedDict()


def get_agent(session_id):
    """Return the agent for this session, creating it on the first request."""
    if session_id not in agents_by_session:
        if len(agents_by_session) >= MAX_SESSIONS:
            agents_by_session.popitem(last=False)
        agents_by_session[session_id] = create_agent()
    agents_by_session.move_to_end(session_id)
    return agents_by_session[session_id]


@app.entrypoint
def invoke(payload, context):
    """Answer one message. The payload is {"prompt": "..."}."""
    agent = get_agent(context.session_id or "default")
    calls_before = tool_call_counts(agent)
    result = agent(payload.get("prompt", ""))
    calls_after = tool_call_counts(agent)
    return {
        "answer": str(result).strip(),
        "tools_used": {name: count - calls_before.get(name, 0) for name, count in calls_after.items()
                       if count > calls_before.get(name, 0)},
    }


if __name__ == "__main__":
    app.run()
