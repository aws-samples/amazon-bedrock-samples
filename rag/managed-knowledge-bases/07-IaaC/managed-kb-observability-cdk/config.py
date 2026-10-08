# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration for the agentic-RAG observability CDK app.

Everything tunable lives here. Account and region default to whatever the CDK CLI
resolves from your AWS profile (``CDK_DEFAULT_ACCOUNT`` / ``CDK_DEFAULT_REGION``),
so the app deploys with no edits at all; override below only if you want to pin them.
"""

import os


class EnvSettings:
    """Deployment target and the name prefix applied to every resource."""

    # Leave as-is to use the CLI's resolved account/region (from your AWS profile).
    # Pin them by replacing the os.getenv(...) call with a literal string.
    ACCOUNT_ID = os.getenv("CDK_DEFAULT_ACCOUNT")
    ACCOUNT_REGION = os.getenv("CDK_DEFAULT_REGION", "us-west-2")

    # Prefix for every resource, stack, and dashboard name. Changing this gives you a
    # fully isolated copy of the solution, so two deployments can coexist in one account.
    # Keep it short — it feeds role names and the AgentCore runtime name (see AgentConfig).
    PROJECT_NAME = "bmkb-obs-cdk"


class KbConfig:
    """The two managed knowledge bases and their S3 prefixes."""

    # Each KB owns one prefix in the shared bucket; inclusionPrefixes keeps them isolated
    # so the agent has two distinct corpora to route between (the semantic-routing story).
    FINANCIAL_PREFIX = "financial/"
    WEATHER_PREFIX = "weather/"

    # Embedding: "MANAGED" lets Bedrock pick and operate the embedding model — bundled at
    # no extra cost, no model access to enable, no ARN to supply. Switch to "CUSTOM" and
    # set CUSTOM_EMBEDDING_MODEL_ARN to bring your own (billed per token at ingestion).
    #
    # The ARN must be a DIRECT foundation-model ARN — inference profile / CRIS ARNs are
    # rejected. Changing embedding config REPLACES the KB, which re-embeds all data.
    EMBEDDING_MODEL_TYPE = "MANAGED"
    CUSTOM_EMBEDDING_MODEL_ARN = None  # e.g. "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v2:0"

    # Reranking is NOT a KB property. A managed KB reranks at retrieve time with a bundled
    # managed reranker. A custom reranker is a query-time choice — here, GatewayConfig below.


class GatewayConfig:
    """AgentCore Gateway exposing each KB's AgenticRetrieveStream as an MCP tool."""

    # MANAGED for both = the bundled service models (no extra cost, nothing to enable).
    # These are the agentic-retrieval knobs the Gateway connector passes to the KB.
    FOUNDATION_MODEL_TYPE = "MANAGED"
    RERANKING_MODEL_TYPE = "MANAGED"


class AgentConfig:
    """The instrumented Strands agent hosted on AgentCore Runtime."""

    # The agent's own reasoning model — this is the Layer 6 (token usage) spend.
    # Needs Bedrock model access enabled in the target account.
    MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    IMAGE_TAG = "latest"
    NETWORK_MODE = "PUBLIC"  # or "VPC"

    # AgentCore runtime names allow letters, digits and underscores only — no hyphens.
    RUNTIME_NAME = f"{EnvSettings.PROJECT_NAME}_agent".replace("-", "_")

    # Bump to force CodeBuild to rebuild + repush the image on the next deploy.
    BUILD_VERSION = "1"


class EvalConfig:
    """Continuous (online) evaluation of live agent sessions."""

    ONLINE_EVAL_NAME = f"{EnvSettings.PROJECT_NAME}_online_eval".replace("-", "_")

    # ⚠️ 100% is set for the blog experiment so every session is scored and results show
    # up immediately. This is NOT a production recommendation: online evaluation invokes
    # an LLM-as-judge per sampled session, so cost scales with this rate × traffic volume.
    # Pick a rate that fits your quality-monitoring needs, budget, and org cost policies.
    SAMPLING_PERCENTAGE = 100
    SESSION_TIMEOUT_MINUTES = 30

    EVALUATORS = [
        "Builtin.Correctness",
        "Builtin.Faithfulness",
        "Builtin.ToolSelectionAccuracy",
        "Builtin.ResponseRelevance",
    ]
