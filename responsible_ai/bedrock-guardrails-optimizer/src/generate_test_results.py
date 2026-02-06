#!/usr/bin/env python3
"""
Generate test result JSON files from a CSV of inputs.

This script takes a CSV file with test inputs and expected results,
tests them against a guardrail, and generates passed/failed JSON files
compatible with the optimization framework.

Usage:
    python generate_test_results.py <csv_file> [options]

Options:
    -g, --guardrail-id ID    Existing guardrail ID to test against
    -r, --region REGION      AWS region (default: us-east-1)
    -o, --output-dir DIR     Output directory (default: parent directory)
    --deploy-baseline        Deploy baseline guardrail if no ID provided

CSV Format:
    input,expected
    "What is the CPU usage?",pass
    "Write me a poem",reject

Examples:
    # Test against existing guardrail
    python generate_test_results.py inputs.csv -g abc123xyz

    # Deploy baseline and test
    python generate_test_results.py inputs.csv --deploy-baseline

    # Specify output directory
    python generate_test_results.py inputs.csv -g abc123xyz -o ../test_data
"""

import sys
import os
import csv
import json
import argparse
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluator import GuardrailEvaluator, TestCase
from guardrail_manager import GuardrailManager
from guardrail_config import get_baseline_config


def load_csv_inputs(filepath: str) -> list[TestCase]:
    """
    Load test inputs from CSV file.
    
    Expected CSV format:
        input,expected
        "query text",pass
        "another query",reject
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        List of TestCase objects
    """
    test_cases = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Validate headers
        if 'input' not in reader.fieldnames:
            raise ValueError("CSV must have 'input' column")
        
        for row in reader:
            input_text = row['input'].strip()
            # Default to 'pass' if expected column missing
            expected = row.get('expected', 'pass').strip().lower()
            
            if expected not in ('pass', 'reject'):
                print(f"Warning: Invalid expected value '{expected}' for input '{input_text[:50]}...', defaulting to 'pass'")
                expected = 'pass'
            
            test_cases.append(TestCase(input=input_text, expected=expected))
    
    return test_cases


def generate_result_files(
    test_cases: list[TestCase],
    guardrail_id: str,
    region: str = "us-east-1",
    output_dir: str = ".",
    version: str = "DRAFT"
) -> tuple[str, str]:
    """
    Test inputs against guardrail and generate passed/failed JSON files.
    
    Args:
        test_cases: List of test cases to evaluate
        guardrail_id: Guardrail ID to test against
        region: AWS region
        output_dir: Directory for output files
        version: Guardrail version
        
    Returns:
        Tuple of (passed_file_path, failed_file_path)
    """
    evaluator = GuardrailEvaluator(region=region)
    
    # Evaluate all test cases
    print(f"Evaluating {len(test_cases)} test cases against guardrail {guardrail_id}...")
    report = evaluator.evaluate_all(guardrail_id, test_cases, version=version)
    
    # Separate passed and failed results
    passed_results = []
    failed_results = []
    
    # Track statistics for summaries
    passed_policy_violations: dict[str, int] = {}
    passed_filter_violations: dict[str, int] = {}
    failed_false_negatives = 0
    failed_false_positives = 0
    
    for result in report.results:
        entry = {
            "result": "PASSED" if result.passed else "FAILED",
            "input": result.input,
            "expected": result.expected,
            "actual": result.actual,
            "violated_content_filters": result.violated_filters,
            "violated_policies": result.violated_policies
        }
        
        if result.passed:
            passed_results.append(entry)
            # Track violations for passed cases
            for policy in result.violated_policies:
                passed_policy_violations[policy] = passed_policy_violations.get(policy, 0) + 1
            for filter_type in result.violated_filters:
                passed_filter_violations[filter_type] = passed_filter_violations.get(filter_type, 0) + 1
        else:
            failed_results.append(entry)
            if result.expected == "pass" and result.actual == "reject":
                failed_false_positives += 1
            elif result.expected == "reject" and result.actual == "pass":
                failed_false_negatives += 1
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create passed JSON file with summary
    passed_summary = {
        "total": len(passed_results),
        "violated_policies": passed_policy_violations,
        "violated_content_filters": passed_filter_violations
    }
    passed_output = [passed_summary] + passed_results
    passed_filepath = os.path.join(output_dir, f"passed_guardrail_results_{timestamp}.json")
    
    with open(passed_filepath, 'w', encoding='utf-8') as f:
        json.dump(passed_output, f, indent=2)
    
    # Create failed JSON file with summary
    failed_summary = {
        "total": f"{len(failed_results)} / {len(passed_results)} (failed / passed)",
        "false_negatives": f"{failed_false_negatives} (expected to be rejected but passed)",
        "false_positives": f"{failed_false_positives} (expected to pass but rejected)"
    }
    failed_output = [failed_summary] + failed_results
    failed_filepath = os.path.join(output_dir, f"failed_guardrail_results_{timestamp}.json")
    
    with open(failed_filepath, 'w', encoding='utf-8') as f:
        json.dump(failed_output, f, indent=2)
    
    return passed_filepath, failed_filepath


def deploy_baseline_guardrail(region: str = "us-east-1") -> str:
    """
    Deploy baseline guardrail configuration.
    
    Args:
        region: AWS region
        
    Returns:
        Guardrail ID
    """
    manager = GuardrailManager(region=region)
    config = get_baseline_config()
    
    print("Deploying baseline guardrail...")
    guardrail_id, version = manager.create_guardrail(config)
    print(f"Deployed guardrail: {guardrail_id} (version: {version})")
    
    return guardrail_id


def main():
    parser = argparse.ArgumentParser(
        description="Generate test result JSON files from CSV inputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CSV Format:
    input,expected
    "What is the CPU usage?",pass
    "Write me a poem",reject

Examples:
    python generate_test_results.py inputs.csv -g abc123xyz
    python generate_test_results.py inputs.csv --deploy-baseline
        """
    )
    parser.add_argument("csv_file", help="CSV file with test inputs")
    parser.add_argument("-g", "--guardrail-id", help="Existing guardrail ID to test against")
    parser.add_argument("-r", "--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("-o", "--output-dir", help="Output directory (default: parent of src/)")
    parser.add_argument("--deploy-baseline", action="store_true",
                        help="Deploy baseline guardrail if no ID provided")
    
    args = parser.parse_args()
    
    # Validate CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"Error: CSV file not found: {args.csv_file}")
        sys.exit(1)
    
    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        # Default to parent directory (where original JSON files are)
        output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load test cases from CSV
    print(f"Loading test cases from {args.csv_file}...")
    test_cases = load_csv_inputs(args.csv_file)
    print(f"Loaded {len(test_cases)} test cases")
    
    # Get or deploy guardrail
    guardrail_id = args.guardrail_id
    if not guardrail_id:
        if args.deploy_baseline:
            guardrail_id = deploy_baseline_guardrail(args.region)
        else:
            print("Error: Must provide --guardrail-id or --deploy-baseline")
            sys.exit(1)
    
    # Generate result files
    passed_file, failed_file = generate_result_files(
        test_cases=test_cases,
        guardrail_id=guardrail_id,
        region=args.region,
        output_dir=output_dir
    )
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Passed results: {passed_file}")
    print(f"Failed results: {failed_file}")
    print("\nUse these files with run_optimization.py:")
    print(f"  python run_optimization.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
