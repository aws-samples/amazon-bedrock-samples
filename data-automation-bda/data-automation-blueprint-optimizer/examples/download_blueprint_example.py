#!/usr/bin/env python3
"""
Example script demonstrating how to use the download_blueprint function programmatically.

This script shows how to:
1. Initialize the AWS clients
2. Download a blueprint by ID
3. Access and use the blueprint details
"""

import os
import json
from src.aws_clients import AWSClients


def main():
    """Main function demonstrating blueprint download."""
    
    # Replace these values with your actual project and blueprint information
    project_arn = "arn:aws:bedrock:us-east-1:123456789012:data-automation-project/my-project"
    blueprint_id = "my-blueprint-123"
    
    try:
        # Initialize AWS clients
        print("Initializing AWS clients...")
        aws_clients = AWSClients()
        
        # Create output directory if it doesn't exist
        output_dir = "output/blueprints/examples"
        os.makedirs(output_dir, exist_ok=True)
        
        # Download the blueprint
        print(f"Downloading blueprint with ID: {blueprint_id}")
        output_path, blueprint_details = aws_clients.download_blueprint(
            blueprint_id=blueprint_id,
            project_arn=project_arn,
            output_path=f"{output_dir}/{blueprint_id}.json"
        )
        
        # Print blueprint details
        print("\nBlueprint details:")
        print(f"  Name: {blueprint_details.get('blueprintName', 'Unknown')}")
        print(f"  ARN: {blueprint_details.get('blueprintArn', 'Unknown')}")
        print(f"  Version: {blueprint_details.get('blueprintVersion', 'Unknown')}")
        print(f"  Stage: {blueprint_details.get('blueprintStage', 'Unknown')}")
        print(f"  Schema saved to: {output_path}")
        
        # Load and parse the schema
        print("\nLoading schema from file...")
        with open(output_path, 'r') as f:
            schema = json.load(f)
        
        # Print schema information
        print(f"Schema description: {schema.get('description', 'No description')}")
        print(f"Number of properties: {len(schema.get('properties', {}))}")
        
        # Print the first few properties
        print("\nFirst few properties:")
        for i, (name, prop) in enumerate(schema.get('properties', {}).items()):
            if i >= 3:  # Only show the first 3 properties
                break
            print(f"  {name}:")
            print(f"    Type: {prop.get('type', 'Unknown')}")
            print(f"    Inference Type: {prop.get('inferenceType', 'Unknown')}")
            instruction = prop.get('instruction', 'No instruction')
            # Truncate long instructions for display
            if len(instruction) > 100:
                instruction = instruction[:97] + "..."
            print(f"    Instruction: {instruction}")
        
        print("\nExample completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
