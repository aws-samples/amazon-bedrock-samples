#!/usr/bin/env python3
"""
Script to download a blueprint based on its ID.

Usage:
    python download_blueprint.py --blueprint-id <blueprint_id> --project-arn <project_arn> [--output-path <output_path>] [--project-stage <project_stage>]

Example:
    python download_blueprint.py --blueprint-id my-blueprint-123 --project-arn arn:aws:bedrock:us-east-1:123456789012:data-automation-project/my-project
"""

import argparse
import sys
from src.aws_clients import AWSClients


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Download a blueprint based on its ID')
    
    parser.add_argument('--blueprint-id', required=True, help='ID of the blueprint to download')
    parser.add_argument('--project-arn', required=True, help='ARN of the project containing the blueprint')
    parser.add_argument('--output-path', help='Path to save the blueprint schema (optional)')
    parser.add_argument('--project-stage', default='LIVE', help='Stage of the project (default: LIVE)')
    
    return parser.parse_args()


def main():
    """Main function to download a blueprint."""
    args = parse_arguments()
    
    try:
        # Initialize AWS clients
        aws_clients = AWSClients()
        
        # Download the blueprint
        output_path, blueprint_details = aws_clients.download_blueprint(
            blueprint_id=args.blueprint_id,
            project_arn=args.project_arn,
            project_stage=args.project_stage,
            output_path=args.output_path
        )
        
        # Print success message
        print(f"\nBlueprint downloaded successfully!")
        print(f"Blueprint Name: {blueprint_details.get('blueprintName', 'Unknown')}")
        print(f"Blueprint ARN: {blueprint_details.get('blueprintArn', 'Unknown')}")
        print(f"Schema saved to: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
