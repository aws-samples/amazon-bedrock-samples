"""
Tests for thread processor validation and rewriting logic.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings

from backend.services.thread_processor import process_thread
from backend.services.thread_manager import ThreadManager
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService, ValidationResult
from backend.services.audit_logger import AuditLogger
from backend.models.thread import Thread, ThreadStatus, Finding


# Feature: ar-chatbot, Property 17: VALID responses are returned
# Validates: Requirements 4.3
@settings(max_examples=100)
@given(
    prompt=st.text(min_size=1, max_size=200),
    response=st.text(min_size=1, max_size=500),
    model_id=st.text(min_size=1, max_size=50)
)
def test_property_valid_responses_are_returned(prompt, response, model_id):
    """
    Property 17: VALID responses are returned
    
    For any response with VALID validation output, the system should return 
    the response to the user.
    
    This test verifies that when validation returns VALID, the thread is 
    completed with the response and logged to audit.
    """
    # Setup mocks
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Create a thread
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM to return the response
    llm_service.generate_response.return_value = response
    
    # Mock validation to return VALID
    validation_result = ValidationResult(
        output="VALID",
        findings=[]
    )
    validation_service.validate.return_value = validation_result
    
    # Process the thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify the thread is completed with the response
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread is not None
    assert processed_thread.status == ThreadStatus.COMPLETED
    assert processed_thread.final_response == response
    
    # Verify audit logger was called
    assert audit_logger.log_valid_response.called
    
    # Verify the response was validated
    assert validation_service.validate.called
    call_args = validation_service.validate.call_args
    assert call_args[0][0] == prompt  # First arg is prompt
    assert call_args[0][1] == response  # Second arg is response


def test_too_complex_handling():
    """Test that TOO_COMPLEX validation results in error without rewriting."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    response = "Test response"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM response
    llm_service.generate_response.return_value = response
    
    # Mock validation to return TOO_COMPLEX
    validation_result = ValidationResult(
        output="TOO_COMPLEX",
        findings=[]
    )
    validation_service.validate.return_value = validation_result
    
    # Process thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify thread is in ERROR state
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.ERROR
    assert "too complex" in processed_thread.final_response.lower()
    
    # Verify no rewriting attempts (only one LLM call)
    assert llm_service.generate_response.call_count == 1
    
    # Verify no audit logging
    assert not audit_logger.log_valid_response.called
    assert not audit_logger.log_max_iterations.called


def test_no_translations_single_finding():
    """Test that single NO_TRANSLATIONS finding returns response without warning."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    response = "Test response"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM response
    llm_service.generate_response.return_value = response
    
    # Mock validation to return single NO_TRANSLATIONS
    validation_result = ValidationResult(
        output="NO_TRANSLATIONS",
        findings=[Finding(validation_output="NO_TRANSLATIONS", details={})]
    )
    validation_service.validate.return_value = validation_result
    
    # Process thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify thread is completed without warning
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.COMPLETED
    assert processed_thread.final_response == response
    assert processed_thread.warning_message is None
    
    # Verify no rewriting attempts
    assert llm_service.generate_response.call_count == 1
    
    # Verify no audit logging
    assert not audit_logger.log_valid_response.called


def test_valid_with_no_translations_warning():
    """Test that VALID with NO_TRANSLATIONS returns response with warning."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    response = "Test response"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM response
    llm_service.generate_response.return_value = response
    
    # Mock validation to return VALID with NO_TRANSLATIONS finding
    validation_result = ValidationResult(
        output="VALID",
        findings=[Finding(validation_output="NO_TRANSLATIONS", details={})]
    )
    validation_service.validate.return_value = validation_result
    
    # Process thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger
    )
    
    # Verify thread is completed with warning
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.COMPLETED
    assert processed_thread.final_response == response
    assert processed_thread.warning_message is not None
    assert "could not be fully validated" in processed_thread.warning_message
    
    # Verify audit logging was called (since it's VALID)
    assert audit_logger.log_valid_response.called


def test_rewriting_loop_achieves_valid():
    """Test that rewriting loop continues until VALID is achieved."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    initial_response = "Initial response"
    rewritten_response = "Rewritten response"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM responses
    llm_service.generate_response.side_effect = [
        initial_response,  # Initial response
        rewritten_response  # Rewritten response
    ]
    
    # Mock rewriting prompt generation
    llm_service.generate_rewriting_prompt.return_value = "Please fix your response"
    
    # Mock validation: first INVALID, then VALID
    validation_service.validate.side_effect = [
        ValidationResult(
            output="INVALID",
            findings=[Finding(validation_output="INVALID", details={"explanation": "Test issue"})]
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
    
    # Verify thread is completed with rewritten response
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.COMPLETED
    assert processed_thread.final_response == rewritten_response
    
    # Verify we have 2 iterations: iteration 0 (initial) + iteration 2 (rewrite)
    assert len(processed_thread.iterations) == 2
    assert processed_thread.iterations[0].iteration_number == 0
    assert processed_thread.iterations[0].type_specific_data.llm_decision == 'INITIAL'
    assert processed_thread.iterations[1].iteration_number == 2
    assert processed_thread.iterations[1].type_specific_data.llm_decision == 'REWRITE'
    
    # Verify original answer is stored in iteration 0
    assert processed_thread.iterations[0].rewritten_answer == initial_response
    assert processed_thread.iterations[0].type_specific_data.validation_output == "INVALID"
    
    # Verify audit logging was called
    assert audit_logger.log_valid_response.called


def test_rewriting_loop_max_iterations():
    """Test that rewriting loop stops at max iterations and logs summary."""
    # Setup
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    prompt = "Test prompt"
    model_id = "test-model"
    
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM to always return responses
    llm_service.generate_response.return_value = "Response"
    llm_service.generate_rewriting_prompt.return_value = "Fix it"
    
    # Mock validation to always return INVALID
    validation_service.validate.return_value = ValidationResult(
        output="INVALID",
        findings=[Finding(validation_output="INVALID", details={"explanation": "Still wrong"})]
    )
    
    # Mock config manager to return max_iterations=3 for faster test
    config_manager = Mock()
    config = Mock()
    config.max_iterations = 3
    config_manager.get_current_config.return_value = config
    
    # Process thread with max_iterations=3 for faster test
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger,
        config_manager=config_manager
    )
    
    # Verify thread is completed with warning
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread.status == ThreadStatus.COMPLETED
    assert processed_thread.warning_message is not None
    assert "may be unsafe" in processed_thread.warning_message
    
    # Verify we have 3 iterations (3 rewrites - original answer is stored separately)
    assert len(processed_thread.iterations) == 3
    
    # Verify max iterations audit logging was called
    assert audit_logger.log_max_iterations.called


# Feature: ar-chatbot, Property 14: Thread errors are isolated
# Validates: Requirements 3.5
@settings(max_examples=100)
@given(
    num_threads=st.integers(min_value=2, max_value=5),
    error_thread_index=st.integers(min_value=0, max_value=4),
    prompts=st.lists(st.text(min_size=1, max_size=100), min_size=2, max_size=5),
    model_id=st.text(min_size=1, max_size=50)
)
def test_property_thread_errors_are_isolated(num_threads, error_thread_index, prompts, model_id):
    """
    Property 14: Thread errors are isolated
    
    For any thread that encounters an error, the error should be displayed 
    in that thread without affecting other threads.
    
    This test verifies that when one thread fails, other threads continue 
    to process normally and maintain their independent state.
    """
    # Ensure we have enough prompts and valid error index
    if len(prompts) < num_threads:
        prompts = prompts + [f"Prompt {i}" for i in range(num_threads - len(prompts))]
    prompts = prompts[:num_threads]
    error_thread_index = error_thread_index % num_threads
    
    # Setup shared services
    thread_manager = ThreadManager()
    audit_logger = Mock(spec=AuditLogger)
    
    # Create multiple threads
    thread_ids = []
    for i in range(num_threads):
        thread = thread_manager.create_thread(prompts[i], model_id)
        thread_ids.append(thread.thread_id)
    
    # Process each thread with different outcomes
    for i, thread_id in enumerate(thread_ids):
        llm_service = Mock(spec=LLMService)
        validation_service = Mock(spec=ValidationService)
        
        if i == error_thread_index:
            # This thread will encounter an error
            llm_service.generate_response.side_effect = Exception("Simulated error")
            
            # Process the thread (should handle error gracefully)
            process_thread(
                thread_id=thread_id,
                thread_manager=thread_manager,
                llm_service=llm_service,
                validation_service=validation_service,
                audit_logger=audit_logger
            )
        else:
            # Other threads succeed normally
            response = f"Response for thread {i}"
            llm_service.generate_response.return_value = response
            validation_service.validate.return_value = ValidationResult(
                output="VALID",
                findings=[]
            )
            
            # Process the thread
            process_thread(
                thread_id=thread_id,
                thread_manager=thread_manager,
                llm_service=llm_service,
                validation_service=validation_service,
                audit_logger=audit_logger
            )
    
    # Verify the error thread is in ERROR state
    error_thread = thread_manager.get_thread(thread_ids[error_thread_index])
    assert error_thread is not None
    assert error_thread.status == ThreadStatus.ERROR
    assert error_thread.final_response is not None
    assert len(error_thread.final_response) > 0
    
    # Verify all other threads are COMPLETED successfully
    for i, thread_id in enumerate(thread_ids):
        if i != error_thread_index:
            thread = thread_manager.get_thread(thread_id)
            assert thread is not None
            assert thread.status == ThreadStatus.COMPLETED
            assert thread.final_response == f"Response for thread {i}"
            
    # Verify that all threads exist and are independent
    all_threads = thread_manager.list_threads()
    assert len(all_threads) == num_threads
    
    # Verify each thread has its original prompt
    for i, thread_id in enumerate(thread_ids):
        thread = thread_manager.get_thread(thread_id)
        assert thread.user_prompt == prompts[i]



# Feature: iteration-display-restructure, Property 12: Prevent iterations at limit
# Validates: Requirements 6.1, 6.2, 6.3
@settings(max_examples=100)
@given(
    max_iterations=st.integers(min_value=1, max_value=10),
    prompt=st.text(min_size=1, max_size=200),
    model_id=st.text(min_size=1, max_size=50)
)
def test_property_prevent_iterations_at_limit(max_iterations, prompt, model_id):
    """
    Property 12: Prevent iterations at limit
    
    For any thread where iteration_counter >= max_iterations, attempting to create 
    a new iteration should be prevented and the thread should complete.
    
    This test verifies that the system enforces the maximum iteration limit and 
    completes the thread with a warning message when the limit is reached.
    """
    # Setup mocks
    thread_manager = ThreadManager()
    llm_service = Mock(spec=LLMService)
    validation_service = Mock(spec=ValidationService)
    audit_logger = Mock(spec=AuditLogger)
    
    # Mock config manager to return our max_iterations
    config_manager = Mock()
    config = Mock()
    config.max_iterations = max_iterations
    config_manager.get_current_config.return_value = config
    
    # Create a thread
    thread = thread_manager.create_thread(prompt, model_id)
    thread_id = thread.thread_id
    
    # Mock LLM to always return responses
    llm_service.generate_response.return_value = "Test response"
    llm_service.generate_rewriting_prompt.return_value = "Fix it"
    
    # Mock validation to always return INVALID (to trigger rewriting)
    validation_service.validate.return_value = ValidationResult(
        output="INVALID",
        findings=[Finding(validation_output="INVALID", details={"explanation": "Test issue"})]
    )
    
    # Process the thread
    process_thread(
        thread_id=thread_id,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger,
        config_manager=config_manager
    )
    
    # Verify the thread completed
    processed_thread = thread_manager.get_thread(thread_id)
    assert processed_thread is not None
    assert processed_thread.status == ThreadStatus.COMPLETED
    
    # Verify max_iterations was set on the thread
    assert processed_thread.max_iterations == max_iterations
    
    # Verify the iteration counter reached the limit
    assert processed_thread.iteration_counter == max_iterations, \
        f"Expected iteration_counter to be {max_iterations}, got {processed_thread.iteration_counter}"
    
    # Verify we have exactly max_iterations iterations (not counting original answer)
    assert len(processed_thread.iterations) == max_iterations, \
        f"Expected {max_iterations} iterations, got {len(processed_thread.iterations)}"
    
    # Verify a warning message was set
    assert processed_thread.warning_message is not None, \
        "Expected warning_message to be set when max iterations reached"
    assert "may be unsafe" in processed_thread.warning_message.lower() or \
           "unable to fully validate" in processed_thread.warning_message.lower(), \
        f"Warning message should indicate validation failure: {processed_thread.warning_message}"
    
    # Verify max iterations audit logging was called
    assert audit_logger.log_max_iterations.called, \
        "Expected log_max_iterations to be called when limit reached"
    
    # Verify no more than max_iterations LLM calls were made
    # The counter starts at 1 after initial response (iteration 0), so we get max_iterations total calls
    assert llm_service.generate_response.call_count == max_iterations, \
        f"Expected {max_iterations} LLM calls, got {llm_service.generate_response.call_count}"
