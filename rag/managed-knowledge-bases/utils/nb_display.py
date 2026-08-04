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
utils.nb_display
================
Small presentation helpers for the Managed-KB observability notebooks — plain
``print`` + ANSI color for status output, plus pandas ``Styler`` helpers for the
metric tables. Shared so the observability and RAG-evaluation notebooks look
consistent.

ANSI escapes render reliably in Jupyter stdout (more predictable than a ``rich``
Console, which reformats output in a notebook). The accent is Amazon-orange
(``#FF9900`` → 24-bit ANSI); terminals/kernels without truecolor just show the
text uncolored.

Usage
-----
::

    from utils import nb_display as ui
    ui.rule("Layer 1 — KB metrics")
    ui.ok("delivery configured")
    display(ui.style_scores(df))
"""

from __future__ import annotations

import pandas as pd

_ACCENT = "#FF9900"  # Amazon orange

# 24-bit ANSI escapes (Amazon orange = RGB 255,153,0)
_ORANGE = "\033[38;2;255;153;0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def rule(title: str, width: int = 72) -> None:
    """Print a section header: an accent-colored title on a horizontal rule."""
    label = f" {title} "
    dashes = max(0, width - len(label))
    left = dashes // 2
    right = dashes - left
    print(f"\n{_ORANGE}{'─' * left}{_BOLD}{label}{_RESET}{_ORANGE}{'─' * right}{_RESET}")


def ok(message: str) -> None:
    """Print a success line with an Amazon-orange dot."""
    print(f"{_ORANGE}●{_RESET} {message}")


def info(message: str) -> None:
    """Print a secondary/dim informational line."""
    print(f"{_DIM}{message}{_RESET}")


def _score_color(val) -> str:
    """Map a 0–1 relevance score to a red→amber→green background (no matplotlib)."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v >= 0.6:
        bg = "#D3F9D8"   # green — confident
    elif v >= 0.45:
        bg = "#FFF3BF"   # amber — mixed
    else:
        bg = "#FFE3E3"   # red — weak
    return f"background-color: {bg}"


def style_scores(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    """Style a retrieval-quality DataFrame: shade score columns red→amber→green.

    Uses discrete background colors (no matplotlib dependency) so it renders in a
    plain Jupyter kernel.

    Parameters
    ----------
    df : pandas.DataFrame
        Output of the Layer-3 quality table (has ``score_*`` and count columns).

    Returns
    -------
    pandas.io.formats.style.Styler
        A styled view for ``display()``; unknown columns are left untouched.
    """
    score_cols = [c for c in df.columns if c.startswith("score_")]
    styler = df.style
    if score_cols:
        styler = styler.map(_score_color, subset=score_cols)
    return styler.format(precision=4)


def style_metrics(df: pd.DataFrame, value_col: str = "value") -> "pd.io.formats.style.Styler":
    """Style a metrics DataFrame: highlight non-zero error/throttle rows in red.

    Parameters
    ----------
    df : pandas.DataFrame
        A metrics table with a ``metric`` column and a numeric value column.
    value_col : str
        Name of the numeric column to read for the error highlight.

    Returns
    -------
    pandas.io.formats.style.Styler
        A styled view for ``display()``.
    """
    err_terms = ("Error", "Throttle", "Failed")

    def _row(row):
        is_err = any(t in str(row.get("metric", "")) for t in err_terms)
        if is_err and float(row.get(value_col, 0) or 0) > 0:
            return ["color: #C92A2A; font-weight: bold"] * len(row)
        return [""] * len(row)

    return df.style.apply(_row, axis=1)
