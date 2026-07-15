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
utils.kb_cost
=============
Per-KB, per-component **current-cost drill-down** for Amazon Bedrock **fully-managed**
Knowledge Bases (``knowledgeBaseConfiguration.type="MANAGED"``). This is the cost
"section" layered on top of the observability/evaluation system in
:mod:`utils.kb_observability` — it reads the same per-KB CloudWatch metrics and applies
the published price book in ``utils/kb_pricing.yaml``.

Scope (Phase 1): the DEFAULT managed-embedding path, where nearly every cost component is
``CloudWatch usage metric (KnowledgeBaseId dimension) × published price``:

    Index Storage      RawDataSize (GB)                       × $5.00/GB-month   [KB namespace]
    Retrieve calls     Invocations(Operation=Retrieve)        × $1.00/1,000      [KB namespace]
    Agentic tool-calls Gateway Invocations(tools/call,         × $4.00/1,000      [GATEWAY namespace]
                       …___AgenticRetrieveStream)
    Managed embed/rerank  —                                   = $0 (bundled)
    Generation FM      NOT a KB metric — from OTEL spans via pricing.compute_cost_usd()

VERIFIED LIVE (2026-07-09): a fully-managed BMKB emits ONLY ``Operation=Retrieve`` to
``AWS/Bedrock/KnowledgeBases`` — even when the agentic tool genuinely runs. The agentic $4/1k
surface is counted in the **Gateway** namespace (``AWS/Bedrock-AgentCore``, ``Method=tools/call``,
``Name=…___AgenticRetrieveStream``), so :func:`estimate_kb_cost` needs the KB's ``gateway_id`` to
price it (per-KB attribution ⇒ one gateway per KB).

Fully-managed KBs have a Bedrock-owned datastore, so there is **NO OpenSearch/OCU** line
item. Custom embedding / advanced parsing / custom reranker are Phase-2 extension points:
:func:`get_kb_config` detects them and :func:`estimate_kb_cost` emits a labeled
"not computed — Phase 2" row rather than a guessed number.

Confidence labels on every row: HIGH (count × published rate = the billing formula),
MEDIUM (metric approximates billing), ESTIMATE (needs assumptions), NOT_OBSERVABLE
(needs separate tooling — e.g. the KB's MANAGED orchestration model tokens).

Cost vs the true bill: these are METRIC-DERIVED estimates for near-real-time drill-down.
Reconcile against the authoritative bill via cost-allocation tags + Cost Explorer / CUR
(~24h latency) — see :func:`reconcile_with_invocation_logs` and the notebook's CUR section.

Usage
-----
::

    from utils import kb_cost
    df = kb_cost.estimate_kb_cost("XXXXKBID", region_name="us-west-2", hours=24)
    kb_cost.emit_kb_cost_components(df, "XXXXKBID", region_name="us-west-2")
    cmp = kb_cost.compare_kb_costs(["KB_A", "KB_B"], region_name="us-west-2", hours=24)
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from functools import lru_cache
from importlib.resources import files

import boto3
import pandas as pd
import yaml

from utils.pricing import compute_cost_usd
from utils.kb_observability import KB_NAMESPACE, COST_NAMESPACE

_KB_PRICING = "kb_pricing.yaml"

# Hours in an average month, for GB-month <-> window and window <-> monthly-run-rate math.
HOURS_PER_MONTH = 730

# Confidence tiers (ride in the output DataFrame's `confidence` column).
HIGH = "HIGH"              # count × published rate — the exact billing formula
MEDIUM = "MEDIUM"          # a metric that approximates billing
ESTIMATE = "ESTIMATE"      # requires assumptions
NOT_OBSERVABLE = "NOT_OBSERVABLE"  # needs separate tooling (spans / invocation logging / CUR)


@lru_cache(maxsize=1)
def _load_kb_pricing() -> dict:
    """Read and parse the fully-managed-KB price book once (cached).

    Mirrors :func:`utils.pricing._load_pricing`. See ``utils/kb_pricing.yaml``.
    """
    resource = files("utils") / _KB_PRICING
    return yaml.safe_load(resource.read_text(encoding="utf-8")) or {}


def _sum_metric_over_window(
    cw, metric_name: str, dims: list[dict], start, end,
) -> float:
    """Sum a Count metric across the WHOLE window (not just the latest datapoint).

    ``kb_observability.get_kb_metrics`` returns the latest single 5-min datapoint — correct
    for a storage *snapshot* (RawDataSize) but wrong for call *counts*, where cost needs the
    total over the window. This helper sums all datapoints in the window.

    Returns 0.0 when there are no datapoints (a KB with no traffic → $0, not missing).
    """
    resp = cw.get_metric_statistics(
        Namespace=KB_NAMESPACE, MetricName=metric_name, Dimensions=dims,
        StartTime=start, EndTime=end, Period=300, Statistics=["Sum"],
    )
    return float(sum(p["Sum"] for p in resp.get("Datapoints", [])))


def _latest_metric(cw, metric_name: str, dims: list[dict], start, end, stat: str = "Average") -> float | None:
    """Return the latest datapoint value for a metric (e.g. RawDataSize snapshot), or None."""
    resp = cw.get_metric_statistics(
        Namespace=KB_NAMESPACE, MetricName=metric_name, Dimensions=dims,
        StartTime=start, EndTime=end, Period=300, Statistics=[stat],
    )
    points = resp.get("Datapoints", [])
    if not points:
        return None
    return float(sorted(points, key=lambda p: p["Timestamp"])[-1][stat])


def get_gateway_agentic_calls(gateway_id: str, region_name: str, hours: int = 24,
                              target_name: str | None = None,
                              tool_suffix: str = "AgenticRetrieveStream") -> float:
    """Count agentic tool-calls for a KB from the GATEWAY metrics namespace.

    VERIFIED LIVE (2026-07-09): a fully-managed BMKB does **not** emit
    ``Operation=AgenticRetrieveStream`` to ``AWS/Bedrock/KnowledgeBases`` even when the agentic tool
    genuinely runs — that namespace only shows ``Operation=Retrieve``. The agentic MCP tool-call is
    counted in the **Gateway** namespace (``AWS/Bedrock-AgentCore``) as ``Invocations`` with
    ``Method=tools/call`` and ``Name=<target>___AgenticRetrieveStream``. This is the billable $4/1k
    surface, so it must be read here.

    Per-KB attribution works two ways: **one gateway per KB** (match on gateway ARN alone), OR the
    realistic **one gateway with a target per KB** (match on the target's distinct tool ``Name`` —
    pass ``target_name`` so a single query-routing agent's calls still split per KB). The count
    reflects *tool calls*, which — due to the agent's multi-step ReAct loop — can exceed the number
    of user queries.

    Parameters
    ----------
    gateway_id : str
        The Gateway id whose agentic tool-call metrics to read.
    region_name : str
        AWS region.
    hours : int
        Look-back window.
    target_name : str, optional
        The KB's Gateway **target name** (e.g. ``"financial-kb"``). When given, only tool-calls whose
        ``Name`` is ``<target_name>___<tool_suffix>`` are counted — this is what isolates one KB's
        agentic cost on a **shared** gateway (semantic-routing topology). When ``None``, all
        ``…___<tool_suffix>`` calls on the gateway are counted (one-gateway-per-KB topology).
    tool_suffix : str
        Tool-name suffix to match (default ``"AgenticRetrieveStream"``).

    Returns
    -------
    float
        Agentic tool-call ``Invocations`` in the window; 0.0 if none / gateway not found.
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    acct = boto3.client("sts", region_name=region_name).get_caller_identity()["Account"]
    gw_arn = f"arn:aws:bedrock-agentcore:{region_name}:{acct}:gateway/{gateway_id}"
    want_name = f"{target_name}___{tool_suffix}" if target_name else None
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    total = 0.0
    for m in cw.list_metrics(Namespace="AWS/Bedrock-AgentCore", MetricName="Invocations").get("Metrics", []):
        dims = {d["Name"]: d["Value"] for d in m["Dimensions"]}
        nm = dims.get("Name", "")
        name_ok = (nm == want_name) if want_name else nm.endswith(tool_suffix)
        if (dims.get("Resource") == gw_arn and dims.get("Method") == "tools/call" and name_ok):
            resp = cw.get_metric_statistics(
                Namespace="AWS/Bedrock-AgentCore", MetricName="Invocations",
                Dimensions=m["Dimensions"], StartTime=start, EndTime=end,
                Period=300, Statistics=["Sum"],
            )
            total += float(sum(p["Sum"] for p in resp.get("Datapoints", [])))
    return total


def get_kb_config(kb_id: str, region_name: str) -> dict:
    """Inspect a KB to determine which cost components apply.

    Reads ``get_knowledge_base`` + ``list_data_sources`` to detect KB type, whether a custom
    embedding model is configured (vs the free managed default), advanced parsing, custom
    reranking, and connector types (for the Secrets Manager count). Drives which rows
    :func:`estimate_kb_cost` marks HIGH vs "Phase 2 — not computed".

    Returns
    -------
    dict
        ``kb_type`` (str), ``is_managed`` (bool), ``custom_embedding`` (bool),
        ``embedding_model_arn`` (str|None), ``advanced_parsing`` (bool),
        ``custom_reranking`` (bool), ``connector_types`` (list[str]),
        ``secret_count`` (int — non-S3 connectors), ``name`` (str|None).
    """
    agent = boto3.client("bedrock-agent", region_name=region_name)
    kb = agent.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]
    kb_cfg = kb.get("knowledgeBaseConfiguration", {})
    kb_type = kb_cfg.get("type", "UNKNOWN")
    managed_cfg = kb_cfg.get("managedKnowledgeBaseConfiguration", {}) or {}
    # A custom embedding model is present only when the managed config names one; the default
    # managed embedding leaves this empty (and is free).
    custom_embedding = bool(managed_cfg.get("embeddingModelArn"))

    # Non-S3 SaaS connectors store credentials in Secrets Manager ($0.40/secret-mo); S3 and the
    # default managed path do not. Only these four are secret-bearing.
    SECRET_CONNECTORS = {"CONFLUENCE", "SHAREPOINT", "ONEDRIVE", "GOOGLEDRIVE"}
    # Only these parsing strategies are BILLABLE advanced parsing. SMART_PARSING is the free default
    # the managed-KB creator always sets — flagging it would falsely trip a Phase-2 parsing cost.
    BILLABLE_PARSING = {"BEDROCK_DATA_AUTOMATION", "FM", "FOUNDATION_MODEL"}

    connector_types, advanced_parsing, source_buckets = [], False, []
    try:
        ds_list = agent.list_data_sources(knowledgeBaseId=kb_id, maxResults=100).get(
            "dataSourceSummaries", []
        )
        for ds in ds_list:
            detail = agent.get_data_source(
                knowledgeBaseId=kb_id, dataSourceId=ds["dataSourceId"]
            )["dataSource"]
            ds_cfg = detail.get("dataSourceConfiguration", {})
            # The managed-KB wrapper reports type "MANAGED_KNOWLEDGE_BASE_CONNECTOR"; the REAL source
            # type lives inside connectorParameters, which is a JSON *string* — unwrap it.
            src_type = ds_cfg.get("type", "UNKNOWN")
            if src_type == "MANAGED_KNOWLEDGE_BASE_CONNECTOR":
                raw = ds_cfg.get("managedKnowledgeBaseConnectorConfiguration", {}).get(
                    "connectorParameters"
                )
                params = {}
                if isinstance(raw, str):
                    try:
                        params = json.loads(raw)
                    except json.JSONDecodeError:
                        params = {}
                elif isinstance(raw, dict):
                    params = raw
                src_type = params.get("type", src_type)
                # Capture the S3 source bucket so storage size can fall back to source bytes when
                # the RawDataSize metric is still lagging (it publishes minutes-to-longer after sync).
                blob = json.dumps(params)
                source_buckets += re.findall(r'"bucketName"\s*:\s*"([a-z0-9.-]+)"', blob)
                source_buckets += [a.split(":::")[-1] for a in re.findall(r"arn:aws:s3:::[a-z0-9.-]+", blob)]
            connector_types.append(src_type)
            # Billable advanced parsing only — SMART_PARSING (the default) is free, don't flag it.
            strat = (
                detail.get("vectorIngestionConfiguration", {})
                .get("parsingConfiguration", {})
                .get("parsingStrategy", "")
            )
            if strat in BILLABLE_PARSING:
                advanced_parsing = True
    except Exception:
        pass  # config detection is best-effort; absence → treat as default path

    non_s3 = [c for c in connector_types if c in SECRET_CONNECTORS]
    return {
        "name": kb.get("name"),
        "kb_type": kb_type,
        "is_managed": kb_type == "MANAGED",
        "custom_embedding": custom_embedding,
        "embedding_model_arn": managed_cfg.get("embeddingModelArn"),
        "advanced_parsing": advanced_parsing,
        "custom_reranking": False,  # reranker is chosen per-query at retrieval, not on the KB; Phase 2
        "connector_types": connector_types,
        "secret_count": len(non_s3),
        "source_buckets": sorted(set(source_buckets)),  # S3 fallback for storage size (RawDataSize lag)
    }


def _source_bytes_gb(buckets: list, region_name: str) -> float | None:
    """Sum the size of all objects across the KB's S3 source bucket(s), in GB.

    Used as a fallback for the storage-size metric: ``RawDataSize`` publishes minutes (sometimes
    longer) after an ingestion completes, so early reads see nothing. Live verification showed
    ``RawDataSize`` ≈ sum of source object bytes (ratio ~1.0), making source bytes a faithful proxy
    while the metric lags. Returns None if no bucket is readable.
    """
    if not buckets:
        return None
    s3 = boto3.client("s3", region_name=region_name)
    total, seen = 0, False
    for b in buckets:
        try:
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=b):
                for obj in page.get("Contents", []):
                    total += obj["Size"]
                    seen = True
        except Exception:
            continue  # best-effort; a missing/forbidden bucket just doesn't contribute
    return total / 1e9 if seen else None


def _row(component, metric_source, metric_value, metric_unit,
         price_dim, price_value, cost_usd, confidence, caveat=""):
    """Build one component row for the estimate DataFrame (uniform schema)."""
    return {
        "component": component,
        "metric_source": metric_source,
        "metric_value": metric_value,
        "metric_unit": metric_unit,
        "price_dim": price_dim,
        "price_value": price_value,
        "cost_usd": None if cost_usd is None else round(cost_usd, 6),
        "confidence": confidence,
        "caveat": caveat,
    }


def estimate_kb_cost(kb_id: str, region_name: str, hours: int = 24,
                     kb_config: dict | None = None, gateway_id: str | None = None,
                     target_name: str | None = None) -> pd.DataFrame:
    """Per-component current-cost estimate for one fully-managed KB (the primary entry point).

    Pulls per-KB CloudWatch usage metrics and applies ``kb_pricing.yaml`` rates. One row per
    component; ``cost_usd=None`` rows carry a ``caveat`` explaining why (not-observable /
    Phase-2 / needs spans). Storage is a monthly figure (RawDataSize × $5/GB-mo); call costs are
    the total over ``hours``. See :func:`monthly_run_rate` to project calls to a monthly rate.

    Parameters
    ----------
    kb_id : str
        Knowledge base id.
    region_name : str
        AWS region.
    hours : int
        Look-back window for call/iteration counts.
    kb_config : dict, optional
        Result of :func:`get_kb_config`; fetched if not supplied (pass it to avoid a re-fetch
        when calling repeatedly, e.g. from :func:`compare_kb_costs`).
    gateway_id : str, optional
        The Gateway id. **Required to price agentic retrieval** — a fully-managed BMKB does not
        emit an agentic metric to the KB namespace (verified live); the $4/1k agentic tool-calls are
        counted in the Gateway namespace instead (see :func:`get_gateway_agentic_calls`). Without it,
        the agentic row is shown as NOT_OBSERVABLE rather than a false $0.
    target_name : str, optional
        This KB's Gateway **target name** (e.g. ``"financial-kb"``). Needed when a SHARED gateway
        hosts a target per KB (semantic-routing topology) so agentic tool-calls attribute to the
        right KB by tool name. Omit for one-gateway-per-KB.

    Returns
    -------
    pandas.DataFrame
        Columns: ``component, metric_source, metric_value, metric_unit, price_dim,
        price_value, cost_usd, confidence, caveat``.
    """
    price = _load_kb_pricing()
    cfg = kb_config or get_kb_config(kb_id, region_name)
    cw = boto3.client("cloudwatch", region_name=region_name)
    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    kb_dim = [{"Name": "KnowledgeBaseId", "Value": f"knowledge-base/{kb_id}"}]

    def op_dims(op):
        return kb_dim + [{"Name": "Operation", "Value": op}]

    rows = []

    # ── Index Storage (size × $/GB-month) ──
    # Size is reported in MB (KB source docs are typically sub-GB — GB would round to a misleading 0).
    # RawDataSize publishes minutes-to-longer after ingestion; while it lags, fall back to summing the
    # S3 source object bytes (verified ≈ RawDataSize, ratio ~1.0) so the row is never empty.
    st_price = price["index_storage"]["price_per_gb_month"]
    gb = _latest_metric(cw, "RawDataSize", kb_dim, start, end, stat="Average")
    if gb is not None:
        size_source, size_conf = "RawDataSize (Average)", HIGH
        size_caveat = ("Monthly figure (current size × $/GB rate). RawDataSize is the billing basis "
                       "(a snapshot, not a month average).")
    else:
        gb = _source_bytes_gb(cfg.get("source_buckets", []), region_name)
        size_source, size_conf = "S3 source bytes (RawDataSize pending)", MEDIUM
        size_caveat = ("RawDataSize metric not published yet (lags ingestion) — using summed S3 "
                       "source bytes as a proxy (verified ≈ RawDataSize). Backfills to HIGH on re-run.")
    mb = None if gb is None else round(gb * 1000, 4)
    rows.append(_row(
        "Index Storage", size_source, mb, "MB",
        "$/GB-month", st_price,
        None if gb is None else gb * st_price,
        size_conf, size_caveat,
    ))

    # ── Retrieve calls (Invocations sum × $/1k) ──
    retr = _sum_metric_over_window(cw, "Invocations", op_dims("Retrieve"), start, end)
    r_price = price["retrieve"]["price_per_1k_requests"]
    rows.append(_row(
        "Retrieve calls", f"Invocations(Retrieve), {hours}h", retr, "calls",
        "$/1,000 calls", r_price, retr / 1000 * r_price, HIGH,
        "Exact billing formula. Includes embedding + vector search + managed reranking (bundled).",
    ))

    # ── Agentic tool-calls ($4/1k) — from the GATEWAY namespace, NOT the KB namespace ──
    # VERIFIED LIVE: a fully-managed BMKB emits only Operation=Retrieve to AWS/Bedrock/KnowledgeBases
    # even when the agentic tool runs; the agentic tool-call is counted in the Gateway namespace.
    a_price = price["agentic_retrieve_stream"]["price_per_1k_calls"]
    if gateway_id:
        ag = get_gateway_agentic_calls(gateway_id, region_name, hours=hours, target_name=target_name)
        tname = f"{target_name}___AgenticRetrieveStream" if target_name else "…___AgenticRetrieveStream"
        rows.append(_row(
            "Agentic tool-calls", f"Gateway Invocations(tools/call, {tname}), {hours}h",
            ag, "tool-calls", "$/1,000 calls", a_price, ag / 1000 * a_price, HIGH,
            "Counted in the Gateway namespace (KB namespace shows only Retrieve). Multi-step agents make "
            ">1 tool-call per query. Per-KB isolation is by target tool-name on a shared gateway.",
        ))
    else:
        rows.append(_row(
            "Agentic tool-calls", "Gateway namespace (no gateway_id supplied)", None, "tool-calls",
            "$/1,000 calls", a_price, None, NOT_OBSERVABLE,
            "Fully-managed KB emits NO agentic metric to the KB namespace (verified). Pass gateway_id "
            "to price it from the Gateway namespace, or read Gateway metrics / CUR directly.",
        ))

    # ── Managed embedding + reranking (bundled = $0) ──
    if cfg["custom_embedding"]:
        rows.append(_row(
            "Embedding (custom model)", "ingestion tokens", None, "tokens",
            "$/1M tokens", price["custom_embedding"]["price_per_1m_input_tokens_example"],
            None, ESTIMATE,
            "Custom embedding model → per-token ingestion cost. Phase 2 — not computed live.",
        ))
    else:
        rows.append(_row(
            "Embedding (managed default)", "bundled", 0, "—",
            "bundled", 0.0, 0.0, HIGH,
            "Default managed embedding is free; add/update/delete + sync incur no separate charge.",
        ))
    rows.append(_row(
        "Reranking (managed default)", "bundled", 0, "—", "bundled", 0.0, 0.0, HIGH,
        "Default managed reranker is free. Custom Cohere reranker is Phase 2.",
    ))

    # ── Generation FM — NOT a KB metric (comes from OTEL spans, see notebook Component C) ──
    rows.append(_row(
        "Generation FM (agent model)", "OTEL chat spans", None, "tokens",
        "$/1M tokens (per model)", None, None, NOT_OBSERVABLE,
        "The agent's answer model — from spans via pricing.compute_cost_usd (notebook Component C), "
        "not KB metrics. The KB's MANAGED orchestration model is invisible client-side (invocation logs only).",
    ))

    # ── Secrets Manager (non-S3 connectors only) ──
    if cfg["secret_count"]:
        sm = price["secrets_manager"]["price_per_secret_month"]
        rows.append(_row(
            "Secrets Manager", f"{cfg['secret_count']} non-S3 connector secret(s)",
            cfg["secret_count"], "secrets", "$/secret-month", sm,
            cfg["secret_count"] * sm, HIGH,
            "Non-S3 connectors (Confluence/SharePoint/…) store credentials in Secrets Manager.",
        ))

    return pd.DataFrame(rows, columns=[
        "component", "metric_source", "metric_value", "metric_unit",
        "price_dim", "price_value", "cost_usd", "confidence", "caveat",
    ])


def monthly_run_rate(cost_df: pd.DataFrame, hours: int) -> pd.DataFrame:
    """Add a ``monthly_rate_usd`` column projecting the window estimate to a monthly run-rate.

    Storage is already a monthly figure (passed through). Call/iteration rows are projected
    linearly: ``window_cost × (730 / hours)`` — assumes uniform traffic. Bundled ($0) and
    not-observable (None) rows pass through unchanged.

    Parameters
    ----------
    cost_df : pandas.DataFrame
        Output of :func:`estimate_kb_cost`.
    hours : int
        The window (hours) used to produce ``cost_df`` — must match.
    """
    factor = HOURS_PER_MONTH / hours
    storage_like = {"Index Storage", "Secrets Manager"}  # already monthly

    def project(r):
        if r["cost_usd"] is None:
            return None
        if r["component"] in storage_like:
            return r["cost_usd"]  # already a monthly number
        return round(r["cost_usd"] * factor, 6)

    out = cost_df.copy()
    out["monthly_rate_usd"] = out.apply(project, axis=1)
    return out


def compare_kb_costs(kb_ids: list[str], region_name: str, hours: int = 24,
                     kb_gateways: dict | None = None, kb_targets: dict | None = None) -> pd.DataFrame:
    """Per-KB cost side-by-side — the "drill down to a SPECIFIC KB" view.

    Runs :func:`estimate_kb_cost` for each KB and pivots to one column per KB (rows = component,
    values = ``cost_usd``), plus a ``TOTAL (metric-derived)`` row summing the computable rows.

    Parameters
    ----------
    kb_ids : list[str]
        Knowledge base ids to compare.
    region_name : str
        AWS region.
    hours : int
        Look-back window.
    kb_gateways : dict, optional
        ``{kb_id: gateway_id}`` — pass so the agentic $4/1k row is priced from the Gateway namespace
        per KB (see :func:`estimate_kb_cost`). Without it, the agentic row is NOT_OBSERVABLE.
    kb_targets : dict, optional
        ``{kb_id: target_name}`` — for a SHARED gateway (semantic-routing), the KB's Gateway target
        name so agentic tool-calls attribute to the right KB by tool name.

    Returns
    -------
    pandas.DataFrame
        Index = component; one column per KB (labeled ``name (kb_id)`` when a name is available).
    """
    kb_gateways = kb_gateways or {}
    kb_targets = kb_targets or {}
    series = {}
    for kb_id in kb_ids:
        cfg = get_kb_config(kb_id, region_name)
        df = estimate_kb_cost(kb_id, region_name, hours=hours, kb_config=cfg,
                              gateway_id=kb_gateways.get(kb_id), target_name=kb_targets.get(kb_id))
        label = f"{cfg.get('name') or kb_id} ({kb_id})"
        col = df.set_index("component")["cost_usd"]
        col.loc["TOTAL (metric-derived)"] = df["cost_usd"].dropna().sum()
        series[label] = col
    return pd.DataFrame(series)


# ── CamelCase-safe metric names for per-component CloudWatch emission ──
_COMPONENT_METRIC = {
    "Index Storage": "KBIndexStorageCostUsd",
    "Retrieve calls": "KBRetrieveCostUsd",
    "Agentic tool-calls": "KBAgenticRetrieveCostUsd",
    "Secrets Manager": "KBSecretsManagerCostUsd",
}

# Generation-FM cost is span-derived (not in cost_df's metric rows), so it is passed in explicitly
# via emit_kb_cost_components(extra_costs=...). Canonical metric name kept here for the dashboard.
GENERATION_FM_METRIC = "KBGenerationFMCostUsd"


def emit_kb_cost_components(cost_df: pd.DataFrame, kb_id: str, region_name: str,
                            extra_costs: dict | None = None) -> None:
    """Publish per-component KB cost to the existing ``BMKB/Cost`` namespace.

    One metric per known component (``KB*CostUsd``) plus a rollup ``KBTotalEstimatedCostUsd`` and
    the storage-size trend ``KBRawDataSizeGB`` — all dimensioned by ``KnowledgeBaseId`` so the
    dashboard graphs one series per KB. Extends the same namespace ``emit_cost_metrics`` writes to
    (cost is one more section of the existing board, not a parallel namespace). Rows with
    ``cost_usd=None`` are skipped.

    Parameters
    ----------
    cost_df : pandas.DataFrame
        Output of :func:`estimate_kb_cost`.
    kb_id : str
        Knowledge base id (the ``KnowledgeBaseId`` metric dimension).
    region_name : str
        AWS region.
    extra_costs : dict, optional
        Span-derived costs not present in ``cost_df`` — e.g. ``{"KBGenerationFMCostUsd": 0.0123}``.
        Generation-FM cost is computed from OTEL ``chat`` spans in the notebook (not a CloudWatch
        metric row), so it is passed here to get its own dashboard series. Included in the rollup.
    """
    cw = boto3.client("cloudwatch", region_name=region_name)
    dims = [{"Name": "KnowledgeBaseId", "Value": kb_id}]
    data = []
    for _, r in cost_df.iterrows():
        mname = _COMPONENT_METRIC.get(r["component"])
        # pd.notna guards BOTH None and NaN — a lagging metric (e.g. RawDataSize) yields NaN,
        # and CloudWatch put_metric_data rejects NaN. Skip those rows; they backfill on re-run.
        if mname and pd.notna(r["cost_usd"]):
            data.append({"MetricName": mname, "Value": float(r["cost_usd"]),
                         "Unit": "None", "Dimensions": dims})
    total = cost_df["cost_usd"].dropna().sum()
    # Span-derived extras (generation FM) — their own series, and folded into the rollup total.
    for mname, val in (extra_costs or {}).items():
        if pd.notna(val):
            data.append({"MetricName": mname, "Value": float(val),
                         "Unit": "None", "Dimensions": dims})
            total += float(val)
    data.append({"MetricName": "KBTotalEstimatedCostUsd", "Value": float(total),
                 "Unit": "None", "Dimensions": dims})
    # Storage-size trend in MB (separate from cost, useful to watch data growth). The storage row's
    # metric_value is MB (KB docs are typically sub-GB — GB rounds to a misleading 0).
    storage_row = cost_df[cost_df["component"] == "Index Storage"]
    if not storage_row.empty and pd.notna(storage_row.iloc[0]["metric_value"]):
        data.append({"MetricName": "KBRawDataSizeMB",
                     "Value": float(storage_row.iloc[0]["metric_value"]),
                     "Unit": "Megabytes", "Dimensions": dims})
    # put_metric_data caps at 1000 items/call; we emit ~6 — no batching needed.
    if data:
        cw.put_metric_data(Namespace=COST_NAMESPACE, MetricData=data)


def reconcile_with_invocation_logs(
    kb_id: str, region_name: str, hours: int = 24,
    log_group: str = "/aws/bedrock/modelinvocations",
) -> pd.DataFrame:
    """Query Bedrock Model Invocation Logging for token totals by model (reconcile step).

    This is the ONLY path to the KB's MANAGED orchestration-model token cost — invisible on KB
    metrics and agent spans (confirmed in the vault). Requires model invocation logging to be
    enabled (Bedrock → Settings). Returns per-model token sums; cost is left to the caller via
    :func:`utils.pricing.compute_cost_usd` since the log field paths for token counts vary by
    account/config and should be verified against a real sample.

    Returns
    -------
    pandas.DataFrame
        Columns ``modelId``, ``invocations`` — empty if logging is not enabled or no records
        match. (Token columns added by the notebook after verifying field paths on a live sample.)
    """
    logs = boto3.client("logs", region_name=region_name)
    start = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    end = int(datetime.utcnow().timestamp())
    query = (
        "fields @timestamp, @message "
        "| filter ispresent(modelId) "
        "| stats count(*) as invocations by modelId"
    )
    try:
        qid = logs.start_query(
            logGroupName=log_group, startTime=start, endTime=end, queryString=query
        )["queryId"]
    except logs.exceptions.ResourceNotFoundException:
        return pd.DataFrame(columns=["modelId", "invocations"])
    for _ in range(30):
        res = logs.get_query_results(queryId=qid)
        if res["status"] in ("Complete", "Failed"):
            break
        time.sleep(1)
    if res["status"] != "Complete":
        return pd.DataFrame(columns=["modelId", "invocations"])
    rows = [{f["field"]: f["value"] for f in row} for row in res.get("results", [])]
    return pd.DataFrame(rows, columns=["modelId", "invocations"]) if rows else pd.DataFrame(
        columns=["modelId", "invocations"]
    )
