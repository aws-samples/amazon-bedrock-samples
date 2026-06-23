"""
Unit tests for FastAPI frontend application.
"""
import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import asyncio

from src.frontend.app import app


class TestFrontendApp:
    """Test cases for FastAPI frontend application."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data for testing."""
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

    def test_root_endpoint_redirect(self, client):
        """Test root endpoint redirects to React app."""
        response = client.get("/")
        assert response.status_code == 200

    def test_update_config_invalid_data(self, client):
        """Test configuration update with invalid data."""
        invalid_data = {"invalid": "data"}
        
        response = client.post("/api/update-config", json=invalid_data)
        
        # Should handle validation error
        assert response.status_code in [400, 422]
