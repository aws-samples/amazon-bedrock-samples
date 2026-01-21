"""
Tests for persistent clarification tracking across rewriting iterations.
"""
import pytest
from unittest.mock import Mock, MagicMock

from backend.models.thread import (
    Thread, ThreadStatus, Finding, QuestionAnswerExchange,
    TypedIteration, IterationType, ClarificationIterationData, ARIterationData
)
from backend.services.thread_processor import ThreadProcessor, resume_thread_with_answers
from backend.services.thread_manager import ThreadManager
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService, ValidationResult
from backend.services.audit_logger import AuditLogger
from backend.services.prompt_template_manager import PromptTemplateManager


class TestAllClarificationsTracking:
    """Test that clarifications are tracked and included in all future rewriting prompts."""
    
    def test_clarifications_added_to_thread_list(self):
        """Test that answered clarifications are added to thread.all_clarifications."""
        # Create a thread with a clarification iteration
        thread = Thread(
            thread_id="test-123",
            user_prompt="Test prompt",
            model_id="test-model",
            status=ThreadStatus.AWAITING_USER_INPUT,
            iteration_counter=1,
            all_clarifications=[]
        )
        
        qa_exchange = QuestionAnswerExchange(
            questions=["Question 1?", "Question 2?"],
            answers=None,
            skipped=False
        )
        
        clar_iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer="Original response",
            rewritten_answer="",
            rewriting_prompt="",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange,
                context_augmentation=None
            )
        )
        
        thread.iterations.append(clar_iteration)
        
        # Mock services
        thread_manager = Mock(spec=ThreadManager)
        thread_manager.get_thread.return_value = thread
        thread_manager.update_thread_status = Mock()
        
        llm_service = Mock(spec=LLMService)
        llm_service.generate_response.return_value = "New response"
        
        validation_service = Mock(spec=ValidationService)
        validation_service.validate.return_value = ValidationResult(
            output="VALID",
            findings=[]
        )
        
        audit_logger = Mock(spec=AuditLogger)
        
        # Resume with answers
        answers = ["Answer 1", "Answer 2"]
        resume_thread_with_answers(
            "test-123",
            answers,
            False,
            thread_manager,
            llm_service,
            validation_service,
            audit_logger
        )
        
        # Verify clarification was added to all_clarifications
        assert len(thread.all_clarifications) == 1
        assert thread.all_clarifications[0].questions == ["Question 1?", "Question 2?"]
        assert thread.all_clarifications[0].answers == ["Answer 1", "Answer 2"]
        assert thread.all_clarifications[0].skipped is False
    
    def test_skipped_clarifications_not_added_to_list(self):
        """Test that skipped clarifications are NOT added to thread.all_clarifications."""
        # Create a thread with a clarification iteration
        thread = Thread(
            thread_id="test-123",
            user_prompt="Test prompt",
            model_id="test-model",
            status=ThreadStatus.AWAITING_USER_INPUT,
            iteration_counter=1,
            all_clarifications=[]
        )
        
        qa_exchange = QuestionAnswerExchange(
            questions=["Question 1?"],
            answers=None,
            skipped=False
        )
        
        clar_iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer="Original response",
            rewritten_answer="",
            rewriting_prompt="",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange,
                context_augmentation=None
            )
        )
        
        thread.iterations.append(clar_iteration)
        
        # Mock services
        thread_manager = Mock(spec=ThreadManager)
        thread_manager.get_thread.return_value = thread
        thread_manager.update_thread_status = Mock()
        
        llm_service = Mock(spec=LLMService)
        llm_service.generate_response.return_value = "New response"
        
        validation_service = Mock(spec=ValidationService)
        validation_service.validate.return_value = ValidationResult(
            output="VALID",
            findings=[]
        )
        
        audit_logger = Mock(spec=AuditLogger)
        
        # Resume with skip
        resume_thread_with_answers(
            "test-123",
            [],
            True,  # skipped
            thread_manager,
            llm_service,
            validation_service,
            audit_logger
        )
        
        # Verify clarification was NOT added to all_clarifications
        assert len(thread.all_clarifications) == 0
    
    def test_llm_service_receives_all_clarifications(self):
        """Test that LLM service's generate_rewriting_prompt receives all clarifications."""
        # Create mock clarifications
        qa1 = QuestionAnswerExchange(
            questions=["First question?"],
            answers=["First answer"],
            skipped=False
        )
        qa2 = QuestionAnswerExchange(
            questions=["Second question?"],
            answers=["Second answer"],
            skipped=False
        )
        
        all_clarifications = [qa1, qa2]
        
        # Create mock LLM service
        llm_service = Mock(spec=LLMService)
        llm_service.generate_rewriting_prompt = Mock(return_value="Rewriting prompt")
        
        # Call generate_rewriting_prompt with all_clarifications
        findings = [Finding(validation_output="INVALID", details={})]
        llm_service.generate_rewriting_prompt(
            findings=findings,
            original_prompt="Test prompt",
            original_response="Test response",
            all_clarifications=all_clarifications
        )
        
        # Verify it was called with all_clarifications
        llm_service.generate_rewriting_prompt.assert_called_once()
        call_kwargs = llm_service.generate_rewriting_prompt.call_args[1]
        assert 'all_clarifications' in call_kwargs
        assert call_kwargs['all_clarifications'] == all_clarifications
    
    def test_multiple_clarifications_formatted_correctly(self):
        """Test that multiple clarifications are formatted with round numbers."""
        template_manager = PromptTemplateManager()
        
        qa1 = QuestionAnswerExchange(
            questions=["Question 1?"],
            answers=["Answer 1"],
            skipped=False
        )
        qa2 = QuestionAnswerExchange(
            questions=["Question 2?"],
            answers=["Answer 2"],
            skipped=False
        )
        
        all_clarifications = [qa1, qa2]
        
        context = template_manager.create_all_clarifications_context(all_clarifications)
        
        # Verify format includes round numbers
        assert "**Previous Clarifications:**" in context
        assert "Clarification Round 1:" in context
        assert "Clarification Round 2:" in context
        assert "Q: Question 1?" in context
        assert "A: Answer 1" in context
        assert "Q: Question 2?" in context
        assert "A: Answer 2" in context
    
    def test_single_clarification_no_round_number(self):
        """Test that single clarification doesn't include round number."""
        template_manager = PromptTemplateManager()
        
        qa1 = QuestionAnswerExchange(
            questions=["Question 1?"],
            answers=["Answer 1"],
            skipped=False
        )
        
        all_clarifications = [qa1]
        
        context = template_manager.create_all_clarifications_context(all_clarifications)
        
        # Verify format doesn't include round number for single clarification
        assert "**Previous Clarifications:**" in context
        assert "Clarification Round" not in context
        assert "Q: Question 1?" in context
        assert "A: Answer 1" in context
    
    def test_thread_serialization_includes_all_clarifications(self):
        """Test that thread serialization includes all_clarifications field."""
        qa1 = QuestionAnswerExchange(
            questions=["Question 1?"],
            answers=["Answer 1"],
            skipped=False
        )
        
        thread = Thread(
            thread_id="test-123",
            user_prompt="Test prompt",
            model_id="test-model",
            status=ThreadStatus.PROCESSING,
            all_clarifications=[qa1]
        )
        
        # Serialize to dict
        thread_dict = thread.to_dict()
        
        # Verify all_clarifications is in the dict
        assert "all_clarifications" in thread_dict
        assert len(thread_dict["all_clarifications"]) == 1
        assert thread_dict["all_clarifications"][0]["questions"] == ["Question 1?"]
        assert thread_dict["all_clarifications"][0]["answers"] == ["Answer 1"]
    
    def test_thread_deserialization_includes_all_clarifications(self):
        """Test that thread deserialization restores all_clarifications field."""
        thread_dict = {
            "thread_id": "test-123",
            "user_prompt": "Test prompt",
            "model_id": "test-model",
            "status": "PROCESSING",
            "schema_version": "2.0",
            "iteration_counter": 0,
            "max_iterations": 5,
            "processed_finding_indices": [],
            "current_findings": [],
            "iterations": [],
            "all_clarifications": [
                {
                    "questions": ["Question 1?"],
                    "answers": ["Answer 1"],
                    "skipped": False
                }
            ],
            "created_at": "2024-01-01T00:00:00+00:00"
        }
        
        # Deserialize from dict
        thread = Thread.from_dict(thread_dict)
        
        # Verify all_clarifications is restored
        assert len(thread.all_clarifications) == 1
        assert thread.all_clarifications[0].questions == ["Question 1?"]
        assert thread.all_clarifications[0].answers == ["Answer 1"]
        assert thread.all_clarifications[0].skipped is False
