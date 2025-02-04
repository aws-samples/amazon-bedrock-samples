import subprocess
from pathlib import Path
import boto3

def run_create_resources(account_id, region):
    resources_script = Path(__file__).parent / 'Resources' / 'create-resources.py'
    result = subprocess.run(
        ['python', str(resources_script), '--account-id', account_id, '--region', region],
        capture_output=True, 
        text=True
    )
    
    if result.returncode == 0:
        print("Successfully created resources!")
    else:
        print("Error:", result.stderr)

def get_aws_region():
    session = boto3.session.Session()
    return session.region_name or 'us-west-2'

def get_aws_account_id():
    sts = boto3.client('sts')
    try:
        return sts.get_caller_identity()['Account']
    except Exception as e:
        print(f"Error getting AWS account ID: {e}")
        return None

if __name__ == "__main__":
    # Specify your AWS account ID here
    # AWS_ACCOUNT_ID = "767397817418"  # Replace with your account ID
    # REGION = "us-west-2"  # Replace with your account ID

    AWS_ACCOUNT_ID = get_aws_account_id()
    REGION = get_aws_region()

    print("Installing requirements...")
    requirements_file = Path(__file__).parent / 'requirements.txt'
    if requirements_file.exists():
        subprocess.run(['pip', 'install', '-r', str(requirements_file)])
    else:
        print("No requirements.txt found!")

    print('Creating resources. This may take 5-10 minutes')
    run_create_resources(AWS_ACCOUNT_ID, REGION)