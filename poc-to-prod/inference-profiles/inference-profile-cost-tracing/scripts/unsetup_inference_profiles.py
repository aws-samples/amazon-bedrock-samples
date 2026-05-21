import boto3
from botocore.exceptions import ClientError
from typing import List, Dict
import time

class BedrockProfileCleaner:
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize the Bedrock Profile cleaner
        
        Args:
            region (str): AWS region name
        """
        self.region = region
        self.bedrock_client = boto3.client('bedrock', region_name=region)
        
    def get_inference_profile(self, profile_id: str) -> Dict:
        """
        Get details of an inference profile
        
        Args:
            profile_id (str): Inference profile ID or ARN
            
        Returns:
            Dict: Profile details if found
        """
        try:
            response = self.bedrock_client.get_inference_profile(
                inferenceProfileIdentifier=profile_id
            )

            print(response)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Inference profile '{profile_id}' not found")
            else:
                print(f"Error getting profile details: {str(e)}")
            return None

    def delete_inference_profile(self, profile_id: str) -> bool:
        """
        Delete a single inference profile
        
        Args:
            profile_id (str): Inference profile ID or ARN
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            # Check if profile exists
            profile = self.get_inference_profile(profile_id)
            if not profile:
                return False

            print(f"Deleting inference profile: {profile_id}")
            # Delete the profile
            responseDelete = self.bedrock_client.delete_inference_profile(
                inferenceProfileIdentifier=profile_id
            )
           
            # Wait for deletion to complete
           #  max_attempts = 10
           #  for attempt in range(max_attempts):
             #    try:
               #      self.get_inference_profile(profile_id)
                 #    print(f"Waiting for profile {profile_id} deletion to complete...")
                  #   time.sleep(5)
                # except ClientError as e:
                  #   if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    #     print(f"Successfully deleted profile {profile_id}")
                      #   return True
            
            # print(f"Warning: Profile {profile_id} deletion verification timed out")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Profile {profile_id} already deleted")
                return True
            elif e.response['Error']['Code'] == 'ConflictException':
                print(f"Profile {profile_id} is in use or in a conflicting state")
            elif e.response['Error']['Code'] == 'ThrottlingException':
                print(f"Throttling detected while deleting {profile_id}. Please try again later.")
            else:
                print(f"Error deleting profile {profile_id}: {str(e)}")
            return False


    def delete_inference_profiles(self, profile_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple inference profiles
        
        Args:
            profile_ids (List[str]): List of inference profile IDs or ARNs
            
        Returns:
            Dict[str, bool]: Dictionary of profile IDs and their deletion status
        """
        results = {}
        
        if not profile_ids:
            print("No profile IDs provided")
            return results
            
        print(f"\nStarting deletion of {len(profile_ids)} inference profile(s)")
        
        for profile_id in profile_ids:
            profile_id_key = ""
            profile_id_val = ""
            for key in profile_id:
                profile_id_val = profile_id[key]
                profile_id_key = key
                
            print(profile_id_val)
            results[profile_id_key] = self.delete_inference_profile(profile_id_val)
            # Add small delay between deletions to avoid throttling
            time.sleep(1)
            
        # Print summary
        successful = sum(1 for status in results.values() if status)
        print(f"\nDeletion Summary:")
        print(f"Successfully deleted: {successful}/{len(profile_ids)} profiles")
        
        if successful != len(profile_ids):
            print("\nFailed deletions:")
            for profile_id, status in results.items():
                if not status:
                    print(f"- {profile_id}")
                    
        return results

def main(profile_ids,region):
    """
    Main function to run the script
    """
    try:

        if not profile_ids:
            print("No valid profile IDs provided")
            return

        print(profile_ids)
        # Initialize cleaner and delete profiles
        cleaner = BedrockProfileCleaner(region)
        results = cleaner.delete_inference_profiles(profile_ids)

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()