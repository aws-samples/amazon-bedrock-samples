"""
Evaluation metric for PDF-based Visual QA (MMVQA).

Uses ROUGE-L F1 as the primary score to measure overlap between
the model's answer and the gold reference paragraph(s).
Also reports token-level F1 as a secondary metric.
"""

import re
from collections import Counter


def _tokenize(text):
    """Lowercase and split into word tokens."""
    return re.findall(r'\w+', text.lower())


def _lcs_length(x, y):
    """Compute length of longest common subsequence."""
    m, n = len(x), len(y)
    if m == 0 or n == 0:
        return 0
    # Optimize memory: only keep two rows
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if x[i - 1] == y[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(curr[j - 1], prev[j])
        prev, curr = curr, [0] * (n + 1)
    return prev[n]


def _rouge_l_f1(prediction, reference):
    """Compute ROUGE-L F1 score between prediction and reference."""
    pred_tokens = _tokenize(prediction)
    ref_tokens = _tokenize(reference)

    if not pred_tokens or not ref_tokens:
        return 0.0

    lcs_len = _lcs_length(pred_tokens, ref_tokens)
    if lcs_len == 0:
        return 0.0

    precision = lcs_len / len(pred_tokens)
    recall = lcs_len / len(ref_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1


def _token_f1(prediction, reference):
    """Compute token-level F1 score."""
    pred_tokens = _tokenize(prediction)
    ref_tokens = _tokenize(reference)

    if not pred_tokens or not ref_tokens:
        return 0.0

    pred_counts = Counter(pred_tokens)
    ref_counts = Counter(ref_tokens)
    overlap = sum((pred_counts & ref_counts).values())

    if overlap == 0:
        return 0.0

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1


def compute_score(preds, golds, **kwargs):
    """
    Evaluate predictions against gold reference answers.

    Args:
        preds: List of model predictions (strings)
        golds: List of gold reference answers (strings)

    Returns:
        dict with 'score' (ROUGE-L F1, higher is better) and secondary metrics
    """
    rouge_scores = []
    token_f1_scores = []

    for pred, gold in zip(preds, golds):
        pred_str = str(pred).strip()
        gold_str = str(gold).strip()

        rouge_scores.append(_rouge_l_f1(pred_str, gold_str))
        token_f1_scores.append(_token_f1(pred_str, gold_str))

    avg_rouge = sum(rouge_scores) / len(rouge_scores) if rouge_scores else 0.0
    avg_token_f1 = sum(token_f1_scores) / len(token_f1_scores) if token_f1_scores else 0.0

    return {
        'score': avg_rouge,
        'scores': rouge_scores,  # per-instance ROUGE-L F1 scores
        'rouge_l_f1': avg_rouge,
        'token_f1': avg_token_f1,
    }


def lambda_handler(event, context):
    preds = event.get("preds", [])
    golds = event.get("golds", [])
    kwargs = event.get("kwargs", {})
    return compute_score(preds, golds, **kwargs)
