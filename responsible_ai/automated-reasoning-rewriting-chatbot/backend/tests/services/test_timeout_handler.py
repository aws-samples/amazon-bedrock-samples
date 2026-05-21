"""
Tests for the timeout handler service.
"""
from datetime import datetime, timedelta
import datetime as dt_module
from unittest.mock import Mock, patch

import pytest

from backend.services.timeout_handler import TimeoutHandler
from backend.services.thread_manager import ThreadManager
from backend.models.thread import Thread, ThreadStatus, Iteration, QuestionAnswerExchange


def test_timeout_handler_initialization():
    """Test that timeout handler initializes correctly."""
    thread_manager = ThreadManager()
    handler = TimeoutHandler(thread_manager, timeout_minutes=5, check_interval_seconds=30)
    
    assert handler.thread_manager == thread_manager
    assert handler.timeout_minutes == 5
    assert handler.check_interval_seconds == 30
    assert not handler._running


def test_timeout_handler_start_stop():
    """Test starting and stopping the timeout handler."""
    thread_manager = ThreadManager()
    handler = TimeoutHandler(thread_manager, timeout_minutes=5, check_interval_seconds=1)
    
    # Start the handler
    handler.start()
    assert handler._running
    assert handler._thread is not None
    assert handler._thread.is_alive()
    
    # Stop the handler
    handler.stop()
    assert not handler._running
    
    # Wait for thread to actually stop (join is deterministic)
    handler._thread.join(timeout=1.0)
    assert not handler._thread.is_alive()


def test_get_stale_awaiting_threads():
    """Test getting stale threads that have exceeded timeout."""
    thread_manager = ThreadManager()
    
    # Create a thread in AWAITING_USER_INPUT status
    thread1 = thread_manager.create_thread("Test prompt 1", "model-1")
    thread_manager.update_thread_status(thread1.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Create another thread that's not awaiting input
    thread2 = thread_manager.create_thread("Test prompt 2", "model-1")
    
    # Create a thread that's awaiting but not stale yet
    thread3 = thread_manager.create_thread("Test prompt 3", "model-1")
    thread_manager.update_thread_status(thread3.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Manually set thread1's timestamp to be old (more than 10 minutes ago)
    thread1_obj = thread_manager.get_thread(thread1.thread_id)
    thread1_obj.awaiting_input_since = datetime.now(dt_module.UTC) - timedelta(minutes=11)
    
    # Get stale threads
    stale_threads = thread_manager.get_stale_awaiting_threads(timeout_minutes=10)
    
    # Should only return thread1
    assert len(stale_threads) == 1
    assert stale_threads[0].thread_id == thread1.thread_id


def test_timeout_handler_detects_stale_threads():
    """Test that timeout handler detects and processes stale threads."""
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
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Make the thread stale
    thread_obj = thread_manager.get_thread(thread.thread_id)
    thread_obj.awaiting_input_since = datetime.now(dt_module.UTC) - timedelta(minutes=11)
    
    # Create handler with short timeout
    handler = TimeoutHandler(thread_manager, timeout_minutes=10, check_interval_seconds=1)
    
    # Mock the resume callback
    resume_callback = Mock()
    handler.set_resume_callback(resume_callback)
    
    # Manually trigger the check
    handler._check_and_handle_timeouts()
    
    # Verify callback was called with skipped=True
    resume_callback.assert_called_once_with(thread.thread_id, [], True)
    
    # Verify qa_exchange was marked as skipped
    updated_thread = thread_manager.get_thread(thread.thread_id)
    last_iteration = updated_thread.iterations[-1]
    assert last_iteration.type_specific_data.qa_exchange.skipped is True
    assert last_iteration.type_specific_data.qa_exchange.answers is None


def test_timeout_handler_no_callback():
    """Test that timeout handler logs warning when no callback is set."""
    thread_manager = ThreadManager()
    
    # Create a stale thread
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
    
    # Make it stale
    thread_obj = thread_manager.get_thread(thread.thread_id)
    thread_obj.awaiting_input_since = datetime.now(dt_module.UTC) - timedelta(minutes=11)
    
    # Create handler without callback
    handler = TimeoutHandler(thread_manager, timeout_minutes=10, check_interval_seconds=1)
    
    # Should not raise an error, just log warning
    handler._check_and_handle_timeouts()
    
    # Verify qa_exchange was still marked as skipped
    updated_thread = thread_manager.get_thread(thread.thread_id)
    last_iteration = updated_thread.iterations[-1]
    assert last_iteration.type_specific_data.qa_exchange.skipped is True


def test_awaiting_input_since_timestamp():
    """Test that awaiting_input_since timestamp is set correctly."""
    thread_manager = ThreadManager()
    
    # Create a thread
    thread = thread_manager.create_thread("Test prompt", "model-1")
    
    # Initially should be None
    thread_obj = thread_manager.get_thread(thread.thread_id)
    assert thread_obj.awaiting_input_since is None
    
    # Set to AWAITING_USER_INPUT
    before = datetime.now(dt_module.UTC)
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    after = datetime.now(dt_module.UTC)
    
    # Should have timestamp
    thread_obj = thread_manager.get_thread(thread.thread_id)
    assert thread_obj.awaiting_input_since is not None
    assert before <= thread_obj.awaiting_input_since <= after
    
    # Change to PROCESSING
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.PROCESSING)
    
    # Should clear timestamp
    thread_obj = thread_manager.get_thread(thread.thread_id)
    assert thread_obj.awaiting_input_since is None


def test_awaiting_input_since_cleared_on_completion():
    """Test that awaiting_input_since is cleared when thread completes."""
    thread_manager = ThreadManager()
    
    # Create a thread and set to awaiting input
    thread = thread_manager.create_thread("Test prompt", "model-1")
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Verify timestamp is set
    thread_obj = thread_manager.get_thread(thread.thread_id)
    assert thread_obj.awaiting_input_since is not None
    
    # Complete the thread
    thread_manager.update_thread_status(
        thread.thread_id,
        ThreadStatus.COMPLETED,
        final_response="Final response"
    )
    
    # Should clear timestamp
    thread_obj = thread_manager.get_thread(thread.thread_id)
    assert thread_obj.awaiting_input_since is None
    assert thread_obj.completed_at is not None


def test_thread_serialization_with_awaiting_timestamp():
    """Test that thread serialization includes awaiting_input_since."""
    thread_manager = ThreadManager()
    
    # Create a thread and set to awaiting input
    thread = thread_manager.create_thread("Test prompt", "model-1")
    thread_manager.update_thread_status(thread.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # Get the thread and serialize it
    thread_obj = thread_manager.get_thread(thread.thread_id)
    thread_dict = thread_obj.to_dict()
    
    # Should include awaiting_input_since
    assert "awaiting_input_since" in thread_dict
    assert thread_dict["awaiting_input_since"] is not None
    
    # Deserialize and verify
    restored_thread = Thread.from_dict(thread_dict)
    assert restored_thread.awaiting_input_since is not None
    assert restored_thread.awaiting_input_since == thread_obj.awaiting_input_since
