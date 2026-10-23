"""
Unit tests for util module.
"""
import pytest
import json
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.util import (
    get_project_blueprints,
    # get_blueprint_schema,  # Function doesn't exist in current util.py
    # optimize_schema_iteratively,  # Function doesn't exist in current util.py
    # calculate_similarity,  # Function doesn't exist in current util.py
    # save_schema_to_file,  # Function doesn't exist in current util.py
    # load_config_from_file,  # Function doesn't exist in current util.py
    # setup_logging  # Function doesn't exist in current util.py
)


class TestUtilFunctions:
    """Test cases for utility functions."""

    def test_get_project_blueprints_success(self, mock_aws_clients):
        """Test successful project blueprints retrieval."""
        mock_bda_client = Mock()
        
        # Mock project response with blueprints
        mock_response = {
            'project': {
                'customOutputConfiguration': {
                    'blueprints': [
                        {
                            'blueprintArn': 'arn:aws:bedrock-data-automation:us-west-2:123456789012:blueprint/bp1',
                            'blueprintName': 'Blueprint 1'
                        },
                        {
                            'blueprintArn': 'arn:aws:bedrock-data-automation:us-west-2:123456789012:blueprint/bp2',
                            'blueprintName': 'Blueprint 2'
                        }
                    ]
                }
            }
        }
        mock_bda_client.get_data_automation_project.return_value = mock_response

        project_arn = 'arn:aws:bedrock-data-automation:us-west-2:123456789012:project/test-project'
        project_stage = 'DEVELOPMENT'

        result = get_project_blueprints(mock_bda_client, project_arn, project_stage)

        assert len(result) == 2
        assert result[0]['blueprintName'] == 'Blueprint 1'
        assert result[1]['blueprintName'] == 'Blueprint 2'

        mock_bda_client.get_data_automation_project.assert_called_once_with(
            projectArn=project_arn,
            projectStage=project_stage
        )

    def test_get_project_blueprints_empty_response(self, mock_aws_clients):
        """Test project blueprints retrieval with empty response."""
        mock_bda_client = Mock()
        mock_bda_client.get_data_automation_project.return_value = {}

        project_arn = 'arn:aws:bedrock-data-automation:us-west-2:123456789012:project/test-project'
        project_stage = 'DEVELOPMENT'

        result = get_project_blueprints(mock_bda_client, project_arn, project_stage)

        assert result == []

    def test_get_project_blueprints_no_blueprints(self, mock_aws_clients):
        """Test project blueprints retrieval when no blueprints exist."""
        mock_bda_client = Mock()
        mock_response = {
            'project': {
                'customOutputConfiguration': {}
            }
        }
        mock_bda_client.get_data_automation_project.return_value = mock_response

        project_arn = 'arn:aws:bedrock-data-automation:us-west-2:123456789012:project/test-project'
        project_stage = 'DEVELOPMENT'

        result = get_project_blueprints(mock_bda_client, project_arn, project_stage)

        assert result == []

    def test_schema_validation_helper(self):
        """Test schema validation helper function."""
        valid_schema = {
            'fields': [
                {
                    'fieldName': 'test_field',
                    'fieldType': 'string',
                    'instruction': 'Test instruction'
                }
            ]
        }

        # This would be a helper function to validate schema structure
        def validate_schema(schema):
            if 'fields' not in schema:
                return False
            for field in schema['fields']:
                if 'fieldName' not in field or 'instruction' not in field:
                    return False
            return True

        assert validate_schema(valid_schema) is True

        invalid_schema = {'fields': [{'fieldName': 'test'}]}  # Missing instruction
        assert validate_schema(invalid_schema) is False
