#!/usr/bin/env python
"""
Integration tests for the rewriting loop fix.

Tests the following workflows:
- Complete flow from initial answer to VALID with multiple findings
- Processing multiple findings in sequence
- LLM asking questions during rewriting loop
- User providing answers and continued processing
- Max iterations termination

Validates: Requirements from rewriting-loop-fix spec
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.flask_app import create_app
from backend.models.thread import ThreadStatus, Finding
from backend.services.validation_service import ValidationResult


class TestRewritingLoopIntegration:
    """Integration tests for rewriting loop fix."""
    
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
    
    def test_full_loop_multiple_findings(self, client, mock_bedrock):
        """
        Test complete flow from initial answer to VALID with multiple findings processed in sequence.
        
        **Property 1: Finding priority sorting**
        **Property 2: One finding per iteration**
        **Property 3: Highest priority unprocessed finding selection**
        **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3**
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM responses:
            # 1. Initial response
            # 2. Response after fixing AMBIGUOUS finding
            # 3. Response after fixing INVALID finding
            mock_llm.generate_response.side_effect = [
                "Initial ambiguous response",
                "DECISION: REWRITE\nANSWER: Fixed ambiguous response",
                "DECISION: REWRITE\nANSWER: Final valid response"
            ]
            
            # Mock rewriting prompt generation
            mock_llm.generate_rewriting_prompt.return_value = "Please fix your response"
            
            # Mock validation:
            # 1. Initial: AMBIGUOUS + INVALID (multiple findings)
            # 2. After fixing AMBIGUOUS: INVALID (one finding remains)
            # 3. After fixing INVALID: VALID
            mock_val.validate.side_effect = [
                ValidationResult(
                    output="TRANSLATION_AMBIGUOUS",
                    findings=[
                        Finding(validation_output="TRANSLATION_AMBIGUOUS", details={"message": "Ambiguous input"}),
                        Finding(validation_output="INVALID", details={"message": "Invalid claim"})
                    ]
                ),
                ValidationResult(
                    output="INVALID",
                    findings=[
                        Finding(validation_output="INVALID", details={"message": "Invalid claim"})
                    ]
                ),
                ValidationResult(
                    output="VALID",
                    findings=[]
                )
            ]
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit a prompt
            prompt_data = {'prompt': 'Test question requiring multiple rewrites'}
            response = client.post('/api/chat', json=prompt_data)
            assert response.status_code == 200
            data = response.get_json()
            assert 'thread_id' in data
            thread_id = data['thread_id']
            
            # Verify thread completed successfully (processing is synchronous in test mode)
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            data = response.get_json()
            thread = data['thread']
            
            assert thread['status'] == ThreadStatus.COMPLETED.value
            assert thread['final_response'] == "Final valid response"
            
            # Verify iterations processed findings in priority order
            # Should have: iteration 0 (initial) + 2 rewriting iterations
            assert len(thread['iterations']) == 3
            
            # Iteration 0 is the initial answer
            initial_iter = thread['iterations'][0]
            assert initial_iter['iteration_type'] == 'ar_feedback'
            assert initial_iter['type_specific_data']['llm_decision'] == 'INITIAL'
            
            # First rewrite iteration should process AMBIGUOUS (higher priority)
            first_iter = thread['iterations'][1]
            assert first_iter['iteration_type'] == 'ar_feedback'
            assert first_iter['type_specific_data']['processed_finding_index'] == 0
            assert first_iter['type_specific_data']['llm_decision'] == 'REWRITE'
            
            # Second rewrite iteration should process INVALID
            second_iter = thread['iterations'][2]
            assert second_iter['iteration_type'] == 'ar_feedback'
            assert second_iter['type_specific_data']['llm_decision'] == 'REWRITE'
            
            # Verify LLM was called 3 times (initial + 2 rewrites)
            assert mock_llm.generate_response.call_count == 3
            
            # Verify validation was called 3 times
            assert mock_val.validate.call_count == 3
            
            print("✓ Full loop with multiple findings test passed")
    
    def test_question_flow_during_rewriting(self, client, mock_bedrock):
        """
        Test LLM asking questions during rewriting loop and user providing answers.
        
        **Property 4: Options match finding type**
        **Property 5: Validation after decisions**
        **Property 6: Loop continuation after decisions**
        **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock template manager for resume
            mock_llm.template_manager = MagicMock()
            mock_llm.template_manager.load_template.return_value = "Template"
            mock_llm.template_manager.render_template.return_value = "Rendered prompt"
            
            # Mock LLM responses:
            # 1. Initial response
            # 2. Response with ASK_QUESTIONS decision
            # 3. Response after user answers
            mock_llm.generate_response.side_effect = [
                "Initial response",
                "DECISION: ASK_QUESTIONS\nQUESTION: What do you mean by X?\nQUESTION: Should I consider Y?",
                "Final response based on clarification"
            ]
            
            # Mock rewriting prompt generation
            mock_llm.generate_rewriting_prompt.return_value = "Please fix your response"
            
            # Mock validation:
            # 1. Initial: SATISFIABLE (allows questions)
            # 2. After user answers: VALID
            mock_val.validate.side_effect = [
                ValidationResult(
                    output="SATISFIABLE",
                    findings=[
                        Finding(validation_output="SATISFIABLE", details={"message": "Could be true or false"})
                    ]
                ),
                ValidationResult(
                    output="VALID",
                    findings=[]
                )
            ]
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit a prompt
            prompt_data = {'prompt': 'Test question that triggers questions'}
            response = client.post('/api/chat', json=prompt_data)
            assert response.status_code == 200
            thread_id = response.get_json()['thread_id']
            
            # Verify thread status is AWAITING_USER_INPUT (processing is synchronous in test mode)
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            thread = response.get_json()['thread']
            
            assert thread['status'] == ThreadStatus.AWAITING_USER_INPUT.value
            
            # Verify questions were detected
            # Should have: iteration 0 (initial) + 1 clarification iteration
            assert len(thread['iterations']) == 2
            last_iteration = thread['iterations'][-1]
            assert last_iteration['iteration_type'] == 'user_clarification'
            assert last_iteration['type_specific_data']['qa_exchange'] is not None
            assert len(last_iteration['type_specific_data']['qa_exchange']['questions']) == 2
            assert last_iteration['type_specific_data']['llm_decision'] == 'ASK_QUESTIONS'
            
            # Submit answers
            answers_data = {
                'answers': [
                    'X means this specific thing',
                    'Yes, please consider Y'
                ],
                'skipped': False
            }
            response = client.post(f'/api/thread/{thread_id}/answer', json=answers_data)
            assert response.status_code == 200
            
            # Verify validation resumed and completed (processing is synchronous in test mode)
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            thread = response.get_json()['thread']
            
            assert thread['status'] == ThreadStatus.COMPLETED.value
            assert thread['final_response'] == "Final response based on clarification"
            
            # Verify Q&A exchange was updated with answers
            # Iteration 0 is initial, iteration 1 is the clarification
            qa_iteration = thread['iterations'][1]
            assert qa_iteration['type_specific_data']['qa_exchange']['answers'] == answers_data['answers']
            assert qa_iteration['type_specific_data']['qa_exchange']['skipped'] is False
            
            # Verify finding was marked as processed
            assert qa_iteration['type_specific_data']['processed_finding_index'] == 0
            
            print("✓ Question flow during rewriting test passed")

    
    def test_max_iterations_termination(self, client, mock_bedrock):
        """
        Test that system terminates at max iterations with warning message.
        
        **Property 7: Iteration type correctness**
        **Property 8: Max iteration termination**
        **Validates: Requirements 7.1, 7.2, 7.3**
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM responses - always rewrite
            mock_llm.generate_response.side_effect = [
                "Initial response",
                "DECISION: REWRITE\nANSWER: Rewrite 1",
                "DECISION: REWRITE\nANSWER: Rewrite 2",
                "DECISION: REWRITE\nANSWER: Rewrite 3",
                "DECISION: REWRITE\nANSWER: Rewrite 4",
                "DECISION: REWRITE\nANSWER: Rewrite 5"
            ]
            
            # Mock rewriting prompt generation
            mock_llm.generate_rewriting_prompt.return_value = "Please fix your response"
            
            # Mock validation - always return INVALID to force max iterations
            mock_val.validate.side_effect = [
                ValidationResult(
                    output="INVALID",
                    findings=[Finding(validation_output="INVALID", details={"message": "Invalid"})]
                ),
                ValidationResult(
                    output="INVALID",
                    findings=[Finding(validation_output="INVALID", details={"message": "Invalid"})]
                ),
                ValidationResult(
                    output="INVALID",
                    findings=[Finding(validation_output="INVALID", details={"message": "Invalid"})]
                ),
                ValidationResult(
                    output="INVALID",
                    findings=[Finding(validation_output="INVALID", details={"message": "Invalid"})]
                ),
                ValidationResult(
                    output="INVALID",
                    findings=[Finding(validation_output="INVALID", details={"message": "Invalid"})]
                ),
                ValidationResult(
                    output="INVALID",
                    findings=[Finding(validation_output="INVALID", details={"message": "Invalid"})]
                )
            ]
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit a prompt
            prompt_data = {'prompt': 'Test question that never validates'}
            response = client.post('/api/chat', json=prompt_data)
            assert response.status_code == 200
            thread_id = response.get_json()['thread_id']
            
            # Verify thread completed with max iterations warning (processing is synchronous in test mode)
            response = client.get(f'/api/thread/{thread_id}')
            assert response.status_code == 200
            thread = response.get_json()['thread']
            
            assert thread['status'] == ThreadStatus.COMPLETED.value
            
            # Verify warning message is present
            assert thread['warning_message'] is not None
            assert 'iteration limit' in thread['warning_message'].lower() or \
                   'maximum' in thread['warning_message'].lower()
            
            # Verify exactly 5 iterations (iteration 0 + 4 rewrites before hitting max)
            # Counter starts at 1 after iteration 0, so we get iterations 0,2,3,4,5 before hitting limit
            assert len(thread['iterations']) == 5
            
            # Verify all iterations are ar_feedback type
            for i, iteration in enumerate(thread['iterations']):
                assert iteration['iteration_type'] == 'ar_feedback'
                # First iteration is INITIAL, rest are REWRITE
                if i == 0:
                    assert iteration['type_specific_data']['llm_decision'] == 'INITIAL'
                else:
                    assert iteration['type_specific_data']['llm_decision'] == 'REWRITE'
            
            # Verify iteration numbers are correct
            # Should be: 0 (initial), then 2, 3, 4, 5 (counter starts at 1, increments to 2,3,4,5)
            expected_numbers = [0, 2, 3, 4, 5]
            for i, iteration in enumerate(thread['iterations']):
                assert iteration['iteration_number'] == expected_numbers[i]
            
            print("✓ Max iterations termination test passed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
