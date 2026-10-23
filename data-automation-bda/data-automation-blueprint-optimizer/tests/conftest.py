"""
Pytest configuration and shared fixtures for BDA Blueprint Optimizer tests.
"""
import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "project_arn": "arn:aws:bedrock-data-automation:us-west-2:123456789012:project/test-project",
        "blueprint_arn": "arn:aws:bedrock-data-automation:us-west-2:123456789012:blueprint/test-blueprint",
        "blueprint_ver": "1",
        "blueprint_stage": "DEVELOPMENT",
        "input_bucket": "s3://test-input-bucket/",
        "output_bucket": "s3://test-output-bucket/",
        "document_name": "test_document.pdf",
        "document_s3_uri": "s3://test-bucket/test_document.pdf",
        "threshold": 0.8,
        "max_iterations": 3,
        "model": "anthropic.claude-3-sonnet-20240229-v1:0",
        "use_document_strategy": True,
        "clean_logs": False
    }

@pytest.fixture
def sample_blueprint_schema():
    """Sample blueprint schema for testing."""
    return {
        "blueprintArn": "arn:aws:bedrock-data-automation:us-west-2:123456789012:blueprint/test-blueprint",
        "blueprintName": "test-blueprint",
        "blueprintVersion": "1",
        "blueprintStage": "DEVELOPMENT",
        "schema": {
            "fields": [
                {
                    "fieldName": "invoice_number",
                    "fieldType": "string",
                    "instruction": "Extract the invoice number from the document"
                },
                {
                    "fieldName": "total_amount",
                    "fieldType": "number",
                    "instruction": "Extract the total amount from the document"
                },
                {
                    "fieldName": "date",
                    "fieldType": "date",
                    "instruction": "Extract the invoice date"
                }
            ]
        }
    }

@pytest.fixture
def mock_aws_clients():
    """Mock AWS clients for testing."""
    with patch('src.aws_clients.AWSClients') as mock_aws:
        # Create mock clients
        mock_instance = Mock()
        mock_instance.region = 'us-west-2'
        mock_instance.account_id = '123456789012'
        
        # Mock BDA clients
        mock_instance.bda_client = Mock()
        mock_instance.bda_runtime_client = Mock()
        
        # Mock S3 client
        mock_instance.s3_client = Mock()
        
        # Mock Bedrock client
        mock_instance.bedrock_runtime = Mock()
        
        # Mock STS client
        mock_instance.sts_client = Mock()
        mock_instance.sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
        
        mock_aws.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock response for prompt rewriting."""
    return {
        'body': Mock(read=lambda: json.dumps({
            'completion': 'Improved instruction: Extract the specific invoice number, typically found in the top-right corner of the document, formatted as "INV-XXXX" or similar alphanumeric pattern.'
        }).encode())
    }

@pytest.fixture
def mock_s3_object():
    """Mock S3 object content."""
    return b"Sample document content for testing"

@pytest.fixture
def sample_log_content():
    """Sample log content for testing."""
    return """2024-01-01 10:00:00 - INFO - Starting optimization process
2024-01-01 10:00:01 - INFO - Processing field: invoice_number
2024-01-01 10:00:02 - INFO - Optimization complete
"""

@pytest.fixture
def fastapi_client():
    """FastAPI test client."""
    from src.frontend.app import app
    return TestClient(app)

@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer for testing."""
    with patch('src.util.SentenceTransformer') as mock_st:
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_st.return_value = mock_model
        yield mock_model

@pytest.fixture
def mock_similarity_util():
    """Mock sentence_transformers util for similarity calculations."""
    with patch('src.util.util') as mock_util:
        mock_util.cos_sim.return_value = [[0.85]]
        yield mock_util

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('AWS_REGION', 'us-west-2')
    monkeypatch.setenv('ACCOUNT', '123456789012')
    monkeypatch.setenv('AWS_MAX_RETRIES', '3')
    monkeypatch.setenv('AWS_CONNECT_TIMEOUT', '500')
    monkeypatch.setenv('AWS_READ_TIMEOUT', '1000')
    monkeypatch.setenv('DEFAULT_MODEL', 'anthropic.claude-3-sonnet-20240229-v1:0')

@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""
    with patch('builtins.open', create=True) as mock_open:
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        yield mock_file

@pytest.fixture
def sample_optimization_result():
    """Sample optimization result for testing."""
    return {
        "original_schema": {
            "fields": [
                {
                    "fieldName": "invoice_number",
                    "instruction": "Extract the invoice number"
                }
            ]
        },
        "optimized_schema": {
            "fields": [
                {
                    "fieldName": "invoice_number",
                    "instruction": "Extract the specific invoice number, typically found in the top-right corner, formatted as 'INV-XXXX'"
                }
            ]
        },
        "iterations": 2,
        "improvements": [
            {
                "field": "invoice_number",
                "similarity_score": 0.85,
                "improved": True
            }
        ]
    }

@pytest.fixture
def mock_upload_file():
    """Mock UploadFile for testing file uploads."""
    mock_file = Mock()
    mock_file.filename = "test_document.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.size = 1024
    mock_file.read = Mock(return_value=b"PDF content")
    return mock_file
