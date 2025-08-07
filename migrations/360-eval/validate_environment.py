#!/usr/bin/env python3
"""
Environment validation script for 360-eval

Checks that all required dependencies and environment variables are properly configured
before running evaluations.
"""

import os
import sys
import boto3
from typing import List, Tuple


def check_aws_credentials() -> Tuple[bool, str]:
    """Check AWS credentials and Bedrock access"""
    try:
        # Check if AWS credentials are configured
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if not credentials:
            return False, "❌ AWS credentials not configured"
        
        # Test basic AWS access
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        
        # Test Bedrock access
        bedrock_client = boto3.client('bedrock', region_name='us-east-1')
        try:
            bedrock_client.list_foundation_models()
            bedrock_status = "✅ Bedrock access confirmed"
        except Exception as e:
            bedrock_status = f"⚠️  Bedrock access issue: {str(e)[:100]}"
        
        return True, f"✅ AWS credentials valid (Account: {identity['Account'][:4]}***)\n   {bedrock_status}"
        
    except Exception as e:
        return False, f"❌ AWS credentials error: {str(e)[:100]}"


def check_file_structure() -> Tuple[bool, List[str]]:
    """Check if required files and directories exist"""
    results = []
    all_exist = True
    
    required_files = [
        'src/benchmarks_run.py',
        'src/utils.py',
        'src/streamlit_dashboard.py',
        'default-config/models_profiles.jsonl',
        'default-config/judge_profiles.jsonl',
        'requirements.txt'
    ]
    
    required_dirs = [
        'src/',
        'benchmark-results/',
        'logs/',
        'default-config/'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            results.append(f"✅ {file_path}")
        else:
            results.append(f"❌ {file_path} - Missing")
            all_exist = False
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            results.append(f"✅ {dir_path}")
        else:
            results.append(f"❌ {dir_path} - Missing")
            all_exist = False
    
    return all_exist, results


def run_config_validation() -> Tuple[bool, List[str]]:
    """Run configuration file validation"""
    try:
        # Import and run config validator
        sys.path.insert(0, 'src')
        from config_validator import validate_config_directory
        
        # Capture output by redirecting stdout
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            is_valid = validate_config_directory('default-config')
        
        output = f.getvalue()
        results = output.split('\n') if output else []
        
        return is_valid, [line for line in results if line.strip()]
        
    except Exception as e:
        return False, [f"❌ Config validation failed: {str(e)}"]


def main():
    """Main validation function"""
    print("🔧 360-Eval Environment Validation")
    print("=" * 50)
    
    overall_status = True
    
    # Check AWS credentials
    print("\n🔐 AWS Credentials")
    aws_ok, aws_msg = check_aws_credentials()
    print(f"   {aws_msg}")
    if not aws_ok:
        overall_status = False
    
    # Check file structure
    print("\n📁 File Structure")
    file_ok, file_results = check_file_structure()
    for result in file_results:
        print(f"   {result}")
    if not file_ok:
        overall_status = False
    
    # Check configuration files
    print("\n⚙️  Configuration Files")
    config_ok, config_results = run_config_validation()
    for result in config_results:
        if result.strip():
            print(f"   {result}")
    if not config_ok:
        overall_status = False
    
    # Final status
    print("\n" + "=" * 50)
    if overall_status:
        print("✅ Environment validation PASSED!")
        print("🚀 You're ready to run 360-eval!")
        print("\nNext steps:")
        print("   • Run the dashboard: ./run_dashboard.sh")
        print("   • Or CLI: python src/benchmarks_run.py <input_file>")
    else:
        print("❌ Environment validation FAILED!")
        print("🔧 Please fix the issues above before running 360-eval")
        print("\nCommon fixes:")
        print("   • Configure AWS: aws configure")
        print("   • Check file paths and permissions")
        print("   • Fix configuration file errors")
    
    print("=" * 50)
    return overall_status


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)