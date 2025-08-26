"""
Unit tests for BDA operations module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.bda_operations import BDAOperations


class TestBDAOperations:
    """Test cases for BDAOperations class."""

    @pytest.fixture
    def bda_config(self):
        """Sample BDA configuration."""
        return {
            'project_arn': 'arn:aws:bedrock-data-automation:us-west-2:123456789012:project/test-project',
            'blueprint_arn': 'arn:aws:bedrock-data-automation:us-west-2:123456789012:blueprint/test-blueprint',
            'blueprint_ver': '1',
            'blueprint_stage': 'DEVELOPMENT',
            'input_bucket': 's3://test-input-bucket/',
            'output_bucket': 's3://test-output-bucket/',
            'profile_arn': 'arn:aws:bedrock-data-automation:us-west-2:123456789012:profile/test-profile'
        }

    @patch('src.bda_operations.AWSClients')
    def test_initialization_success(self, mock_aws_clients, bda_config):
        """Test successful initialization of BDAOperations."""
        mock_aws = Mock()
        mock_aws.bda_runtime_client = Mock()
        mock_aws.bda_client = Mock()
        mock_aws.region = 'us-west-2'
        mock_aws_clients.return_value = mock_aws

        bda_ops = BDAOperations(**bda_config)

        assert bda_ops.project_arn == bda_config['project_arn']
        assert bda_ops.blueprint_arn == bda_config['blueprint_arn']
        assert bda_ops.blueprint_ver == bda_config['blueprint_ver']
        assert bda_ops.blueprint_stage == bda_config['blueprint_stage']
        assert bda_ops.input_bucket == bda_config['input_bucket']
        assert bda_ops.output_bucket == bda_config['output_bucket']
        assert bda_ops.profile_arn == bda_config['profile_arn']
        assert bda_ops.region_name == 'us-west-2'

    @patch('src.bda_operations.AWSClients')
    def test_initialization_without_profile_arn(self, mock_aws_clients, bda_config):
        """Test initialization without profile_arn."""
        mock_aws = Mock()
        mock_aws.bda_runtime_client = Mock()
        mock_aws.bda_client = Mock()
        mock_aws.region = 'us-west-2'
        mock_aws_clients.return_value = mock_aws

        # Remove profile_arn from config
        config_without_profile = bda_config.copy()
        del config_without_profile['profile_arn']

        bda_ops = BDAOperations(**config_without_profile)

        assert bda_ops.profile_arn is None

    @patch('src.bda_operations.AWSClients')
    def test_invoke_data_automation_success(self, mock_aws_clients, bda_config):
        """Test successful data automation invocation."""
        mock_aws = Mock()
        mock_bda_runtime_client = Mock()
        mock_aws.bda_runtime_client = mock_bda_runtime_client
        mock_aws.bda_client = Mock()
        mock_aws.region = 'us-west-2'
        mock_aws_clients.return_value = mock_aws

        # Mock successful invocation response
        mock_response = {
            'invocationArn': 'arn:aws:bedrock-data-automation:us-west-2:123456789012:invocation/test-invocation',
            'invocationStatus': 'IN_PROGRESS'
        }
        mock_bda_runtime_client.invoke_data_automation_async.return_value = mock_response

        bda_ops = BDAOperations(**bda_config)
        result = bda_ops.invoke_data_automation()

        assert result == mock_response
        mock_bda_runtime_client.invoke_data_automation_async.assert_called_once()
