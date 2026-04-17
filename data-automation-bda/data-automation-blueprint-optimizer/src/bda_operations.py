from typing import Dict, Optional
import os
import json
from dotenv import load_dotenv
from src.aws_clients import AWSClients

# Load environment variables
load_dotenv()


class BDAOperations:
    """Class to handle Bedrock Data Automation operations"""

    def __init__(self, project_arn: str, blueprint_arn: str, blueprint_ver: str, blueprint_stage: str, input_bucket: str,
                 output_bucket: str, profile_arn: str = None):
        """
        Initialize with AWS clients and project configuration

        Args:
            project_arn (str): ARN of the project
            blueprint_arn (str): ARN of the blueprint
            blueprint_ver (str): Version of the blueprint
            blueprint_stage (str): Stage of the blueprint
            input_bucket (str): S3 bucket/path for input
            output_bucket (str): S3 bucket/path for output
            profile_arn (str, optional): ARN of the data automation profile
        """
        # Get AWS clients
        aws = AWSClients()
        self.bda_runtime_client = aws.bda_runtime_client
        self.bda_client = aws.bda_client

        # Store configuration
        self.project_arn = project_arn
        self.blueprint_arn = blueprint_arn
        self.blueprint_ver = blueprint_ver
        self.blueprint_stage = blueprint_stage
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self.region_name = aws.region
        self.profile_arn = profile_arn

        # Validate inputs
        self._validate_config()

    def _validate_config(self):
        """Validate required configuration"""
        required_fields = {
            'project_arn': self.project_arn,
            'blueprint_arn': self.blueprint_arn,
            'blueprint_ver': self.blueprint_ver,
            'blueprint_stage': self.blueprint_stage,
            'input_bucket': self.input_bucket,
            'output_bucket': self.output_bucket,
        }

        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}")

    def invoke_data_automation(self) -> Optional[Dict]:
        """
        Invoke an asynchronous data automation job.

        Returns:
            dict: The response including the invocationArn, or None if error occurs
        """
        try:
            # Create blueprint configuration
            blueprints = [{
                "blueprintArn": self.blueprint_arn,
                "version": self.blueprint_ver,
                "stage": self.blueprint_stage,
            }]

            # Use the profile ARN if provided, otherwise construct it
            profile_arn = self.profile_arn
            if not profile_arn:
                account_id = os.getenv('ACCOUNT')
                profile_arn = f'arn:aws:bedrock:{self.region_name}:{account_id}:data-automation-profile/us.data-automation-v1'

            # Invoke the automation
            response = self.bda_runtime_client.invoke_data_automation_async(
                inputConfiguration={
                    's3Uri': self.input_bucket
                },
                outputConfiguration={
                    's3Uri': self.output_bucket
                },
                # blueprints=blueprints,
                dataAutomationProfileArn=profile_arn,
                dataAutomationConfiguration={
                    'dataAutomationProjectArn': self.project_arn,
                    'stage': 'LIVE'
                }
            )

            invocation_arn = response.get('invocationArn', 'Unknown')
            print(
                f'Invoked data automation job with invocation ARN: {invocation_arn}')

            return response

        except Exception as e:
            print(f"Error invoking data automation: {str(e)}")
            return None

    def update_blueprint(self, schema_path) -> Optional[Dict]:
        """
        Update blueprint with new instructions

        Args:
            schema_path (str): Path to the schema file
            
        Returns:
            dict: The response from the API call, or None if error occurs
        """
        try:
            # Read the schema file as a string to avoid double serialization
            with open(schema_path, 'r') as f:
                schema_str = f.read()
            
            # Validate that it's valid JSON
            try:
                json.loads(schema_str)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in schema file: {e}")
                return None
            
            # Update the blueprint with the schema string directly
            response = self.bda_client.update_test_blueprint(
                blueprintArn=self.blueprint_arn,
                blueprintStage='LIVE',
                schema=schema_str,  # Use the raw string instead of json.dumps()
            )

            blueprint_name = response.get('blueprint')['blueprintName']
            print(f'\nUpdated instructions for blueprint: {blueprint_name}')

            return response

        except Exception as e:
            print(f"Error updating blueprint: {str(e)}")
            return None
