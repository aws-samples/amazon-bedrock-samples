#!/usr/bin/env python3
"""
Deploy the baseline guardrail configuration.
Usage: python deploy_baseline.py [region]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from guardrail_config import get_baseline_config, save_config
from guardrail_manager import deploy_guardrail


def main():
    region = sys.argv[1] if len(sys.argv) > 1 else "us-east-1"
    
    print("Deploying baseline guardrail configuration...")
    print(f"Region: {region}")
    print("-" * 60)
    
    # Get baseline config
    config = get_baseline_config()
    
    # Save config for reference
    save_config(config, "baseline_config.json")
    print("Saved baseline config to: baseline_config.json")
    
    # Deploy to Bedrock
    guardrail_id = deploy_guardrail(config, region=region)
    
    print("-" * 60)
    print(f"Guardrail deployed successfully!")
    print(f"Guardrail ID: {guardrail_id}")
    print(f"\nTo evaluate, run:")
    print(f"  python run_evaluation.py {guardrail_id} {region}")


if __name__ == "__main__":
    main()
