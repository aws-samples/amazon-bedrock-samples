"""
Integration test for timeout handling in the complete system.
"""
import time
from datetime import datetime, timedelta
import datetime as dt_module
from unittest.mock import Mock, patch, MagicMock

import pytest

from backend.services.thread_manager import ThreadManager
from backend.services.timeout_handler import TimeoutHandler
from backend.models.thread import Thread, ThreadStatus, Iteration, QuestionAnswerExchange, Finding


def test_timeout_integration_with_resume():
    """
    Integration test for complete timeout flow with resume.
    
    This test verifies:
    1. Thread enters AWAITING_USER_INPUT status
    2. Timestamp is set correctly
    3. Timeout handler detects stale thread
    4. Resume callback is triggered
    5. Thread is resumed with skipped=True
    """
    # Setup
    thread_manager = ThreadManager()
    
    # Create a thread with questions
    thread = thread_manager.create_thread("Test prompt", "model-1")
    qa_exchange = QuestionAnswerExchange(
        questions=["Question 1?", "Question 2?"],
        answers=None,
        skipped=False
    )
    
    # Create a TypedIteration with clarification data
    from backend.models.thread import TypedIteration, IterationType, ClarificationIterationData
    iteration = TypedIteration(
        iteration_number=1,
        iteration_type=IterationType.USER_CLARIFICATION,
        original_answer="Original response",
        rewritten_answer="Response with questions",
        rewriting_prompt="Rewrite prompt",
        type_specific_data=ClarificationIterationData(
            qa_exchange=qa_exchange,
            context_augmentation=None
        )
    )
    thread_obj = thread_manager.get_thread(thread.thread_id)
    thread_obj.iterations.append(iteration)
    
    # Set thread to AWAITING_USER_INPUT
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Verify timestamp is set
    thread_obj = thread_manager.get_thread(thread.thread_id)
    assert thread_obj.awaiting_input_since is not None
    assert thread_obj.status == ThreadStatus.AWAITING_USER_INPUT
    
    # Make the thread stale (simulate 11 minutes passing)
    thread_obj.awaiting_input_since = datetime.now(dt_module.UTC) - timedelta(minutes=11)
    
    # Create timeout handler with mock resume callback
    handler = TimeoutHandler(thread_manager, timeout_minutes=10, check_interval_seconds=1)
    resume_callback = Mock()
    handler.set_resume_callback(resume_callback)
    
    # Trigger timeout check
    handler._check_and_handle_timeouts()
    
    # Verify resume callback was called with correct parameters
    resume_callback.assert_called_once()
    call_args = resume_callback.call_args
    assert call_args[0][0] == thread.thread_id  # thread_id
    assert call_args[0][1] == []  # empty answers
    assert call_args[0][2] is True  # skipped=True
    
    # Verify qa_exchange was marked as skipped
    updated_thread = thread_manager.get_thread(thread.thread_id)
    last_iteration = updated_thread.iterations[-1]
    assert last_iteration.type_specific_data.qa_exchange.skipped is True
    assert last_iteration.type_specific_data.qa_exchange.answers is None


def test_timeout_does_not_affect_fresh_threads():
    """Test that timeout handler doesn't affect threads that haven't timed out."""
    thread_manager = ThreadManager()
    
    # Create a thread that's awaiting input but not stale
    thread = thread_manager.create_thread("Test prompt", "model-1")
    qa_exchange = QuestionAnswerExchange(
        questions=["Question 1?"],
        answers=None,
        skipped=False
    )
    
    # Create a TypedIteration with clarification data
    from backend.models.thread import TypedIteration, IterationType, ClarificationIterationData
    iteration = TypedIteration(
        iteration_number=1,
        iteration_type=IterationType.USER_CLARIFICATION,
        original_answer="Original response",
        rewritten_answer="Response",
        rewriting_prompt="Rewrite prompt",
        type_specific_data=ClarificationIterationData(
            qa_exchange=qa_exchange,
            context_augmentation=None
        )
    )
    thread_obj = thread_manager.get_thread(thread.thread_id)
    thread_obj.iterations.append(iteration)
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Create timeout handler
    handler = TimeoutHandler(thread_manager, timeout_minutes=10, check_interval_seconds=1)
    resume_callback = Mock()
    handler.set_resume_callback(resume_callback)
    
    # Trigger timeout check
    handler._check_and_handle_timeouts()
    
    # Verify callback was NOT called
    resume_callback.assert_not_called()
    
    # Verify qa_exchange was NOT modified
    updated_thread = thread_manager.get_thread(thread.thread_id)
    last_iteration = updated_thread.iterations[-1]
    assert last_iteration.type_specific_data.qa_exchange.skipped is False
    assert last_iteration.type_specific_data.qa_exchange.answers is None


def test_timeout_only_affects_awaiting_threads():
    """Test that timeout handler only affects threads in AWAITING_USER_INPUT status."""
    thread_manager = ThreadManager()
    
    # Create threads in different statuses
    thread1 = thread_manager.create_thread("Prompt 1", "model-1")
    thread_manager.update_thread_status(thread1.thread_id, ThreadStatus.PROCESSING)
    
    thread2 = thread_manager.create_thread("Prompt 2", "model-1")
    thread_manager.update_thread_status(thread2.thread_id, ThreadStatus.COMPLETED)
    
    thread3 = thread_manager.create_thread("Prompt 3", "model-1")
    thread_manager.update_thread_status(thread3.thread_id, ThreadStatus.ERROR)
    
    # Create timeout handler
    handler = TimeoutHandler(thread_manager, timeout_minutes=10, check_interval_seconds=1)
    resume_callback = Mock()
    handler.set_resume_callback(resume_callback)
    
    # Trigger timeout check
    handler._check_and_handle_timeouts()
    
    # Verify callback was NOT called for any thread
    resume_callback.assert_not_called()


def test_multiple_stale_threads_handled():
    """Test that timeout handler handles multiple stale threads."""
    thread_manager = ThreadManager()
    
    # Create multiple stale threads
    thread_ids = []
    for i in range(3):
        thread = thread_manager.create_thread(f"Prompt {i}", "model-1")
        qa_exchange = QuestionAnswerExchange(
            questions=[f"Question {i}?"],
            answers=None,
            skipped=False
        )
        
        # Create a TypedIteration with clarification data
        from backend.models.thread import TypedIteration, IterationType, ClarificationIterationData
        iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer=f"Original {i}",
            rewritten_answer=f"Response {i}",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange,
                context_augmentation=None
            )
        )
        thread_obj = thread_manager.get_thread(thread.thread_id)
        thread_obj.iterations.append(iteration)
        thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
        
        # Make it stale
        thread_obj.awaiting_input_since = datetime.now(dt_module.UTC) - timedelta(minutes=11)
        thread_ids.append(thread.thread_id)
    
    # Create timeout handler
    handler = TimeoutHandler(thread_manager, timeout_minutes=10, check_interval_seconds=1)
    resume_callback = Mock()
    handler.set_resume_callback(resume_callback)
    
    # Trigger timeout check
    handler._check_and_handle_timeouts()
    
    # Verify callback was called for all threads
    assert resume_callback.call_count == 3
    
    # Verify all threads were marked as skipped
    for thread_id in thread_ids:
        thread = thread_manager.get_thread(thread_id)
        last_iteration = thread.iterations[-1]
        assert last_iteration.type_specific_data.qa_exchange.skipped is True


def test_timeout_handler_logs_events():
    """Test that timeout handler logs appropriate events."""
    thread_manager = ThreadManager()
    
    # Create a stale thread
    thread = thread_manager.create_thread("Test prompt", "model-1")
    qa_exchange = QuestionAnswerExchange(
        questions=["Question?"],
        answers=None,
        skipped=False
    )
    iteration = Iteration(
        iteration_number=1,
        llm_response="Response",
        validation_output="TRANSLATION_AMBIGUOUS",
        findings=[],
        qa_exchange=qa_exchange
    )
    thread_manager.update_thread(thread.thread_id, iteration)
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Make it stale
    thread_obj = thread_manager.get_thread(thread.thread_id)
    thread_obj.awaiting_input_since = datetime.now(dt_module.UTC) - timedelta(minutes=11)
    
    # Create timeout handler
    handler = TimeoutHandler(thread_manager, timeout_minutes=10, check_interval_seconds=1)
    resume_callback = Mock()
    handler.set_resume_callback(resume_callback)
    
    # Capture logs
    with patch('backend.services.timeout_handler.logger') as mock_logger:
        handler._check_and_handle_timeouts()
        
        # Verify logging calls
        assert mock_logger.info.called
        assert mock_logger.warning.called
        
        # Check that timeout event was logged
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any('did not respond within' in str(call) for call in warning_calls)
