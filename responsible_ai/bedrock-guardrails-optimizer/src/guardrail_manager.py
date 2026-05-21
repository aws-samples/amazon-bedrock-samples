"""
Guardrail management module.
Handles creation, update, and deletion of Bedrock Guardrails.
"""

import boto3
import time
from typing import Any, Optional


class GuardrailManager:
    """Manages Amazon Bedrock Guardrails lifecycle."""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the guardrail manager.
        
        Args:
            region: AWS region for Bedrock
        """
        self.bedrock = boto3.client("bedrock", region_name=region)
        self.region = region
        
    def create_guardrail(self, config: dict[str, Any]) -> dict[str, str]:
        """
        Create a new guardrail from configuration.
        
        Args:
            config: Guardrail configuration dictionary
            
        Returns:
            Dictionary with guardrailId, guardrailArn, and version
        """
        try:
            response = self.bedrock.create_guardrail(**config)
            
            print(f"Created guardrail: {response['guardrailId']}")
            print(f"ARN: {response['guardrailArn']}")
            print(f"Version: {response['version']}")
            
            return {
                "guardrailId": response["guardrailId"],
                "guardrailArn": response["guardrailArn"],
                "version": response["version"]
            }
        except Exception as e:
            print(f"Error creating guardrail: {e}")
            raise
    
    def update_guardrail(
        self, 
        guardrail_id: str, 
        config: dict[str, Any]
    ) -> dict[str, str]:
        """
        Update an existing guardrail.
        
        Args:
            guardrail_id: The guardrail identifier
            config: Updated configuration
            
        Returns:
            Dictionary with updated guardrail info
        """
        try:
            # Add guardrailIdentifier to config
            update_config = {**config, "guardrailIdentifier": guardrail_id}
            
            response = self.bedrock.update_guardrail(**update_config)
            
            print(f"Updated guardrail: {response['guardrailId']}")
            print(f"Version: {response['version']}")
            
            return {
                "guardrailId": response["guardrailId"],
                "guardrailArn": response["guardrailArn"],
                "version": response["version"]
            }
        except Exception as e:
            print(f"Error updating guardrail: {e}")
            raise
    
    def delete_guardrail(self, guardrail_id: str) -> bool:
        """
        Delete a guardrail.
        
        Args:
            guardrail_id: The guardrail identifier
            
        Returns:
            True if successful
        """
        try:
            self.bedrock.delete_guardrail(guardrailIdentifier=guardrail_id)
            print(f"Deleted guardrail: {guardrail_id}")
            return True
        except Exception as e:
            print(f"Error deleting guardrail: {e}")
            return False
    
    def get_guardrail(self, guardrail_id: str, version: str = "DRAFT") -> dict[str, Any]:
        """
        Get guardrail details.
        
        Args:
            guardrail_id: The guardrail identifier
            version: Guardrail version
            
        Returns:
            Guardrail details
        """
        try:
            response = self.bedrock.get_guardrail(
                guardrailIdentifier=guardrail_id,
                guardrailVersion=version
            )
            return response
        except Exception as e:
            print(f"Error getting guardrail: {e}")
            raise
    
    def list_guardrails(self) -> list[dict[str, Any]]:
        """
        List all guardrails in the account.
        
        Returns:
            List of guardrail summaries
        """
        try:
            guardrails = []
            paginator = self.bedrock.get_paginator("list_guardrails")
            
            for page in paginator.paginate():
                guardrails.extend(page.get("guardrails", []))
            
            return guardrails
        except Exception as e:
            print(f"Error listing guardrails: {e}")
            return []
    
    def create_version(self, guardrail_id: str, description: str = "") -> str:
        """
        Create a new version of a guardrail from DRAFT.
        
        Args:
            guardrail_id: The guardrail identifier
            description: Version description
            
        Returns:
            New version number
        """
        try:
            response = self.bedrock.create_guardrail_version(
                guardrailIdentifier=guardrail_id,
                description=description
            )
            
            version = response["version"]
            print(f"Created version {version} for guardrail {guardrail_id}")
            return version
        except Exception as e:
            print(f"Error creating version: {e}")
            raise
    
    def find_guardrail_by_name(self, name: str) -> Optional[str]:
        """
        Find a guardrail by name.
        
        Args:
            name: Guardrail name to search for
            
        Returns:
            Guardrail ID if found, None otherwise
        """
        guardrails = self.list_guardrails()
        for g in guardrails:
            if g.get("name") == name:
                return g.get("id")
        return None
    
    def create_or_update(self, config: dict[str, Any]) -> dict[str, str]:
        """
        Create a new guardrail or update existing one with same name.
        
        Args:
            config: Guardrail configuration
            
        Returns:
            Dictionary with guardrail info
        """
        name = config.get("name")
        existing_id = self.find_guardrail_by_name(name)
        
        if existing_id:
            print(f"Found existing guardrail '{name}' with ID {existing_id}, updating...")
            return self.update_guardrail(existing_id, config)
        else:
            print(f"Creating new guardrail '{name}'...")
            return self.create_guardrail(config)


def deploy_guardrail(config: dict[str, Any], region: str = "us-east-1") -> str:
    """
    Deploy a guardrail configuration.
    
    Args:
        config: Guardrail configuration
        region: AWS region
        
    Returns:
        Guardrail ID
    """
    manager = GuardrailManager(region=region)
    result = manager.create_or_update(config)
    return result["guardrailId"]


if __name__ == "__main__":
    from guardrail_config import get_baseline_config
    
    config = get_baseline_config()
    guardrail_id = deploy_guardrail(config)
    print(f"\nDeployed guardrail ID: {guardrail_id}")
