import boto3
import time
from typing import Dict, List, Optional
from botocore.exceptions import ClientError

class LambdaResourceCleaner:
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize the Lambda resource cleaner
        
        Args:
            region (str): AWS region name
        """
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
    
    def get_function_details(self, function_name: str) -> Optional[Dict]:
        """
        Get Lambda function details
        
        Args:
            function_name (str): Lambda function name or ARN
            
        Returns:
            Dict: Function details if found, None otherwise
        """
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Lambda function '{function_name}' not found")
            else:
                print(f"Error getting function details: {str(e)}")
            return None

    def delete_function_versions(self, function_name: str) -> bool:
        """
        Delete all versions of the Lambda function
        
        Args:
            function_name (str): Lambda function name
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"Deleting function versions for {function_name}")
            paginator = self.lambda_client.get_paginator('list_versions_by_function')
            
            for page in paginator.paginate(FunctionName=function_name):
                for version in page['Versions']:
                    # Skip $LATEST version as it can't be deleted directly
                    if version['Version'] != '$LATEST':
                        try:
                            self.lambda_client.delete_function(
                                FunctionName=function_name,
                                Qualifier=version['Version']
                            )
                            print(f"Deleted version {version['Version']}")
                        except ClientError as e:
                            print(f"Error deleting version {version['Version']}: {str(e)}")
            
            return True
        except ClientError as e:
            print(f"Error listing versions: {str(e)}")
            return False

    def delete_function_aliases(self, function_name: str) -> bool:
        """
        Delete all aliases of the Lambda function
        
        Args:
            function_name (str): Lambda function name
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"Deleting function aliases for {function_name}")
            paginator = self.lambda_client.get_paginator('list_aliases')
            
            for page in paginator.paginate(FunctionName=function_name):
                for alias in page['Aliases']:
                    try:
                        self.lambda_client.delete_alias(
                            FunctionName=function_name,
                            Name=alias['Name']
                        )
                        print(f"Deleted alias {alias['Name']}")
                    except ClientError as e:
                        print(f"Error deleting alias {alias['Name']}: {str(e)}")
            
            return True
        except ClientError as e:
            print(f"Error listing aliases: {str(e)}")
            return False

    def delete_function_event_source_mappings(self, function_name: str) -> bool:
        """
        Delete all event source mappings for the Lambda function
        
        Args:
            function_name (str): Lambda function name
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"Deleting event source mappings for {function_name}")
            paginator = self.lambda_client.get_paginator('list_event_source_mappings')
            
            for page in paginator.paginate(FunctionName=function_name):
                for mapping in page['EventSourceMappings']:
                    try:
                        self.lambda_client.delete_event_source_mapping(
                            UUID=mapping['UUID']
                        )
                        print(f"Deleted event source mapping {mapping['UUID']}")
                    except ClientError as e:
                        print(f"Error deleting event source mapping {mapping['UUID']}: {str(e)}")
            
            return True
        except ClientError as e:
            print(f"Error listing event source mappings: {str(e)}")
            return False

    def delete_function_concurrency(self, function_name: str) -> bool:
        """
        Delete function concurrency settings
        
        Args:
            function_name (str): Lambda function name
            
        Returns:
            bool: True if successful
        """
        try:
            self.lambda_client.delete_function_concurrency(FunctionName=function_name)
            print("Deleted function concurrency settings")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                print(f"Error deleting function concurrency: {str(e)}")
            return False

    def delete_function(self, function_name: str) -> bool:
        """
        Delete the Lambda function
        
        Args:
            function_name (str): Lambda function name
            
        Returns:
            bool: True if successful
        """
        try:
            # Delete the main function
            self.lambda_client.delete_function(FunctionName=function_name)
            print(f"Deleted function {function_name}")
            
            # Wait for deletion to complete
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    self.lambda_client.get_function(FunctionName=function_name)
                    print("Waiting for function deletion to complete...")
                    time.sleep(5)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        return True
            
            print("Warning: Function deletion verification timed out")
            return True
            
        except ClientError as e:
            print(f"Error deleting function: {str(e)}")
            return False

    def cleanup_lambda_resources(self, function_name: str) -> bool:
        """
        Clean up all resources associated with a Lambda function
        
        Args:
            function_name (str): Lambda function name
            
        Returns:
            bool: True if successful
        """
        # Get function details first
        function_details = self.get_function_details(function_name)
        if not function_details:
            return False

        print(f"\nStarting cleanup for Lambda function: {function_name}")
        
        # Delete resources in order
        self.delete_function_event_source_mappings(function_name)
        self.delete_function_aliases(function_name)
        self.delete_function_versions(function_name)
        self.delete_function_concurrency(function_name)
        
        # Finally, delete the function itself
        return self.delete_function(function_name)



def main(function_name, region):
    """
    Main function to run the script
    """
    try:
     

        # Initialize cleaner and delete resources
        cleaner = LambdaResourceCleaner(region)
        success = cleaner.cleanup_lambda_resources(function_name)
        
        if success:
            print(f"\nSuccessfully deleted Lambda function '{function_name}' and associated resources")
        else:
            print(f"\nFailed to complete all cleanup tasks for '{function_name}'")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()