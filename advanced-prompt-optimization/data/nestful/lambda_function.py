"""
NESTFUL - Nested Function Calling Evaluation Metric

Evaluates predicted function call sequences against gold trajectories.
Ported from NESTFUL's scorer.py, adapted for PromptForge.

Metrics reported:
  - score (primary): Partial Match Accuracy — mean per-example accuracy
    of aligned function calls (name + sorted arguments)
  - full_match_accuracy: Fraction of examples with perfect sequence match
  - f1_intent: Macro F1 on function name sequences
  - f1_slot: Macro F1 on argument slot sequences

Gold format: JSON list of function call dicts, each with "name", "arguments", "label".
Example: [{"name": "add", "arguments": {"arg_0": 1, "arg_1": 2}, "label": "$var_1"}]

Main entry point:
    compute_score(preds: list[str], golds: list[str], **kwargs) -> dict[str, Any]
"""

import json
import re
from typing import Any


# ============================================================================
# OUTPUT PARSER
# ============================================================================

def parse_function_calls(text: str) -> list[dict]:
    """
    Parse model output text into a list of function call dicts.

    Expected format: JSON list of {"name": ..., "arguments": {...}, "label": ...}

    Handles common model output variations:
    - Direct JSON list
    - JSON wrapped in markdown code blocks
    - JSON with "tool_calls" wrapper
    """
    text = text.strip()

    # Strip markdown code blocks if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Try direct JSON parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "tool_calls" in parsed:
            return parsed["tool_calls"]
        if isinstance(parsed, dict) and "name" in parsed:
            return [parsed]
        return []
    except json.JSONDecodeError:
        pass

    # Try to extract JSON list from text
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    return []


# ============================================================================
# GROUNDING: Replace variable labels with function names
# ============================================================================

def ground_variable_references(func_calls: list[dict]) -> list[dict]:
    """
    Replace variable labels in arguments with function names for
    robust comparison (insensitive to label naming conventions).

    E.g., if $var_1 was assigned to "divide", then "$var_1.result$"
    becomes "$divide.result$".
    """
    # Build label -> function name mapping
    label_to_func = {}
    for call in func_calls:
        label = call.get("label", "")
        if label:
            clean_label = label.replace("$", "")
            label_to_func[clean_label] = call.get("name", "")

    # Replace references in arguments
    grounded = []
    for call in func_calls:
        new_args = {}
        for key, val in call.get("arguments", {}).items():
            if isinstance(val, str) and "$" in val:
                for label, func_name in label_to_func.items():
                    # Handle both $var_1.result$ and $var1.result$ patterns
                    val = val.replace(f"${label}.", f"${func_name}.")
                    val = val.replace(f"${label}$", f"${func_name}$")
            new_args[key] = val
        grounded.append({
            "name": call.get("name", ""),
            "arguments": new_args,
            "label": call.get("label", ""),
        })
    return grounded


# ============================================================================
# CALL STRINGIFICATION
# ============================================================================

def call_to_string(call: dict) -> str:
    """
    Convert a function call dict to a canonical string for comparison.
    Format: func_name(arg1 = val1, arg2 = val2) with args sorted alphabetically.
    """
    name = str(call.get("name", ""))
    args = call.get("arguments", {})
    arg_strs = []
    for key in sorted(args.keys()):
        val = args[key]
        if isinstance(val, str) and val.startswith("$") and not val.endswith("$"):
            val = val + "$"
        arg_strs.append(f"{key} = {val}")
    return f"{name}({', '.join(arg_strs)})"


def extract_func_names(func_calls: list[dict]) -> list[str]:
    """Extract function name sequence from a list of calls."""
    names = []
    for call in func_calls:
        if isinstance(call, dict) and "name" in call:
            names.append(str(call["name"]))
    return names


def extract_slots(func_calls: list[dict]) -> list[list[str]]:
    """Extract argument slot lists per function call."""
    all_slots = []
    for call in func_calls:
        if not isinstance(call, dict) or "name" not in call:
            continue
        slots = []
        for key, val in call.get("arguments", {}).items():
            if isinstance(val, str) and val.startswith("$") and not val.endswith("$"):
                val = val + "$"
            slots.append(f"{key} = {val}")
        all_slots.append(slots)
    return all_slots


# ============================================================================
# SEQUENCE ALIGNMENT
# ============================================================================

def align_lists(list1: list, list2: list) -> tuple[list, list]:
    """
    Greedy alignment of two lists for comparison.
    Matching elements are paired; unmatched elements are paired with "".
    """
    aligned1, aligned2 = [], []
    i, j = 0, 0

    while i < len(list1) or j < len(list2):
        if i < len(list1) and j < len(list2) and list1[i] == list2[j]:
            aligned1.append(list1[i])
            aligned2.append(list2[j])
            i += 1
            j += 1
        elif i < len(list1):
            aligned1.append(list1[i])
            aligned2.append("")
            i += 1
        else:
            aligned1.append("")
            aligned2.append(list2[j])
            j += 1

    return aligned1, aligned2


# ============================================================================
# F1 COMPUTATION
# ============================================================================

def compute_f1_macro(gold_lists: list[list[str]], pred_lists: list[list[str]]) -> tuple[float, float, float]:
    """
    Compute macro-averaged precision, recall, F1 using multi-label binarization.
    Each item is a list of labels (function names or slots).
    """
    # Build vocabulary
    all_labels = set()
    for lst in gold_lists + pred_lists:
        all_labels.update(lst)

    if not all_labels:
        return 0.0, 0.0, 0.0

    label_to_idx = {label: idx for idx, label in enumerate(sorted(all_labels))}
    n = len(label_to_idx)

    # Binarize
    def binarize(label_list):
        vec = [0] * n
        for label in label_list:
            if label in label_to_idx:
                vec[label_to_idx[label]] = 1
        return vec

    gold_vecs = [binarize(lst) for lst in gold_lists]
    pred_vecs = [binarize(lst) for lst in pred_lists]

    # Compute per-label metrics, then macro average
    precisions, recalls, f1s = [], [], []
    for j in range(n):
        tp = sum(1 for i in range(len(gold_vecs)) if gold_vecs[i][j] == 1 and pred_vecs[i][j] == 1)
        fp = sum(1 for i in range(len(gold_vecs)) if gold_vecs[i][j] == 0 and pred_vecs[i][j] == 1)
        fn = sum(1 for i in range(len(gold_vecs)) if gold_vecs[i][j] == 1 and pred_vecs[i][j] == 0)

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        precisions.append(p)
        recalls.append(r)
        f1s.append(f1)

    macro_p = sum(precisions) / len(precisions) if precisions else 0.0
    macro_r = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0

    return macro_p, macro_r, macro_f1


# ============================================================================
# SINGLE EXAMPLE EVALUATION
# ============================================================================

def evaluate_single(pred_str: str, gold_str: str) -> dict:
    """
    Evaluate a single prediction against gold.

    Args:
        pred_str: Raw model output text (should be JSON list of function calls)
        gold_str: JSON string of gold function call sequence

    Returns:
        dict with per-example metrics
    """
    try:
        gold_calls = json.loads(gold_str)
    except json.JSONDecodeError:
        return {
            "partial_match": 0.0,
            "full_match": False,
            "gold_names": [],
            "pred_names": [],
            "gold_slots": [],
            "pred_slots": [],
            "parse_error": True,
        }

    pred_calls = parse_function_calls(pred_str)

    # Ground variable references
    gold_grounded = ground_variable_references(gold_calls)
    pred_grounded = ground_variable_references(pred_calls) if pred_calls else []

    # Compute call strings
    gold_strings = [call_to_string(c) for c in gold_grounded]
    pred_strings = [call_to_string(c) for c in pred_grounded]

    # Align and compute partial match accuracy
    if len(gold_strings) == len(pred_strings):
        aligned_gold, aligned_pred = gold_strings, pred_strings
    else:
        # Extract function names for alignment
        gold_names_for_align = [s.split("(", 1)[0] for s in gold_strings]
        pred_names_for_align = [s.split("(", 1)[0] for s in pred_strings]
        aligned_gold_names, aligned_pred_names = align_lists(gold_names_for_align, pred_names_for_align)

        # Rebuild aligned full strings
        aligned_gold, aligned_pred = [], []
        gold_idx, pred_idx = 0, 0
        for gn, pn in zip(aligned_gold_names, aligned_pred_names):
            if gn == "":
                aligned_gold.append("")
                aligned_pred.append(pred_strings[pred_idx])
                pred_idx += 1
            elif pn == "":
                aligned_gold.append(gold_strings[gold_idx])
                aligned_pred.append("")
                gold_idx += 1
            else:
                aligned_gold.append(gold_strings[gold_idx])
                aligned_pred.append(pred_strings[pred_idx])
                gold_idx += 1
                pred_idx += 1

    # Partial match: fraction of aligned calls that match exactly
    if aligned_gold:
        matches = sum(1 for g, p in zip(aligned_gold, aligned_pred) if g == p)
        partial_match = matches / len(aligned_gold)
    else:
        partial_match = 0.0

    full_match = partial_match == 1.0

    # Extract names and slots for F1 computation
    gold_names = extract_func_names(gold_grounded)
    pred_names = extract_func_names(pred_grounded)
    gold_slots_flat = []
    pred_slots_flat = []
    for slots in extract_slots(gold_grounded):
        gold_slots_flat.extend(slots)
    for slots in extract_slots(pred_grounded):
        pred_slots_flat.extend(slots)

    return {
        "partial_match": partial_match,
        "full_match": full_match,
        "gold_names": gold_names,
        "pred_names": pred_names,
        "gold_slots": [gold_slots_flat],
        "pred_slots": [pred_slots_flat],
        "parse_error": len(pred_calls) == 0,
    }


# ============================================================================
# PUBLIC API
# ============================================================================

def compute_score(preds: list[str], golds: list[str], **kwargs) -> dict[str, Any]:
    """
    Compute NESTFUL evaluation metrics.

    Args:
        preds: List of raw model output strings
        golds: List of JSON strings — each is the gold function call sequence,
               e.g. '[{"name": "add", "arguments": {"arg_0": 1, "arg_1": 2}, "label": "$var_1"}]'
        **kwargs: Additional parameters (unused)

    Returns:
        dict with keys:
            - 'score': Partial Match Accuracy (primary, 0.0-1.0, higher is better)
            - 'full_match_accuracy': Fraction with perfect sequence match
            - 'f1_intent': Macro F1 on function name sequences
            - 'f1_slot': Macro F1 on argument slot sequences
            - 'scores': Per-instance partial match scores
            - 'parse_failures': Count of predictions that failed to parse
    """
    if len(preds) != len(golds):
        raise ValueError(
            f"preds and golds must have same length. "
            f"Got {len(preds)} vs {len(golds)}"
        )

    if len(preds) == 0:
        return {
            "score": 0.0,
            "full_match_accuracy": 0.0,
            "f1_intent": 0.0,
            "f1_slot": 0.0,
            "total": 0,
            "scores": [],
            "parse_failures": 0,
        }

    partial_matches = []
    full_matches = 0
    parse_failures = 0
    all_gold_names = []
    all_pred_names = []
    all_gold_slots = []
    all_pred_slots = []

    for pred, gold in zip(preds, golds):
        result = evaluate_single(pred, gold)
        partial_matches.append(result["partial_match"])
        if result["full_match"]:
            full_matches += 1
        if result["parse_error"]:
            parse_failures += 1

        all_gold_names.append(result["gold_names"])
        all_pred_names.append(result["pred_names"])
        all_gold_slots.extend(result["gold_slots"])
        all_pred_slots.extend(result["pred_slots"])

    n = len(preds)
    partial_match_accuracy = sum(partial_matches) / n
    full_match_accuracy = full_matches / n

    # F1 Intent
    _, _, f1_intent = compute_f1_macro(all_gold_names, all_pred_names)

    # F1 Slot
    _, _, f1_slot = compute_f1_macro(all_gold_slots, all_pred_slots)

    return {
        "score": partial_match_accuracy,
        "partial_match_accuracy": partial_match_accuracy,
        "full_match_accuracy": full_match_accuracy,
        "f1_intent": f1_intent,
        "f1_slot": f1_slot,
        "total": n,
        "scores": partial_matches,
        "parse_failures": parse_failures,
    }


# ============================================================================
# QUICK EVALUATE
# ============================================================================

def quick_evaluate(preds: list[str], golds: list[str], **kwargs) -> float:
    """Return just the score as a float."""
    return compute_score(preds, golds, **kwargs)["score"]




def lambda_handler(event, context):
    preds = event.get("preds", [])
    golds = event.get("golds", [])
    kwargs = event.get("kwargs", {})
    return compute_score(preds, golds, **kwargs)
