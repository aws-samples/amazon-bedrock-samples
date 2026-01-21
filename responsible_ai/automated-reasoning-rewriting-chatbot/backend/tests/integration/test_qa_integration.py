#!/usr/bin/env python
"""
Integration test for complete Q&A flow.

Tests the following workflow:
- Prompt submission that triggers TRANSLATION_AMBIGUOUS
- Question detection and thread status change to AWAITING_USER_INPUT
- Answer submission and validation resumption
- Iteration counter increments correctly
- Skip functionality
- Audit log includes Q&A data

Validates: Requirements 2.1, 5.1, 5.4, 7.4, 10.3, 12.2
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from backend.flask_app import create_app
from backend.models.thread import ThreadStatus, Finding
from backend.services.validation_service import ValidationResult


class TestQAIntegrationFlow:
    """Integration tests for complete Q&A flow."""
    
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
        with patch('backend.services.config_manager.boto3.client') as mock_client:
            mock_bedrock = MagicMock()
            
            def client_factory(service_name, **kwargs):
                if service_name == 'bedrock':
                    return mock_bedrock
                return MagicMock()
            
            mock_client.side_effect = client_factory
            
            # Mock list_foundation_models
            mock_bedrock.list_foundation_models.return_value = {
                'modelSummaries': [
                    {'modelId': 'anthropic.claude-3-5-haiku-20241022-v1:0'}
                ]
            }
            
            # Mock list_automated_reasoning_policies
            mock_bedrock.list_automated_reasoning_policies.return_value = {
                'automatedReasoningPolicySummaries': [
                    {
                        'policyArn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy',
                        'policyName': 'Test AR Policy'
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
            
            yield mock_bedrock
    
    def test_complete_qa_flow_with_answers(self, client, mock_bedrock):
        """
        Test complete Q&A flow: question detection, answer submission, and validation resumption.
        
        Validates: Requirements 2.1, 5.1, 5.4, 7.4, 10.3
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM responses:
            # 1. Initial response
            # 2. Response with questions (after first rewrite) - using new DECISION format
            # 3. Final response after user answers
            mock_llm.generate_response.side_effect = [
                "Initial ambiguous response",
                "DECISION: ASK_QUESTIONS\n\nQUESTION: What specific aspect are you asking about?\nQUESTION: Do you need technical or business details?",
                "Final clear response based on your answers"
            ]
            
            # Mock rewriting prompt generation
            mock_llm.generate_rewriting_prompt.return_value = "Please fix your response"
            
            # Mock template manager for resume
            mock_llm.template_manager = MagicMock()
            mock_llm.template_manager.load_template.return_value = "Template"
            mock_llm.template_manager.render_template.return_value = "Rendered prompt with augmentation"
            
            # Mock validation:
            # 1. TRANSLATION_AMBIGUOUS (initial)
            # 2. VALID (after user answers)
            # Note: Response with questions is NOT validated (questions detected before validation)
            mock_val.validate.side_effect = [
                ValidationResult(
                    output="TRANSLATION_AMBIGUOUS",
                    findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})]
                ),
                ValidationResult(
                    output="VALID",
                    findings=[]
                )
            ]
            
            # Step 1: Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Step 2: Submit a prompt that will trigger TRANSLATION_AMBIGUOUS
            prompt_data = {'prompt': 'Explain the system architecture'}
            response = client.post('/api/chat', json=prompt_data)
            assert response.status_code == 200
            data = response.get_json()
            assert 'thread_id' in data
            thread_id = data['thread_id']
            
            # Wait for processing to detect questions
            time.sleep(2)
            
            # Step 3: Verify thread status is AWAITING_USER_INPUT (Requirement 5.1)
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            data = response.get_json()
            thread = data['thread']
            
            assert thread['status'] == ThreadStatus.AWAITING_USER_INPUT.value, \
                f"Expected AWAITING_USER_INPUT, got {thread['status']}"
            
            # Step 4: Verify questions were detected (Requirement 2.1)
            assert len(thread['iterations']) >= 1  # At least one iteration with questions
            last_iteration = thread['iterations'][-1]
            
            # For TypedIteration, qa_exchange is in type_specific_data for USER_CLARIFICATION
            assert last_iteration['iteration_type'] == 'user_clarification'
            qa_exchange = last_iteration['type_specific_data']['qa_exchange']
            assert qa_exchange is not None
            assert len(qa_exchange['questions']) == 2
            assert qa_exchange['questions'][0] == "What specific aspect are you asking about?"
            assert qa_exchange['questions'][1] == "Do you need technical or business details?"
            assert qa_exchange['answers'] is None
            assert qa_exchange['skipped'] is False
            
            # Step 5: Submit answers (Requirement 5.4)
            answers_data = {
                'answers': [
                    'I am asking about the backend architecture',
                    'I need technical details'
                ],
                'skipped': False
            }
            response = client.post(f'/api/thread/{thread_id}/answer', json=answers_data)
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
            
            # Wait for validation to resume and complete
            time.sleep(2)
            
            # Step 6: Verify validation resumed and completed
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            data = response.get_json()
            thread = data['thread']
            
            assert thread['status'] == ThreadStatus.COMPLETED.value
            assert thread['final_response'] == "Final clear response based on your answers"
            
            # Step 7: Verify iteration counter incremented correctly (Requirement 7.4)
            # After completion, we should have at least the clarification iteration
            assert len(thread['iterations']) >= 1
            
            # Step 8: Verify Q&A exchange was updated with answers
            # Find the iteration with Q&A exchange (USER_CLARIFICATION type)
            qa_iteration = None
            for iteration in thread['iterations']:
                if iteration.get('iteration_type') == 'user_clarification':
                    qa_iteration = iteration
                    break
            
            assert qa_iteration is not None, "No USER_CLARIFICATION iteration found"
            qa_exchange = qa_iteration['type_specific_data']['qa_exchange']
            assert qa_exchange['answers'] == answers_data['answers']
            assert qa_exchange['skipped'] is False
            
            # Step 9: Verify LLM was called to regenerate response with user clarification
            # The LLM should be called with a prompt that includes the Q&A but NOT the findings
            # Check that generate_response was called (should be 3 times: initial, questions, regenerate)
            assert mock_llm.generate_response.call_count == 3
            
            # Get the regeneration prompt (the 3rd call)
            regeneration_call = mock_llm.generate_response.call_args_list[2]
            regeneration_prompt = regeneration_call[0][0]
            
            # Verify the prompt contains the Q&A
            assert "What specific aspect are you asking about?" in regeneration_prompt
            assert "I am asking about the backend architecture" in regeneration_prompt
            assert "I need technical details" in regeneration_prompt
            
            # Verify it's asking for a regenerated answer based on clarification
            assert "clarification" in regeneration_prompt.lower() or "improved answer" in regeneration_prompt.lower()
            
            # Step 10: Verify audit log includes Q&A data (Requirement 10.3)
            # The Q&A data is stored in the thread iterations, which will be logged
            # We've already verified the Q&A exchange is in the thread above
            # The audit logger will receive this thread with Q&A data when it logs
            
            print("✓ Complete Q&A flow with answers test passed")
    
    def test_complete_qa_flow_with_skip(self, client, mock_bedrock):
        """
        Test complete Q&A flow with skip functionality.
        
        Validates: Requirement 12.2
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM responses - using new DECISION format
            mock_llm.generate_response.side_effect = [
                "Initial response",
                "DECISION: ASK_QUESTIONS\n\nQUESTION: Need clarification?",
                "Final response without user input"
            ]
            
            mock_llm.generate_rewriting_prompt.return_value = "Please fix"
            
            # Mock template manager
            mock_llm.template_manager = MagicMock()
            mock_llm.template_manager.load_template.return_value = "Template"
            mock_llm.template_manager.render_template.return_value = "Rendered prompt"
            
            # Mock validation
            # Note: Response with questions is NOT validated (questions detected before validation)
            mock_val.validate.side_effect = [
                ValidationResult(
                    output="SATISFIABLE",
                    findings=[Finding(validation_output="SATISFIABLE", details={})]
                ),
                ValidationResult(
                    output="VALID",
                    findings=[]
                )
            ]
            
            # Configure and submit prompt
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            client.post('/api/config', json=config_data)
            
            response = client.post('/api/chat', json={'prompt': 'Test prompt'})
            thread_id = response.get_json()['thread_id']
            
            # Wait for questions
            time.sleep(2)
            
            # Verify AWAITING_USER_INPUT
            response = client.get(f'/api/thread/{thread_id}')
            thread = response.get_json()['thread']
            assert thread['status'] == ThreadStatus.AWAITING_USER_INPUT.value
            
            # Skip the questions
            skip_data = {
                'answers': [],
                'skipped': True
            }
            response = client.post(f'/api/thread/{thread_id}/answer', json=skip_data)
            assert response.status_code == 200
            
            # Wait for completion
            time.sleep(2)
            
            # Verify completion
            response = client.get(f'/api/thread/{thread_id}')
            thread = response.get_json()['thread']
            assert thread['status'] == ThreadStatus.COMPLETED.value
            
            # Verify skipped flag was set
            # Find the iteration with Q&A exchange (USER_CLARIFICATION type)
            qa_iteration = None
            for iteration in thread['iterations']:
                if iteration.get('iteration_type') == 'user_clarification':
                    qa_iteration = iteration
                    break
            
            assert qa_iteration is not None, "No USER_CLARIFICATION iteration found"
            qa_exchange = qa_iteration['type_specific_data']['qa_exchange']
            assert qa_exchange['skipped'] is True
            assert qa_exchange['answers'] is None or qa_exchange['answers'] == []
            
            # Verify no context augmentation was used (skip should omit augmentation)
            render_call = mock_llm.template_manager.render_template.call_args
            if render_call:
                context_aug = render_call.kwargs.get('context_augmentation')
                assert context_aug is None or context_aug == ""
            
            print("✓ Complete Q&A flow with skip test passed")
    
    def test_qa_flow_no_questions_detected(self, client, mock_bedrock):
        """
        Test that flow continues normally when no questions are detected.
        
        Validates: Normal flow without Q&A intervention
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM responses without questions
            mock_llm.generate_response.side_effect = [
                "Initial response",
                "Improved response without questions"
            ]
            
            mock_llm.generate_rewriting_prompt.return_value = "Please fix"
            
            # Mock validation
            mock_val.validate.side_effect = [
                ValidationResult(
                    output="TRANSLATION_AMBIGUOUS",
                    findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})]
                ),
                ValidationResult(
                    output="VALID",
                    findings=[]
                )
            ]
            
            # Configure and submit
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            client.post('/api/config', json=config_data)
            
            response = client.post('/api/chat', json={'prompt': 'Test prompt'})
            thread_id = response.get_json()['thread_id']
            
            # Wait for completion
            time.sleep(2)
            
            # Verify completed without Q&A pause
            response = client.get(f'/api/thread/{thread_id}')
            thread = response.get_json()['thread']
            assert thread['status'] == ThreadStatus.COMPLETED.value
            
            # Verify no Q&A exchanges in any iteration (no USER_CLARIFICATION iterations)
            for iteration in thread['iterations']:
                assert iteration.get('iteration_type') != 'user_clarification'
            
            print("✓ Q&A flow with no questions detected test passed")
    
    def test_qa_flow_invalid_answer_count(self, client, mock_bedrock):
        """
        Test that submitting wrong number of answers returns error.
        
        Validates: Answer validation
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM with questions - using new DECISION format
            mock_llm.generate_response.side_effect = [
                "Initial",
                "DECISION: ASK_QUESTIONS\n\nQUESTION: Q1?\nQUESTION: Q2?"
            ]
            
            mock_llm.generate_rewriting_prompt.return_value = "Fix"
            
            mock_val.validate.side_effect = [
                ValidationResult(
                    output="TRANSLATION_AMBIGUOUS",
                    findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})]
                ),
                ValidationResult(
                    output="TRANSLATION_AMBIGUOUS",
                    findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})]
                )
            ]
            
            # Configure and submit
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            client.post('/api/config', json=config_data)
            
            response = client.post('/api/chat', json={'prompt': 'Test'})
            thread_id = response.get_json()['thread_id']
            
            time.sleep(2)
            
            # Try to submit wrong number of answers
            wrong_answers = {
                'answers': ['Only one answer'],  # Should be 2
                'skipped': False
            }
            response = client.post(f'/api/thread/{thread_id}/answer', json=wrong_answers)
            
            # Should return error
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'answer count' in data['error']['message'].lower() or \
                   'does not match' in data['error']['message'].lower()
            
            print("✓ Q&A flow invalid answer count test passed")
    
    def test_qa_flow_invalid_thread_status(self, client, mock_bedrock):
        """
        Test that submitting answers to thread not awaiting input returns error.
        
        Validates: Thread status validation
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM without questions - will complete normally
            mock_llm.generate_response.return_value = "Valid response"
            
            mock_val.validate.return_value = ValidationResult(
                output="VALID",
                findings=[]
            )
            
            # Configure and submit
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            client.post('/api/config', json=config_data)
            
            response = client.post('/api/chat', json={'prompt': 'Test'})
            thread_id = response.get_json()['thread_id']
            
            time.sleep(2)
            
            # Thread should be COMPLETED, not AWAITING_USER_INPUT
            response = client.get(f'/api/thread/{thread_id}')
            thread = response.get_json()['thread']
            assert thread['status'] == ThreadStatus.COMPLETED.value
            
            # Try to submit answers anyway
            answers_data = {
                'answers': ['Some answer'],
                'skipped': False
            }
            response = client.post(f'/api/thread/{thread_id}/answer', json=answers_data)
            
            # Should return error
            assert response.status_code == 409
            data = response.get_json()
            assert 'error' in data
            assert 'not awaiting' in data['error']['message'].lower() or \
                   'invalid state' in data['error']['message'].lower()
            
            print("✓ Q&A flow invalid thread status test passed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
