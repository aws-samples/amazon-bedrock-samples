"""
Property-based tests for thread data models.
"""
import pytest
from hypothesis import given, strategies as st, settings
from backend.models.thread import Thread, ThreadStatus


# Feature: ar-chatbot, Property 6: Thread identifiers are unique
# Validates: Requirements 2.2
@settings(max_examples=100)
@given(
    prompts=st.lists(
        st.text(min_size=1, max_size=100),
        min_size=2,
        max_size=50
    ),
    model_id=st.text(min_size=1, max_size=50)
)
def test_thread_id_uniqueness(prompts, model_id):
    """
    Property: For any set of created threads, all thread identifiers should be unique.
    
    This test generates multiple thread creation requests and verifies that all
    thread IDs are unique across all created threads.
    """
    # Create multiple threads
    threads = []
    for prompt in prompts:
        thread_id = Thread.generate_id()
        thread = Thread(
            thread_id=thread_id,
            user_prompt=prompt,
            model_id=model_id,
            status=ThreadStatus.PROCESSING
        )
        threads.append(thread)
    
    # Extract all thread IDs
    thread_ids = [thread.thread_id for thread in threads]
    
    # Verify all thread IDs are unique
    assert len(thread_ids) == len(set(thread_ids)), \
        f"Thread IDs are not unique. Found {len(thread_ids)} threads but only {len(set(thread_ids))} unique IDs"


# === Tests from test_thread_new_fields.py ===

from backend.models.thread import (
    Finding, ARIterationData, TypedIteration, IterationType,
    ClarificationIterationData, QuestionAnswerExchange
)


class TestThreadNewFields:
    """Tests for new fields added to Thread and related models."""
    
    def test_thread_new_fields_initialization(self):
        """Test that Thread initializes with new fields."""
        thread = Thread(
            thread_id='test-123',
            user_prompt='Test prompt',
            model_id='test-model',
            status=ThreadStatus.PROCESSING
        )
        assert thread.max_iterations == 5
        assert thread.processed_finding_indices == set()
        assert thread.current_findings == []
    
    def test_thread_serialization_with_new_fields(self):
        """Test that Thread serializes and deserializes with new fields."""
        findings = [Finding(validation_output='INVALID', details={'reason': 'test'})]
        thread = Thread(
            thread_id='test-456',
            user_prompt='Test',
            model_id='model-2',
            status=ThreadStatus.AWAITING_USER_INPUT,
            max_iterations=7,
            processed_finding_indices={1, 3},
            current_findings=findings
        )
        
        thread_dict = thread.to_dict()
        assert thread_dict['max_iterations'] == 7
        
        restored = Thread.from_dict(thread_dict)
        assert restored.max_iterations == 7
        assert restored.processed_finding_indices == {1, 3}
    
    def test_ar_iteration_data_fields(self):
        """Test ARIterationData fields and defaults."""
        ar_data = ARIterationData(
            findings=[Finding(validation_output='SATISFIABLE', details={})],
            validation_output='SATISFIABLE'
        )
        assert ar_data.processed_finding_index == 0
        assert ar_data.llm_decision == 'REWRITE'
        assert ar_data.iteration_type == 'rewriting'
    
    def test_backward_compatibility(self):
        """Test backward compatibility with old thread format."""
        old_data = {
            'thread_id': 'old-123',
            'user_prompt': 'Old prompt',
            'model_id': 'old-model',
            'status': 'COMPLETED',
            'schema_version': '1.0',
            'iterations': [],
            'created_at': '2024-01-01T00:00:00+00:00'
        }
        thread = Thread.from_dict(old_data)
        assert thread.max_iterations == 5
        assert thread.processed_finding_indices == set()
        assert thread.schema_version == '2.0'
