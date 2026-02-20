"""
Guardrail optimization agent using Strands Agents SDK.
Iteratively improves guardrail configuration based on test results.
"""

import json
import os
from datetime import datetime
from typing import Any
from strands import Agent, tool
from strands.models import BedrockModel

from guardrail_config import get_baseline_config
from guardrail_manager import GuardrailManager
from evaluator import GuardrailEvaluator
from report_generator import generate_final_report, load_iteration_reports

# Reports directory
REPORTS_DIR = "evaluation_reports"

# Optimization metrics options
METRIC_ACCURACY = "accuracy"
METRIC_LATENCY = "latency"
METRIC_GENERALIZATION = "generalization"
METRIC_ALL = "all"

# Global state for the optimization session
_session_state = {
    "guardrail_id": None,
    "current_config": None,
    "best_accuracy": 0.0,
    "best_latency": float("inf"),
    "best_generalization": 0.0,
    "best_config": None,
    "iteration": 0,
    "max_iterations": 5,
    "region": "us-east-1",
    "history": [],  # List of dicts with all metrics per iteration
    "session_id": None,
    "start_from_best": True,  # Start from best previous config or baseline
    "target_metrics": [METRIC_ACCURACY],  # Metrics to optimize
    "iteration_changes": [],  # Track changes made each iteration
    "generalization_details": [],  # Details from generalization testing
    "passed_file": "passed_guardrail_results.json",  # Test cases file
    "failed_file": "failed_guardrail_results.json"   # Test cases file
}


def _ensure_reports_dir():
    """Ensure the reports directory exists."""
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)


def _get_report_filename(iteration: int) -> str:
    """Generate timestamped report filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = _session_state.get("session_id", timestamp)
    return os.path.join(REPORTS_DIR, f"eval_{session_id}_iter{iteration}.json")


@tool
def analyze_previous_optimizations() -> str:
    """
    Analyze all previous optimization reports to learn from past sessions.
    
    Returns:
        Summary of learnings from previous optimization sessions
    """
    _ensure_reports_dir()
    reports = load_iteration_reports(REPORTS_DIR)
    
    if not reports:
        return "No previous optimization reports found. Starting fresh."
    
    # Group reports by session (based on filename patterns)
    sessions = {}
    for r in reports:
        session = r.get("session_id", "unknown")
        if session not in sessions:
            sessions[session] = []
        sessions[session].append(r)
    
    # Analyze each session
    analysis = [f"Found {len(reports)} reports from {len(sessions)} previous session(s).\n"]
    
    # Find best overall configuration
    best_report = max(reports, key=lambda r: r.get("metrics", {}).get("accuracy", 0))
    best_acc = best_report.get("metrics", {}).get("accuracy", 0) * 100
    
    analysis.append(f"BEST HISTORICAL ACCURACY: {best_acc:.1f}%")
    
    # Analyze common failure patterns
    all_fp_inputs = []
    all_fn_inputs = []
    
    for r in reports:
        for case in r.get("failed_cases", []):
            if case.get("expected") == "pass" and case.get("actual") == "reject":
                all_fp_inputs.append(case.get("input", ""))
            elif case.get("expected") == "reject" and case.get("actual") == "pass":
                all_fn_inputs.append(case.get("input", ""))
    
    # Find most common false positive patterns
    if all_fp_inputs:
        from collections import Counter
        fp_counter = Counter(all_fp_inputs)
        common_fp = fp_counter.most_common(5)
        analysis.append("\nMOST COMMON FALSE POSITIVES (queries incorrectly blocked):")
        for inp, count in common_fp:
            analysis.append(f"  - \"{inp[:60]}...\" (occurred {count}x)")
    
    # Find most common false negative patterns
    if all_fn_inputs:
        from collections import Counter
        fn_counter = Counter(all_fn_inputs)
        common_fn = fn_counter.most_common(5)
        analysis.append("\nMOST COMMON FALSE NEGATIVES (queries incorrectly allowed):")
        for inp, count in common_fn:
            analysis.append(f"  - \"{inp[:60]}...\" (occurred {count}x)")
    
    # Extract best configuration insights
    best_config = best_report.get("configuration", {})
    if best_config:
        topics = best_config.get("topicPolicyConfig", {}).get("topicsConfig", [])
        analysis.append(f"\nBEST CONFIG HAD {len(topics)} DENIED TOPICS:")
        for t in topics[:5]:
            analysis.append(f"  - {t.get('name', 'Unknown')}")
        if len(topics) > 5:
            analysis.append(f"  ... and {len(topics) - 5} more")
    
    analysis.append("\nUSE THESE INSIGHTS to avoid repeating past mistakes and build on successful configurations.")
    
    return "\n".join(analysis)


@tool
def load_test_cases(passed_file: str = None, failed_file: str = None) -> str:
    """
    Load test cases from the JSON files.
    
    Args:
        passed_file: Path to passed test cases file (uses session default if not provided)
        failed_file: Path to failed test cases file (uses session default if not provided)
    
    Returns:
        Summary of loaded test cases with examples
    """
    # Use session state defaults if not provided
    if passed_file is None:
        passed_file = _session_state["passed_file"]
    if failed_file is None:
        failed_file = _session_state["failed_file"]
    
    evaluator = GuardrailEvaluator(region=_session_state["region"])
    
    passed_cases = evaluator.load_test_cases(passed_file)
    failed_cases = evaluator.load_test_cases(failed_file)
    
    should_pass = [tc for tc in passed_cases + failed_cases if tc.expected == "pass"]
    should_reject = [tc for tc in passed_cases + failed_cases if tc.expected == "reject"]
    
    result = f"""
Loaded {len(passed_cases) + len(failed_cases)} total test cases:
- Should PASS (legitimate queries): {len(should_pass)}
- Should REJECT (off-topic/harmful): {len(should_reject)}

Sample queries that should PASS:
{chr(10).join(f'- "{tc.input}"' for tc in should_pass[:5])}

Sample queries that should REJECT:
{chr(10).join(f'- "{tc.input}"' for tc in should_reject[:5])}
"""
    return result


@tool
def get_best_practices() -> str:
    """
    Get AWS best practices for Bedrock Guardrails optimization.
    
    Returns:
        Best practices documentation content
    """
    bp_path = os.path.join(os.path.dirname(__file__), "guardrails_best_practices.md")
    try:
        with open(bp_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Best practices file not found. Use general guardrails optimization principles."


@tool
def deploy_guardrail(config_json: str) -> str:
    """
    Deploy a guardrail configuration to AWS Bedrock.
    
    Args:
        config_json: JSON string of the guardrail configuration
    
    Returns:
        Deployment result with guardrail ID
    """
    try:
        config = json.loads(config_json)
        manager = GuardrailManager(region=_session_state["region"])
        result = manager.create_or_update(config)
        
        _session_state["guardrail_id"] = result["guardrailId"]
        _session_state["current_config"] = config
        
        return f"Deployed guardrail successfully. ID: {result['guardrailId']}, Version: {result['version']}"
    except Exception as e:
        return f"Error deploying guardrail: {str(e)}"


@tool
def get_current_config() -> str:
    """
    Get the starting guardrail configuration.
    Returns best previous config if start_from_best=True and one exists, otherwise baseline.
    
    Returns:
        JSON string of the configuration
    """
    if _session_state["start_from_best"]:
        # Try to load best config from previous sessions
        best_config = _load_best_previous_config()
        if best_config:
            return json.dumps(best_config, indent=2)
    
    config = get_baseline_config()
    return json.dumps(config, indent=2)


def _load_best_previous_config() -> dict | None:
    """Load the best configuration from previous optimization sessions."""
    _ensure_reports_dir()
    reports = load_iteration_reports(REPORTS_DIR)
    
    if not reports:
        return None
    
    # Find report with best accuracy that has a configuration
    best_report = None
    best_acc = 0.0
    
    for r in reports:
        acc = r.get("metrics", {}).get("accuracy", 0)
        config = r.get("configuration", {})
        if acc > best_acc and config:
            best_acc = acc
            best_report = r
    
    if best_report and best_report.get("configuration"):
        print(f"Loading best previous config with {best_acc*100:.1f}% accuracy")
        return best_report["configuration"]
    
    return None


@tool
def evaluate_guardrail(guardrail_id: str) -> str:
    """
    Evaluate a guardrail against all test cases with accuracy, latency, and generalization metrics.
    
    Args:
        guardrail_id: The guardrail ID to evaluate
    
    Returns:
        Evaluation report with all metrics and failed cases
    """
    _ensure_reports_dir()
    evaluator = GuardrailEvaluator(region=_session_state["region"])
    
    passed_cases = evaluator.load_test_cases(_session_state["passed_file"])
    failed_cases = evaluator.load_test_cases(_session_state["failed_file"])
    all_cases = passed_cases + failed_cases
    
    print(f"Evaluating {len(all_cases)} test cases...")
    report = evaluator.evaluate_all(guardrail_id, all_cases, max_workers=3)
    
    # Always evaluate generalization so it appears in reports
    # (but only use it for optimization decisions if it's in target_metrics)
    if _session_state["current_config"]:
        print("Evaluating denied topic generalization with LLM-generated cases...")
        score, details = evaluator.evaluate_generalization_with_llm(
            guardrail_id,
            _session_state["current_config"],
            all_cases,
            num_cases_per_topic=2  # 2 cases per denied topic for balanced coverage
        )
        report.generalization_score = score
        # Store details for reporting
        _session_state["generalization_details"] = details
    
    # Update iteration counter
    _session_state["iteration"] += 1
    
    # Store metrics history
    iteration_metrics = {
        "accuracy": report.accuracy,
        "avg_latency_ms": report.avg_latency_ms,
        "p95_latency_ms": report.p95_latency_ms,
        "generalization_score": report.generalization_score,
        "false_positives": report.false_positives,
        "false_negatives": report.false_negatives
    }
    _session_state["history"].append(iteration_metrics)
    
    # Update best config based on target metrics
    is_better = _is_better_config(report)
    if is_better:
        _session_state["best_accuracy"] = report.accuracy
        _session_state["best_latency"] = report.avg_latency_ms
        _session_state["best_generalization"] = report.generalization_score
        _session_state["best_config"] = _session_state["current_config"].copy() if _session_state["current_config"] else None
    
    # Format failed cases for analysis
    fp_cases = [c for c in report.failed_cases if c.expected == "pass" and c.actual == "reject"]
    fn_cases = [c for c in report.failed_cases if c.expected == "reject" and c.actual == "pass"]
    
    result = f"""
EVALUATION REPORT (Iteration {_session_state['iteration']} of {_session_state['max_iterations']})
{'='*50}
Total Tests: {report.total_tests}
Passed: {report.passed_tests}
Failed: {report.failed_tests}

METRICS:
- Accuracy: {report.accuracy:.2%}
- Avg Latency: {report.avg_latency_ms:.1f}ms
- P95 Latency: {report.p95_latency_ms:.1f}ms
- Generalization: {report.generalization_score:.2%}

False Positives: {report.false_positives} (should pass, got reject)
False Negatives: {report.false_negatives} (should reject, got pass)

BEST SO FAR:
- Accuracy: {_session_state['best_accuracy']:.2%}
- Latency: {_session_state['best_latency']:.1f}ms
- Generalization: {_session_state['best_generalization']:.2%}

Iterations Remaining: {_session_state['max_iterations'] - _session_state['iteration']}

FALSE POSITIVES (legitimate queries incorrectly blocked):
{chr(10).join(f'- "{c.input}" -> blocked by: {", ".join(c.violated_policies + c.violated_filters)}' for c in fp_cases[:10])}

FALSE NEGATIVES (off-topic queries incorrectly allowed):
{chr(10).join(f'- "{c.input}"' for c in fn_cases[:10])}
"""
    
    # Save report with timestamp and configuration
    report_path = _get_report_filename(_session_state["iteration"])
    evaluator.save_report(
        report, 
        report_path,
        config=_session_state["current_config"],
        session_id=_session_state["session_id"]
    )
    print(f"Report saved to: {report_path}")
    
    return result


def _is_better_config(report) -> bool:
    """Determine if current report represents a better config based on target metrics."""
    target_metrics = _session_state["target_metrics"]
    
    # For "all", use weighted combination
    if METRIC_ALL in target_metrics:
        current_score = (
            report.accuracy * 0.5 +
            (1 - min(report.avg_latency_ms / 1000, 1)) * 0.2 +  # Normalize latency
            report.generalization_score * 0.3
        )
        best_score = (
            _session_state["best_accuracy"] * 0.5 +
            (1 - min(_session_state["best_latency"] / 1000, 1)) * 0.2 +
            _session_state["best_generalization"] * 0.3
        )
        return current_score > best_score
    
    # Check individual metrics
    if METRIC_ACCURACY in target_metrics:
        if report.accuracy > _session_state["best_accuracy"]:
            return True
    
    if METRIC_LATENCY in target_metrics:
        if report.avg_latency_ms < _session_state["best_latency"]:
            return True
    
    if METRIC_GENERALIZATION in target_metrics:
        if report.generalization_score > _session_state["best_generalization"]:
            return True
    
    return False


@tool
def check_iteration_limit() -> str:
    """
    Check if we've reached the maximum iteration limit or if stop was requested.
    
    Returns:
        Status message indicating if optimization should continue
    """
    current = _session_state["iteration"]
    max_iter = _session_state["max_iterations"]
    best_acc = _session_state["best_accuracy"]
    stop_flag = _session_state.get("stop_flag")
    
    print(f"\n###### Current iter: {current}, Max iter: {max_iter}, Best acc: {best_acc} ######\n")

    # Check if stop was requested
    if stop_flag and stop_flag.is_set():
        print("Stop requested by user!")
        return f"STOP: User requested stop. Best accuracy: {best_acc:.2%}. Call save_best_config then create_final_report to finish."

    if current >= max_iter:
        return f"STOP: Reached maximum iterations ({max_iter}). Best accuracy: {best_acc:.2%}. Call save_best_config then create_final_report to finish."
    
    if best_acc >= 1.0:
        return f"STOP: Reached 100% accuracy ({best_acc:.2%}). Call save_best_config then create_final_report to finish."
    
    return f"CONTINUE: Iteration {current}/{max_iter}, Best accuracy: {best_acc:.2%}. You may continue optimizing."


@tool
def update_topic_definition(topic_name: str, new_definition: str, new_examples: str) -> str:
    """
    Update a specific topic's definition and examples in the current config.
    
    Args:
        topic_name: Name of the topic to update
        new_definition: New definition for the topic
        new_examples: Comma-separated list of new example phrases
    
    Returns:
        Confirmation of the update
    """
    if not _session_state["current_config"]:
        return "No current config loaded. Deploy a guardrail first."
    
    config = _session_state["current_config"]
    topics = config.get("topicPolicyConfig", {}).get("topicsConfig", [])
    
    examples_list = [e.strip() for e in new_examples.split(",")]
    
    for topic in topics:
        if topic["name"] == topic_name:
            topic["definition"] = new_definition
            topic["examples"] = examples_list
            _session_state["current_config"] = config
            return f"Updated topic '{topic_name}' with new definition and {len(examples_list)} examples."
    
    return f"Topic '{topic_name}' not found in current config."


@tool
def add_new_topic(name: str, definition: str, examples: str) -> str:
    """
    Add a new denied topic to the current configuration.
    
    Args:
        name: Name for the new topic
        definition: Definition describing what to block
        examples: Comma-separated list of example phrases
    
    Returns:
        Confirmation of the addition
    """
    if not _session_state["current_config"]:
        return "No current config loaded. Deploy a guardrail first."
    
    config = _session_state["current_config"]
    examples_list = [e.strip() for e in examples.split(",")]
    
    new_topic = {
        "name": name,
        "definition": definition,
        "examples": examples_list,
        "type": "DENY",
        "inputEnabled": True,
        "outputEnabled": True
    }
    
    config["topicPolicyConfig"]["topicsConfig"].append(new_topic)
    _session_state["current_config"] = config
    
    return f"Added new topic '{name}' with {len(examples_list)} examples."


@tool
def add_word_filter(words: str) -> str:
    """
    Add words to the word filter list.
    
    Args:
        words: Comma-separated list of words to block
    
    Returns:
        Confirmation of words added
    """
    if not _session_state["current_config"]:
        return "No current config loaded. Deploy a guardrail first."
    
    config = _session_state["current_config"]
    word_list = [w.strip() for w in words.split(",")]
    
    for word in word_list:
        config["wordPolicyConfig"]["wordsConfig"].append({
            "text": word,
            "inputEnabled": True,
            "outputEnabled": True
        })
    
    _session_state["current_config"] = config
    return f"Added {len(word_list)} words to filter: {', '.join(word_list)}"


@tool
def test_generalization(guardrail_id: str, num_cases_per_topic: int = 2) -> str:
    """
    Test how well the current denied topic configuration generalizes to novel inputs.
    Generates test cases for EACH denied topic to ensure balanced coverage.
    This helps detect if the configuration is overfitting to the specific test samples.
    
    Args:
        guardrail_id: The guardrail ID to test
        num_cases_per_topic: Number of novel test cases per denied topic (default: 2)
    
    Returns:
        Generalization test results with overall score and per-topic breakdown
    """
    if not _session_state["current_config"]:
        return "No current config loaded. Deploy a guardrail first."
    
    evaluator = GuardrailEvaluator(region=_session_state["region"])
    
    # Load existing test cases using session state file paths
    passed_cases = evaluator.load_test_cases(_session_state["passed_file"])
    failed_cases = evaluator.load_test_cases(_session_state["failed_file"])
    all_cases = passed_cases + failed_cases
    
    # Run LLM-based generalization test (generates cases for each topic)
    score, details = evaluator.evaluate_generalization_with_llm(
        guardrail_id,
        _session_state["current_config"],
        all_cases,
        num_cases_per_topic=num_cases_per_topic
    )
    
    # Store for reporting
    _session_state["generalization_details"] = details
    _session_state["best_generalization"] = max(_session_state["best_generalization"], score)
    
    # Group results by topic
    topic_results = {}
    for d in details:
        topic = d.get("target_topic", "Unknown")
        if topic not in topic_results:
            topic_results[topic] = {"blocked": 0, "total": 0, "failed_inputs": []}
        topic_results[topic]["total"] += 1
        if d["correct"]:
            topic_results[topic]["blocked"] += 1
        else:
            topic_results[topic]["failed_inputs"].append(d["input"])
    
    # Format per-topic results
    topic_breakdown = []
    for topic, results in sorted(topic_results.items()):
        topic_score = results["blocked"] / results["total"] if results["total"] > 0 else 0
        status = "✓" if topic_score >= 0.8 else "⚠" if topic_score >= 0.5 else "✗"
        topic_breakdown.append(f"  {status} {topic}: {results['blocked']}/{results['total']} ({topic_score:.0%})")
        if results["failed_inputs"]:
            for inp in results["failed_inputs"][:2]:
                topic_breakdown.append(f"      - PASSED: \"{inp[:50]}...\"")
    
    result = f"""
GENERALIZATION TEST RESULTS
{'='*50}
Overall Score: {score:.1%} ({sum(1 for d in details if d['correct'])}/{len(details)} novel cases blocked)

PER-TOPIC BREAKDOWN:
{chr(10).join(topic_breakdown)}

INTERPRETATION:
- ✓ Score >= 80%: Good generalization
- ⚠ Score 50-79%: Moderate - consider broadening topic definition
- ✗ Score < 50%: Poor - topic may be overfitting to examples
"""
    return result


@tool
def record_iteration_changes(changes_summary: str) -> str:
    """
    Record the key changes made in the current iteration for the final report.
    Call this after making changes and before redeploying.
    
    Args:
        changes_summary: Brief description of changes made (e.g., "Added celebrity word filters, refined Medical topic definition")
    
    Returns:
        Confirmation message
    """
    iteration = _session_state["iteration"] + 1  # Next iteration
    _session_state["iteration_changes"].append({
        "iteration": iteration,
        "changes": changes_summary
    })
    return f"Recorded changes for iteration {iteration}: {changes_summary}"


@tool
def save_best_config(filepath: str = None) -> str:
    """
    Save the best performing configuration to a file.
    
    Args:
        filepath: Path to save the configuration (optional, auto-generated if not provided)
    
    Returns:
        Confirmation message with file path
    """
    _ensure_reports_dir()
    
    if not _session_state["best_config"]:
        return "No best config available yet. Run evaluations first."
    
    if not filepath:
        filepath = os.path.join(REPORTS_DIR, f"best_config_{_session_state['session_id']}.json")
    
    with open(filepath, 'w') as f:
        json.dump(_session_state["best_config"], f, indent=2)
    
    return f"Saved best config (accuracy: {_session_state['best_accuracy']:.2%}) to {filepath}"


@tool
def redeploy_current_config() -> str:
    """
    Redeploy the current modified configuration.
    
    Returns:
        Deployment result
    """
    if not _session_state["current_config"]:
        return "No current config to deploy."
    
    return deploy_guardrail(json.dumps(_session_state["current_config"]))


@tool
def create_final_report() -> str:
    """
    Generate final HTML and PDF reports with accuracy graphs, insights, and best config appendix.
    
    Returns:
        Paths to generated reports
    """
    _ensure_reports_dir()
    
    # Save best config first
    best_config_path = None
    if _session_state["best_config"]:
        best_config_path = os.path.join(REPORTS_DIR, f"best_config_{_session_state['session_id']}.json")
        with open(best_config_path, 'w') as f:
            json.dump(_session_state["best_config"], f, indent=2)
    
    html_path, pdf_path = generate_final_report(
        REPORTS_DIR, 
        best_config=_session_state["best_config"],
        best_accuracy=_session_state["best_accuracy"],
        session_id=_session_state["session_id"]
    )
    
    result = f"Generated final reports:\n- HTML: {html_path}"
    if pdf_path:
        result += f"\n- PDF: {pdf_path}"
    else:
        result += "\n- PDF: Install weasyprint for PDF generation, or open HTML and print to PDF"
    if best_config_path:
        result += f"\n- Best Config: {best_config_path}"
    
    return result


def create_optimization_agent(
    region: str = "us-east-1",
    max_iterations: int = 5,
    start_from_best: bool = True,
    target_metrics: list[str] = None,
    passed_file: str = "passed_guardrail_results.json",
    failed_file: str = "failed_guardrail_results.json"
) -> Agent:
    """
    Create the optimization agent with Strands SDK.
    
    Args:
        region: AWS region for Bedrock
        max_iterations: Maximum optimization iterations
        start_from_best: If True, start from best previous config; if False, start from baseline
        target_metrics: List of metrics to optimize ("accuracy", "latency", "generalization", "all")
        passed_file: Path to passed test cases JSON file
        failed_file: Path to failed test cases JSON file
    
    Returns:
        Configured Agent instance
    """
    if target_metrics is None:
        target_metrics = [METRIC_ACCURACY]
    
    # Initialize session with timestamp
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    _session_state["region"] = region
    _session_state["max_iterations"] = max_iterations
    _session_state["iteration"] = 0
    _session_state["best_accuracy"] = 0.0
    _session_state["best_latency"] = float("inf")
    _session_state["best_generalization"] = 0.0
    _session_state["best_config"] = None
    _session_state["history"] = []
    _session_state["session_id"] = session_id
    _session_state["start_from_best"] = start_from_best
    _session_state["target_metrics"] = target_metrics
    _session_state["iteration_changes"] = []
    _session_state["generalization_details"] = []
    _session_state["passed_file"] = passed_file
    _session_state["failed_file"] = failed_file
    
    _ensure_reports_dir()
    
    model = BedrockModel(
        model_id="global.anthropic.claude-opus-4-5-20251101-v1:0",
        region_name=region,
        temperature=0.3,
        max_tokens=8192
    )
    
    # Build metrics description
    metrics_desc = ", ".join(target_metrics)
    start_desc = "best previous configuration" if start_from_best else "baseline configuration"
    
    system_prompt = f"""You are an expert at optimizing Amazon Bedrock Guardrails configurations.

Your goal is to find the optimal guardrail configuration for an AI assistant that:
1. ALLOWS legitimate domain-specific queries
2. BLOCKS off-topic queries (celebrities, general knowledge, personal opinions)
3. BLOCKS harmful content and prompt injection attempts

TARGET METRICS: {metrics_desc}
STARTING FROM: {start_desc}

CRITICAL: You have a MAXIMUM of {max_iterations} iterations. After each evaluation, call check_iteration_limit to see if you should continue or stop.

OPTIMIZATION WORKFLOW:
1. FIRST, call analyze_previous_optimizations to learn from past sessions
2. Call get_best_practices to learn AWS recommended optimization techniques
3. Load and analyze the test cases
4. Get and deploy the starting configuration (will use {start_desc})
5. Evaluate against all test cases
6. Call check_iteration_limit - if STOP, call save_best_config then create_final_report and finish
7. If CONTINUE, analyze failures and make targeted improvements
8. Call record_iteration_changes with a summary of what you changed
9. Redeploy and re-evaluate
10. Repeat steps 6-9 until limit reached

KEY OPTIMIZATION PRINCIPLES:
- Analyze false positives: legitimate queries incorrectly blocked
- Analyze false negatives: off-topic queries incorrectly allowed
- Refine topic definitions to be more precise
- Use word filters for specific terms that should always be blocked
- Test generalization to avoid overfitting to specific test samples

IMPORTANT: 
- Always call analyze_previous_optimizations FIRST to learn from history
- Always call record_iteration_changes after making changes to track what was modified
- Always call check_iteration_limit after each evaluation to respect the iteration limit
- When optimization is complete (STOP signal), call save_best_config then create_final_report"""

    agent = Agent(
        model=model,
        tools=[
            analyze_previous_optimizations,
            load_test_cases,
            get_best_practices,
            get_current_config,
            deploy_guardrail,
            evaluate_guardrail,
            test_generalization,
            check_iteration_limit,
            update_topic_definition,
            add_new_topic,
            add_word_filter,
            record_iteration_changes,
            redeploy_current_config,
            save_best_config,
            create_final_report
        ],
        system_prompt=system_prompt
    )
    
    return agent


def run_optimization(
    max_iterations: int = 5,
    region: str = "us-east-1",
    start_from_best: bool = True,
    target_metrics: list[str] = None,
    passed_file: str = "passed_guardrail_results.json",
    failed_file: str = "failed_guardrail_results.json",
    stop_flag=None
) -> None:
    """
    Run the optimization loop with strict iteration control.
    
    Args:
        max_iterations: Maximum optimization iterations
        region: AWS region
        start_from_best: If True, start from best previous config; if False, start from baseline
        target_metrics: List of metrics to optimize ("accuracy", "latency", "generalization", "all")
        passed_file: Path to passed test cases JSON file
        failed_file: Path to failed test cases JSON file
        stop_flag: Threading event to signal stop request
    """
    if target_metrics is None:
        target_metrics = [METRIC_ACCURACY]
    
    # Store stop flag in session state for tools to check
    _session_state["stop_flag"] = stop_flag
    
    agent = create_optimization_agent(
        region=region,
        max_iterations=max_iterations,
        start_from_best=start_from_best,
        target_metrics=target_metrics,
        passed_file=passed_file,
        failed_file=failed_file
    )
    
    start_desc = "best previous configuration" if start_from_best else "baseline configuration"
    metrics_desc = ", ".join(target_metrics)
    
    initial_prompt = f"""
Please optimize the AI assistant guardrail configuration.

You have exactly {max_iterations} iterations maximum.
Starting from: {start_desc}
Target metrics: {metrics_desc}

Follow this workflow:

1. FIRST, call analyze_previous_optimizations to learn from any past sessions
2. Call get_best_practices to understand AWS optimization guidelines
3. Load the test cases to understand what we're optimizing for
4. Get and deploy the starting configuration
5. Evaluate the configuration
6. Call check_iteration_limit to see if you should continue
7. If CONTINUE: make improvements, call record_iteration_changes, redeploy, evaluate, and check limit again
8. If STOP: call save_best_config then create_final_report, then finish

Start now by calling analyze_previous_optimizations.
"""
    
    print("Starting guardrail optimization agent...")
    print(f"Session ID: {_session_state['session_id']}")
    print(f"Max iterations: {max_iterations}")
    print(f"Start from: {start_desc}")
    print(f"Target metrics: {metrics_desc}")
    print(f"Reports directory: {REPORTS_DIR}")
    print("=" * 60)
    
    # Single agent call - the agent manages its own iteration loop
    response = agent(initial_prompt)
    print(response)
    
    # Print final summary (report generation is handled by the agent via create_final_report tool)
    if _session_state["iteration"] > 0:
        print("\n" + "=" * 60)
        print(f"Optimization complete after {_session_state['iteration']} iterations")
        print(f"Best accuracy: {_session_state['best_accuracy']:.2%}")


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Run guardrail optimization")
    parser.add_argument("--max-iterations", "-n", type=int, default=5, help="Maximum iterations")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--start-from-baseline", "-b", action="store_true",
                        help="Start from baseline config instead of best previous")
    parser.add_argument("--metrics", "-m", nargs="+", 
                        choices=["accuracy", "latency", "generalization", "all"],
                        default=["accuracy"], help="Target metrics to optimize")
    
    args = parser.parse_args()
    
    run_optimization(
        max_iterations=args.max_iterations,
        region=args.region,
        start_from_best=not args.start_from_baseline,
        target_metrics=args.metrics
    )
