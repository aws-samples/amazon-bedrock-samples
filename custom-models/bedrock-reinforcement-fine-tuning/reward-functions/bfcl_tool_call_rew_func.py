"""
BFCL Tool-Calling Reward Function for Bedrock RFT.

Scores model outputs by comparing predicted function calls against
ground truth using AST-level parsing with type coercion.

Scoring breakdown (per call):
  - 33% function name match
  - 33% parameter name accuracy
  - 34% parameter value accuracy (with type coercion)

Multiple calls are averaged. Missing or extra calls score 0.
"""
import ast
import re


def lambda_handler(event, context):
    """AWS Lambda handler for BFCL tool-calling reward function."""
    results = []
    for item in event:
        item_id = item.get("id") or item.get("task_id", "unknown")
        messages = item.get("messages", [])
        metadata = item.get("metadata", {})

        # Get ground truth — check metadata then top-level
        ground_truth = metadata.get("ground_truth")
        if not ground_truth:
            ground_truth = item.get("reference_answer", {}).get(
                "ground_truth"
            )
        if not ground_truth:
            ground_truth = item.get("ground_truth")

        # Get assistant response
        assistant_response = ""
        for msg in messages:
            if msg.get("role") == "assistant":
                assistant_response = msg.get("content", "")

        score = compute_score(assistant_response, ground_truth)

        results.append({
            "id": item_id,
            "aggregate_reward_score": score,
            "reward_components": {
                "tool_call_accuracy": score,
            },
        })

    return results


# ---------------------------------------------------------------------------
# Function call parsing
# ---------------------------------------------------------------------------

def parse_function_call(call_str):
    """Parse 'func(param1=val1, param2="str")' into (name, params)."""
    call_str = call_str.strip()
    try:
        tree = ast.parse(call_str, mode="eval")
    except SyntaxError:
        return None, {}

    if not isinstance(tree.body, ast.Call):
        return None, {}

    node = tree.body

    # Function name
    if isinstance(node.func, ast.Name):
        name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        n = node.func
        while isinstance(n, ast.Attribute):
            parts.append(n.attr)
            n = n.value
        if isinstance(n, ast.Name):
            parts.append(n.id)
        name = ".".join(reversed(parts))
    else:
        return None, {}

    # Arguments
    params = {}
    for i, arg in enumerate(node.args):
        try:
            params[f"_arg{i}"] = ast.literal_eval(arg)
        except (ValueError, TypeError):
            params[f"_arg{i}"] = ast.dump(arg)

    for kw in node.keywords:
        if kw.arg is None:
            continue
        try:
            params[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, TypeError):
            params[kw.arg] = ast.dump(kw.value)

    return name, params


def split_calls(text):
    """Split text containing multiple function calls."""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()

    calls = []
    depth = 0
    current = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "\n" and depth == 0:
            chunk = "".join(current).strip()
            if chunk:
                calls.append(chunk)
            current = []
        else:
            current.append(ch)
    chunk = "".join(current).strip()
    if chunk:
        calls.append(chunk)

    return [c.rstrip(",").strip() for c in calls if c.strip()]


# ---------------------------------------------------------------------------
# Value comparison with type coercion
# ---------------------------------------------------------------------------

def values_match(predicted, expected):
    """Compare two values with type coercion."""
    if predicted == expected:
        return True
    # String to number
    if isinstance(predicted, str) and isinstance(expected, (int, float)):
        try:
            return float(predicted) == float(expected)
        except (ValueError, TypeError):
            pass
    if isinstance(expected, str) and isinstance(predicted, (int, float)):
        try:
            return float(expected) == float(predicted)
        except (ValueError, TypeError):
            pass
    # String to bool
    if isinstance(predicted, str) and isinstance(expected, bool):
        return (predicted.lower() == "true") == expected
    # Recursive list/dict
    if isinstance(predicted, list) and isinstance(expected, list):
        if len(predicted) != len(expected):
            return False
        return all(values_match(p, e) for p, e in zip(predicted, expected))
    if isinstance(predicted, dict) and isinstance(expected, dict):
        if set(predicted.keys()) != set(expected.keys()):
            return False
        return all(values_match(predicted[k], expected[k]) for k in expected)
    return False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_single_call(pred_name, pred_params, exp_name, exp_params):
    """Score one predicted call against one expected call."""
    name_match = 1.0 if pred_name == exp_name else 0.0

    exp_keys = set(exp_params.keys())
    pred_keys = set(pred_params.keys())
    common = exp_keys & pred_keys

    if exp_keys:
        name_acc = len(common) / len(exp_keys)
        val_matches = sum(
            1 for k in common if values_match(pred_params[k], exp_params[k])
        )
        val_acc = val_matches / len(exp_keys)
    else:
        name_acc = 1.0 if not pred_keys else 0.0
        val_acc = 1.0 if not pred_keys else 0.0

    return name_match * 0.33 + name_acc * 0.33 + val_acc * 0.34


def compute_score(response, ground_truth):
    """
    Compute reward score for a tool-calling response.

    Args:
        response: The model's assistant response text
        ground_truth: str or list of expected function call strings

    Returns:
        float between 0.0 and 1.0
    """
    if not response or not ground_truth:
        return 0.0

    # Normalize ground truth to list
    if isinstance(ground_truth, str):
        gt_strs = [ground_truth]
    elif isinstance(ground_truth, list):
        gt_strs = [str(g) for g in ground_truth]
    else:
        return 0.0

    # Parse predicted calls
    try:
        pred_calls = [parse_function_call(s) for s in split_calls(response)]
    except Exception:
        return 0.0

    # Parse expected calls
    try:
        exp_calls = [parse_function_call(s) for s in gt_strs]
    except Exception:
        return 0.0

    # Score by position
    n = max(len(exp_calls), len(pred_calls), 1)
    total = 0.0
    for (pn, pp), (en, ep) in zip(pred_calls, exp_calls):
        if pn is None or en is None:
            continue
        total += score_single_call(pn, pp, en, ep)

    return round(total / n, 4)
