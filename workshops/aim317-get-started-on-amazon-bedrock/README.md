# Amazon Bedrock Getting Started Workshop (AIM317)

Hands-on workshop that takes you from your first [Amazon Bedrock](https://aws.amazon.com/bedrock/)
API call to a working application in one session. You choose a model, ground it with a Managed
Knowledge Base, apply Guardrails, pick a service tier, then deploy and monitor what you built.

- Duration: 2 hours
- Level: 300 (you know AWS basics and are new to Amazon Bedrock)
- Format: Jupyter notebooks
- Region: `us-east-1` or `us-west-2`

> **Note:** This is sample code, for non-production usage. You should work with your security and
> legal teams to meet your organizational security, regulatory and compliance requirements before
> deployment.

## What you build

An employee travel assistant for AnyCompany, a fictional company. It starts as a plain chat and
gains one capability per module, so you finish with one deployed, monitored application rather
than a set of separate demos. It does two jobs:

- **Travel chat**: answers employees' travel questions from AnyCompany's travel policy, with
  citations.
- **Expense checks**: checks expense reports against the policy and returns APPROVED or FLAGGED,
  with a reason.

| Model | Used for |
|---|---|
| Claude Sonnet 5 (Anthropic) | Travel chat |
| gpt-oss-120b (OpenAI, open-weight) | Expense checks |
| GPT-5.6 Luna (OpenAI) | The OpenAI Responses API example in Module 1 |

## Modules

Run the notebooks in order. Each one adds a capability to the assistant.

| # | Notebook | What it does |
|---|---|---|
| 0 | [Setup](notebooks/00_setup.ipynb) | Installs the Python packages and turns on model invocation logging, so every call in the workshop is recorded. |
| 1 | [First call](notebooks/01_first_call.ipynb) | Builds a travel chat assistant with the Converse API: system prompt, inference parameters, streaming and conversation history. Also shows the same call with the Anthropic and OpenAI SDKs. |
| 2 | [Choosing a model](notebooks/02_choosing_a_model.ipynb) | Adds the expense check, runs both tasks on Claude Sonnet 5 and gpt-oss-120b, and picks a model for each by accuracy, latency and cost. Explains in-Region, geographic and global model IDs. |
| 3 | [Knowledge Base](notebooks/03_knowledge_base.ipynb) | Creates a Managed Knowledge Base from the policy documents, then uses `Retrieve` plus Converse so chat answers and expense checks come from the policy, with citations. |
| 4 | [Guardrails](notebooks/04_guardrails.ipynb) | Creates a guardrail that masks passport and card numbers, blocks requests to get around the policy, and checks that chat answers are supported by the policy. Attaches it to both tasks. |
| 5 | [Service tiers](notebooks/05_service_tiers.ipynb) | Runs the expense check on the Priority tier, reads which tier served each request, and explains when to use Standard, Priority and Flex. |
| 6 | [Deploy and monitor](notebooks/06_deploy_and_monitor.ipynb) | Deploys both tasks as one AWS Lambda function, then reviews invocation logs, CloudWatch metrics by service tier, and cost per feature from request tags. |
| - | [Stretch: AgentCore](notebooks/stretch_agentcore.ipynb) | Turns the assistant into a Strands agent with two tools and deploys it to Amazon Bedrock AgentCore Runtime with the AgentCore CLI. Optional; do it before Cleanup. |
| - | [Cleanup](notebooks/99_cleanup.ipynb) | Deletes the knowledge base, guardrail, Lambda function and S3 bucket, and turns off invocation logging. |

## Getting started

At an AWS event, your account and environment are set up for you. Open
`notebooks/00_setup.ipynb` in Jupyter, run it, then work through the notebooks in order. If you do
the optional stretch notebook, do it after Module 6 and before cleanup. Run `99_cleanup.ipynb` at the end.

In your own account, you need:

- Python 3.12 or later, and AWS credentials for `us-east-1` or `us-west-2`
- Access to Claude Sonnet 5, gpt-oss-120b and GPT-5.6 Luna in Amazon Bedrock
- For the stretch notebook only: Node.js and the AgentCore CLI 0.31.1 (`npm install -g @aws/agentcore@0.31.1`),
  and a CDK-bootstrapped account

To get only this workshop's folder instead of the whole samples repository:

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/aws-samples/amazon-bedrock-samples.git
cd amazon-bedrock-samples
git sparse-checkout set workshops/aim317-get-started-on-amazon-bedrock
cd workshops/aim317-get-started-on-amazon-bedrock
```

> **Note:** Module 0 replaces the account's model invocation logging configuration, and the cleanup
> notebook turns logging off. In an account that already uses invocation logging, save the
> configuration first and restore it afterwards.

## Repository layout

| Path | Contents |
|---|---|
| `notebooks/` | Workshop notebooks, run in order |
| `data/` | AnyCompany's travel policy and sample expense reports |
| `app/lambda_function.py` | The deployed assistant (Module 6) |
| `app/agent/` | The agent version (stretch notebook) |
| `requirements.txt` | Python packages, installed by Module 0 |

## Sample data

- `data/policies/`: seven short Markdown documents. Module 3 uploads them to Amazon S3 and
  ingests them into a Managed Knowledge Base.
- `data/expense_reports.json`: seven sample reports. `expected` is the verdict under the
  hand-typed rules in Module 2; `expected_with_policy` is the verdict under the full policy, used
  from Module 3 on.

## The deployed application

**Lambda (Module 6).** `app/lambda_function.py` is one stateless function with two requests:

| Request | Event | Returns | Model and tier |
|---|---|---|---|
| `ask` | `{"action": "ask", "question": "...", "history": [...]}` | `answer`, `citations`, `guardrail_intervened`, `history` | Claude Sonnet 5, Standard |
| `check_expense` | `{"action": "check_expense", "report": {...}}` | `status` (`approved` or `flagged`), `reasons`, `policy_refs`, `guardrail_intervened`, `service_tier` | gpt-oss-120b, Priority |

- Both requests retrieve policy passages from the knowledge base, use the guardrail from Module 4,
  and tag each call with `requestMetadata` (`feature: ask | check_expense`) for cost attribution.
- For a follow-up question, send the returned `history` with the next `ask` request.
- Configuration comes from the environment variables `KNOWLEDGE_BASE_ID`, `GUARDRAIL_ID` and
  `GUARDRAIL_VERSION`. Model IDs are in the code.
- The Module 6 notebook packages the function with boto3 1.43.98 or later, which Managed
  Knowledge Base retrieval needs.
- The role `aim317-lambda-role` allows `bedrock:InvokeModel` on the two models and the global inference
  profile, `bedrock:Retrieve` on the knowledge base and `bedrock:ApplyGuardrail` on the guardrail, plus
  `AWSLambdaBasicExecutionRole`.

**Agent (stretch).** `app/agent/` holds the same capabilities as tools for a Strands agent on
Claude Sonnet 5:

- `travel_agent.py` defines the tools `search_policy` and `check_expense`, and the agent.
- `main.py` is the AgentCore Runtime entrypoint. It takes `{"prompt": "..."}` and keeps one agent
  per session.
- `pyproject.toml` lists the agent's packages.

The stretch notebook creates a project with the AgentCore CLI, copies these files into it,
deploys it, and removes it at the end.

## Contributing

- Keep notebooks short: one or two sentences before each code cell, saying what it does. Avoid
  long explanations, error demos and side-by-side measurements.
- Every notebook has the same sections: Contents, Introduction, Setup, numbered sections, Try it,
  Conclusion and Next steps.
- Set model IDs in the notebook's first code cell. Name AWS resources `aim317-*`, and write cells
  so they can be run more than once.
- Run every notebook you change from top to bottom before you open a pull request, and save it
  with outputs cleared.
- No emojis in notebooks, code or output.
