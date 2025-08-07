#!/usr/bin/env python3
"""
Configuration file validator for 360-eval

Validates model profiles and judge profiles JSONL files to catch common errors
before they cause runtime failures.
"""

import json
import os
import sys
import re
from typing import Dict, List, Optional, Tuple


def validate_model_profile(profile: Dict, line_num: int) -> List[str]:
    """Validate a single model profile entry"""
    errors = []
    
    # Required fields
    required_fields = ["model_id", "region", "input_token_cost", "output_token_cost"]
    for field in required_fields:
        if field not in profile:
            errors.append(f"Line {line_num}: Missing required field '{field}'")
    
    # Validate model_id format
    if "model_id" in profile:
        model_id = profile["model_id"]
        if not isinstance(model_id, str) or not model_id.strip():
            errors.append(f"Line {line_num}: model_id must be a non-empty string")
        elif not re.match(r'^(bedrock/|openai/|anthropic/|gemini/|azure/)', model_id):
            errors.append(f"Line {line_num}: model_id '{model_id}' should start with a provider prefix (bedrock/, openai/, etc.)")
    
    # Validate region
    if "region" in profile:
        region = profile["region"]
        if not isinstance(region, str) or not region.strip():
            errors.append(f"Line {line_num}: region must be a non-empty string")
        elif not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            errors.append(f"Line {line_num}: region '{region}' doesn't match AWS region format (e.g., 'us-east-1')")
    
    # Validate costs
    for cost_field in ["input_token_cost", "output_token_cost"]:
        if cost_field in profile:
            cost = profile[cost_field]
            if not isinstance(cost, (int, float)) or cost < 0:
                errors.append(f"Line {line_num}: {cost_field} must be a non-negative number")
            elif cost > 1.0:
                errors.append(f"Line {line_num}: Warning: {cost_field} ({cost}) seems unusually high (>$1 per 1K tokens)")
    
    return errors


def validate_judge_profile(profile: Dict, line_num: int) -> List[str]:
    """Validate a single judge profile entry"""
    errors = []
    
    # Required fields
    required_fields = ["model_id", "region", "input_cost_per_1k", "output_cost_per_1k"]
    for field in required_fields:
        if field not in profile:
            errors.append(f"Line {line_num}: Missing required field '{field}'")
    
    # Validate model_id format
    if "model_id" in profile:
        model_id = profile["model_id"]
        if not isinstance(model_id, str) or not model_id.strip():
            errors.append(f"Line {line_num}: model_id must be a non-empty string")
        elif not re.match(r'^(bedrock/|openai/|anthropic/|gemini/|azure/)', model_id):
            errors.append(f"Line {line_num}: model_id '{model_id}' should start with a provider prefix (bedrock/, openai/, etc.)")
    
    # Validate region
    if "region" in profile:
        region = profile["region"]
        if not isinstance(region, str) or not region.strip():
            errors.append(f"Line {line_num}: region must be a non-empty string")
        elif not re.match(r'^[a-z]{2}-[a-z]+-\d+$', region):
            errors.append(f"Line {line_num}: region '{region}' doesn't match AWS region format (e.g., 'us-east-1')")
    
    # Validate costs
    for cost_field in ["input_cost_per_1k", "output_cost_per_1k"]:
        if cost_field in profile:
            cost = profile[cost_field]
            if not isinstance(cost, (int, float)) or cost < 0:
                errors.append(f"Line {line_num}: {cost_field} must be a non-negative number")
            elif cost > 1.0:
                errors.append(f"Line {line_num}: Warning: {cost_field} ({cost}) seems unusually high (>$1 per 1K tokens)")
    
    return errors


def validate_jsonl_file(file_path: str, profile_type: str) -> Tuple[List[str], List[str]]:
    """
    Validate a JSONL configuration file
    
    Args:
        file_path: Path to the JSONL file
        profile_type: Either 'model' or 'judge'
    
    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []
    
    if not os.path.exists(file_path):
        errors.append(f"File not found: {file_path}")
        return errors, warnings
    
    if not os.path.isfile(file_path):
        errors.append(f"Path is not a file: {file_path}")
        return errors, warnings
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        errors.append(f"Failed to read file {file_path}: {e}")
        return errors, warnings
    
    if not lines:
        errors.append(f"File is empty: {file_path}")
        return errors, warnings
    
    model_ids_seen = set()
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            warnings.append(f"Line {line_num}: Empty line (will be skipped)")
            continue
        
        try:
            profile = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {line_num}: Invalid JSON - {e}")
            continue
        
        if not isinstance(profile, dict):
            errors.append(f"Line {line_num}: Expected JSON object, got {type(profile).__name__}")
            continue
        
        # Check for duplicate model_ids
        if "model_id" in profile:
            model_id = profile["model_id"]
            if model_id in model_ids_seen:
                errors.append(f"Line {line_num}: Duplicate model_id '{model_id}'")
            else:
                model_ids_seen.add(model_id)
        
        # Validate based on profile type
        if profile_type == "model":
            profile_errors = validate_model_profile(profile, line_num)
        elif profile_type == "judge":
            profile_errors = validate_judge_profile(profile, line_num)
        else:
            errors.append(f"Invalid profile_type: {profile_type}")
            continue
        
        errors.extend(profile_errors)
    
    return errors, warnings


def validate_config_directory(config_dir: str) -> bool:
    """
    Validate all configuration files in the given directory
    
    Args:
        config_dir: Path to the configuration directory
    
    Returns:
        True if all files are valid, False otherwise
    """
    if not os.path.exists(config_dir):
        print(f"❌ Configuration directory not found: {config_dir}")
        return False
    
    model_profiles_path = os.path.join(config_dir, "models_profiles.jsonl")
    judge_profiles_path = os.path.join(config_dir, "judge_profiles.jsonl")
    
    all_valid = True
    
    # Validate model profiles
    print("🔍 Validating model profiles...")
    model_errors, model_warnings = validate_jsonl_file(model_profiles_path, "model")
    
    if model_errors:
        print(f"❌ Model profiles validation failed:")
        for error in model_errors:
            print(f"   {error}")
        all_valid = False
    else:
        print("✅ Model profiles are valid")
    
    if model_warnings:
        print("⚠️  Model profiles warnings:")
        for warning in model_warnings:
            print(f"   {warning}")
    
    # Validate judge profiles
    print("\n🔍 Validating judge profiles...")
    judge_errors, judge_warnings = validate_jsonl_file(judge_profiles_path, "judge")
    
    if judge_errors:
        print(f"❌ Judge profiles validation failed:")
        for error in judge_errors:
            print(f"   {error}")
        all_valid = False
    else:
        print("✅ Judge profiles are valid")
    
    if judge_warnings:
        print("⚠️  Judge profiles warnings:")
        for warning in judge_warnings:
            print(f"   {warning}")
    
    return all_valid


def main():
    """Main CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: python config_validator.py <config_directory>")
        print("Example: python config_validator.py default-config/")
        sys.exit(1)
    
    config_dir = sys.argv[1]
    
    print("🔧 360-Eval Configuration Validator")
    print("=" * 40)
    
    is_valid = validate_config_directory(config_dir)
    
    print("\n" + "=" * 40)
    if is_valid:
        print("✅ All configuration files are valid!")
        sys.exit(0)
    else:
        print("❌ Configuration validation failed. Please fix the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()