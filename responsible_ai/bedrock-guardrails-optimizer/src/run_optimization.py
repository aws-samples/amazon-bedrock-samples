#!/usr/bin/env python3
"""
Run the guardrail optimization agent.

Usage:
    python run_optimization.py [options]

Options:
    -n, --max-iterations N    Maximum iterations (default: 5)
    -r, --region REGION       AWS region (default: us-east-1)
    -b, --start-from-baseline Start from baseline config instead of best previous
    -m, --metrics METRICS     Target metrics: accuracy, latency, generalization, all (default: accuracy)
    -p, --passed-file FILE    Path to passed test cases JSON (default: passed_guardrail_results.json)
    -f, --failed-file FILE    Path to failed test cases JSON (default: failed_guardrail_results.json)

Examples:
    python run_optimization.py -n 10 -m accuracy latency
    python run_optimization.py --start-from-baseline --metrics all
    python run_optimization.py -p custom_passed.json -f custom_failed.json
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimization_agent import run_optimization


def main():
    parser = argparse.ArgumentParser(
        description="Run guardrail optimization agent",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-n", "--max-iterations", type=int, default=5,
                        help="Maximum optimization iterations (default: 5)")
    parser.add_argument("-r", "--region", default="us-east-1",
                        help="AWS region (default: us-east-1)")
    parser.add_argument("-b", "--start-from-baseline", action="store_true",
                        help="Start from baseline config instead of best previous")
    parser.add_argument("-m", "--metrics", nargs="+",
                        choices=["accuracy", "latency", "generalization", "all"],
                        default=["accuracy"],
                        help="Target metrics to optimize (default: accuracy)")
    parser.add_argument("-p", "--passed-file", default="passed_guardrail_results.json",
                        help="Path to passed test cases JSON (default: passed_guardrail_results.json)")
    parser.add_argument("-f", "--failed-file", default="failed_guardrail_results.json",
                        help="Path to failed test cases JSON (default: failed_guardrail_results.json)")
    
    args = parser.parse_args()
    
    start_from = "baseline" if args.start_from_baseline else "best previous"
    
    print("=" * 60)
    print("GUARDRAIL OPTIMIZATION AGENT")
    print("=" * 60)
    print(f"Max Iterations: {args.max_iterations}")
    print(f"Region: {args.region}")
    print(f"Start From: {start_from} configuration")
    print(f"Target Metrics: {', '.join(args.metrics)}")
    print(f"Passed File: {args.passed_file}")
    print(f"Failed File: {args.failed_file}")
    print(f"Model: global.anthropic.claude-opus-4-5-20251101-v1:0")
    print("=" * 60)
    
    # Change to parent directory for test file access
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    run_optimization(
        max_iterations=args.max_iterations,
        region=args.region,
        start_from_best=not args.start_from_baseline,
        target_metrics=args.metrics,
        passed_file=args.passed_file,
        failed_file=args.failed_file
    )


if __name__ == "__main__":
    main()
