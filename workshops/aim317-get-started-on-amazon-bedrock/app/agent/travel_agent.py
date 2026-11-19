"""AnyCompany travel assistant as a Strands agent.

The same two capabilities as the Lambda version, turned into tools: search_policy answers
questions from the travel policy, and check_expense checks expense items against it. The model
decides which tools to call, and in what order. Unlike the Lambda version, it applies no
guardrail and runs on the Standard tier.

Used two ways: imported by the stretch notebook to run the agent locally, and deployed to
Amazon Bedrock AgentCore Runtime by main.py.
"""

import os
import re

import boto3
from botocore.config import Config
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

REGION = os.environ.get("AWS_REGION") or boto3.session.Session().region_name

# Claude Sonnet 5 plans the work and writes the answer. The "global." prefix lets Amazon
# Bedrock route each request to any AWS Region with capacity.
AGENT_MODEL_ID = "global.anthropic.claude-sonnet-5"
# gpt-oss-120b checks expenses, as in Modules 2 to 5. It is called in this Region (no prefix).
EXPENSE_MODEL_ID = "openai.gpt-oss-120b-1:0"

KNOWLEDGE_BASE_NAME = "aim317-travel-policy"

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)


def find_knowledge_base_id():
    """Return the knowledge base ID from the environment, or look it up by name."""
    if os.environ.get("KNOWLEDGE_BASE_ID"):
        return os.environ["KNOWLEDGE_BASE_ID"]
    bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)
    summaries = bedrock_agent.list_knowledge_bases(maxResults=100)["knowledgeBaseSummaries"]
    for kb in summaries:
        if kb["name"] == KNOWLEDGE_BASE_NAME and kb["status"] == "ACTIVE":
            return kb["knowledgeBaseId"]
    raise RuntimeError("No AnyCompany travel policy knowledge base found. Run Module 3 first.")


KNOWLEDGE_BASE_ID = find_knowledge_base_id()


def retrieve(query, number_of_results=5):
    """Return the most relevant policy passages for a query."""
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={"managedSearchConfiguration": {"numberOfResults": number_of_results}},
    )
    return [
        {"text": result["content"]["text"], "source": result["location"]["s3Location"]["uri"].split("/")[-1]}
        for result in response["retrievalResults"]
    ]


def format_passages(passages):
    """Number the passages so the model can cite them."""
    return "\n\n".join(f"[{i}] (source: {p['source']})\n{p['text']}" for i, p in enumerate(passages, start=1))


@tool
def search_policy(query: str) -> str:
    """Search the AnyCompany travel and expense policy.

    Use this for any question about what the policy allows: limits, booking rules, what is
    reimbursed, and what to do when a trip is disrupted. Returns numbered policy passages,
    each with its source document.

    Args:
        query: What to look for, for example "hotel limit in Chicago".
    """
    return format_passages(retrieve(query, number_of_results=3))


EXPENSE_PROMPT = (
    "You check AnyCompany expense reports against the AnyCompany policy passages inside the "
    "<policy> tags. Use only those passages. Reply with exactly two lines: first line APPROVED "
    "or FLAGGED, second line a one-sentence reason that names the policy document."
)


@tool
def check_expense(trip: str, items: list[dict]) -> str:
    """Check expense items against the AnyCompany policy, and return APPROVED or FLAGGED with a reason.

    Use this when an employee asks whether something they spent, or plan to spend, is within policy.

    Args:
        trip: Where and how long, for example "Chicago, 1 night".
        items: The expenses. Each item has "type" (hotel, meals, flight, ground transportation
            or other), "description" and "amount" in US dollars.
    """
    # One search per expense type, as in Module 3: a single combined search can miss a policy.
    passages = []
    for item_type in sorted({str(item.get("type", "other")) for item in items}):
        for passage in retrieve(f"AnyCompany {item_type} policy limits for a trip to {trip}", 2):
            if passage["source"] not in [p["source"] for p in passages]:
                passages.append(passage)
    lines = [f"Trip: {trip}"] + [
        f"- {item.get('type')}: {item.get('description', '')}: ${float(item.get('amount', 0)):.2f}" for item in items
    ]
    response = bedrock_runtime.converse(
        modelId=EXPENSE_MODEL_ID,
        system=[{"text": EXPENSE_PROMPT}],
        messages=[{
            "role": "user",
            "content": [{"text": f"<policy>\n{format_passages(passages)}\n</policy>\n\n" + "\n".join(lines)}],
        }],
        inferenceConfig={"maxTokens": 2000},
        requestMetadata={"workshop": "aim317", "feature": "agent-check-expense"},
    )
    text = "".join(b["text"] for b in response["output"]["message"]["content"] if "text" in b).strip()
    match = re.search(r"\b(APPROVED|FLAGGED)\b", text)
    verdict = match.group(1) if match else "UNKNOWN"
    return f"{verdict}: {text.splitlines()[-1]}"


SYSTEM_PROMPT = (
    "You are the travel assistant for AnyCompany, helping employees with business travel and "
    "expenses. Use search_policy to answer questions about the policy, and check_expense to check "
    "whether specific expenses are within policy. Answer only from what the tools return; if they "
    "do not cover the question, say so and suggest contacting the AnyCompany Travel Desk. Be "
    "friendly and concise, and name the policy documents you relied on. Write plain text: no "
    "emojis and no headings."
)


def tool_call_counts(agent):
    """Return how many times the agent has called each tool so far."""
    return {name: metrics.call_count for name, metrics in agent.event_loop_metrics.tool_metrics.items()}


def create_agent():
    """Create a new travel assistant agent with its own conversation history."""
    return Agent(
        model=BedrockModel(
            model_id=AGENT_MODEL_ID,
            region_name=REGION,
            # Fail and retry a stalled response instead of waiting indefinitely.
            boto_client_config=Config(read_timeout=120, retries={"max_attempts": 3, "mode": "standard"}),
        ),
        system_prompt=SYSTEM_PROMPT,
        tools=[search_policy, check_expense],
        callback_handler=None,  # Do not print while the agent works; callers read the result.
    )
