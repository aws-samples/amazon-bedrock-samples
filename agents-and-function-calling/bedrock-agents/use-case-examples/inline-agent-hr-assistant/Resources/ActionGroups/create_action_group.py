import logging
import boto3
import time
import zipfile
from io import BytesIO
import json
import os
from typing import Dict

# Configure logging
logging.basicConfig(
    format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def generate_timestamp_suffix() -> str:
    """Generate a short timestamp-based suffix for resource names."""
    return time.strftime("%m%d%H%M", time.localtime())

def create_assume_role_policy() -> Dict:
    """Create the assume role policy document."""
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            },
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

def create_iam_role(iam_client, role_name: str) -> Dict:
    """Create IAM role for Lambda function."""
    try:
        # Keep role name short but unique
        timestamp = generate_timestamp_suffix()
        role_name = f"ia-role-{timestamp}"
        
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(create_assume_role_policy())
        )
        
        # Wait for role to be created
        time.sleep(10)
        
        # Attach basic execution role policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        return role
    except Exception as e:
        logger.error(f"Error creating IAM role: {str(e)}")
        raise

def create_zip_package(lambda_code_path: str) -> bytes:
    """Create zip package from Lambda function code."""
    try:
        s = BytesIO()
        with zipfile.ZipFile(s, 'w') as z:
            z.write(lambda_code_path, "lambda_function.py")
        return s.getvalue()
    except Exception as e:
        logger.error(f"Error creating zip package: {str(e)}")
        raise

def save_lambda_functions_info(lambda_functions: Dict, output_file: str = "lambda_functions_info.json") -> None:
    """Save Lambda functions information to a JSON file."""
    try:
        # Create a formatted dictionary with full response and quick access fields
        formatted_info = {}
        for key, value in lambda_functions.items():
            formatted_info[key] = {
                'name': value['full_response']['FunctionName'],
                'arn': value['full_response']['FunctionArn'],
                'full_response': value['full_response']
            }

        with open(output_file, 'w') as f:
            json.dump(formatted_info, f, indent=2, default=str)
        logger.info(f"Successfully saved Lambda functions information to {output_file}")
    except Exception as e:
        logger.error(f"Error saving Lambda functions information: {str(e)}")
        raise

def create_all_lambda_functions(region: str, account_id: str, output_file: str = "lambda_functions_info.json") -> Dict:
    """Create all Lambda functions and save their information to a file."""
    
    timestamp = generate_timestamp_suffix()
    
    # Initialize AWS clients
    iam_client = boto3.client('iam', region_name=region)
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Create a single IAM role to be used by all Lambda functions
    role = create_iam_role(iam_client, f"ia-role-{timestamp}")
    role_arn = role['Role']['Arn']
    
    # Get the correct base path for lambda functions
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Script directory: {script_dir}")
    
    # Define your action groups and their corresponding paths with shorter names
    action_groups = {
        "compensation": {
            "name": f"comp-func-{timestamp}",
            "path": os.path.join(script_dir, "compensation", "lambda_function.py"),
            "description": "Used for submitting employee pay change raise request to HR team."
        },
        "vacation": {
            "name": f"pto-func-{timestamp}",
            "path": os.path.join(script_dir, "vacation", "lambda_function.py"),
            "description": "Manage vacation requests and check balance"
        },
        "budget": {
            "name": f"budget-func-{timestamp}",
            "path": os.path.join(script_dir, "budget", "lambda_function.py"),
            "description": "Process bills for approval."
        }
    }
    
    # Log all paths for debugging
    for key, config in action_groups.items():
        logger.info(f"Path for {key}: {config['path']}")
    
    # Create Lambda functions and store their ARNs
    lambda_functions = {}
    
    for key, config in action_groups.items():
        try:
            lambda_name = config["name"]
            
            # Verify file exists before attempting to create zip
            if not os.path.exists(config["path"]):
                logger.error(f"Lambda function file not found: {config['path']}")
                continue
                
            # Create zip package
            zip_content = create_zip_package(config["path"])
            
            # Create Lambda function
            lambda_function = lambda_client.create_function(
                FunctionName=lambda_name,
                Runtime='python3.12',
                Timeout=180,
                Role=role_arn,
                Code={'ZipFile': zip_content},
                Handler='lambda_function.lambda_handler'
            )
            
            # Add Bedrock permission
            lambda_client.add_permission(
                FunctionName=lambda_name,
                StatementId=f'bedrock-{timestamp}',
                Action='lambda:InvokeFunction',
                Principal='bedrock.amazonaws.com',
                SourceArn=f"arn:aws:bedrock:{region}:{account_id}:agent/*",
            )
            
            lambda_functions[key] = {'full_response': lambda_function}
            logger.info(f"Successfully created Lambda function: {lambda_name}")
            
        except Exception as e:
            logger.error(f"Failed to create Lambda function for {config['name']}: {str(e)}")
    
    return lambda_functions