"""
Unit tests for AWS clients module.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import boto3
from botocore.config import Config

from src.aws_clients import AWSClients


class TestAWSClients:
    """Test cases for AWSClients class."""

    def test_singleton_pattern(self):
        """Test that AWSClients follows singleton pattern."""
        client1 = AWSClients()
        client2 = AWSClients()
        assert client1 is client2

    @patch.dict(os.environ, {
        'AWS_REGION': 'us-east-1',
        'ACCOUNT': '987654321098',
        'AWS_MAX_RETRIES': '5',
        'AWS_CONNECT_TIMEOUT': '600',
        'AWS_READ_TIMEOUT': '1200'
    })
    @patch('boto3.Session')
    def test_initialization_with_env_vars(self, mock_session):
        """Test initialization with environment variables."""
        # Reset singleton
        AWSClients._instance = None
        
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        client = AWSClients()
        
        assert client.region == 'us-east-1'
        assert client.account_id == '987654321098'
        
        # Verify session was created with correct region
        mock_session.assert_called_with(region_name='us-east-1')

    @patch.dict(os.environ, {}, clear=True)
    @patch('boto3.Session')
    def test_initialization_with_defaults(self, mock_session):
        """Test initialization with default values."""
        # Reset singleton
        AWSClients._instance = None
        
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        client = AWSClients()
        
        assert client.region == 'us-west-2'  # Default region
        assert client.account_id is None  # No account ID set

    @patch('boto3.Session')
    def test_config_parameters(self, mock_session):
        """Test that Config object is created with correct parameters."""
        # Reset singleton
        AWSClients._instance = None
        
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        with patch.dict(os.environ, {
            'AWS_MAX_RETRIES': '5',
            'AWS_CONNECT_TIMEOUT': '600',
            'AWS_READ_TIMEOUT': '1200'
        }):
            client = AWSClients()
            
            # Access a client to trigger creation
            _ = client.s3_client
            
            # Verify client was called with Config
            call_args = mock_session_instance.client.call_args
            assert 'config' in call_args[1]
            
            config = call_args[1]['config']
            assert isinstance(config, Config)

    @patch('boto3.Session')
    def test_error_handling_during_initialization(self, mock_session):
        """Test error handling during client initialization."""
        # Reset singleton
        AWSClients._instance = None
        
        mock_session.side_effect = Exception("AWS Session creation failed")
        
        with pytest.raises(Exception, match="AWS Session creation failed"):
            AWSClients()

    @patch('boto3.Session')
    def test_region_property(self, mock_session):
        """Test region property access."""
        # Reset singleton
        AWSClients._instance = None
        
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        with patch.dict(os.environ, {'AWS_REGION': 'eu-west-1'}):
            client = AWSClients()
            assert client.region == 'eu-west-1'

    @patch('boto3.Session')
    def test_account_id_property(self, mock_session):
        """Test account_id property access."""
        # Reset singleton
        AWSClients._instance = None
        
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        with patch.dict(os.environ, {'ACCOUNT': '123456789012'}):
            client = AWSClients()
            assert client.account_id == '123456789012'
