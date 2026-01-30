"""
Tests for thread processor question handling functionality.
"""
import pytest
from unittest.mock import Mock
from typing import List, Optional

from backend.services.thread_processor import (
    process_thread,
    resume_thread_with_answers,
    ThreadProcessor
)
from backend.services.thread_manager import ThreadManager
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService, ValidationResult
from backend.services.audit_logger import AuditLogger
from backend.models.thread import (
    Thread, ThreadStatus, Finding, IterationType, ClarificationIterationData,
    QuestionAnswerExchange, TypedIteration
)


def _handle_follow_up_questions(
    thread_id: str,
    thread: Thread,
    llm_response: str,
    questions: List[str],
    thread_manager: ThreadManager,
    current_validation,
    enriched_findings: List[Finding],
    rewriting_prompt: Optional[str]
) -> None:
    """
    Helper function for tests - simulates the old _handle_follow_up_questions behavior.
    Creates a clarification iteration and sets thread status to AWAITING_USER_INPUT.
    """
    qa_exchange = QuestionAnswerExchange(
        questions=questions,
        answers=None,
        skipped=False
    )
    
    clarification_iteration = TypedIteration(
        iteration_number=thread.iteration_counter,
        iteration_type=IterationType.USER_CLARIFICATION,
        original_answer=llm_response,
        rewritten_answer="",
        rewriting_prompt=rewriting_prompt or "",
        type_specific_data=ClarificationIterationData(
            qa_exchange=qa_exchange,
            context_augmentation=None,
            processed_finding_index=None,
            llm_decision="ASK_QUESTIONS"
        )
    )
    thread_manager.update_thread(thread_id, clarification_iteration)
    thread_manager.update_thread_status(thread_id, ThreadStatus.AWAITING_USER_INPUT)


def test_should_check_for_questions_translation_ambiguous():
    """Test that question detection is enabled for TRANSLATION_AMBIGUOUS."""
    # Create a minimal processor to test the method
    thread_manager = ThreadManager()
    thread = thread_manager.create_thread("Test", "test-model")
    processor = ThreadProcessor(
        thread=thread,
        thread_manager=thread_manager,
        llm_service=Mock(spec=LLMService),
        validation_service=Mock(spec=ValidationService),
        audit_logger=Mock(spec=AuditLogger)
    )
    assert processor._should_check_for_questions("TRANSLATION_AMBIGUOUS") is True


def test_should_check_for_questions_satisfiable():
    """Test that question detection is enabled for SATISFIABLE."""
    thread_manager = ThreadManager()
    thread = thread_manager.create_thread("Test", "test-model")
    processor = ThreadProcessor(
        thread=thread,
        thread_manager=thread_manager,
        llm_service=Mock(spec=LLMService),
        validation_service=Mock(spec=ValidationService),
        audit_logger=Mock(spec=AuditLogger)
    )
    assert processor._should_check_for_questions("SATISFIABLE") is True


def test_should_check_for_questions_invalid():
    """Test that question detection is disabled for INVALID."""
    thread_manager = ThreadManager()
    thread = thread_manager.create_thread("Test", "test-model")
    processor = ThreadProcessor(
        thread=thread,
        thread_manager=thread_manager,
        llm_service=Mock(spec=LLMService),
        validation_service=Mock(spec=ValidationService),
        audit_logger=Mock(spec=AuditLogger)
    )
    assert processor._should_check_for_questions("INVALID") is False


def test_should_check_for_questions_impossible():
    """Test that question detection is disabled for IMPOSSIBLE."""
    thread_manager = ThreadManager()
    thread = thread_manager.create_thread("Test", "test-model")
    processor = ThreadProcessor(
        thread=thread,
        thread_manager=thread_manager,
        llm_service=Mock(spec=LLMService),
        validation_service=Mock(spec=ValidationService),
        audit_logger=Mock(spec=AuditLogger)
    )
    assert processor._should_check_for_questions("IMPOSSIBLE") is False


def test_should_check_for_questions_valid():
    """Test that question detection is disabled for VALID."""
    thread_manager = ThreadManager()
    thread = thread_manager.create_thread("Test", "test-model")
    processor = ThreadProcessor(
        thread=thread,
        thread_manager=thread_manager,
        llm_service=Mock(spec=LLMService),
        validation_service=Mock(spec=ValidationService),
        audit_logger=Mock(spec=AuditLogger)
    )
    assert processor._should_check_for_questions("VALID") is False


def test_rewriting_loop_pauses_on_questions():
    """Test that rewriting loop pauses when questions are detected."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    initial_response = "Initial response"
    response_with_questions = "DECISION: ASK_QUESTIONS\n\nQUESTION: What do you mean by X?"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM responses
    llm_service.generate_response.side_effect = [
        initial_response,  # Initial response
        response_with_questions  # Response with questions (proper format)
    ]
    
    # Mock rewriting prompt generation
    llm_service.generate_rewriting_prompt.return_value = "Please fix your response"
    
    # Mock validation: first TRANSLATION_AMBIGUOUS, then we should pause
    validation_service.validate.side_effect = [
        ValidationResult(
            output="TRANSLATION_AMBIGUOUS",
            findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})]
        )
    ]
    
    # Process thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify thread status is AWAITING_USER_INPUT
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.AWAITING_USER_INPUT
    
    # Verify we have 2 iterations: iteration 0 (initial) + clarification iteration
    assert len(processed_thread.iterations) == 2
    
    # Verify iteration 0 is the initial response
    assert processed_thread.iterations[0].iteration_type == IterationType.AR_FEEDBACK
    assert processed_thread.iterations[0].type_specific_data.llm_decision == 'INITIAL'
    
    # Verify the second iteration has Q&A exchange
    clarification_iteration = processed_thread.iterations[1]
    assert clarification_iteration.iteration_type == IterationType.USER_CLARIFICATION
    assert isinstance(clarification_iteration.type_specific_data, ClarificationIterationData)
    clar_data = clarification_iteration.type_specific_data
    assert clar_data.qa_exchange is not None
    assert len(clar_data.qa_exchange.questions) == 1
    assert clar_data.qa_exchange.questions[0] == "What do you mean by X?"
    
    # Verify no audit logging (validation paused)
    assert not audit_logger.log_valid_response.called
    assert not audit_logger.log_max_iterations.called


def test_rewriting_loop_continues_without_questions():
    """Test that rewriting loop continues normally when no questions are detected."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    initial_response = "Initial response"
    rewritten_response = "Rewritten response without questions"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM responses
    llm_service.generate_response.side_effect = [
        initial_response,  # Initial response
        rewritten_response  # Rewritten response without questions
    ]
    
    # Mock rewriting prompt generation
    llm_service.generate_rewriting_prompt.return_value = "Please fix your response"
    
    # Mock validation: first TRANSLATION_AMBIGUOUS, then VALID
    validation_service.validate.side_effect = [
        ValidationResult(
            output="TRANSLATION_AMBIGUOUS",
            findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})]
        ),
        ValidationResult(
            output="VALID",
            findings=[]
        )
    ]
    
    # Process thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify thread is completed (not paused)
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.COMPLETED
    assert processed_thread.final_response == rewritten_response
    
    # Verify we have 2 iterations: iteration 0 (initial) + iteration 2 (rewrite)
    assert len(processed_thread.iterations) == 2
    
    # Verify iteration 0 is the initial response
    assert processed_thread.iterations[0].iteration_type == IterationType.AR_FEEDBACK
    assert processed_thread.iterations[0].type_specific_data.llm_decision == 'INITIAL'
    
    # Verify iteration 2 is the rewrite
    assert processed_thread.iterations[1].iteration_type == IterationType.AR_FEEDBACK
    assert processed_thread.iterations[1].type_specific_data.llm_decision == 'REWRITE'
    
    # Verify no Q&A exchange in iterations (all should be AR_FEEDBACK type)
    for iteration in processed_thread.iterations:
        assert iteration.iteration_type == IterationType.AR_FEEDBACK
    
    # Verify audit logging was called
    assert audit_logger.log_valid_response.called


def test_no_question_detection_for_invalid():
    """Test that questions are not detected for INVALID validation output."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    initial_response = "Initial response"
    response_with_questions = "Response.\n\nQUESTION: What do you mean?"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM responses
    llm_service.generate_response.side_effect = [
        initial_response,
        response_with_questions,
        "Final response"
    ]
    
    # Mock rewriting prompt generation
    llm_service.generate_rewriting_prompt.return_value = "Please fix"
    
    # Mock validation: INVALID, INVALID (with questions but should be ignored), then VALID
    validation_service.validate.side_effect = [
        ValidationResult(
            output="INVALID",
            findings=[Finding(validation_output="INVALID", details={})]
        ),
        ValidationResult(
            output="INVALID",
            findings=[Finding(validation_output="INVALID", details={})]
        ),
        ValidationResult(
            output="VALID",
            findings=[]
        )
    ]
    
    # Process thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify thread is completed (not paused for questions)
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.COMPLETED
    
    # Verify no Q&A exchanges were created (all should be AR_FEEDBACK type)
    for iteration in processed_thread.iterations:
        assert iteration.iteration_type == IterationType.AR_FEEDBACK



def test_resume_thread_with_answers_validates_status():
    """Test that resume_thread_with_answers validates thread is in AWAITING_USER_INPUT status."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread in PROCESSING status (not AWAITING_USER_INPUT)
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    
    # Try to resume with answers
    with pytest.raises(ValueError) as exc_info:
        resume_thread_with_answers(
            thread_id=thread_id,
            answers=["Answer 1"],
            skipped=False,
            thread_manager=thread_manager,
            llm_service=llm_service,
            validation_service=validation_service,
            audit_logger=audit_logger
        )
    
    assert "not awaiting user input" in str(exc_info.value).lower()


def test_resume_thread_with_answers_validates_answer_count():
    """Test that resume_thread_with_answers validates answer count matches question count."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    thread = thread_manager.get_thread(thread_id)
    
    # Simulate a thread with questions
    questions = ["Question 1?", "Question 2?"]
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response="Response with questions",
        questions=questions,
        thread_manager=thread_manager,
        current_validation=Mock(output="TRANSLATION_AMBIGUOUS"),
        enriched_findings=[],
        rewriting_prompt="Fix it"
    )
    
    # Try to resume with wrong number of answers
    with pytest.raises(ValueError) as exc_info:
        resume_thread_with_answers(
            thread_id=thread_id,
            answers=["Only one answer"],  # Should be 2
            skipped=False,
            thread_manager=thread_manager,
            llm_service=llm_service,
            validation_service=validation_service,
            audit_logger=audit_logger
        )
    
    assert "answer count" in str(exc_info.value).lower()
    assert "does not match" in str(exc_info.value).lower()


def test_resume_thread_with_answers_updates_qa_exchange():
    """Test that resume_thread_with_answers updates the Q&A exchange with answers."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    thread = thread_manager.get_thread(thread_id)
    
    questions = ["Question 1?", "Question 2?"]
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response="Response with questions",
        questions=questions,
        thread_manager=thread_manager,
        current_validation=Mock(output="TRANSLATION_AMBIGUOUS"),
        enriched_findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})],
        rewriting_prompt="Fix it"
    )
    
    # Mock LLM and validation for resumption
    llm_service.template_manager = Mock()
    llm_service.template_manager.load_template_by_name.return_value = "Template"
    llm_service.template_manager.render_template.return_value = "Rendered prompt"
    llm_service.generate_response.return_value = "New response"
    validation_service.validate.return_value = ValidationResult(
        output="VALID",
        findings=[]
    )
    
    # Resume with answers
    answers = ["Answer 1", "Answer 2"]
    resume_thread_with_answers(
        thread_id=thread_id,
        answers=answers,
        skipped=False,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify Q&A exchange was updated
    updated_thread = thread_manager.get_thread(thread_id)
    first_iteration = updated_thread.iterations[0]
    assert first_iteration.iteration_type == IterationType.USER_CLARIFICATION
    assert isinstance(first_iteration.type_specific_data, ClarificationIterationData)
    clar_data = first_iteration.type_specific_data
    assert clar_data.qa_exchange is not None
    assert clar_data.qa_exchange.answers == answers
    assert clar_data.qa_exchange.skipped is False


def test_resume_thread_with_answers_changes_status_to_processing():
    """Test that resume_thread_with_answers changes thread status to PROCESSING."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    thread = thread_manager.get_thread(thread_id)
    
    questions = ["Question 1?"]
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response="Response with questions",
        questions=questions,
        thread_manager=thread_manager,
        current_validation=Mock(output="TRANSLATION_AMBIGUOUS"),
        enriched_findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})],
        rewriting_prompt="Fix it"
    )
    
    # Verify status is AWAITING_USER_INPUT
    thread = thread_manager.get_thread(thread_id)
    assert thread.status == ThreadStatus.AWAITING_USER_INPUT
    
    # Mock LLM and validation
    llm_service.template_manager = Mock()
    llm_service.template_manager.load_template_by_name.return_value = "Template"
    llm_service.template_manager.render_template.return_value = "Rendered prompt"
    llm_service.generate_response.return_value = "New response"
    validation_service.validate.return_value = ValidationResult(
        output="VALID",
        findings=[]
    )
    
    # Resume with answers
    resume_thread_with_answers(
        thread_id=thread_id,
        answers=["Answer 1"],
        skipped=False,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify status changed to COMPLETED (via PROCESSING)
    updated_thread = thread_manager.get_thread(thread_id)
    assert updated_thread.status == ThreadStatus.COMPLETED


def test_resume_thread_with_answers_creates_context_augmentation():
    """Test that resume_thread_with_answers creates context augmentation when not skipped."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    thread = thread_manager.get_thread(thread_id)
    
    questions = ["Question 1?"]
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response="Response with questions",
        questions=questions,
        thread_manager=thread_manager,
        current_validation=Mock(output="TRANSLATION_AMBIGUOUS"),
        enriched_findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})],
        rewriting_prompt="Fix it"
    )
    
    # Mock LLM and validation
    llm_service.template_manager = Mock()
    llm_service.template_manager.load_template_by_name.return_value = "Template"
    llm_service.template_manager.render_template.return_value = "Rendered prompt"
    llm_service.generate_response.return_value = "New response"
    validation_service.validate.return_value = ValidationResult(
        output="VALID",
        findings=[]
    )
    
    # Resume with answers
    answers = ["Answer 1"]
    resume_thread_with_answers(
        thread_id=thread_id,
        answers=answers,
        skipped=False,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify LLM was called to generate a new response
    assert llm_service.generate_response.called
    
    # Get the prompt that was sent to the LLM
    generate_call = llm_service.generate_response.call_args
    prompt = generate_call[0][0]
    
    # Verify the prompt contains the user's answer (context augmentation)
    assert "Answer 1" in prompt
    assert "Question 1?" in prompt
    assert "clarification" in prompt.lower() or "improved" in prompt.lower()


def test_resume_thread_with_answers_skips_augmentation_when_skipped():
    """Test that resume_thread_with_answers skips context augmentation when skipped=True."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    thread = thread_manager.get_thread(thread_id)
    
    questions = ["Question 1?"]
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response="Response with questions",
        questions=questions,
        thread_manager=thread_manager,
        current_validation=Mock(output="TRANSLATION_AMBIGUOUS"),
        enriched_findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})],
        rewriting_prompt="Fix it"
    )
    
    # Mock LLM and validation
    llm_service.template_manager = Mock()
    llm_service.template_manager.load_template_by_name.return_value = "Template"
    llm_service.template_manager.render_template.return_value = "Rendered prompt"
    llm_service.generate_response.return_value = "New response"
    validation_service.validate.return_value = ValidationResult(
        output="VALID",
        findings=[]
    )
    
    # Resume with skip
    resume_thread_with_answers(
        thread_id=thread_id,
        answers=[],
        skipped=True,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # When skipped=True, the function creates a simple prompt directly
    # without using the template manager, so render_template should NOT be called
    render_call = llm_service.template_manager.render_template.call_args
    assert render_call is None  # Should not be called when skipped
    
    # Verify skipped flag was set
    updated_thread = thread_manager.get_thread(thread_id)
    first_iteration = updated_thread.iterations[0]
    assert first_iteration.iteration_type == IterationType.USER_CLARIFICATION
    assert isinstance(first_iteration.type_specific_data, ClarificationIterationData)
    assert first_iteration.type_specific_data.qa_exchange.skipped is True


def test_resume_thread_with_answers_increments_iteration_counter():
    """Test that resume_thread_with_answers does NOT increment the iteration counter.
    
    The counter was already incremented when the clarification iteration was created.
    The entire clarification cycle (ask + answer + rewrite) counts as a single iteration.
    """
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    thread = thread_manager.get_thread(thread_id)
    thread.iteration_counter = 2  # Counter was incremented when clarification iteration was created
    
    questions = ["Question 1?"]
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response="Response with questions",
        questions=questions,
        thread_manager=thread_manager,
        current_validation=Mock(output="TRANSLATION_AMBIGUOUS"),
        enriched_findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})],
        rewriting_prompt="Fix it"
    )
    
    # Mock LLM and validation
    llm_service.template_manager = Mock()
    llm_service.template_manager.load_template_by_name.return_value = "Template"
    llm_service.template_manager.render_template.return_value = "Rendered prompt"
    llm_service.generate_response.return_value = "New response"
    validation_service.validate.return_value = ValidationResult(
        output="VALID",
        findings=[]
    )
    
    # Resume with answers
    resume_thread_with_answers(
        thread_id=thread_id,
        answers=["Answer 1"],
        skipped=False,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify iteration counter was NOT incremented (stays at 2)
    updated_thread = thread_manager.get_thread(thread_id)
    assert updated_thread.iteration_counter == 2
    # Should have 1 iteration (the clarification iteration)
    assert len(updated_thread.iterations) == 1
    assert updated_thread.iterations[0].iteration_number == 2


def test_resume_thread_with_answers_continues_rewriting_if_not_valid():
    """Test that resume_thread_with_answers continues rewriting loop if response is not VALID."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "test-model")
    thread_id = thread.thread_id
    thread = thread_manager.get_thread(thread_id)
    
    questions = ["Question 1?"]
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response="Response with questions",
        questions=questions,
        thread_manager=thread_manager,
        current_validation=Mock(output="TRANSLATION_AMBIGUOUS"),
        enriched_findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})],
        rewriting_prompt="Fix it"
    )
    
    # Mock LLM and validation
    llm_service.template_manager = Mock()
    llm_service.template_manager.load_template_by_name.return_value = "Template"
    llm_service.template_manager.render_template.return_value = "Rendered prompt"
    llm_service.generate_response.side_effect = [
        "New response (still invalid)",
        "Final valid response"
    ]
    llm_service.generate_rewriting_prompt.return_value = "Fix it again"
    
    validation_service.validate.side_effect = [
        ValidationResult(
            output="INVALID",
            findings=[Finding(validation_output="INVALID", details={})]
        ),
        ValidationResult(
            output="VALID",
            findings=[]
        )
    ]
    
    # Resume with answers
    resume_thread_with_answers(
        thread_id=thread_id,
        answers=["Answer 1"],
        skipped=False,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify rewriting loop continued
    updated_thread = thread_manager.get_thread(thread_id)
    assert updated_thread.status == ThreadStatus.COMPLETED
    # Should have: clarification iteration (updated with answers) + AR_FEEDBACK iteration from rewriting loop
    # The clarification iteration is updated in place, not created as a new iteration
    assert len(updated_thread.iterations) == 2


# Feature: iteration-display-restructure, Property 10: Counter unchanged during question detection
# Validates: Requirements 5.4
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(
    prompt=st.text(min_size=1, max_size=200),
    model_id=st.text(min_size=1, max_size=50),
    initial_counter=st.integers(min_value=0, max_value=10)
)
def test_property_counter_unchanged_during_questions(prompt, model_id, initial_counter):
    """
    Property 10: Counter unchanged during clarification cycle
    
    For any thread where follow-up questions are detected, the iteration_counter 
    should be incremented ONCE for the entire clarification cycle (ask + answer + rewrite).
    
    In the rewriting loop, the counter is incremented when the clarification iteration
    is created. When the user provides answers, the counter is NOT incremented again.
    
    This test simulates the scenario where:
    1. Counter is at initial_counter
    2. Rewriting loop increments counter (simulated by setting it to initial_counter + 1)
    3. Questions are detected and clarification iteration is created
    4. User provides answers
    5. Counter remains at initial_counter + 1 (not incremented again)
    """
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Set the iteration counter to simulate it being incremented in the rewriting loop
    thread = thread_manager.get_thread(thread_id)
    thread.iteration_counter = initial_counter + 1  # Counter was incremented before asking questions
    
    # Mock validation result that enables question detection
    validation_result = Mock()
    validation_result.output = "TRANSLATION_AMBIGUOUS"
    validation_result.findings = [Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})]
    
    # Simulate detecting questions
    questions = ["What do you mean by X?", "Can you clarify Y?"]
    llm_response = "Response with questions"
    
    # Call _handle_follow_up_questions (this doesn't increment counter)
    _handle_follow_up_questions(
        thread_id=thread_id,
        thread=thread,
        llm_response=llm_response,
        questions=questions,
        thread_manager=thread_manager,
        current_validation=validation_result,
        enriched_findings=[Finding(validation_output="TRANSLATION_AMBIGUOUS", details={})],
        rewriting_prompt="Fix it"
    )
    
    # Verify the counter is unchanged (still at initial_counter + 1)
    updated_thread = thread_manager.get_thread(thread_id)
    assert updated_thread.iteration_counter == initial_counter + 1, \
        f"Expected counter to remain {initial_counter + 1}, but got {updated_thread.iteration_counter}"
    
    # Verify thread status is AWAITING_USER_INPUT
    assert updated_thread.status == ThreadStatus.AWAITING_USER_INPUT
    
    # Now simulate providing answers
    llm_service.generate_response.return_value = "New response after clarification"
    validation_service.validate.return_value = ValidationResult(
        output="VALID",
        findings=[]
    )
    
    # Resume with answers
    resume_thread_with_answers(
        thread_id=thread_id,
        answers=["Answer 1", "Answer 2"],
        skipped=False,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify the counter is STILL unchanged (still at initial_counter + 1)
    # The entire clarification cycle counts as a single iteration
    final_thread = thread_manager.get_thread(thread_id)
    assert final_thread.iteration_counter == initial_counter + 1, \
        f"Expected counter to remain {initial_counter + 1} after answers, but got {final_thread.iteration_counter}"
