"""
Tests for ThreadManager class.
"""
import pytest
from backend.services.thread_manager import ThreadManager
from backend.models.thread import Iteration, Finding, ThreadStatus


def test_create_thread():
    """Test creating a new thread."""
    manager = ThreadManager()
    
    thread = manager.create_thread("Test prompt", "test-model-id")
    
    assert thread is not None
    assert thread.thread_id is not None
    assert thread.user_prompt == "Test prompt"
    assert thread.model_id == "test-model-id"
    assert thread.status == ThreadStatus.PROCESSING
    assert len(thread.iterations) == 0


def test_get_thread():
    """Test retrieving a thread by ID."""
    manager = ThreadManager()
    
    created_thread = manager.create_thread("Test prompt", "test-model-id")
    retrieved_thread = manager.get_thread(created_thread.thread_id)
    
    assert retrieved_thread is not None
    assert retrieved_thread.thread_id == created_thread.thread_id
    assert retrieved_thread.user_prompt == created_thread.user_prompt


def test_get_nonexistent_thread():
    """Test retrieving a thread that doesn't exist."""
    manager = ThreadManager()
    
    thread = manager.get_thread("nonexistent-id")
    
    assert thread is None


def test_update_thread():
    """Test updating a thread with an iteration."""
    manager = ThreadManager()
    
    thread = manager.create_thread("Test prompt", "test-model-id")
    iteration = Iteration(
        iteration_number=1,
        llm_response="Test response",
        validation_output="VALID",
        findings=[]
    )
    
    success = manager.update_thread(thread.thread_id, iteration)
    
    assert success is True
    
    updated_thread = manager.get_thread(thread.thread_id)
    assert len(updated_thread.iterations) == 1
    assert updated_thread.iterations[0].iteration_number == 1


def test_update_nonexistent_thread():
    """Test updating a thread that doesn't exist."""
    manager = ThreadManager()
    
    iteration = Iteration(
        iteration_number=1,
        llm_response="Test response",
        validation_output="VALID",
        findings=[]
    )
    
    success = manager.update_thread("nonexistent-id", iteration)
    
    assert success is False


def test_list_threads():
    """Test listing all threads."""
    manager = ThreadManager()
    
    thread1 = manager.create_thread("Prompt 1", "model-1")
    thread2 = manager.create_thread("Prompt 2", "model-2")
    
    threads = manager.list_threads()
    
    assert len(threads) == 2
    thread_ids = [t.thread_id for t in threads]
    assert thread1.thread_id in thread_ids
    assert thread2.thread_id in thread_ids


def test_update_thread_status():
    """Test updating thread status."""
    manager = ThreadManager()
    
    thread = manager.create_thread("Test prompt", "test-model-id")
    
    success = manager.update_thread_status(
        thread.thread_id,
        ThreadStatus.COMPLETED,
        final_response="Final response",
        warning_message="Warning"
    )
    
    assert success is True
    
    updated_thread = manager.get_thread(thread.thread_id)
    assert updated_thread.status == ThreadStatus.COMPLETED
    assert updated_thread.final_response == "Final response"
    assert updated_thread.warning_message == "Warning"
    assert updated_thread.completed_at is not None


def test_thread_manager_thread_safety():
    """Test that ThreadManager handles concurrent access correctly."""
    import threading
    
    manager = ThreadManager()
    threads_created = []
    
    def create_thread_task(prompt):
        thread = manager.create_thread(prompt, "test-model")
        threads_created.append(thread)
    
    # Create multiple threads concurrently
    thread_tasks = []
    for i in range(10):
        t = threading.Thread(target=create_thread_task, args=(f"Prompt {i}",))
        thread_tasks.append(t)
        t.start()
    
    # Wait for all threads to complete
    for t in thread_tasks:
        t.join()
    
    # Verify all threads were created
    assert len(threads_created) == 10
    
    # Verify all thread IDs are unique
    thread_ids = [t.thread_id for t in threads_created]
    assert len(thread_ids) == len(set(thread_ids))
    
    # Verify all threads are in the manager
    all_threads = manager.list_threads()
    assert len(all_threads) == 10
