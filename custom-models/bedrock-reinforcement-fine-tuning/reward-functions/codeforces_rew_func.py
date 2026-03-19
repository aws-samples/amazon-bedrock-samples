import json
import re
import subprocess
import tempfile
import os
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class RewardOutput:
    id: str
    aggregate_reward_score: float
    score: float
    metrics_list: List[dict]


def extract_python_code(response: str) -> Optional[str]:
    """
    Extract Python code from the assistant response.
    Handles responses wrapped in ```python ... ``` blocks or raw code.
    """
    # Try to extract from markdown code blocks
    patterns = [
        r"```python\s*\n(.*?)```",
        r"```\s*\n(.*?)```",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[-1].strip()

    # If no code block found, treat the entire response as code
    # but only if it looks like Python (contains def, import, print, input, etc.)
    stripped = response.strip()
    code_indicators = ["import ", "from ", "def ", "print(", "input(", "for ", "while ", "if ", "="]
    if any(indicator in stripped for indicator in code_indicators):
        return stripped

    return None


def run_code_against_test(code: str, test_input: str, expected_output: str, timeout: int = 10) -> bool:
    """
    Run the extracted code against a single test case.
    Returns True if the output matches expected output.
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            tmp_path = f.name

        result = subprocess.run(
            ['python3', tmp_path],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        os.unlink(tmp_path)

        actual = result.stdout.strip()
        expected = expected_output.strip()

        return actual == expected

    except (subprocess.TimeoutExpired, Exception):
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return False


def compute_score(trajectory_id: str, response: str, test_cases: list) -> RewardOutput:
    """
    Score a response by extracting code and running it against test cases.

    Scoring:
    - 1.0 if all test cases pass
    - partial credit: fraction of test cases passed
    - 0.1 if code is extracted but no tests pass (format reward)
    - 0.0 if no code can be extracted
    """
    code = extract_python_code(response)

    if code is None:
        return RewardOutput(
            id=trajectory_id,
            aggregate_reward_score=0.0,
            score=0.0,
            metrics_list=[{"metric": "no_code_extracted", "value": 1}],
        )

    if not test_cases:
        # No test cases available — give a small format reward for producing code
        return RewardOutput(
            id=trajectory_id,
            aggregate_reward_score=0.1,
            score=0.1,
            metrics_list=[{"metric": "no_test_cases", "value": 1}],
        )

    passed = 0
    total = len(test_cases)

    for tc in test_cases:
        test_input = tc.get("input", "")
        expected_output = tc.get("output", "")
        if run_code_against_test(code, test_input, expected_output):
            passed += 1

    if total > 0:
        fraction = passed / total
    else:
        fraction = 0.0

    # Give a small format reward (0.1) if code was extracted but nothing passed
    final_score = max(fraction, 0.1) if fraction == 0.0 else fraction

    return RewardOutput(
        id=trajectory_id,
        aggregate_reward_score=float(final_score),
        score=float(final_score),
        metrics_list=[
            {"metric": "tests_passed", "value": passed},
            {"metric": "tests_total", "value": total},
        ],
    )


def lambda_handler(event, context):
    """
    Receives a batch of trajectory objects as a JSON array.
    Each trajectory has: id, messages, metadata (with test_cases).
    Returns a JSON array of reward outputs.
    """
    print("Event: ", json.dumps(event))

    trajectories = event if isinstance(event, list) else event.get("trajectories", [])

    scores = []
    for trajectory in trajectories:
        trajectory_id = trajectory.get("id", "no-id")

        # Get the assistant response (last assistant message)
        response = ""
        for msg in reversed(trajectory.get("messages", [])):
            if msg.get("role") == "assistant":
                response = msg.get("content", "")
                break

        # Get test cases from metadata
        metadata = trajectory.get("metadata", {})
        test_cases = metadata.get("test_cases", [])

        # Also check reference_answer for test cases (fallback)
        if not test_cases:
            ref = trajectory.get("reference_answer", {})
            if isinstance(ref, dict):
                test_cases = ref.get("test_cases", [])

        result = compute_score(
            trajectory_id=trajectory_id,
            response=response,
            test_cases=test_cases,
        )
        scores.append(result)

        code = extract_python_code(response)
        print(
            f"id={trajectory_id} "
            f"code_extracted={code is not None} "
            f"score={result.aggregate_reward_score}"
        )

    return [asdict(s) for s in scores]
