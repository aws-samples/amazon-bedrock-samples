"""
Unit tests for prompt tuner module.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse

from src.prompt_tuner import (
    read_s3_object,
    rewrite_prompt_bedrock,
    rewrite_prompt_bedrock_with_document
)


class TestPromptTuner:
    """Test cases for prompt tuner functions."""

    @patch('src.prompt_tuner.AWSClients')
    def test_read_s3_object_success(self, mock_aws_clients):
        """Test successful S3 object reading."""
        mock_aws = Mock()
        mock_s3_client = Mock()
        mock_aws.s3_client = mock_s3_client
        mock_aws_clients.return_value = mock_aws

        # Mock S3 response
        mock_response = {
            'Body': Mock(read=lambda: b'Test document content')
        }
        mock_s3_client.get_object.return_value = mock_response

        s3_uri = 's3://test-bucket/test-document.pdf'
        result = read_s3_object(s3_uri)

        assert result == b'Test document content'
        mock_s3_client.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test-document.pdf'
        )

    @patch('src.prompt_tuner.AWSClients')
    def test_read_s3_object_with_nested_path(self, mock_aws_clients):
        """Test S3 object reading with nested path."""
        mock_aws = Mock()
        mock_s3_client = Mock()
        mock_aws.s3_client = mock_s3_client
        mock_aws_clients.return_value = mock_aws

        mock_response = {
            'Body': Mock(read=lambda: b'Nested document content')
        }
        mock_s3_client.get_object.return_value = mock_response

        s3_uri = 's3://test-bucket/documents/invoices/invoice-001.pdf'
        result = read_s3_object(s3_uri)

        assert result == b'Nested document content'
        mock_s3_client.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='documents/invoices/invoice-001.pdf'
        )

    @patch('src.prompt_tuner.AWSClients')
    def test_read_s3_object_failure(self, mock_aws_clients):
        """Test S3 object reading failure."""
        mock_aws = Mock()
        mock_s3_client = Mock()
        mock_aws.s3_client = mock_s3_client
        mock_aws_clients.return_value = mock_aws

        # Mock S3 exception
        mock_s3_client.get_object.side_effect = Exception("Access denied")

        s3_uri = 's3://test-bucket/nonexistent.pdf'
        result = read_s3_object(s3_uri)

        assert result is None

    def test_read_s3_object_invalid_uri(self):
        """Test S3 object reading with invalid URI."""
        invalid_uri = 'not-an-s3-uri'
        
        # This should handle the invalid URI gracefully
        with patch('src.prompt_tuner.AWSClients') as mock_aws_clients:
            mock_aws = Mock()
            mock_s3_client = Mock()
            mock_aws.s3_client = mock_s3_client
            mock_aws_clients.return_value = mock_aws
            
            # The function should handle parsing errors
            result = read_s3_object(invalid_uri)
            # Depending on implementation, this might return None or raise an exception

    @patch('src.prompt_tuner.bedrock_runtime_client')
    def test_rewrite_prompt_bedrock_with_different_field(self, mock_bedrock_client):
        """Test prompt rewriting for different field types."""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'completion': 'Improved instruction: Extract the total amount including currency symbol, typically found at the bottom of the document in bold text.'
            }).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        field_name = 'total_amount'
        original_prompt = 'Extract the total amount'
        expected_output = '$1,234.56'

        result = rewrite_prompt_bedrock(field_name, original_prompt, expected_output)

        assert 'total amount' in result
        assert 'currency symbol' in result

    @patch('src.prompt_tuner.bedrock_runtime_client')
    def test_rewrite_prompt_bedrock_failure(self, mock_bedrock_client):
        """Test prompt rewriting failure handling."""
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock service error")

        field_name = 'invoice_number'
        original_prompt = 'Extract the invoice number'
        expected_output = 'INV-12345'

        with pytest.raises(Exception, match="Bedrock service error"):
            rewrite_prompt_bedrock(field_name, original_prompt, expected_output)

    @patch('src.prompt_tuner.bedrock_runtime_client')
    def test_rewrite_prompt_bedrock_malformed_response(self, mock_bedrock_client):
        """Test handling of malformed Bedrock response."""
        mock_response = {
            'body': Mock(read=lambda: b'invalid json response')
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        field_name = 'invoice_number'
        original_prompt = 'Extract the invoice number'
        expected_output = 'INV-12345'

        with pytest.raises(json.JSONDecodeError):
            rewrite_prompt_bedrock(field_name, original_prompt, expected_output)

