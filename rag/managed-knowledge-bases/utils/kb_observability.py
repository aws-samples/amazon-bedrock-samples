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
utils.kb_observability
======================
Observability helpers for Amazon Bedrock **Managed** Knowledge Bases plugged into
AgentCore. Shared backbone for the observability and RAG-evaluation notebooks so
that reading each telemetry layer is a single call instead of repeated boilerplate.

Telemetry layers covered here (see the notebook for the full 7-layer taxonomy):

    1  KB-native metrics    → get_kb_metrics        (AWS/Bedrock/KnowledgeBases)
    2  KB ingestion logs    → query_ingestion_logs  (APPLICATION_LOGS)
    3  Retrieval quality    → extract_retrieval_quality + emit_retrieval_metrics
    4  Gateway metrics      → get_gateway_metrics    (AWS/Bedrock-AgentCore)
    5  Traces (spans)       → query_spans            (aws/spans)
    dashboard              → build_kb_dashboard     (put_dashboard over layers 1/3/4/5)

Metric facts are verified against the AWS docs for managed KB observability. Note
there is **no `Latency` metric** in AWS/Bedrock/KnowledgeBases — request latency is
carried by X-Ray traces, not a CloudWatch metric.

Usage
-----
::

    from utils.kb_observability import get_kb_metrics, extract_retrieval_quality
    df = get_kb_metrics(kb_id, region_name="us-west-2")
"""

from __future__ import annotations

import json
import time
import statistics
from datetime import datetime, timedelta

import boto3
import pandas as pd

# ── Verified constants ────────────────────────────────────────────────
KB_NAMESPACE = "AWS/Bedrock/KnowledgeBases"
GATEWAY_NAMESPACE = "AWS/Bedrock-AgentCore"
SPANS_LOG_GROUP = "aws/spans"
RETRIEVAL_QUALITY_NAMESPACE = "BMKB/RetrievalQuality"   # Layer 3
COST_NAMESPACE = "BMKB/Cost"                            # Layer 6 (cost + quota)
EVAL_NAMESPACE = "BMKB/Evaluation"                      # Layer 7 (quality scores)

# Metrics published under AWS/Bedrock/KnowledgeBases. There is intentionally NO
# "Latency" here — latency lives in X-Ray traces. RawDataSize is in gigabytes;
# TotalIterationCount is emitted for AgenticRetrieveStream only.
_KB_COUNT_METRICS = [
    "Invocations",
    "ClientErrors",
    "ServerErrors",
    "Throttles",
    "TotalIterationCount",
]
_KB_STORAGE_METRIC = "RawDataSize"

# Gateway metrics under AWS/Bedrock-AgentCore.
_GW_COUNT_METRICS = ["Invocations", "SystemErrors", "UserErrors", "Throttles"]
_GW_LATENCY_METRIC = "Latency"


def _query_logs_insights(logs_client, log_group: str, query: str, hours: int = 1) -> list:
    """Run a CloudWatch Logs Insights query and return its result rows.

    Parameters
    ----------
    logs_client : botocore client
        A ``boto3`` ``logs`` client.
    log_group : str
        Log group to query.
    query : str
        Logs Insights query string.
    hours : int
        Look-back window in hours.

    Returns
    -------
    list
        The ``results`` list from ``get_query_results`` (empty on failure or no data).
    """
    start = datetime.now() - timedelta(hours=hours)
    try:
        query_id = logs_client.start_query(
            logGroupName=log_group,
            startTime=int(start.timestamp()),
            endTime=int(datetime.now().timestamp()),
            queryString=query,
        )["queryId"]
    except logs_client.exceptions.ResourceNotFoundException:
        return []

    for _ in range(30):
        result = logs_client.get_query_results(queryId=query_id)
        if result["status"] in ("Complete", "Failed"):
            break
        time.sleep(2)
    return result.get("results", []) if result["status"] == "Complete" else []


def get_kb_metrics(kb_id: str, region_name: str, hours: int = 1) -> pd.DataFrame:
    """Pull Layer-1 KB-native metrics from ``AWS/Bedrock/KnowledgeBases``.

    Parameters
    ----------
    kb_id : str
        Knowledge base id (the ``KnowledgeBaseId`` dimension is ``knowledge-base/{id}``).
    region_name : str
        AWS region.
    hours : int
        Look-back window in hours.

    Returns
    -------
    pandas.DataFrame
        Columns ``metric``, ``operation``, ``stat``, ``value``. One row per metric
        that has data in the window. Count metrics are summed; ``RawDataSize`` is
        an average (gigabytes).
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    kb_dim_value = f"knowledge-base/{kb_id}"

    available = cw.list_metrics(Namespace=KB_NAMESPACE)["Metrics"]
    rows = []
    for m in available:
        name = m["MetricName"]
        dims = {d["Name"]: d["Value"] for d in m["Dimensions"]}
        # Keep only metrics scoped to this KB or non-KB-scoped operation metrics.
        if dims.get("KnowledgeBaseId") not in (None, kb_dim_value):
            continue
        stat = "Average" if name == _KB_STORAGE_METRIC else "Sum"
        resp = cw.get_metric_statistics(
            Namespace=KB_NAMESPACE, MetricName=name, Dimensions=m["Dimensions"],
            StartTime=start, EndTime=end, Period=300, Statistics=[stat],
        )
        points = resp.get("Datapoints", [])
        if not points:
            continue
        latest = sorted(points, key=lambda p: p["Timestamp"])[-1]
        rows.append({
            "metric": name,
            "operation": dims.get("Operation", ""),
            "stat": stat,
            "value": round(latest[stat], 2),
        })
    return pd.DataFrame(rows, columns=["metric", "operation", "stat", "value"])


def get_ingestion_stats(kb_id: str, region_name: str) -> pd.DataFrame:
    """Pull Layer-2 ingestion statistics from the ingestion-job API (authoritative).

    The per-document ``APPLICATION_LOGS`` (see :func:`query_ingestion_logs`) give the
    lifecycle status of each file, but the ingestion job itself carries the aggregate
    counts — documents scanned, indexed, failed, skipped — which is the reliable
    ingestion-quality signal. These come from ``get_ingestion_job`` (not CloudWatch).

    Parameters
    ----------
    kb_id : str
        Knowledge base id.
    region_name : str
        AWS region.

    Returns
    -------
    pandas.DataFrame
        One row per (data source, ingestion job) with the job status and its
        ``statistics`` counts flattened into columns. Most recent jobs first.
    """
    agent = boto3.client("bedrock-agent", region_name=region_name)
    rows = []
    for ds in agent.list_data_sources(knowledgeBaseId=kb_id).get("dataSourceSummaries", []):
        ds_id = ds["dataSourceId"]
        jobs = agent.list_ingestion_jobs(
            knowledgeBaseId=kb_id, dataSourceId=ds_id, maxResults=5,
        ).get("ingestionJobSummaries", [])
        for job in jobs:
            row = {"data_source": ds_id, "job_id": job["ingestionJobId"], "status": job["status"]}
            row.update(job.get("statistics", {}))
            rows.append(row)
    return pd.DataFrame(rows)


def query_ingestion_logs(kb_id: str, region_name: str, query: str | None = None, hours: int = 6) -> list:
    """Query Layer-2 ingestion ``APPLICATION_LOGS`` via Logs Insights (per-document detail).

    Parameters
    ----------
    kb_id : str
        Knowledge base id.
    region_name : str
        AWS region.
    query : str, optional
        Logs Insights query. Defaults to listing each document with its crawl/sync/
        index status. (``chunk_statistics`` is requested opportunistically — it is
        not emitted on every KB/ingestion, so it may be blank.)
    hours : int
        Look-back window in hours.

    Returns
    -------
    list
        Result rows from Logs Insights (each row is a list of ``{field, value}``).
    """
    logs_client = boto3.client("logs", region_name=region_name)
    log_group = f"/aws/vendedlogs/bedrock/knowledge-base/APPLICATION_LOGS/{kb_id}"
    if query is None:
        query = (
            "fields event.document_id, event.connector_document_status.Status, "
            "event.crawl_status.Status, event.index_status.Status, "
            "event.chunk_statistics.created, @timestamp "
            "| filter event_type = 'StartIngestionJob.ResourceStatusChanged' "
            "| sort @timestamp desc | limit 50"
        )
    return _query_logs_insights(logs_client, log_group, query, hours=hours)


def extract_retrieval_quality(response: dict) -> dict:
    """Derive Layer-3 retrieval-quality stats from a ``Retrieve`` response.

    Nothing emits these signals by default — they are computed from the relevance
    scores in the response body.

    Parameters
    ----------
    response : dict
        A boto3 ``retrieve`` response (has a ``retrievalResults`` list, each item
        with a ``score``).

    Returns
    -------
    dict
        ``chunk_count`` (results returned) and ``distinct_docs`` (how many source
        documents they span — a coverage signal). When scores are present, also
        ``score_min`` / ``score_mean`` / ``score_max`` / ``score_spread`` (max − min),
        rounded to 4 places.
    """
    results = response.get("retrievalResults", [])
    scores = [r["score"] for r in results if "score" in r]
    # Each result names the chunk + source document it came from (retrieval-time
    # provenance). Distinct source docs across the results is a coverage signal:
    # many results from one doc = narrow; spread across docs = broad.
    docs = {
        r.get("metadata", {}).get("_document_title")
        or r.get("metadata", {}).get("_source_uri")
        or r.get("documentId")
        for r in results
    }
    docs.discard(None)
    stats = {"chunk_count": len(results), "distinct_docs": len(docs)}
    if scores:
        stats.update({
            "score_min": round(min(scores), 4),
            "score_mean": round(statistics.mean(scores), 4),
            "score_max": round(max(scores), 4),
            "score_spread": round(max(scores) - min(scores), 4),
        })
    return stats


# ── Layer 3 (agentic) ─────────────────────────────────────────────────
# When the Gateway exposes the AgenticRetrieveStream tool (multi-step planning +
# rerank + a synthesized, cited answer), the retrieval result no longer carries a
# per-chunk relevance ``score`` — so the score-stats above do not apply. Instead we
# read what the *deployed agent actually retrieved* from its own telemetry and derive
# two reference-free metric families:
#
#   A) Retrieval-set    — how much/how redundant/how large the retrieved context is.
#   C) Grounding        — how well the synthesized answer is anchored to the results
#                         (citation coverage) and how much of the retrieved set the
#                         answer actually used (utilization / precision proxy).
#
# Where the data comes from (verified, us-west-2, 2026-07-08):
#   • The agent's tool-call span (``execute_tool …___AgenticRetrieveStream``) carries
#     only tool METADATA (name, description, status) — NOT the result payload.
#   • The full payload (``results`` + ``generatedResponse.answer`` + ``citations``)
#     is emitted to the RUNTIME log group by the ``opentelemetry.instrumentation
#     .botocore.bedrock-runtime`` scope, inside ``body.content[].text`` as a JSON
#     string. Those records lack a ``session.id``, so we correlate them to a session
#     by ``traceId`` (join against the session's spans).
#   • The agentic *trace* events (planning/iteration steps) stream over MCP
#     ``notifications/message`` and are NOT persisted to any log — so a
#     planning/iteration metric family is intentionally absent here.


def fetch_agentic_retrievals(agent_id: str, session_trace_ids: set, region_name: str, hours: int = 1) -> list:
    """Pull the AgenticRetrieveStream payloads a deployed agent produced this session.

    Reads the agent's runtime log group and returns the raw agentic-retrieve response
    objects (``results`` + ``generatedResponse``) correlated to the current session by
    ``traceId``. This is the agent's *real* retrieval telemetry — no extra retrieval
    call is made.

    Parameters
    ----------
    agent_id : str
        Runtime agent id (``<name>-<hash>``); the log group is
        ``/aws/bedrock-agentcore/runtimes/{agent_id}-DEFAULT``.
    session_trace_ids : set
        The ``traceId`` values belonging to the session (typically
        ``{s["traceId"] for s in query_spans(...) if <session filter>}``). Only
        payloads whose record ``traceId`` is in this set are returned.
    region_name : str
        AWS region.
    hours : int
        Look-back window in hours.

    Returns
    -------
    list
        One dict per agentic-retrieve call, each with ``traceId`` and the parsed
        payload (``results``: list, ``generatedResponse``: {``answer``, ``citations``}).
        Empty if none correlate (e.g. spans not yet landed).
    """
    logs_client = boto3.client("logs", region_name=region_name)
    log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-DEFAULT"
    query = (
        'fields @message '
        '| filter scope.name = "opentelemetry.instrumentation.botocore.bedrock-runtime" '
        'and (@message like /generatedResponse/ or @message like /retrievalResults/) '
        '| sort @timestamp asc | limit 100'
    )
    rows = _query_logs_insights(logs_client, log_group, query, hours=hours)
    out = []
    for row in rows:
        msg = next((f["value"] for f in row if f["field"] == "@message"), "")
        try:
            record = json.loads(msg)
        except json.JSONDecodeError:
            continue
        trace_id = record.get("traceId")
        if session_trace_ids and trace_id not in session_trace_ids:
            continue
        for part in record.get("body", {}).get("content", []):
            if not (isinstance(part, dict) and "text" in part):
                continue
            try:
                payload = json.loads(part["text"])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and ("generatedResponse" in payload or "results" in payload):
                # Normalise: the API returns "results"; some records use "retrievalResults".
                results = payload.get("results", payload.get("retrievalResults", []))
                out.append({
                    "traceId": trace_id,
                    "results": results,
                    "generatedResponse": payload.get("generatedResponse", {}) or {},
                })
    return out


def extract_agentic_retrieval_quality(payload: dict) -> dict:
    """Derive Layer-3 metrics from one AgenticRetrieveStream payload (families A + C).

    Reference-free — computed entirely from the retrieved chunks and the synthesized,
    cited answer (no LLM judge, no ground truth). ``score``-based stats do not apply to
    agentic retrieval (the API returns no per-chunk score); these signals replace them.

    Parameters
    ----------
    payload : dict
        One item from :func:`fetch_agentic_retrievals` — ``results`` (list of chunks,
        each with ``content.text`` and ``metadata``) and ``generatedResponse``
        (``answer`` + ``citations``).

    Returns
    -------
    dict
        **A. Retrieval-set** — ``chunk_count`` (chunks returned), ``distinct_docs`` /
        ``distinct_chunks`` (coverage), ``duplicate_rate`` (``1 − distinct/total``;
        redundant retrieval), ``avg_chunk_chars`` / ``total_context_chars`` (context
        budget). **C. Grounding** — ``num_citations`` (citation spans in the answer),
        ``cited_chunks`` (distinct results actually referenced), ``retrieval_utilization``
        (``cited_chunks / chunk_count``; a precision proxy — low means the retriever
        over-fetched), ``grounded_coverage`` (fraction of the answer text covered by a
        citation span; a reference-free faithfulness proxy), ``answer_chars`` (answer
        length in CHARACTERS — a verbosity signal, not tokens).
    """
    results = payload.get("results", []) or []
    gen = payload.get("generatedResponse", {}) or {}

    # ── A. Retrieval-set ──
    docs = {r.get("metadata", {}).get("_document_id") for r in results}
    docs.discard(None)
    chunks = {r.get("metadata", {}).get("_chunk_id") for r in results}
    chunks.discard(None)
    lengths = [len(r.get("content", {}).get("text", "")) for r in results]
    stats = {
        "chunk_count": len(results),
        "distinct_docs": len(docs),
        "distinct_chunks": len(chunks),
        "duplicate_rate": round(1 - len(chunks) / len(results), 3) if results else 0.0,
        "avg_chunk_chars": int(statistics.mean(lengths)) if lengths else 0,
        "total_context_chars": sum(lengths),
    }

    # ── C. Grounding / citation ──
    citations = gen.get("citations", []) or []
    cited = {ref.get("resultIndex")
             for c in citations for ref in c.get("references", [])}
    cited.discard(None)
    answer_len = len(gen.get("answer", "") or "")
    cited_len = sum(c.get("endIndex", 0) - c.get("startIndex", 0) for c in citations)
    stats.update({
        "num_citations": len(citations),
        "cited_chunks": len(cited),
        "retrieval_utilization": round(len(cited) / len(results), 3) if results else 0.0,
        "grounded_coverage": round(min(cited_len, answer_len) / answer_len, 3) if answer_len else 0.0,
        "answer_chars": answer_len,
    })
    return stats


def emit_retrieval_metrics(stats: dict, kb_id: str, region_name: str) -> None:
    """Publish Layer-3 retrieval-quality stats as CloudWatch custom metrics.

    Uses ``put_metric_data`` to send the derived stats to the
    ``BMKB/RetrievalQuality`` namespace (dimension ``KnowledgeBaseId``), so they
    become graphable and alarmable alongside the KB's native metrics.

    Parameters
    ----------
    stats : dict
        Output of :func:`extract_retrieval_quality`.
    kb_id : str
        Knowledge base id (recorded as the metric dimension).
    region_name : str
        AWS region.
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    cw.put_metric_data(
        Namespace=RETRIEVAL_QUALITY_NAMESPACE,
        MetricData=[
            {
                "MetricName": name,
                "Value": float(value),
                "Dimensions": [{"Name": "KnowledgeBaseId", "Value": kb_id}],
            }
            for name, value in stats.items()
        ],
    )


def emit_cost_metrics(cost_usd: float, quota_tokens: int, kb_id: str, region_name: str) -> None:
    """Publish Layer-6 cost + quota as CloudWatch custom metrics (``BMKB/Cost``).

    Cost and quota are distinct (billing vs throttling). Both are graphed so the
    dashboard shows dollars *and* TPM/TPD burn side by side.

    Parameters
    ----------
    cost_usd : float
        Session dollar cost (flat, from actual tokens).
    quota_tokens : int
        Session quota consumed (input + output*burndown).
    kb_id : str
        Knowledge base id (metric dimension).
    region_name : str
        AWS region.
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    cw.put_metric_data(
        Namespace=COST_NAMESPACE,
        MetricData=[
            {"MetricName": "SessionCostUsd", "Value": float(cost_usd), "Unit": "None",
             "Dimensions": [{"Name": "KnowledgeBaseId", "Value": kb_id}]},
            {"MetricName": "SessionQuotaTokens", "Value": float(quota_tokens), "Unit": "Count",
             "Dimensions": [{"Name": "KnowledgeBaseId", "Value": kb_id}]},
        ],
    )


def emit_query_cost_metrics(per_query: list, kb_id: str, region_name: str) -> None:
    """Publish Layer-6 **per-query** cost + quota to ``BMKB/Cost``.

    Complements :func:`emit_cost_metrics` (session totals) by emitting one metric
    series *per user query*, using a ``Query`` dimension so each question is its own
    graphable line. This is the "cost to serve one KB-grounded answer" signal — the
    number a team running a KB-backed assistant budgets on.

    Parameters
    ----------
    per_query : list of dict
        One item per query, each with ``query`` (str, becomes the ``Query`` dimension,
        truncated to 60 chars), ``cost_usd`` (float), and ``quota_tokens`` (int).
    kb_id : str
        Knowledge base id (metric dimension).
    region_name : str
        AWS region.
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    data = []
    for q in per_query:
        dims = [{"Name": "KnowledgeBaseId", "Value": kb_id},
                {"Name": "Query", "Value": str(q["query"])[:60]}]
        data.append({"MetricName": "QueryCostUsd", "Value": float(q["cost_usd"]),
                     "Unit": "None", "Dimensions": dims})
        data.append({"MetricName": "QueryQuotaTokens", "Value": float(q["quota_tokens"]),
                     "Unit": "Count", "Dimensions": dims})
    if data:
        cw.put_metric_data(Namespace=COST_NAMESPACE, MetricData=data)


def emit_eval_scores(scores: list, kb_id: str, region_name: str) -> None:
    """Publish Layer-7 evaluation scores as CloudWatch custom metrics (``BMKB/Evaluation``).

    One metric per evaluator (metric name = evaluator name), so each quality
    dimension (Correctness, Faithfulness, …) becomes its own graphable series.

    Parameters
    ----------
    scores : list of dict
        Each item needs ``evaluator`` (str) and ``score`` (0–1 float or None).
        Items with a ``None`` score are skipped.
    kb_id : str
        Knowledge base id (metric dimension).
    region_name : str
        AWS region.
    """
    data = [
        {"MetricName": s["evaluator"], "Value": float(s["score"]), "Unit": "None",
         "Dimensions": [{"Name": "KnowledgeBaseId", "Value": kb_id}]}
        for s in scores if s.get("score") is not None
    ]
    if data:
        boto3.client("cloudwatch", region_name=region_name).put_metric_data(
            Namespace=EVAL_NAMESPACE, MetricData=data)


def get_gateway_metrics(region_name: str, hours: int = 1) -> pd.DataFrame:
    """Pull Layer-4 Gateway metrics from ``AWS/Bedrock-AgentCore``.

    Parameters
    ----------
    region_name : str
        AWS region.
    hours : int
        Look-back window in hours.

    Returns
    -------
    pandas.DataFrame
        Columns ``metric``, ``stat``, ``value``. ``Latency`` is averaged (ms);
        the rest are summed counts. Only metrics with data in the window appear.
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    dims = [{"Name": "Operation", "Value": "InvokeGateway"}, {"Name": "Protocol", "Value": "MCP"}]

    rows = []
    for name in _GW_COUNT_METRICS + [_GW_LATENCY_METRIC]:
        stat = "Average" if name == _GW_LATENCY_METRIC else "Sum"
        resp = cw.get_metric_statistics(
            Namespace=GATEWAY_NAMESPACE, MetricName=name, Dimensions=dims,
            StartTime=start, EndTime=end, Period=300, Statistics=[stat],
        )
        points = resp.get("Datapoints", [])
        if not points:
            continue
        latest = sorted(points, key=lambda p: p["Timestamp"])[-1]
        rows.append({"metric": name, "stat": stat, "value": round(latest[stat], 2)})
    return pd.DataFrame(rows, columns=["metric", "stat", "value"])


def query_spans(region_name: str, gateway_id: str | None = None, hours: int = 2, limit: int = 50) -> list:
    """Query Layer-5 OTEL spans from the ``aws/spans`` log group.

    Gateway-emitted spans do NOT carry a ``session.id`` — that field only appears on
    spans from an AgentCore *Runtime* invoked with the session-id header. For the
    local-agent → Gateway path, spans are correlated by ``gateway.id`` (and ``traceId``
    groups the spans of a single request).

    Parameters
    ----------
    region_name : str
        AWS region.
    gateway_id : str, optional
        When given, filters to this gateway's spans via the ``attributes.gateway.id``
        field.
    hours : int
        Look-back window in hours.
    limit : int
        Maximum spans to return.

    Returns
    -------
    list
        Parsed span dicts (``@message`` JSON), newest first.
    """
    logs_client = boto3.client("logs", region_name=region_name)
    filt = f"| filter attributes.gateway.id = '{gateway_id}' " if gateway_id else ""
    query = (
        f"fields @timestamp, @message | filter ispresent(name) {filt}"
        f"| sort @timestamp desc | limit {limit}"
    )
    rows = _query_logs_insights(logs_client, SPANS_LOG_GROUP, query, hours=hours)
    spans = []
    for row in rows:
        for field in row:
            if field["field"] == "@message":
                try:
                    spans.append(json.loads(field["value"]))
                except json.JSONDecodeError:
                    pass
    return spans


def build_kb_dashboard(
    dashboard_name: str,
    kb_id: str,
    gateway_id: str,
    region_name: str,
    include_eval_cost: bool = False,
    include_cost: bool = False,
    cost_kb_ids: list | None = None,
    include_base: bool = True,
) -> str:
    """Create a CloudWatch dashboard unifying the KB observability layers.

    Base board (when ``include_base=True``, the default): Layer-1 KB metrics,
    Layer-3 retrieval quality, Layer-4 Gateway metrics, Layer-5 span log widget.
    With ``include_eval_cost=True`` it also adds **Layer-6 cost & quota** (from
    :func:`emit_cost_metrics`) and **Layer-7 quality scores** (from
    :func:`emit_eval_scores`) — the full 7-layer view for the evaluation notebook.
    Layers 2 (ingestion logs) live in Logs Insights, not a metric widget.

    When ``include_base=False``, the four base widgets (Layer 1, 3, 4, 5) are
    skipped entirely. The ``include_cost`` / ``include_eval_cost`` sections are
    still emitted, but their y-offsets start at 0 instead of 24. This is used by
    the cost notebook to build a cost-only dashboard without empty "No data" widgets
    from the observability layers.

    Parameters
    ----------
    dashboard_name : str
        Dashboard name.
    kb_id : str
        Knowledge base id.
    gateway_id : str
        Gateway id — the span widget filters to this gateway's spans (used only
        when ``include_base=True``).
    region_name : str
        AWS region.
    include_eval_cost : bool
        Add the Layer-6 (cost/quota) and Layer-7 (eval scores) widgets. Requires the
        matching metrics to have been emitted; default ``False`` keeps the 4-layer board.
    include_cost : bool
        Add a per-KB **cost drill-down** section (from :func:`utils.kb_cost.emit_kb_cost_components`
        — ``KB*CostUsd`` metrics under ``BMKB/Cost``). Cost is one more section on this same board,
        not a separate dashboard. Default ``False`` — backward-compatible.
    cost_kb_ids : list, optional
        KB ids to graph in the cost section, one series per KB. When ``None`` and ``include_cost``
        is set, defaults to ``[kb_id]``.
    include_base : bool
        When ``False``, omit the four base widgets (Layer 1 KB metrics, Layer 4 Gateway,
        Layer 3 retrieval quality, Layer 5 spans) and start cost/eval sections at y=0.
        Default ``True`` preserves the existing full board for the eval/observability
        notebooks.

    Returns
    -------
    str
        The dashboard name (echoing input for convenience).
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    kb_dim = f"knowledge-base/{kb_id}"

    kb_metrics = [[KB_NAMESPACE, m, "Operation", "Retrieve", "KnowledgeBaseId", kb_dim]
                  for m in ("Invocations", "ClientErrors", "ServerErrors", "Throttles")]
    gw_metrics = [[GATEWAY_NAMESPACE, m, "Operation", "InvokeGateway", "Protocol", "MCP"]
                  for m in _GW_COUNT_METRICS + [_GW_LATENCY_METRIC]]
    quality_metrics = [[RETRIEVAL_QUALITY_NAMESPACE, m, "KnowledgeBaseId", kb_id]
                       for m in ("score_mean", "score_spread", "chunk_count")]

    span_query = (
        f"SOURCE '{SPANS_LOG_GROUP}' | fields @timestamp, name, kind, durationNano, "
        f"attributes.latency_ms, attributes.overhead_latency_ms "
        f"| filter attributes.gateway.id = '{gateway_id}' "
        f"| sort @timestamp desc | limit 20"
    )

    if include_base:
        widgets = [
            {"type": "metric", "x": 0, "y": 0, "width": 12, "height": 6,
             "properties": {"title": "Layer 1 — KB metrics", "region": region_name,
                            "metrics": kb_metrics, "stat": "Sum", "period": 300}},
            {"type": "metric", "x": 12, "y": 0, "width": 12, "height": 6,
             "properties": {"title": "Layer 4 — Gateway metrics", "region": region_name,
                            "metrics": gw_metrics, "stat": "Sum", "period": 300}},
            {"type": "metric", "x": 0, "y": 6, "width": 12, "height": 6,
             "properties": {"title": "Layer 3 — Retrieval quality", "region": region_name,
                            "metrics": quality_metrics, "stat": "Average", "period": 300}},
            {"type": "log", "x": 12, "y": 6, "width": 12, "height": 6,
             "properties": {"title": "Layer 5 — Spans", "region": region_name,
                            "query": span_query, "view": "table"}},
        ]
        # Base board occupies rows 0–11; eval/cost sections follow at y=12+.
        _base_height = 12
    else:
        widgets = []
        # No base board; cost/eval sections start at y=0.
        _base_height = 0

    if include_eval_cost:
        cost_metrics = [[COST_NAMESPACE, "SessionCostUsd", "KnowledgeBaseId", kb_id]]
        quota_metrics = [[COST_NAMESPACE, "SessionQuotaTokens", "KnowledgeBaseId", kb_id]]
        # Score series are per-evaluator; list_metrics discovers whatever was emitted.
        eval_series = [[m["Namespace"], m["MetricName"]] + [x for d in m["Dimensions"] for x in (d["Name"], d["Value"])]
                       for m in cw.list_metrics(Namespace=EVAL_NAMESPACE).get("Metrics", [])]
        # Per-query cost — one series per Query dimension (see emit_query_cost_metrics).
        query_cost_series = [[m["Namespace"], m["MetricName"]] + [x for d in m["Dimensions"] for x in (d["Name"], d["Value"])]
                             for m in cw.list_metrics(Namespace=COST_NAMESPACE, MetricName="QueryCostUsd").get("Metrics", [])]
        widgets += [
            {"type": "metric", "x": 0, "y": _base_height, "width": 8, "height": 6,
             "properties": {"title": "Layer 6 — Cost (USD, flat billing)", "region": region_name,
                            "metrics": cost_metrics, "stat": "Sum", "period": 300}},
            {"type": "metric", "x": 8, "y": _base_height, "width": 8, "height": 6,
             "properties": {"title": "Layer 6 — Quota consumed (burndown)", "region": region_name,
                            "metrics": quota_metrics, "stat": "Sum", "period": 300}},
            {"type": "metric", "x": 16, "y": _base_height, "width": 8, "height": 6,
             "properties": {"title": "Layer 7 — Eval scores (0–1)", "region": region_name,
                            "metrics": eval_series or [[EVAL_NAMESPACE, "Correctness", "KnowledgeBaseId", kb_id]],
                            "stat": "Average", "period": 300}},
        ]
        if query_cost_series:
            widgets.append(
                {"type": "metric", "x": 0, "y": _base_height + 6, "width": 24, "height": 6,
                 "properties": {"title": "Layer 6 — Cost per KB-grounded answer (USD, by query)",
                                "region": region_name, "metrics": query_cost_series,
                                "stat": "Average", "period": 300, "view": "timeSeries"}})

    if include_cost:
        # Per-KB cost drill-down — one series per KB (KnowledgeBaseId dimension), reading the
        # KB*CostUsd metrics emitted by utils.kb_cost.emit_kb_cost_components. This is the
        # incremental "cost section" on the existing board (mirrors include_eval_cost above).
        #
        # Design principle: the dashboard IS the summary table. Every row of the cost model gets
        # exactly one widget so a reader never has to cross-reference — metric widgets for the four
        # measurable rows (Storage / Retrieve / Agentic / Generation FM) and TEXT widgets for the
        # two non-measurable rows (Embedding+Reranking = $0 bundled; managed-orchestration FM =
        # NOT_OBSERVABLE). Cost is emitted once per notebook run (sparse point-in-time snapshots),
        # so bar/singleValue + setPeriodToTimeRange is used — a line graph renders empty when the
        # lone datapoint falls near the window edge.
        ids = cost_kb_ids or [kb_id]
        y0 = _base_height

        def _series(metric_name):
            return [[COST_NAMESPACE, metric_name, "KnowledgeBaseId", i] for i in ids]

        def _bar(title, metric_name, x, y, w=6, h=6):
            return {"type": "metric", "x": x, "y": y, "width": w, "height": h,
                    "properties": {"title": title, "region": region_name,
                                   "metrics": _series(metric_name), "stat": "Maximum",
                                   "period": 300, "view": "bar", "setPeriodToTimeRange": True}}

        # Legend — the summary table itself, so the board reads standalone.
        legend = ("### Per-KB cost drill-down — one widget per cost-model row\n"
                  "Fully-managed KB → **no OpenSearch / OCU line item**. Metric-derived = "
                  "near-real-time; reconcile against the bill with cost-allocation tags + Cost "
                  "Explorer / CUR (~24h). Values are point-in-time snapshots (emitted per run).\n\n"
                  "| Row | Source | Confidence |\n|---|---|---|\n"
                  "| Index Storage | `RawDataSize` × $5/GB-mo | HIGH |\n"
                  "| Retrieve | `Invocations`(Retrieve) × $1/1k | HIGH |\n"
                  "| Agentic tool-calls | Gateway `Invocations`(`…___AgenticRetrieveStream`) × $4/1k | HIGH |\n"
                  "| Embedding / Reranking | bundled | HIGH — $0 on default managed path |\n"
                  "| Generation FM (agent) | OTEL `chat` spans, trace→tool correlation | HIGH* |\n"
                  "| Managed-orchestration FM | Model Invocation Logging only | NOT_OBSERVABLE |")

        widgets += [
            # Legend + headline total.
            {"type": "text", "x": 0, "y": y0, "width": 16, "height": 8,
             "properties": {"markdown": legend}},
            {"type": "metric", "x": 16, "y": y0, "width": 8, "height": 8,
             "properties": {"title": "TOTAL estimated cost (USD, per KB)", "region": region_name,
                            "metrics": _series("KBTotalEstimatedCostUsd"), "stat": "Maximum",
                            "period": 300, "view": "singleValue", "sparkline": True,
                            "setPeriodToTimeRange": True}},
            # Four measurable rows — one bar each.
            _bar("Index Storage (USD, per KB)", "KBIndexStorageCostUsd", 0, y0 + 8),
            _bar("Retrieve calls (USD, per KB)", "KBRetrieveCostUsd", 6, y0 + 8),
            _bar("Agentic tool-calls (USD, per KB)", "KBAgenticRetrieveCostUsd", 12, y0 + 8),
            _bar("Generation FM (USD, per KB)", "KBGenerationFMCostUsd", 18, y0 + 8),
            # Storage-size trend (data-growth watch, separate from the storage $ row). MB, not GB —
            # KB docs are typically sub-GB, so GB would render a misleading ~0 bar.
            _bar("Index size (MB, per KB)", "KBRawDataSizeMB", 0, y0 + 14, w=12),
            # Two non-measurable rows — text, so the board covers all six components honestly.
            {"type": "text", "x": 12, "y": y0 + 14, "width": 12, "height": 6,
             "properties": {"markdown":
                 "### Rows with no metric (by design)\n"
                 "**Embedding / Reranking — $0**\n"
                 "Bundled into Retrieve on the default managed path; no separate charge or metric. "
                 "Custom embedding / advanced parsing are paid exceptions (Phase 2).\n\n"
                 "**Managed-orchestration FM — NOT_OBSERVABLE**\n"
                 "The KB's internal agentic-orchestration model is invisible on CloudWatch metrics "
                 "*and* OTEL spans. Only **Model Invocation Logging** can surface it — reconcile "
                 "separately."}},
        ]

    cw.put_dashboard(DashboardName=dashboard_name, DashboardBody=json.dumps({"widgets": widgets}))
    return dashboard_name
