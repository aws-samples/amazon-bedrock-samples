#!/usr/bin/env python3
"""
Complete AWS Bedrock Model Discovery Script

This script discovers all Bedrock models available and accessible to your account
across all regions, including cross-region inference profile models.

Returns a clean JSONL file with:
- Regular foundation models
- Cross-region inference profile models (with us./eu./apac. prefixes)
- Only models you have access to
- Simple format: {"model_id": "bedrock/...", "region": "...", "input_token_cost": 0, "output_token_cost": 0}
"""

import boto3
import json
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError, NoCredentialsError


def check_aws_credentials() -> bool:
    """Check if AWS credentials are configured and working"""
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if not credentials:
            print("❌ AWS credentials not configured")
            print("   Please configure with: aws configure")
            return False
            
        # Test credentials
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS credentials valid (Account: {identity['Account'][:4]}***)")
        return True
        
    except NoCredentialsError:
        print("❌ No AWS credentials found")
        print("   Please configure with: aws configure")
        return False
    except Exception as e:
        print(f"❌ Error checking credentials: {e}")
        return False


def get_all_aws_regions() -> List[str]:
    """Get all AWS regions dynamically"""
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        return [region['RegionName'] for region in response['Regions']]
    except Exception as e:
        print(f"❌ Error fetching regions: {e}")
        # Fallback to known regions if API fails
        return [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1', 'eu-north-1',
            'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
            'ap-southeast-1', 'ap-southeast-2', 'ap-south-1',
            'ca-central-1', 'sa-east-1'
        ]


def check_model_access(bedrock_runtime, model_id: str) -> str:
    """Check if we have access to invoke a specific model"""
    try:
        # Try a minimal invocation to check access
        test_prompt = "Hi"
        messages = [
            {
                "role": "user",
                "content": [{"text": test_prompt}]
            }
        ]
        # Make a minimal request
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": 10,
                "temperature": 0.7
            }
        )
        
        # If we get a response without error, access is granted
        return 'granted'
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', '')
        
        if error_code == 'AccessDeniedException':
            return 'denied'
        elif error_code == 'ValidationException':
            return 'denied'
        elif error_code == 'ThrottlingException':
            # Throttling means we have access but hit rate limits
            return 'granted'
        else:
            return 'denied'
    except Exception:
        return 'denied'


def get_inference_profile_models(region: str) -> List[Dict]:
    """Get cross-region inference profile models (system-defined only)"""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        
        # Get system-defined profiles (cross-region)
        system_response = bedrock.list_inference_profiles(typeEquals='SYSTEM_DEFINED')
        
        profile_models = []
        
        # Process system-defined profiles only
        for profile in system_response.get('inferenceProfileSummaries', []):
            profile_id = profile.get('inferenceProfileId', '')
            profile_name = profile.get('inferenceProfileName', '')
            
            # Create a model entry for the profile
            profile_model = {
                'modelId': profile_id,
                'modelName': profile_name,
                'provider': 'AWS_BEDROCK_PROFILE',
                'isInferenceProfile': True,
                'profileType': 'SYSTEM_DEFINED'
            }
            profile_models.append(profile_model)
        
        return profile_models
    
    except Exception:
        # If inference profiles aren't available, return empty list
        return []


def check_bedrock_in_region(region: str) -> Tuple[str, Optional[Dict]]:
    """Check Bedrock models in a specific region"""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        
        # Get foundation models
        response = bedrock.list_foundation_models(byOutputModality='TEXT')
        models = response.get('modelSummaries', [])
        
        # Extract active models
        model_info = []
        for model in models:
            if model.get('modelLifecycle', {}).get('status') == 'ACTIVE':
                model_id = model.get('modelId')
                
                # Check access to this model
                access_status = check_model_access(bedrock_runtime, model_id)
                
                if access_status == 'granted':
                    model_data = {
                        'modelId': model_id,
                        'modelName': model.get('modelName'),
                        'provider': model.get('providerName'),
                        'isInferenceProfile': False,
                        'accessGranted': True
                    }
                    model_info.append(model_data)
        
        # Add cross-region inference profile models
        profile_models = get_inference_profile_models(region)
        
        # Check access to profile models
        for profile in profile_models:
            profile_id = profile['modelId']
            access_status = check_model_access(bedrock_runtime, profile_id)
            
            if access_status == 'granted':
                profile['accessGranted'] = True
                model_info.append(profile)
        
        return (region, {
            'available': True,
            'model_count': len(model_info),
            'models': model_info
        })
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        
        if error_code in ['UnknownEndpoint', 'ServiceUnavailable', 'EndpointConnectionError']:
            return (region, {
                'available': False,
                'model_count': 0,
                'models': [],
                'reason': 'Service not available in region'
            })
        elif error_code == 'AccessDeniedException':
            return (region, {
                'available': 'unknown',
                'model_count': 0,
                'models': [],
                'reason': 'Access denied - check permissions'
            })
        else:
            return (region, {
                'available': 'error',
                'model_count': 0,
                'models': [],
                'reason': f'Error: {error_code}'
            })
    except Exception as e:
        return (region, {
            'available': 'error',
            'model_count': 0,
            'models': [],
            'reason': f'Unexpected error: {str(e)[:100]}'
        })


def discover_all_models(output_file: str = "default-config/models_profiles.jsonl") -> Dict:
    """Discover all accessible Bedrock models across all regions"""
    
    print("🔍 AWS Bedrock Complete Model Discovery")
    print("=" * 60)
    
    # Check credentials
    print("\n🔐 Checking AWS credentials...")
    if not check_aws_credentials():
        return {"error": "AWS credentials not configured"}
    
    # Get all regions
    print("\n🌍 Fetching all AWS regions...")
    regions = get_all_aws_regions()
    print(f"   Found {len(regions)} regions")
    
    # Check all regions in parallel
    print(f"\n🔄 Checking Bedrock models across {len(regions)} regions...")
    print("   ✓ Testing actual model access (this may take a few minutes)")
    print("   ✓ Including cross-region inference profiles")
    
    results = {}
    total_accessible_models = 0
    
    # Use ThreadPoolExecutor for parallel checking
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_region = {
            executor.submit(check_bedrock_in_region, region): region 
            for region in regions
        }
        
        # Process completed tasks
        completed = 0
        for future in as_completed(future_to_region):
            completed += 1
            region, result = future.result()
            results[region] = result
            
            # Show progress
            progress = completed / len(regions) * 100
            if result and result.get('available') == True:
                model_count = result.get('model_count', 0)
                total_accessible_models += model_count
                status = f"✅ {model_count} models"
            else:
                status = "❌ no access"
            
            print(f"   {status:<15} {region:<20} [{completed}/{len(regions)}] {progress:.0f}%")
    
    # Generate JSONL output
    print(f"\n💾 Generating JSONL output...")
    models_data = []
    
    for region, region_data in results.items():
        if region_data.get('available') and region_data.get('models'):
            for model in region_data['models']:
                model_id = model['modelId']
                
                # Create simplified entry
                entry = {
                    "model_id": f"bedrock/{model_id}",
                    "region": region,
                    "input_token_cost": 0.0,
                    "output_token_cost": 0.0
                }
                
                models_data.append(entry)
    
    # Sort by region and model_id
    models_data.sort(key=lambda x: (x['region'], x['model_id']))
    
    # Write to JSONL file
    try:
        with open(output_file, 'w') as f:
            for entry in models_data:
                f.write(json.dumps(entry) + '\n')
        
        print(f"   ✅ Generated {output_file}")
    except Exception as e:
        print(f"   ❌ Error writing file: {e}")
        return {"error": f"Could not write file: {e}"}
    
    # Summary
    available_regions = sum(1 for r in results.values() if r.get('available') == True)
    regular_models = len([m for m in models_data if not m['model_id'].startswith('bedrock/us.') and not m['model_id'].startswith('bedrock/eu.') and not m['model_id'].startswith('bedrock/apac.')])
    cross_region_models = len(models_data) - regular_models
    
    print(f"\n" + "=" * 60)
    print("📈 DISCOVERY COMPLETE")
    print("=" * 60)
    print(f"✅ Total accessible models: {len(models_data)}")
    print(f"   • Regular foundation models: {regular_models}")
    print(f"   • Cross-region inference profiles: {cross_region_models}")
    print(f"🌍 Regions with Bedrock access: {available_regions}/{len(regions)}")
    print(f"📄 Output file: {output_file}")
    
    # Show sample cross-region models
    cross_region_samples = [m for m in models_data if any(m['model_id'].startswith(f'bedrock/{prefix}') for prefix in ['us.', 'eu.', 'apac.'])]
    if cross_region_samples:
        print(f"\n🌐 Sample cross-region models:")
        for model in cross_region_samples[:5]:
            print(f"   • {model['model_id']} (region: {model['region']})")
    
    return {
        "success": True,
        "total_models": len(models_data),
        "regular_models": regular_models,
        "cross_region_models": cross_region_models,
        "accessible_regions": available_regions,
        "total_regions": len(regions),
        "output_file": output_file
    }


def main():
    """Main function"""
    result = discover_all_models()
    
    if result.get("error"):
        print(f"\n❌ Discovery failed: {result['error']}")
        return 1
    else:
        print(f"\n🎉 Success! All accessible Bedrock models discovered.")
        return 0


if __name__ == "__main__":
    main()