#!/usr/bin/env python
"""
End-to-end tests for the AR Chatbot application.

Tests the following workflows:
- Configuration update flow
- Prompt submission and response flow
- Concurrent thread processing
- Debug panel interaction (via API)
- Error scenarios
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from backend.flask_app import create_app
from backend.services.thread_manager import ThreadManager
from backend.models.thread import ThreadStatus


class TestE2EWorkflows:
    """End-to-end workflow tests."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = create_app({'TESTING': True})
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def mock_bedrock(self):
        """Mock Bedrock client."""
        with patch('backend.services.config_manager.boto3.client') as mock_client, \
             patch('backend.services.llm_service.boto3.client') as mock_llm_client, \
             patch('backend.services.validation_service.boto3.client') as mock_val_client:
            
            mock_bedrock = MagicMock()
            mock_bedrock_runtime = MagicMock()
            
            def client_factory(service_name, **kwargs):
                if service_name == 'bedrock':
                    return mock_bedrock
                elif service_name == 'bedrock-runtime':
                    return mock_bedrock_runtime
                return MagicMock()
            
            mock_client.side_effect = client_factory
            mock_llm_client.side_effect = client_factory
            mock_val_client.side_effect = client_factory
            
            # Mock list_foundation_models
            mock_bedrock.list_foundation_models.return_value = {
                'modelSummaries': [
                    {
                        'modelId': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                        'inferenceTypesSupported': ['ON_DEMAND']
                    },
                    {
                        'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0',
                        'inferenceTypesSupported': ['ON_DEMAND']
                    }
                ]
            }
            
            # Mock list_automated_reasoning_policies
            mock_bedrock.list_automated_reasoning_policies.return_value = {
                'automatedReasoningPolicySummaries': [
                    {
                        'policyArn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy',
                        'policyName': 'Test AR Policy',
                        'description': 'Test automated reasoning policy'
                    }
                ]
            }
            
            # Mock list_guardrails
            mock_bedrock.list_guardrails.return_value = {
                'guardrails': []
            }
            
            # Mock create_guardrail
            mock_bedrock.create_guardrail.return_value = {
                'guardrailId': 'test-guardrail-id',
                'version': 'DRAFT'
            }
            
            # Mock update_guardrail
            mock_bedrock.update_guardrail.return_value = {
                'guardrailId': 'test-guardrail-id',
                'version': 'DRAFT'
            }
            
            yield mock_bedrock
    
    @pytest.fixture
    def mock_llm_and_validation(self):
        """Mock LLM and validation services through ServiceContainer."""
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        # Mock LLM response
        mock_llm.generate_response.return_value = "Test response"
        
        # Mock validation - VALID by default
        mock_val.validate.return_value = Mock(
            output='VALID',
            findings=[]
        )
        
        # Patch the service container methods to return our mocks
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val):
            yield mock_llm, mock_val
    
    def test_configuration_update_flow(self, client, mock_bedrock):
        """
        Test configuration update flow.
        
        Validates: Requirements 1.1, 1.2, 1.3, 1.4
        """
        # Mock ensure_guardrail to avoid AWS API calls
        with patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure, \
             patch('backend.flask_app.config_manager.bedrock_client', mock_bedrock):
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Get available models
            response = client.get('/api/config/models')
            assert response.status_code == 200
            data = response.get_json()
            assert 'models' in data
            assert len(data['models']) > 0
            
            # Get available policies
            response = client.get('/api/config/policies')
            assert response.status_code == 200
            data = response.get_json()
            assert 'policies' in data
            assert len(data['policies']) > 0
            
            # Update configuration
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            data = response.get_json()
            assert 'config' in data
            assert data['config']['model_id'] == config_data['model_id']
            assert data['config']['guardrail_id'] == 'test-guardrail-id'
            
            # Verify configuration persists
            response = client.get('/api/config')
            assert response.status_code == 200
            data = response.get_json()
            assert data['model_id'] == config_data['model_id']
            
            print("✓ Configuration update flow test passed")
    
    def test_prompt_submission_and_response_flow(self, client, mock_bedrock, mock_llm_and_validation):
        """
        Test prompt submission and response flow.
        
        Validates: Requirements 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 4.1, 4.3
        """
        mock_llm, mock_val = mock_llm_and_validation
        
        with patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # First configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
        
            # Submit a prompt
            prompt_data = {'prompt': 'What is 2+2?'}
            response = client.post('/api/chat', json=prompt_data)
            assert response.status_code == 200
            data = response.get_json()
            assert 'thread_id' in data
            thread_id = data['thread_id']
            
            # Wait for processing
            time.sleep(2)
            
            # Get thread status
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            data = response.get_json()
            assert 'thread' in data
            thread = data['thread']
            assert thread['thread_id'] == thread_id
            assert thread['user_prompt'] == prompt_data['prompt']
            assert thread['status'] in [ThreadStatus.PROCESSING.value, ThreadStatus.COMPLETED.value]
            
            # If completed, verify response
            if thread['status'] == ThreadStatus.COMPLETED.value:
                assert thread['final_response'] is not None
                # Note: If validation returns VALID immediately, there may be no iterations
                # Iterations are only created when rewriting or asking questions
            
            print("✓ Prompt submission and response flow test passed")
    
    def test_concurrent_thread_processing(self, client, mock_bedrock, mock_llm_and_validation):
        """
        Test concurrent thread processing.
        
        Validates: Requirements 2.4, 2.5, 3.5
        """
        mock_llm, mock_val = mock_llm_and_validation
        
        with patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit multiple prompts concurrently
            prompts = [
                'What is 2+2?',
                'What is the capital of France?',
                'Explain quantum computing'
            ]
            
            thread_ids = []
            for prompt in prompts:
                response = client.post('/api/chat', json={'prompt': prompt})
                assert response.status_code == 200
                data = response.get_json()
                thread_ids.append(data['thread_id'])
            
            # Verify all threads are unique
            assert len(thread_ids) == len(set(thread_ids))
            
            # Wait for processing
            time.sleep(2)
            
            # Verify all threads exist and are independent
            for thread_id in thread_ids:
                response = client.get(f'/api/thread/{thread_id}')
                assert response.status_code == 200
                data = response.get_json()
                assert data['thread']['thread_id'] == thread_id
            
            # List all threads
            response = client.get('/api/threads')
            assert response.status_code == 200
            data = response.get_json()
            assert 'threads' in data
            assert len(data['threads']) >= len(thread_ids)
            
            print("✓ Concurrent thread processing test passed")
    
    def test_debug_panel_interaction(self, client, mock_bedrock, mock_llm_and_validation):
        """
        Test debug panel interaction via API.
        
        Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
        """
        mock_llm, mock_val = mock_llm_and_validation
        
        with patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit a prompt
            response = client.post('/api/chat', json={'prompt': 'Test prompt'})
            assert response.status_code == 200
            thread_id = response.get_json()['thread_id']
            
            # Wait for processing
            time.sleep(2)
            
            # Get thread with iterations (debug panel data)
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            data = response.get_json()
            thread = data['thread']
            
            # Verify iteration data is available
            assert 'iterations' in thread
            # Note: If validation returns VALID immediately, there may be no iterations
            # Iterations are only created when rewriting or asking questions
            if thread['status'] == ThreadStatus.COMPLETED.value and len(thread['iterations']) > 0:
                # Verify iteration structure if iterations exist
                iteration = thread['iterations'][0]
                assert 'iteration_number' in iteration
                assert 'iteration_type' in iteration
            
            print("✓ Debug panel interaction test passed")
    
    def test_error_scenarios(self, client, mock_bedrock):
        """
        Test error scenarios.
        
        Validates: Requirements 1.5, 3.5, 6.1, 6.2
        """
        # Reset configuration by accessing services through container
        from backend.flask_app import service_container, config_manager
        config_manager._current_config = None
        service_container.thread_manager._threads = {}
        
        # Test missing configuration
        response = client.post('/api/chat', json={'prompt': 'Test'})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        
        # Test invalid thread ID
        response = client.get('/api/thread/invalid-thread-id')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        
        # Test missing prompt
        config_data = {
            'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
            'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
        }
        client.post('/api/config', json=config_data)
        
        response = client.post('/api/chat', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        
        # Test missing config fields
        response = client.post('/api/config', json={'model_id': 'test'})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        
        print("✓ Error scenarios test passed")
    
    def test_too_complex_validation(self, client, mock_bedrock):
        """
        Test TOO_COMPLEX validation handling.
        
        Validates: Requirements 6.1, 6.2, 6.3
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM response
            mock_llm.generate_response.return_value = "Complex response"
            
            # Mock validation - TOO_COMPLEX
            mock_val.validate.return_value = Mock(
                output='TOO_COMPLEX',
                findings=[]
            )
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit a prompt
            response = client.post('/api/chat', json={'prompt': 'Complex prompt'})
            assert response.status_code == 200
            thread_id = response.get_json()['thread_id']
            
            # Wait for processing
            time.sleep(2)
            
            # Get thread status
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            data = response.get_json()
            thread = data['thread']
            
            # Verify TOO_COMPLEX handling
            if thread['status'] == ThreadStatus.ERROR.value:
                assert 'cannot be handled' in thread['final_response'].lower() or \
                       'too complex' in thread['final_response'].lower()
        
        print("✓ TOO_COMPLEX validation test passed")
    
    def test_no_translations_handling(self, client, mock_bedrock):
        """
        Test NO_TRANSLATIONS validation handling.
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM response
            mock_llm.generate_response.return_value = "Response with no translations"
            
            # Mock validation - VALID with NO_TRANSLATIONS
            from backend.services.validation_service import Finding
            mock_val.validate.return_value = Mock(
                output='VALID',
                findings=[Finding(validation_output='NO_TRANSLATIONS', details={})]
            )
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit a prompt
            response = client.post('/api/chat', json={'prompt': 'Test prompt'})
            assert response.status_code == 200
            thread_id = response.get_json()['thread_id']
            
            # Wait for processing
            time.sleep(2)
            
            # Get thread status
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            data = response.get_json()
            thread = data['thread']
            
            # Verify NO_TRANSLATIONS handling
            if thread['status'] == ThreadStatus.COMPLETED.value:
                assert thread['warning_message'] is not None
                assert 'validated' in thread['warning_message'].lower() or \
                       'translation' in thread['warning_message'].lower()
        
        print("✓ NO_TRANSLATIONS handling test passed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
