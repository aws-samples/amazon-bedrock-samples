import boto3
from botocore.config import Config
from dotenv import load_dotenv
import os
import json
from typing import Optional, Dict, Any, List, Tuple

# Load environment variables
load_dotenv()


class AWSClients:
    """Class to manage AWS service clients using environment variables"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AWSClients, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        try:
            # Get configuration from environment variables
            self.region = os.getenv('AWS_REGION', 'us-west-2')
            print(f"Using AWS region: {self.region}")
            
            self.account_id = os.getenv('ACCOUNT')
            max_retries = int(os.getenv('AWS_MAX_RETRIES', '3'))
            connect_timeout = int(os.getenv('AWS_CONNECT_TIMEOUT', '500'))
            read_timeout = int(os.getenv('AWS_READ_TIMEOUT', '1000'))
            

            # Configure session
            self.session = boto3.Session(
                region_name=self.region,
            )

            # Configure client
            config = Config(
                retries=dict(
                    max_attempts=max_retries
                ),
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
            )

            # Initialize clients
            self._bda_client = self.session.client('bedrock-data-automation', config=config)
            self._bda_runtime_client = self.session.client('bedrock-data-automation-runtime', config=config)
            self._bedrock_runtime = self.session.client('bedrock-runtime', config=config)
            self._s3_client = self.session.client('s3', config=config)

            self._initialized = True
            print(f"AWS clients initialized with region: {self.region}")

        except Exception as e:
            print(f"Error initializing AWS clients: {str(e)}")
            raise

    @property
    def bda_client(self):
        return self._bda_client

    @property
    def bda_runtime_client(self):
        return self._bda_runtime_client

    @property
    def bedrock_runtime(self):
        return self._bedrock_runtime

    @property
    def s3_client(self):
        return self._s3_client
        
    def download_blueprint(self, blueprint_id: str, project_arn: str, project_stage: str = "LIVE", output_path: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Download a blueprint based on its ID.
        
        Args:
            blueprint_id (str): The ID of the blueprint to download
            project_arn (str): The ARN of the project containing the blueprint
            project_stage (str, optional): The stage of the project. Defaults to "LIVE".
            output_path (str, optional): Path to save the blueprint schema. If None, a default path will be used.
            
        Returns:
            Tuple[str, Dict[str, Any]]: Tuple containing the path to the saved schema file and the blueprint details
        """
        try:
            print(f"Downloading blueprint with ID: {blueprint_id}")
            
            # Get all blueprints from the project
            blueprints = self._get_project_blueprints(project_arn, project_stage)
            
            if not blueprints:
                raise ValueError(f"No blueprints found in project {project_arn}")
                
            # Find the blueprint with the specified ID
            blueprint = self._find_blueprint_by_id(blueprints, blueprint_id)
            
            if not blueprint:
                raise ValueError(f"No blueprint found with ID: {blueprint_id}")
                
            print(f"Found blueprint: {blueprint.get('blueprintName', 'Unknown')} (ARN: {blueprint.get('blueprintArn')})")
            
            # Get the blueprint details
            response = self._bda_client.get_blueprint(
                blueprintArn=blueprint.get('blueprintArn'),
                blueprintStage=blueprint.get('blueprintStage', 'LIVE')
            )
            
            # Extract schema string from response
            blueprint_details = response.get('blueprint', {})
            schema_str = blueprint_details.get('schema')
            
            if not schema_str:
                raise ValueError("No schema found in blueprint response")
            
            # Determine output path if not provided
            if not output_path:
                blueprint_name = blueprint_details.get('blueprintName', 'unknown')
                output_dir = "output/blueprints"
                os.makedirs(output_dir, exist_ok=True)
                output_path = f"{output_dir}/{blueprint_name}_{blueprint_id}.json"
            else:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write schema string directly to file
            with open(output_path, 'w') as f:
                f.write(schema_str)
            
            print(f"✅ Blueprint schema saved to {output_path}")
            return output_path, blueprint_details
            
        except Exception as e:
            print(f"❌ Error downloading blueprint: {str(e)}")
            raise
    
    def _get_project_blueprints(self, project_arn: str, project_stage: str) -> List[Dict[str, Any]]:
        """
        Get all blueprints from a data automation project.
        
        Args:
            project_arn (str): ARN of the project
            project_stage (str): Project stage ('DEVELOPMENT' or 'LIVE')
            
        Returns:
            List[Dict[str, Any]]: List of blueprints
        """
        try:
            # Call the API to get project details
            response = self._bda_client.get_data_automation_project(
                projectArn=project_arn,
                projectStage=project_stage
            )
            
            # Extract blueprints from the response
            blueprints = []
            if response and 'project' in response:
                custom_config = response['project'].get('customOutputConfiguration', {})
                blueprints = custom_config.get('blueprints', [])
                
                print(f"Found {len(blueprints)} blueprints in project {project_arn}")
                return blueprints
            else:
                print("No project data found in response")
                return []
                
        except Exception as e:
            print(f"Unexpected error getting project blueprints: {e}")
            return []
    
    def _find_blueprint_by_id(self, blueprints: List[Dict[str, Any]], blueprint_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a blueprint by its ID from a list of blueprints.
        
        Args:
            blueprints (List[Dict[str, Any]]): List of blueprints
            blueprint_id (str): The blueprint ID to search for
            
        Returns:
            Optional[Dict[str, Any]]: The matching blueprint or None if not found
        """
        if not blueprints or not blueprint_id:
            return None
            
        # Loop through blueprints and check if blueprint_id is in the ARN
        for blueprint in blueprints:
            arn = blueprint.get('blueprintArn', '')
            # Extract the blueprint ID from the ARN
            if blueprint_id in arn:
                return blueprint
                
        # If no match is found
        return None
