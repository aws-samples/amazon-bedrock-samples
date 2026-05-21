import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional
import time

class S3BucketCleaner:
    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        """
        Initialize the S3 Bucket cleaner
        
        Args:
            bucket_name (str): Name of the S3 bucket
            region (str): AWS region name
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.s3_resource = boto3.resource('s3', region_name=region)
        self.bucket = self.s3_resource.Bucket(bucket_name)

    def verify_bucket_exists(self) -> bool:
        """
        Verify if the bucket exists and is accessible
        
        Returns:
            bool: True if bucket exists and is accessible
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                print(f"Bucket {self.bucket_name} does not exist")
            elif error_code == '403':
                print(f"Permission denied accessing bucket {self.bucket_name}")
            else:
                print(f"Error accessing bucket {self.bucket_name}: {str(e)}")
            return False

    def delete_objects(self, objects: List[Dict]) -> bool:
        """
        Delete a batch of objects
        
        Args:
            objects (List[Dict]): List of objects to delete
            
        Returns:
            bool: True if deletion was successful
        """
        if not objects:
            return True

        try:
            delete_items = {'Objects': [{'Key': obj['Key']} for obj in objects]}
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete=delete_items
            )
            
            # Check for errors in deletion
            errors = response.get('Errors', [])
            if errors:
                print(f"Errors during deletion: {errors}")
                return False
                
            return True
            
        except ClientError as e:
            print(f"Error deleting objects: {str(e)}")
            return False

    def delete_object_versions(self, versions: List[Dict]) -> bool:
        """
        Delete a batch of object versions
        
        Args:
            versions (List[Dict]): List of object versions to delete
            
        Returns:
            bool: True if deletion was successful
        """
        if not versions:
            return True

        try:
            delete_items = {
                'Objects': [
                    {
                        'Key': version['Key'],
                        'VersionId': version['VersionId']
                    } 
                    for version in versions
                ]
            }
            
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete=delete_items
            )
            
            # Check for errors in deletion
            errors = response.get('Errors', [])
            if errors:
                print(f"Errors during version deletion: {errors}")
                return False
                
            return True
            
        except ClientError as e:
            print(f"Error deleting object versions: {str(e)}")
            return False

    def delete_all_objects(self) -> bool:
        """
        Delete all objects in the bucket
        
        Returns:
            bool: True if all objects were deleted successfully
        """
        try:
            print(f"Deleting all objects in bucket {self.bucket_name}")
            
            # Delete current objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name):
                objects = page.get('Contents', [])
                if objects:
                    if not self.delete_objects(objects):
                        return False
                    
            return True
            
        except ClientError as e:
            print(f"Error deleting objects: {str(e)}")
            return False

    def delete_all_versions(self) -> bool:
        """
        Delete all object versions in the bucket
        
        Returns:
            bool: True if all versions were deleted successfully
        """
        try:
            print(f"Deleting all object versions in bucket {self.bucket_name}")
            
            paginator = self.s3_client.get_paginator('list_object_versions')
            for page in paginator.paginate(Bucket=self.bucket_name):
                # Delete version markers
                markers = page.get('DeleteMarkers', [])
                if markers:
                    if not self.delete_object_versions(markers):
                        return False
                
                # Delete versions
                versions = page.get('Versions', [])
                if versions:
                    if not self.delete_object_versions(versions):
                        return False
                    
            return True
            
        except ClientError as e:
            print(f"Error deleting versions: {str(e)}")
            return False

    def delete_incomplete_multipart_uploads(self) -> bool:
        """
        Delete all incomplete multipart uploads
        
        Returns:
            bool: True if all incomplete uploads were deleted
        """
        try:
            print(f"Deleting incomplete multipart uploads in bucket {self.bucket_name}")
            
            paginator = self.s3_client.get_paginator('list_multipart_uploads')
            for page in paginator.paginate(Bucket=self.bucket_name):
                uploads = page.get('Uploads', [])
                for upload in uploads:
                    self.s3_client.abort_multipart_upload(
                        Bucket=self.bucket_name,
                        Key=upload['Key'],
                        UploadId=upload['UploadId']
                    )
                    
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchUpload':
                return True
            print(f"Error deleting multipart uploads: {str(e)}")
            return False

    def clean_bucket(self) -> bool:
        """
        Clean the bucket by removing all objects, versions, and incomplete uploads
        
        Returns:
            bool: True if bucket was cleaned successfully
        """
        try:
            if not self.verify_bucket_exists():
                return False
                
            print(f"Starting cleanup of bucket: {self.bucket_name}")
            
            # Delete incomplete multipart uploads
            if not self.delete_incomplete_multipart_uploads():
                return False
                
            # Delete all versions (including delete markers)
            if not self.delete_all_versions():
                return False
                
            # Delete all current objects
            if not self.delete_all_objects():
                return False
                
            print(f"Successfully cleaned bucket: {self.bucket_name}")
            return True
            
        except Exception as e:
            print(f"Error cleaning bucket: {str(e)}")
            return False
        
def main(bucket_name, region):
 
    try:
   
        # Initialize cleaner and clean bucket
        cleaner = S3BucketCleaner(bucket_name, region)
        success = cleaner.clean_bucket()
        
        if success:
            print(f"Bucket {bucket_name} cleaned successfully")
        else:
            print(f"Failed to clean bucket {bucket_name}")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()