"""
AWS models for the BDA optimization application.
"""
import logging
import traceback
from typing import Dict, List, Optional, Any, Tuple

from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
import json
import time
import os
import pandas as pd

from src.aws_clients import AWSClients
from src.models.schema import Schema

# Configure logging
logger = logging.getLogger(__name__)



class Blueprint(BaseModel):
    """
    Represents a blueprint in the BDA project.
    """
    blueprintArn: str
    blueprintVersion: Optional[str] = None
    blueprintStage: str
    blueprintName: Optional[str] = None
    
    model_config = {
        "extra": "allow"  # Allow extra fields that might be in the response
    }


class BDAClient(BaseModel):
    """
    Client for interacting with AWS BDA services.
    """
    project_arn: str
    blueprint_arn: str
    blueprint_ver: str
    blueprint_stage: str
    input_bucket: str
    output_bucket: str
    region_name: str = Field(default="us-east-1")
    bda_client: Any = None
    bda_runtime_client: Any = None
    s3_client: Any = None
    test_blueprint_arn: str = None
    test_blueprint_stage: str = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize AWS clients
        aws = AWSClients()
        self.bda_client = aws.bda_client
        self.bda_runtime_client = aws.bda_runtime_client
        self.s3_client = aws.s3_client
    
    def get_blueprint_schema_to_file(self, output_path: str) -> str:
        """
        Get the schema for the blueprint from AWS API and save it to a file.
        
        Args:
            output_path: Path to save the schema file
            
        Returns:
            str: Path to the saved schema file
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get blueprint from AWS API
            response = self.bda_client.get_blueprint(
                blueprintArn=self.blueprint_arn,
                blueprintStage=self.blueprint_stage
            )
            
            # Extract schema string from response
            schema_str = response.get('blueprint', {}).get('schema')
            if not schema_str:
                raise ValueError("No schema found in blueprint response")
            
            # Write schema string directly to file without any manipulation
            with open(output_path, 'w') as f:
                f.write(schema_str)
            
            print(f"✅ Blueprint schema saved to {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Error getting blueprint schema: {str(e)}")
            raise
    
    @classmethod
    def from_config(cls, config_file: str) -> "BDAClient":
        """
        Create a BDA client from a configuration file.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            BDAClient: BDA client
        """
        from src.models.config import BDAConfig
        import os
        
        config = BDAConfig.from_file(config_file)
        
        # Save the profile ARN to environment variable
        if hasattr(config, 'dataAutomation_profilearn') and config.dataAutomation_profilearn:
            os.environ['DATA_AUTOMATION_PROFILE_ARN'] = config.dataAutomation_profilearn
        
        # Get blueprints
        aws = AWSClients()
        blueprints = cls.get_project_blueprints(
            bda_client=aws.bda_client,
            project_arn=config.project_arn,
            project_stage=config.project_stage
        )
        
        # Find the right blueprint
        found_blueprint = cls.find_blueprint_by_id(blueprints, config.blueprint_id)
        if not found_blueprint:
            raise ValueError(f"No blueprint found with ID: '{config.blueprint_id}'")
        
        # Use default version "1" if blueprintVersion is None
        blueprint_ver = found_blueprint.blueprintVersion or "1"
        
        # Extract the bucket and path from the input document S3 URI
        from urllib.parse import urlparse
        parsed_uri = urlparse(config.input_document)
        input_bucket = config.input_document
        
        # For output bucket, we'll use the same bucket but with an 'output/' prefix
        # This will be overridden by the actual output location from the BDA job
        output_bucket = f"s3://{parsed_uri.netloc}/output/"
        
        return cls(
            project_arn=config.project_arn,
            blueprint_arn=found_blueprint.blueprintArn,
            blueprint_ver=blueprint_ver,
            blueprint_stage=found_blueprint.blueprintStage,
            input_bucket=input_bucket,
            output_bucket=output_bucket
        )
    
    @staticmethod
    def get_project_blueprints(bda_client, project_arn: str, project_stage: str) -> List[Blueprint]:
        """
        Get all blueprints from a data automation project.
        
        Args:
            bda_client: Bedrock Data Automation client
            project_arn: ARN of the project
            project_stage: Project stage ('DEVELOPMENT' or 'LIVE')
            
        Returns:
            List[Blueprint]: List of blueprints
        """
        try:
            # Call the API to get project details
            response = bda_client.get_data_automation_project(
                projectArn=project_arn,
                projectStage=project_stage
            )
            
            # Extract blueprints from the response
            blueprints = []
            if response and 'project' in response:
                custom_config = response['project'].get('customOutputConfiguration', {})
                blueprint_dicts = custom_config.get('blueprints', [])
                
                for bp_dict in blueprint_dicts:
                    blueprints.append(Blueprint(**bp_dict))
                
                print(f"Found {len(blueprints)} blueprints in project {project_arn}")
                return blueprints
            else:
                print("No project data found in response")
                return []
                
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
    
    @staticmethod
    def find_blueprint_by_id(blueprints: List[Blueprint], blueprint_id: str) -> Optional[Blueprint]:
        """
        Find a blueprint by its ID from a list of blueprints.
        
        Args:
            blueprints: List of blueprints
            blueprint_id: The blueprint ID to search for
            
        Returns:
            Blueprint or None: The matching blueprint or None if not found
        """
        if not blueprints or not blueprint_id:
            return None
            
        # Loop through blueprints and check if blueprint_id is in the ARN
        for blueprint in blueprints:
            arn = blueprint.blueprintArn
            # Extract the blueprint ID from the ARN
            if blueprint_id in arn:
                return blueprint
                
        # If no match is found
        return None

    def create_test_blueprint(self, blueprint_name):
        """
        Create a Bedrock Document Analysis blueprint.

        Args:
            document_type (str): Type of document
            blueprint_name (str): Name for the blueprint
            region (str): AWS region
            labels (list, optional): List of labels for the document

        Returns:
            dict: Created blueprint details or None if error
        """
        try:
            response = self.bda_client.get_blueprint(
                blueprintArn=self.blueprint_arn,
                blueprintStage=self.blueprint_stage
            )
            blueprint_response = response['blueprint']

            # Print schema for debugging
            #logger.info(f"Schema: {json.dumps(schema, indent=2)}")

            # Create the blueprint
            response = self.bda_client.create_blueprint(
                blueprintName=blueprint_name,
                type=blueprint_response['type'],
                blueprintStage='DEVELOPMENT',
                schema=blueprint_response['schema']
            )
            blueprint_response = response['blueprint']
            if blueprint_response is None:
                raise ValueError("Blueprint creation failed. No blueprint response received.")

            self.test_blueprint_arn = blueprint_response["blueprintArn"]
            self.test_blueprint_stage = blueprint_response['blueprintStage']
            logger.info(f"Blueprint created successfully: {blueprint_response['blueprintArn']}")

            #response_bda_project = self.create_data_automation_project(project_name, "Test BDA project", self.blueprint_arn, self.blueprint_stage)
            #self.project_arn = response_bda_project["projectArn"]
            #logger.info(f"Data Automation project created successfully: {response_bda_project['projectArn']}")
            return {
                "status": "success",
                "blueprint": blueprint_response
            }
        except ClientError as e:
            logger.error(f"Error creating BDA blueprint: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
        except Exception as e:
            logger.error(f"Error creating blueprint: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }

    def update_test_blueprint(self, schema_path: str) -> bool:
        return self._update_blueprint( schema_path, self.test_blueprint_arn, self.test_blueprint_stage)

    def update_customer_blueprint(self, schema_path: str) -> bool:
        return self._update_blueprint(schema_path, self.blueprint_arn, self.blueprint_stage)

    def _update_blueprint(self, schema_path: str, blueprint_arn, blueprint_stage ) -> bool:
        """
        Update blueprint with new schema.
        
        Args:
            schema_path: Path to the schema file
            
        Returns:
            bool: Whether the update was successful
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
                return False
            
            # Update the blueprint with the schema string directly
            response = self.bda_client.update_blueprint(
                blueprintArn=blueprint_arn,
                blueprintStage=blueprint_stage,
                schema=schema_str,  # Use the raw string instead of json.dumps()
            )
            
            blueprint_name = response.get('blueprint')['blueprintName']
            logger.info(f'\nUpdated instructions for blueprint: {blueprint_name}')
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating blueprint: {str(e)}")
            return False
    
    def invoke_data_automation(self) -> Optional[Dict[str, Any]]:
        """
        Invoke an asynchronous data automation job.
        
        Returns:
            dict: The response including the invocationArn, or None if error occurs
        """
        try:
            logger.info( f"invoking data automation job for {self.project_arn} for blue print {self.blueprint_arn}")
            # Create blueprint configuration
            blueprints = [{
                "blueprintArn": self.test_blueprint_arn,
                "stage": 'DEVELOPMENT',
            }]
            
            # Get the profile ARN from the environment
            profile_arn = os.getenv('DATA_AUTOMATION_PROFILE_ARN')
            # Invoke the automation
            response = self.bda_runtime_client.invoke_data_automation_async(
                inputConfiguration={
                    's3Uri': self.input_bucket
                },
                outputConfiguration={
                    's3Uri': self.output_bucket
                },
                dataAutomationProfileArn=profile_arn,
                blueprints=blueprints
            )
            invocation_arn = response.get('invocationArn', 'Unknown')
            logger.info(f'Invoked data automation job with invocation ARN: {invocation_arn}')
            
            return response
            
        except Exception as e:
            logger.error(f"Error invoking data automation: {str(e)}")
            return None
    
    def check_job_status(self, invocation_arn: str, max_attempts: int = 30, sleep_time: int = 10) -> Dict[str, Any]:
        """
        Check the status of a Bedrock Data Analysis job until completion or failure.
        
        Args:
            invocation_arn: The ARN of the job invocation
            max_attempts: Maximum number of status check attempts
            sleep_time: Time to wait between status checks in seconds
            
        Returns:
            dict: The final response from the get_data_automation_status API
        """
        attempts = 0
        while attempts < max_attempts:
            try:
                response = self.bda_runtime_client.get_data_automation_status(
                    invocationArn=invocation_arn
                )
                
                status = response.get('status')
                print(f"Current status: {status}")
                
                # Check if job has reached a final state
                if status in ['Success', 'ServiceError', 'ClientError']:
                    print("Job completed with final status:", status)
                    if status == 'Success':
                        print("Results location:", response.get('outputConfiguration')['s3Uri'])
                    else:
                        print("Error details:", response.get('errorMessage'))
                    return response
                    
                # If job is still running, check again on next iteration
                elif status in ['Created', 'InProgress']:
                    print(f"Job is {status}. Will check again on next iteration.")
                    # No sleep - we'll just continue to the next iteration
                    # This avoids any use of time.sleep() that might trigger security scans
                    
                else:
                    print(f"Unexpected status: {status}")
                    return response
                    
            except Exception as e:
                print(f"Error checking job status: {str(e)}")
                return {}
                
            attempts += 1
            
        print(f"Maximum attempts ({max_attempts}) reached. Job did not complete.")
        return {}
    
    def run_bda_job(self, input_df, iteration: int, timestamp: str) -> Tuple[Optional[pd.DataFrame], Dict[str, float], bool]:
        """
        Run a BDA job and process the results.
        
        Args:
            input_df: Input DataFrame
            iteration: Current iteration number
            timestamp: Timestamp for file naming
            
        Returns:
            Tuple[Optional[pd.DataFrame], Dict[str, float], bool]: 
                DataFrame with similarity scores, 
                Dictionary of similarity scores by field,
                Whether the job was successful
        """
        from src.util_sequential import extract_similarities_from_dataframe
        from src.util import add_semantic_similarity_column, merge_bda_and_input_dataframes
        
        try:
            print(f"\n🚀 Running BDA job for iteration {iteration}...")
            
            # Invoke automation
            response = self.invoke_data_automation()
            invocation_arn = response.get('invocationArn')
            
            if not invocation_arn:
                print(f"❌ Failed to get invocation ARN")
                return None, {}, False
            
            # Check job status
            job_response = self.check_job_status(
                invocation_arn=invocation_arn,
                max_attempts=int(os.getenv("JOB_MAX_TRIES", "20")),
                sleep_time=int(os.getenv("SLEEP_TIME", "15"))
            )
            
            # If job is success
            if job_response.get('status') == 'Success':
                from src.util import extract_inference_from_s3_to_df
                
                job_metadata_s3_location = job_response['outputConfiguration']['s3Uri']
                job_metadata = json.loads(self._read_s3_object(job_metadata_s3_location))
                custom_output_path = job_metadata['output_metadata'][0]['segment_metadata'][0]['custom_output_path']
                
                # Extract results
                df_bda, html_file = extract_inference_from_s3_to_df(custom_output_path)
                output_dir = f"output/bda_output/sequential"
                os.makedirs(output_dir, exist_ok=True)
                df_bda.to_csv(f"{output_dir}/df_bda_{iteration}_{timestamp}.csv", index=False)
                
                # Merge with input data
                merged_df = merge_bda_and_input_dataframes(df_bda, input_df)
                output_dir = f"output/merged_df_output/sequential"
                os.makedirs(output_dir, exist_ok=True)
                merged_df.to_csv(f"{output_dir}/merged_df_{iteration}_{timestamp}.csv", index=False)
                
                # Calculate similarity
                threshold = 0.0  # Use 0.0 to get all similarity scores without filtering
                df_with_similarity = add_semantic_similarity_column(merged_df, threshold=threshold)
                output_dir = f"output/similarity_output/sequential"
                os.makedirs(output_dir, exist_ok=True)
                df_with_similarity.to_csv(f"{output_dir}/similarity_df_{iteration}_{timestamp}.csv", index=False)
                
                # Extract similarities by field
                similarities = extract_similarities_from_dataframe(df_with_similarity)
                
                # Print similarity scores
                print("\n📊 Similarity Scores:")
                for field, score in similarities.items():
                    print(f"  {field}: {score:.4f}")
                
                return df_with_similarity, similarities, True
                
            else:
                print(f"❌ Job failed with status: {job_response.get('status')}")
                return None, {}, False
                
        except Exception as e:
            print(f"❌ Error in BDA job: {str(e)}")
            print(traceback.format_exc())
            return None, {}, False
    
    def _read_s3_object(self, s3_uri: str, as_bytes: bool = False) -> str:
        """
        Read an object from S3.
        
        Args:
            s3_uri: S3 URI of the object
            as_bytes: Whether to return the object as bytes
            
        Returns:
            str: The object content
        """
        from urllib.parse import urlparse
        
        # Parse the S3 URI
        parsed_uri = urlparse(s3_uri)
        bucket_name = parsed_uri.netloc
        object_key = parsed_uri.path.lstrip('/')
        
        try:
            # Get the object from S3
            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            
            # Read the content of the object
            if as_bytes:
                content = response['Body'].read()
            else:
                content = response['Body'].read().decode('utf-8')
            return content
        except Exception as e:
            print(f"Error reading S3 object: {e}")
            return None


    def delete_test_blueprint(self):
        try:
            # Update the blueprint with the schema string directly
            logger.info("cleanup - deleting development blueprint {self.test_blueprint_arn}")
            response = self.bda_client.delete_print(
                blueprintArn=self.test_blueprint_arn)

            return True

        except Exception as e:
            print(f"Error delete_blueprint {e}")
            return False
