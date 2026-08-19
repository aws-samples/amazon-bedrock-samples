#!/usr/bin/env python3
"""
Standalone evaluation script for testing guardrail configurations.
Usage: python run_evaluation.py <guardrail_id> [region]
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluator import run_evaluation


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_evaluation.py <guardrail_id> [region]")
        print("\nExample:")
        print("  python run_evaluation.py abc123def456 us-east-1")
        sys.exit(1)
    
    guardrail_id = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "us-east-1"
    
    # Paths to test files (relative to workspace root)
    passed_file = "../passed_guardrail_results.json"
    failed_file = "../failed_guardrail_results.json"
    
    # Check if files exist, try alternate paths
    if not os.path.exists(passed_file):
        passed_file = "passed_guardrail_results.json"
        failed_file = "failed_guardrail_results.json"
    
    print(f"Evaluating guardrail: {guardrail_id}")
    print(f"Region: {region}")
    print(f"Test files: {passed_file}, {failed_file}")
    print("-" * 60)
    
    report = run_evaluation(
        guardrail_id=guardrail_id,
        passed_tests_file=passed_file,
        failed_tests_file=failed_file,
        region=region
    )
    
    print(f"\nFinal Accuracy: {report.accuracy:.2%}")
    print(f"Report saved to: evaluation_report.json")


if __name__ == "__main__":
    main()
