"""
Test Case Service for interacting with Amazon Bedrock Automated Reasoning Policy Test Cases.
"""
import logging
import time
import re
from typing import List, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError

logger = logging.getLogger(__name__)


class TestCaseService:
    """
    Service for fetching test cases from Amazon Bedrock Automated Reasoning policies.
    
    This class handles:
    - Fetching test cases via the list-automated-reasoning-policy-test-cases API
    - Extracting guard_content from test case responses
    - Validation of policy ARN format
    - Retry logic with exponential backoff for transient failures
    - Error handling for various AWS error types
    """
    
    def __init__(self, region_name: str = "us-west-2"):
        """
        Initialize the test case service.
        
        Args:
            region_name: AWS region name (default: us-west-2)
        """
        self.region_name = region_name
        self.client = boto3.client(
            service_name="bedrock",
            region_name=region_name
        )
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds for exponential backoff
    
    def list_test_cases(self, policy_arn: str) -> List[Dict[str, str]]:
        """
        Fetch test cases from AWS Bedrock and extract guard_content.
        
        Implements retry logic with exponential backoff for transient failures.
        
        Args:
            policy_arn: The policy ARN to fetch test cases for
            
        Returns:
            List of dicts with test_case_id and guard_content
            
        Raises:
            ValueError: If policy_arn is invalid or empty
            Exception: If AWS API call fails after all retries
        """
        # Validate policy ARN
        self._validate_policy_arn(policy_arn)
        
        for attempt in range(self.max_retries):
            try:
                # Call the list-automated-reasoning-policy-test-cases API
                response = self.client.list_automated_reasoning_policy_test_cases(
                    policyArn=policy_arn
                )
                
                # Extract test cases from response
                test_cases = response.get("testCases", [])
                
                # Extract query_content (the prompt) from each test case
                result = []
                for test_case in test_cases:
                    test_case_id = test_case.get("testCaseId")
                    query_content = self._extract_query_content(test_case)
                    
                    # Only include test cases with valid query_content
                    if test_case_id and query_content:
                        result.append({
                            "test_case_id": test_case_id,
                            "guard_content": query_content  # Keep the field name for API compatibility
                        })
                    elif test_case_id:
                        logger.warning(f"Test case {test_case_id} has no query_content, skipping")
                
                logger.info(f"Successfully fetched {len(result)} test cases for policy {policy_arn}")
                return result
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                
                # Check if this is a transient error that should be retried
                if self._is_transient_error(error_code) and attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(
                        f"Transient error on attempt {attempt + 1}/{self.max_retries}: {error_code} - {error_message}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                
                # Non-transient error or final attempt - log and raise with detailed info
                logger.warning(
                    f"AWS Bedrock API call failed after {attempt + 1} attempts. "
                    f"Error code: {error_code}, Message: {error_message}, Policy ARN: {policy_arn}"
                )
                raise Exception(f"Failed to fetch test cases: {error_message}")
            
            except NoCredentialsError as e:
                raise Exception("AWS credentials not configured. Please configure your AWS credentials.")
            
            except EndpointConnectionError as e:
                raise Exception("AWS Bedrock service is temporarily unavailable. Please try again later.")
            
            except Exception as e:
                raise Exception(f"Failed to fetch test cases: {str(e)}")
        
        # Should not reach here, but just in case
        raise Exception("Failed to fetch test cases after all retries")
    
    def _extract_query_content(self, test_case: Dict[str, Any]) -> str:
        """
        Extract query_content (the prompt/question) from test case response.
        
        The queryContent field is directly in the test case object.
        
        Args:
            test_case: The test case dictionary from AWS response
            
        Returns:
            The extracted query_content text, or empty string if not found
        """
        # AWS returns queryContent in camelCase
        return test_case.get("queryContent", "")
    
    def _validate_policy_arn(self, policy_arn: str) -> None:
        """
        Validate policy ARN format.
        
        A valid policy ARN should follow the format:
        arn:aws:bedrock:{region}:{account-id}:automated-reasoning-policy/{policy-id}
        
        Args:
            policy_arn: The policy ARN to validate
            
        Raises:
            ValueError: If policy_arn is invalid or empty
        """
        if not policy_arn:
            raise ValueError("policy_arn cannot be empty")
        
        if not isinstance(policy_arn, str):
            raise ValueError("policy_arn must be a string")
        
        # Check basic ARN format
        arn_pattern = r'^arn:aws:bedrock:[a-z0-9-]+:\d+:automated-reasoning-policy/.+$'
        if not re.match(arn_pattern, policy_arn):
            raise ValueError(
                "Invalid policy ARN format. Expected format: "
                "arn:aws:bedrock:{region}:{account-id}:automated-reasoning-policy/{policy-id}"
            )
    
    def _is_transient_error(self, error_code: str) -> bool:
        """
        Determine if an error code represents a transient failure.
        
        Args:
            error_code: The AWS error code
            
        Returns:
            True if the error is transient and should be retried
        """
        transient_errors = {
            "ThrottlingException",
            "ServiceUnavailableException",
            "InternalServerException",
            "RequestTimeout",
            "TooManyRequestsException"
        }
        return error_code in transient_errors
