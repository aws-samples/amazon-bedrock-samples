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
utils.pricing
=============
Per-model **dollar** pricing for estimating Bedrock invocation cost — the Layer-6
(RAG-app cost) helper for the evaluation notebook. Prices live in
``utils/model_pricing.yaml`` (USD per 1M tokens, keyed by version-agnostic model
family) and are hand-maintained from the AWS Bedrock pricing page.

Two distinct calculations — do not conflate them (per the AWS token-burndown doc,
"You're only billed for your actual token usage"):

- **Billing** (:func:`compute_cost_usd`) — flat: ``input*in_price + output*out_price``.
  The burndown multiplier plays NO part.
- **Quota** (:func:`quota_consumed`) — TPM/TPD throttling: ``input + output*burndown``.
  Burndown is per-model (Claude v4.8=15x, Sonnet 5=10x, v4.7-and-below=5x, others=1x).
  Matters for concurrency/throttling capacity, not dollars.

Usage
-----
::

    from utils.pricing import compute_cost_usd, quota_consumed
    cost  = compute_cost_usd("us.anthropic.claude-haiku-4-5-20251001-v1:0", 1200, 350)  # $
    quota = quota_consumed("us.anthropic.claude-haiku-4-5-20251001-v1:0", 1200, 350)   # quota tokens
"""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files

import yaml

_PRICING = "model_pricing.yaml"

# Strip a leading cross-region inference prefix (us./eu./apac./global.) and the trailing
# "-<date>-vN(:k)" version suffix so a live inference-profile id normalizes to the
# version-agnostic family key the table is keyed by.
_REGION_PREFIX = re.compile(r"^(?:us|eu|apac|global)\.")
_VERSION_SUFFIX = re.compile(r"-(?:\d{8}-)?v\d+(?::\d+)?$")


@lru_cache(maxsize=1)
def _load_pricing() -> dict:
    """Read and parse the per-model price table once (cached)."""
    resource = files("utils") / _PRICING
    return yaml.safe_load(resource.read_text(encoding="utf-8")) or {}


def _row_for(model_id: str) -> dict | None:
    """Find a price row by exact key, else by the normalized family key.

    A live id like ``us.anthropic.claude-haiku-4-5-20251001-v1:0`` won't match the
    family-keyed table directly; stripping the region prefix and ``-<date>-vN`` suffix
    yields ``anthropic.claude-haiku-4-5``, which does. Exact match always wins.
    """
    pricing = _load_pricing()
    row = pricing.get(model_id)
    if row is not None:
        return row
    family = _VERSION_SUFFIX.sub("", _REGION_PREFIX.sub("", model_id))
    return pricing.get(family) if family != model_id else None


def compute_cost_usd(
    model_id: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """Estimate the USD cost of one invocation from its token counts.

    Parameters
    ----------
    model_id : str | None
        The Bedrock model / inference-profile id.
    input_tokens, output_tokens : int | None
        Token counts from the invocation.

    Returns
    -------
    float | None
        Rounded USD cost, or ``None`` when it cannot be computed (unknown/None model,
        missing prices, or missing token counts) — cost is omitted, never guessed.
    """
    if not model_id or input_tokens is None or output_tokens is None:
        return None
    row = _row_for(model_id)
    if not row:
        return None
    input_per_1m = row.get("input_per_1m")
    output_per_1m = row.get("output_per_1m")
    if input_per_1m is None or output_per_1m is None:
        return None
    cost = (input_tokens / 1_000_000) * input_per_1m + (
        output_tokens / 1_000_000
    ) * output_per_1m
    return round(cost, 6)


def quota_consumed(
    model_id: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
) -> int | None:
    """Compute TPM/TPD **quota** tokens consumed (NOT dollars) for one invocation.

    Applies the model's output-token burndown multiplier — a throttling/capacity concept,
    separate from billing. AWS: quota-consumed = ``InputTokenCount + OutputTokenCount x
    burndown_rate`` (cache-read tokens excluded; not modeled here).

    Parameters
    ----------
    model_id : str | None
        The Bedrock model / inference-profile id.
    input_tokens, output_tokens : int | None
        Actual token counts from the invocation.

    Returns
    -------
    int | None
        Quota tokens depleted from TPM/TPD, or ``None`` when it can't be computed.
        A missing burndown in the table defaults to 1x (non-Anthropic behaviour).
    """
    if not model_id or input_tokens is None or output_tokens is None:
        return None
    row = _row_for(model_id) or {}
    burndown = row.get("quota_burndown", 1)
    return int(input_tokens + output_tokens * burndown)
