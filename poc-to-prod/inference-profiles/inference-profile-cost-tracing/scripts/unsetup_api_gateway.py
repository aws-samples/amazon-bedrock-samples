import boto3
import time


def main(api_id, region, s3_bucket_name):
    """
    Delete an API Gateway and all its resources
    
    Args:
        api_id (str): The ID of the API Gateway to delete
        region (str): AWS region (default: 'us-east-1')
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        

        # Create API Gateway client
        apigateway_client = boto3.client('apigateway', region_name=region)
        
        print(f"Starting deletion of API Gateway with ID: {api_id}")
        
        try:
            # First, try to get the API to verify it exists
            apigateway_client.get_rest_api(restApiId=api_id)
            print('API FETCHED')
        except apigateway_client.exceptions.NotFoundException:
            print(f"API Gateway with ID {api_id} not found.")
            return False
        
        # Delete all stages first
        try:
            stages = apigateway_client.get_stages(restApiId=api_id)
            for stage in stages['item']:
                print(f"Deleting stage: {stage['stageName']}")
                apigateway_client.delete_stage(
                    restApiId=api_id,
                    stageName=stage['stageName']
                )
        except Exception as e:
            print(f"Warning while deleting stages: {str(e)}")

        # Delete all resources
        try:
            resources = apigateway_client.get_resources(restApiId=api_id)
            for resource in resources['items']:
                if resource['path'] != '/':  # Don't delete root resource
                    print(f"Deleting resource: {resource['path']}")
                    apigateway_client.delete_resource(
                        restApiId=api_id,
                        resourceId=resource['id']
                    )
        except Exception as e:
            print(f"Warning while deleting resources: {str(e)}")

        # Delete the API Gateway
        print("Deleting API Gateway...")
        apigateway_client.delete_rest_api(restApiId=api_id)
        
        # Wait for deletion to complete
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            try:
                apigateway_client.get_rest_api(restApiId=api_id)
                print("Waiting for API Gateway deletion to complete...")
                time.sleep(10)
                attempt += 1
            except apigateway_client.exceptions.NotFoundException:
                print("API Gateway deleted successfully")
                return True
        
        print("Warning: Deletion completed but verification timed out")
        return True

    except apigateway_client.exceptions.TooManyRequestsException:
        print("Rate limit exceeded. Please try again later.")
        return False
    except Exception as e:
        print(f"Error deleting API Gateway: {str(e)}")
        return False

