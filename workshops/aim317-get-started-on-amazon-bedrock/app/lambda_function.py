"""AnyCompany travel assistant, deployed as one AWS Lambda function (Module 6).

The function handles two requests, assembled from what you built in Modules 1-5:

    {"action": "ask", "question": "...", "history": [...]}
        Answers a travel question from the policy, with citations.
        Claude Sonnet 5 on the Standard tier, with the guardrail.

    {"action": "check_expense", "report": {...}}
        Checks an expense report against the policy and returns approved or flagged.
        gpt-oss-120b on the Priority tier, with the guardrail.

The function is stateless: for a follow-up question, the caller sends the history returned
by the previous `ask` response.
"""

import json
import os
import re

import boto3

# Model IDs stay visible in the code. The "global." prefix lets Amazon Bedrock route chat
# requests to any AWS Region with capacity; gpt-oss-120b is called in this Region.
CHAT_MODEL_ID = "global.anthropic.claude-sonnet-5"
EXPENSE_MODEL_ID = "openai.gpt-oss-120b-1:0"

# Set by the Module 6 notebook.
KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
GUARDRAIL_ID = os.environ["GUARDRAIL_ID"]
GUARDRAIL_VERSION = os.environ["GUARDRAIL_VERSION"]

bedrock_runtime = boto3.client("bedrock-runtime")
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")

GUARDRAIL_CONFIG = {"guardrailIdentifier": GUARDRAIL_ID, "guardrailVersion": GUARDRAIL_VERSION}

CHAT_PROMPT = (
    "You are the travel assistant for AnyCompany, helping employees plan and manage business "
    "travel. Answer using only the AnyCompany policy passages provided with the question. Cite the "
    "passages you use by number, like [1]. If the passages do not answer the question, say so and "
    "suggest contacting the AnyCompany Travel Desk. Be friendly and concise: three sentences or "
    "fewer unless the employee asks for detail."
)

EXPENSE_PROMPT = (
    "You check AnyCompany expense reports against the AnyCompany policy passages inside the "
    "<policy> tags. Use only those passages. Reply with exactly two lines: first line APPROVED "
    "or FLAGGED, second line a one-sentence reason that cites the passage number, like [1]."
)


def retrieve(query, number_of_results=5):
    """Return the most relevant policy passages for a query."""
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={"managedSearchConfiguration": {"numberOfResults": number_of_results}},
    )
    return [
        {
            "text": result["content"]["text"],
            "source": result["location"]["s3Location"]["uri"].split("/")[-1],
        }
        for result in response["retrievalResults"]
    ]


def format_passages(passages):
    """Number the passages so the model can cite them."""
    return "\n\n".join(f"[{i}] (source: {p['source']})\n{p['text']}" for i, p in enumerate(passages, start=1))


def format_report(report):
    """Turn an expense report into the text the model reads."""
    lines = [f"Expense report {report['id']} - {report['employee']} - {report['trip']}"]
    for item in report["items"]:
        lines.append(f"- {item['type']}: {item['description']}: ${item['amount']:.2f}")
    return "\n".join(lines)


def get_text(response):
    """Return the text blocks of a Converse response, joined together."""
    return "".join(block["text"] for block in response["output"]["message"]["content"] if "text" in block)


def cited_sources(text, passages):
    """Return the passages cited in the text as [n]."""
    numbers = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})
    return [{"number": n, "source": passages[n - 1]["source"]} for n in numbers if 1 <= n <= len(passages)]


def ask(question, history):
    """Answer a travel question from the policy, with citations."""
    passages = retrieve(question)
    response = bedrock_runtime.converse(
        modelId=CHAT_MODEL_ID,
        system=[{"text": CHAT_PROMPT}],
        messages=history + [{
            "role": "user",
            "content": [
                # The passages are the source the grounding check compares the answer against.
                {"guardContent": {"text": {"text": format_passages(passages), "qualifiers": ["grounding_source"]}}},
                # The question is checked by the guardrail and used for the relevance check.
                {"guardContent": {"text": {"text": question, "qualifiers": ["query", "guard_content"]}}},
            ],
        }],
        inferenceConfig={"maxTokens": 2000},
        guardrailConfig=GUARDRAIL_CONFIG,
        requestMetadata={"workshop": "aim317", "feature": "ask"},
    )
    answer = get_text(response)
    intervened = response["stopReason"] == "guardrail_intervened"
    # Keep the history short: the question and answer, without the passages.
    history = history + [
        {"role": "user", "content": [{"text": question}]},
        {"role": "assistant", "content": [{"text": answer}]},
    ]
    return {
        "answer": answer,
        "citations": [] if intervened else cited_sources(answer, passages),
        "guardrail_intervened": intervened,
        "history": history,
    }


def check_expense(report):
    """Check an expense report against the policy on the Priority tier."""
    passages = []
    for item_type in sorted({item["type"] for item in report["items"]}):
        for passage in retrieve(f"AnyCompany {item_type} policy limits for a trip to {report['trip']}", 2):
            if passage["source"] not in [p["source"] for p in passages]:
                passages.append(passage)
    response = bedrock_runtime.converse(
        modelId=EXPENSE_MODEL_ID,
        system=[{"text": EXPENSE_PROMPT}],
        messages=[{
            "role": "user",
            "content": [
                {"text": f"<policy>\n{format_passages(passages)}\n</policy>"},
                # Only the report is checked by the guardrail.
                {"guardContent": {"text": {"text": format_report(report)}}},
            ],
        }],
        inferenceConfig={"maxTokens": 2000},
        guardrailConfig=GUARDRAIL_CONFIG,
        serviceTier={"type": "priority"},
        requestMetadata={"workshop": "aim317", "feature": "check_expense"},
    )
    text = get_text(response).strip()
    intervened = response["stopReason"] == "guardrail_intervened"
    match = re.search(r"\b(APPROVED|FLAGGED)\b", text)
    # Anything the check cannot decide goes to a person, so it is flagged.
    status = "approved" if match and match.group(1) == "APPROVED" and not intervened else "flagged"
    reason = text.splitlines()[-1].strip() if text else ""
    return {
        "status": status,
        "reasons": [reason],
        "policy_refs": [] if intervened else cited_sources(reason, passages),
        "guardrail_intervened": intervened,
        "service_tier": response.get("serviceTier", {}).get("type"),
    }


def lambda_handler(event, context):
    action = event.get("action")
    if action == "ask":
        return ask(event["question"], event.get("history", []))
    if action == "check_expense":
        return check_expense(event["report"])
    return {"error": f"Unknown action {action!r}. Use 'ask' or 'check_expense'."}
