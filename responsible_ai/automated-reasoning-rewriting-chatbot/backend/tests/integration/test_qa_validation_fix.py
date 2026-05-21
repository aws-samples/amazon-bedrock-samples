#!/usr/bin/env python
"""
Test to verify that after Q&A, the validated answer is returned as final response.

This test verifies the fix for the issue where the system was returning the original
answer instead of the rewritten answer after user clarification.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.flask_app import create_app
from backend.models.thread import ThreadStatus, Finding
from backend.services.validation_service import ValidationResult


class TestQAValidationFix:
    """Test that Q&A flow returns the validated rewritten answer."""
    
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
            
            mock_bedrock.list_foundation_models.return_value = {
                'modelSummaries': [
                    {'modelId': 'anthropic.claude-3-5-haiku-20241022-v1:0'}
                ]
            }
            
            mock_bedrock.list_automated_reasoning_policies.return_value = {
                'automatedReasoningPolicySummaries': [
                    {
                        'policyArn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy',
                        'policyName': 'Test AR Policy'
                    }
                ]
            }
            
            mock_bedrock.list_guardrails.return_value = {
                'guardrails': []
            }
            
            mock_bedrock.create_guardrail.return_value = {
                'guardrailId': 'test-guardrail-id',
                'version': 'DRAFT'
            }
            
            yield mock_bedrock
    
    def test_qa_returns_validated_rewritten_answer(self, client, mock_bedrock):
        """
        Test that after Q&A, the system returns the validated rewritten answer as final response.
        
        Flow:
        1. Initial answer is TRANSLATION_AMBIGUOUS
        2. LLM asks questions
        3. User provides answers
        4. LLM generates new answer based on clarification
        5. New answer is VALID
        6. System should return the NEW answer (not the original)
        """
        mock_llm = MagicMock()
        mock_val = MagicMock()
        
        with patch('backend.flask_app.service_container.get_llm_service', return_value=mock_llm), \
             patch('backend.flask_app.service_container.get_validation_service', return_value=mock_val), \
             patch('backend.flask_app.config_manager.ensure_guardrail') as mock_ensure:
            
            mock_ensure.return_value = ('test-guardrail-id', 'DRAFT')
            
            # Mock LLM responses:
            # 1. Initial ambiguous response
            # 2. Response with questions (using DECISION format)
            # 3. Final clear response after user answers
            mock_llm.generate_response.side_effect = [
                "Initial ambiguous response",
                "DECISION: ASK_QUESTIONS\n\nQUESTION: What do you mean by X?",
                "Final clear response based on your clarification"
            ]
            
            mock_llm.generate_rewriting_prompt.return_value = "Please fix your response"
            
            # Mock template manager for resume
            mock_llm.template_manager = MagicMock()
            mock_llm.template_manager.load_template.return_value = "Template"
            mock_llm.template_manager.render_template.return_value = "Rendered prompt"
            
            # Mock validation:
            # 1. TRANSLATION_AMBIGUOUS (initial)
            # 2. VALID (after user answers)
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
            
            # Configure the app
            config_data = {
                'model_id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'policy_arn': 'arn:aws:bedrock:us-west-2:123456789012:policy/test-policy'
            }
            response = client.post('/api/config', json=config_data)
            assert response.status_code == 200
            
            # Submit a prompt
            prompt_data = {'prompt': 'Test question'}
            response = client.post('/api/chat', json=prompt_data)
            assert response.status_code == 200
            thread_id = response.get_json()['thread_id']
            
            # Verify AWAITING_USER_INPUT (processing is synchronous in test mode)
            response = client.get(f'/api/thread/{thread_id}')
            thread = response.get_json()['thread']
            assert thread['status'] == ThreadStatus.AWAITING_USER_INPUT.value
            
            # Submit answers
            answers_data = {
                'answers': ['I mean Y'],
                'skipped': False
            }
            response = client.post(f'/api/thread/{thread_id}/answer', json=answers_data)
            assert response.status_code == 200
            
            # Verify completion (processing is synchronous in test mode)
            response = client.get(f'/api/thread/{thread_id}')
            thread = response.get_json()['thread']
            
            # CRITICAL ASSERTION: The final response should be the NEW answer, not the original
            assert thread['status'] == ThreadStatus.COMPLETED.value
            assert thread['final_response'] == "Final clear response based on your clarification"
            assert thread['final_response'] != "Initial ambiguous response"
            
            print("✓ Q&A validation fix test passed - returns validated rewritten answer")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
