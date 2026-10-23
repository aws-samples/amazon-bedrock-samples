# BDA Blueprint Optimizer - Test Suite

This directory contains comprehensive unit and integration tests for the BDA Blueprint Optimizer project.

## Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and shared fixtures
├── test_aws_clients.py           # Tests for AWS client management
├── test_bda_operations.py        # Tests for BDA operations
├── test_prompt_tuner.py          # Tests for prompt tuning functionality
├── test_util.py                  # Tests for utility functions
├── test_frontend_app.py          # Tests for FastAPI application
├── test_app_sequential_pydantic.py # Tests for main optimization logic
├── test_integration.py           # Integration tests for complete workflows
└── README.md                     # This file
```

## Test Categories

### Unit Tests
- **AWS Clients** (`test_aws_clients.py`): Tests for AWS service client initialization and configuration
- **BDA Operations** (`test_bda_operations.py`): Tests for Bedrock Data Automation operations
- **Prompt Tuner** (`test_prompt_tuner.py`): Tests for AI-powered prompt optimization
- **Utilities** (`test_util.py`): Tests for helper functions and utilities
- **Frontend App** (`test_frontend_app.py`): Tests for FastAPI endpoints and web interface
- **Main App** (`test_app_sequential_pydantic.py`): Tests for core optimization logic

### Integration Tests
- **Complete Workflow** (`test_integration.py`): End-to-end testing of the optimization process

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Quick Start

Run all tests:
```bash
./run_tests.sh
```

### Test Options

Run only unit tests:
```bash
./run_tests.sh --unit-only
```

Run only integration tests:
```bash
./run_tests.sh --integration-only
```

Run tests with coverage:
```bash
./run_tests.sh --verbose --html
```

Run tests in parallel:
```bash
./run_tests.sh --parallel
```

### Manual pytest Commands

Run all tests:
```bash
pytest tests/
```

Run specific test file:
```bash
pytest tests/test_aws_clients.py
```

Run tests with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

Run tests with specific markers:
```bash
pytest tests/ -m "not integration"  # Skip integration tests
pytest tests/ -m "unit"             # Run only unit tests
pytest tests/ -m "integration"      # Run only integration tests
```

## Test Configuration

### Pytest Configuration
- Configuration is in `pytest.ini` at the project root
- Custom markers are defined for test categorization
- Warnings are filtered for cleaner output

### Environment Variables
Tests use environment variables for configuration:
- `AWS_REGION`: AWS region for testing (default: us-west-2)
- `ACCOUNT`: AWS account ID for testing
- `AWS_MAX_RETRIES`: Maximum retry attempts
- `DEFAULT_MODEL`: Default AI model for testing

### Fixtures

Common fixtures are defined in `conftest.py`:
- `temp_dir`: Temporary directory for test files
- `sample_config`: Sample configuration data
- `sample_blueprint_schema`: Sample blueprint schema
- `mock_aws_clients`: Mocked AWS clients
- `fastapi_client`: FastAPI test client

## Mocking Strategy

Tests use extensive mocking to avoid external dependencies:
- **AWS Services**: All AWS API calls are mocked
- **File Operations**: File I/O operations are mocked
- **Network Requests**: HTTP requests are mocked
- **Time-dependent Operations**: Time functions are mocked for deterministic tests

## Coverage Requirements

- **Minimum Coverage**: 80% line coverage
- **Critical Components**: 90%+ coverage for core optimization logic
- **Integration Tests**: Cover complete user workflows

## Test Data

Test data is generated using:
- **Fixtures**: Predefined test data in `conftest.py`
- **Factory Pattern**: Dynamic test data generation
- **Mock Objects**: Simulated AWS responses and file content

## Continuous Integration

Tests run automatically on:
- **Push to main/develop branches**
- **Pull requests**
- **Multiple Python versions** (3.8, 3.9, 3.10, 3.11)

CI includes:
- Unit and integration tests
- Code coverage reporting
- Security vulnerability scanning
- Code quality checks (formatting, imports, type hints)

## Debugging Tests

### Verbose Output
```bash
pytest tests/ -v -s
```

### Debug Specific Test
```bash
pytest tests/test_aws_clients.py::TestAWSClients::test_initialization_success -v -s
```

### Print Debug Information
```bash
pytest tests/ --capture=no
```

### Run with PDB Debugger
```bash
pytest tests/ --pdb
```

## Performance Testing

Performance tests are included for:
- **Load Testing**: Multiple concurrent requests
- **Memory Usage**: Memory consumption during optimization
- **Response Times**: API endpoint response times

Run performance tests:
```bash
pytest tests/ -m "performance" --benchmark-only
```

## Security Testing

Security tests verify:
- **Input Validation**: Proper handling of malicious inputs
- **File Path Traversal**: Prevention of directory traversal attacks
- **AWS Credential Handling**: Secure credential management

## Best Practices

### Writing New Tests

1. **Use Descriptive Names**: Test names should clearly describe what is being tested
2. **Follow AAA Pattern**: Arrange, Act, Assert
3. **Mock External Dependencies**: Don't rely on external services
4. **Test Edge Cases**: Include boundary conditions and error scenarios
5. **Keep Tests Independent**: Each test should be able to run in isolation

### Test Organization

1. **Group Related Tests**: Use test classes to group related functionality
2. **Use Fixtures**: Leverage pytest fixtures for common setup
3. **Mark Tests Appropriately**: Use markers to categorize tests
4. **Document Complex Tests**: Add docstrings for complex test scenarios

### Example Test Structure

```python
class TestMyComponent:
    """Test cases for MyComponent class."""

    def test_successful_operation(self, mock_dependency):
        """Test successful operation with valid inputs."""
        # Arrange
        component = MyComponent()
        mock_dependency.return_value = "expected_result"
        
        # Act
        result = component.perform_operation()
        
        # Assert
        assert result == "expected_result"
        mock_dependency.assert_called_once()

    def test_error_handling(self, mock_dependency):
        """Test error handling with invalid inputs."""
        # Arrange
        component = MyComponent()
        mock_dependency.side_effect = Exception("Test error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Test error"):
            component.perform_operation()
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `src` directory is in Python path
2. **Mock Failures**: Verify mock patches match actual import paths
3. **Fixture Conflicts**: Check for fixture name collisions
4. **Environment Variables**: Ensure test environment variables are set

### Getting Help

- Check test output for detailed error messages
- Use `pytest --tb=long` for full tracebacks
- Review fixture definitions in `conftest.py`
- Consult pytest documentation for advanced features

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve code coverage
4. Update test documentation as needed
5. Follow existing test patterns and conventions
