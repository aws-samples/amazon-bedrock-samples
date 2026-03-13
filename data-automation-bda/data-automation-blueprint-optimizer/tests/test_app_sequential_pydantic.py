"""
Unit tests for the main optimization application (app_sequential_pydantic.py).
"""
import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the main function from the application
# Note: This assumes the main function is importable from app_sequential_pydantic
# You may need to adjust the import based on the actual structure


class TestMainOptimizationApp:
    """Test cases for the main optimization application."""

    @pytest.fixture
    def sample_input_config(self):
        """Sample input configuration for testing."""
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
            "clean_logs": False,
            "expected_outputs": {
                "invoice_number": "INV-12345",
                "total_amount": "$1,234.56",
                "date": "2024-01-15"
            }
        }

    @patch('builtins.open', create=True)
    @patch('json.load')
    def test_load_configuration_success(self, mock_json_load, mock_open, sample_input_config):
        """Test successful configuration loading."""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_json_load.return_value = sample_input_config

        # This would be the actual function call in the main app
        # Adjust based on actual implementation
        config_file = "input_0.json"
        
        # Simulate loading configuration
        with open(config_file, 'r') as f:
            config = json.load(f)

        assert config == sample_input_config
        mock_open.assert_called_once_with(config_file, 'r')

    @patch('builtins.open', create=True)
    def test_load_configuration_file_not_found(self, mock_open):
        """Test configuration loading when file not found."""
        mock_open.side_effect = FileNotFoundError("Configuration file not found")

        config_file = "nonexistent_input.json"

        with pytest.raises(FileNotFoundError):
            with open(config_file, 'r') as f:
                json.load(f)

    @patch('builtins.open', create=True)
    @patch('json.load')
    def test_load_configuration_invalid_json(self, mock_json_load, mock_open):
        """Test configuration loading with invalid JSON."""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        config_file = "invalid_input.json"

        with pytest.raises(json.JSONDecodeError):
            with open(config_file, 'r') as f:
                json.load(f)

    def test_configuration_validation(self, sample_input_config):
        """Test configuration validation logic."""
        # This would be a validation function in the main app
        def validate_config(config):
            required_fields = [
                'project_arn', 'blueprint_arn', 'blueprint_ver', 
                'blueprint_stage', 'threshold', 'max_iterations'
            ]
            
            for field in required_fields:
                if field not in config or not config[field]:
                    return False, f"Missing required field: {field}"
            
            if not (0.0 <= config['threshold'] <= 1.0):
                return False, "Threshold must be between 0.0 and 1.0"
            
            if config['max_iterations'] <= 0:
                return False, "Max iterations must be positive"
            
            return True, "Valid configuration"

        # Test valid configuration
        is_valid, message = validate_config(sample_input_config)
        assert is_valid is True
        assert message == "Valid configuration"

        # Test invalid threshold
        invalid_config = sample_input_config.copy()
        invalid_config['threshold'] = 1.5
        is_valid, message = validate_config(invalid_config)
        assert is_valid is False
        assert "Threshold must be between" in message

        # Test missing field
        incomplete_config = sample_input_config.copy()
        del incomplete_config['project_arn']
        is_valid, message = validate_config(incomplete_config)
        assert is_valid is False
        assert "Missing required field: project_arn" in message

    @patch('time.time')
    def safe_operation(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs), None
        except Exception as e:
            return None, str(e)

        # Test successful operation
        def successful_op():
            return "success"

        result, error = safe_operation(successful_op)
        assert result == "success"
        assert error is None

        # Test failing operation
        def failing_op():
            raise ValueError("Operation failed")

        result, error = safe_operation(failing_op)
        assert result is None
        assert error == "Operation failed"
        filename = generate_output_filename("optimized_schema", "20240101_120000")
        assert filename == "optimized_schema_20240101_120000.json"

        # Test with auto timestamp
        with patch('src.util.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "20240101_120000"
            mock_datetime.now.return_value = mock_now
            
            filename = generate_output_filename("optimized_schema")
            assert filename == "optimized_schema_20240101_120000.json"
