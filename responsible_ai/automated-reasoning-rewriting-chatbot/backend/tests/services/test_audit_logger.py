"""
Tests for the audit logger service.
"""
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from backend.services.audit_logger import AuditLogger
from backend.models.thread import Thread, Finding, ThreadStatus


class TestAuditLogger:
    """Test suite for AuditLogger class."""
    
    def test_log_valid_response_writes_to_file(self, tmp_path):
        """Test that log_valid_response writes a structured JSON entry to the audit log."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="test-thread-123",
            user_prompt="What is 2+2?",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="2+2 equals 4",
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        findings = [
            Finding(
                validation_output="VALID",
                details={"property": "arithmetic_correctness"}
            )
        ]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        assert audit_log_path.exists()
        
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert log_entry["event_type"] == "VALID_RESPONSE"
        assert log_entry["thread_id"] == "test-thread-123"
        assert log_entry["prompt"] == "What is 2+2?"
        assert log_entry["response"] == "2+2 equals 4"
        assert log_entry["model_id"] == "claude-3"
        assert len(log_entry["findings"]) == 1
        assert log_entry["findings"][0]["validation_output"] == "VALID"
        assert "timestamp" in log_entry
    
    def test_log_valid_response_includes_all_required_fields(self, tmp_path):
        """Test that VALID audit entries contain all required fields."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="thread-456",
            user_prompt="Test prompt",
            model_id="test-model",
            status=ThreadStatus.COMPLETED,
            final_response="Test response"
        )
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        # Verify all required fields are present
        required_fields = ["timestamp", "thread_id", "prompt", "response", "findings"]
        for field in required_fields:
            assert field in log_entry, f"Missing required field: {field}"
    
    def test_log_max_iterations_writes_to_file(self, tmp_path):
        """Test that log_max_iterations writes a structured JSON entry with summaries."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="test-thread-789",
            user_prompt="Complex question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Final attempt response",
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        iteration_summaries = [
            "Iteration 1: INVALID - arithmetic error",
            "Iteration 2: INVALID - logic error",
            "Iteration 3: SATISFIABLE - partial correctness",
            "Iteration 4: INVALID - boundary condition",
            "Iteration 5: INVALID - still incorrect"
        ]
        
        last_finding = Finding(
            validation_output="INVALID",
            details={
                "property": "correctness",
                "explanation": "Response still contains errors"
            }
        )
        
        # Act
        logger.log_max_iterations(thread, iteration_summaries, last_finding)
        
        # Assert
        assert audit_log_path.exists()
        
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert log_entry["event_type"] == "MAX_ITERATIONS_REACHED"
        assert log_entry["thread_id"] == "test-thread-789"
        assert log_entry["prompt"] == "Complex question"
        assert log_entry["response"] == "Final attempt response"
        assert log_entry["model_id"] == "claude-3"
        assert len(log_entry["iteration_summaries"]) == 5
        assert log_entry["last_finding"]["validation_output"] == "INVALID"
        assert "timestamp" in log_entry
    
    def test_log_max_iterations_includes_all_required_fields(self, tmp_path):
        """Test that max iterations audit entries contain all required fields."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="thread-999",
            user_prompt="Test prompt",
            model_id="test-model",
            status=ThreadStatus.COMPLETED,
            final_response="Test response"
        )
        
        iteration_summaries = ["Summary 1", "Summary 2"]
        last_finding = Finding(validation_output="INVALID", details={})
        
        # Act
        logger.log_max_iterations(thread, iteration_summaries, last_finding)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        # Verify all required fields are present
        required_fields = [
            "timestamp", "thread_id", "prompt", "response",
            "iteration_summaries", "last_finding"
        ]
        for field in required_fields:
            assert field in log_entry, f"Missing required field: {field}"
    
    def test_multiple_log_entries_append_to_file(self, tmp_path):
        """Test that multiple log entries are appended to the same file."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        thread1 = Thread(
            thread_id="thread-1",
            user_prompt="Question 1",
            model_id="model-1",
            status=ThreadStatus.COMPLETED,
            final_response="Answer 1"
        )
        
        thread2 = Thread(
            thread_id="thread-2",
            user_prompt="Question 2",
            model_id="model-2",
            status=ThreadStatus.COMPLETED,
            final_response="Answer 2"
        )
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        logger.log_valid_response(thread1, findings)
        logger.log_valid_response(thread2, findings)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        
        assert entry1["thread_id"] == "thread-1"
        assert entry2["thread_id"] == "thread-2"
    
    def test_log_valid_response_handles_write_failure(self, tmp_path, caplog):
        """Test that write failures are logged to application log."""
        # Arrange
        # Create a directory where the file should be, making it impossible to write
        audit_log_path = tmp_path / "audit.log"
        audit_log_path.mkdir()  # Create as directory instead of file
        
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="thread-error",
            user_prompt="Test",
            model_id="model",
            status=ThreadStatus.COMPLETED,
            final_response="Response"
        )
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        with caplog.at_level(logging.ERROR):
            logger.log_valid_response(thread, findings)
        
        # Assert - should log error without raising exception
        assert any("Failed to write VALID response audit log" in record.message 
                   for record in caplog.records)
        assert any("thread-error" in record.message 
                   for record in caplog.records)
    
    def test_log_max_iterations_handles_write_failure(self, tmp_path, caplog):
        """Test that write failures for max iterations are logged to application log."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        audit_log_path.mkdir()  # Create as directory instead of file
        
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="thread-error-2",
            user_prompt="Test",
            model_id="model",
            status=ThreadStatus.COMPLETED,
            final_response="Response"
        )
        
        iteration_summaries = ["Summary"]
        last_finding = Finding(validation_output="INVALID", details={})
        
        # Act
        with caplog.at_level(logging.ERROR):
            logger.log_max_iterations(thread, iteration_summaries, last_finding)
        
        # Assert - should log error without raising exception
        assert any("Failed to write max iterations audit log" in record.message 
                   for record in caplog.records)
        assert any("thread-error-2" in record.message 
                   for record in caplog.records)
    
    def test_audit_log_separate_from_application_log(self, tmp_path):
        """Test that audit log is maintained separately from application log."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        app_log_path = tmp_path / "app.log"
        
        # Configure application logger to write to separate file
        app_logger = logging.getLogger("backend.services.audit_logger")
        handler = logging.FileHandler(str(app_log_path))
        app_logger.addHandler(handler)
        
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="thread-separate",
            user_prompt="Test",
            model_id="model",
            status=ThreadStatus.COMPLETED,
            final_response="Response"
        )
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        assert audit_log_path.exists()
        
        # Audit log should contain JSON entry
        with open(audit_log_path, 'r') as f:
            audit_content = f.read()
        
        assert "thread-separate" in audit_content
        assert json.loads(audit_content.strip())  # Should be valid JSON
        
        # Clean up
        app_logger.removeHandler(handler)
        handler.close()
    
    def test_log_valid_response_with_multiple_findings(self, tmp_path):
        """Test logging VALID response with multiple findings."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        thread = Thread(
            thread_id="thread-multi",
            user_prompt="Multi-property question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Multi-property answer"
        )
        
        findings = [
            Finding(
                validation_output="VALID",
                details={"property": "property1", "check": "passed"}
            ),
            Finding(
                validation_output="VALID",
                details={"property": "property2", "check": "passed"}
            ),
            Finding(
                validation_output="NO_TRANSLATIONS",
                details={"reason": "out of scope"}
            )
        ]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert len(log_entry["findings"]) == 3
        assert log_entry["findings"][0]["validation_output"] == "VALID"
        assert log_entry["findings"][1]["validation_output"] == "VALID"
        assert log_entry["findings"][2]["validation_output"] == "NO_TRANSLATIONS"

    def test_log_valid_response_with_qa_exchange(self, tmp_path):
        """Test that log_valid_response includes Q&A exchanges from iterations."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        from backend.models.thread import TypedIteration, IterationType, ClarificationIterationData, QuestionAnswerExchange
        
        thread = Thread(
            thread_id="thread-qa-1",
            user_prompt="Ambiguous question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Clarified answer"
        )
        
        # Add iteration with Q&A exchange
        qa_exchange = QuestionAnswerExchange(
            questions=["What do you mean by X?", "Are you asking about Y or Z?"],
            answers=["I mean X in context A", "I'm asking about Y"],
            skipped=False
        )
        
        iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer="Original answer",
            rewritten_answer="I need clarification...",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange,
                context_augmentation=None
            )
        )
        
        thread.iterations.append(iteration)
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert "qa_exchanges" in log_entry
        assert len(log_entry["qa_exchanges"]) == 1
        
        qa_entry = log_entry["qa_exchanges"][0]
        assert qa_entry["iteration_number"] == 1
        assert qa_entry["clarification_requested"] is True
        assert qa_entry["skipped"] is False
        assert len(qa_entry["questions"]) == 2
        assert len(qa_entry["answers"]) == 2
        assert qa_entry["questions"][0] == "What do you mean by X?"
        assert qa_entry["answers"][0] == "I mean X in context A"
        
        # Check formatted Q&A pairs
        assert "qa_pairs" in qa_entry
        assert len(qa_entry["qa_pairs"]) == 2
        assert qa_entry["qa_pairs"][0]["Q"] == "What do you mean by X?"
        assert qa_entry["qa_pairs"][0]["A"] == "I mean X in context A"
    
    def test_log_valid_response_with_skipped_qa(self, tmp_path):
        """Test that log_valid_response handles skipped Q&A exchanges."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        from backend.models.thread import TypedIteration, IterationType, ClarificationIterationData, QuestionAnswerExchange
        
        thread = Thread(
            thread_id="thread-qa-skip",
            user_prompt="Question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Answer"
        )
        
        # Add iteration with skipped Q&A exchange
        qa_exchange = QuestionAnswerExchange(
            questions=["Question 1?", "Question 2?"],
            answers=None,
            skipped=True
        )
        
        iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer="Original answer",
            rewritten_answer="I need clarification...",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange,
                context_augmentation=None
            )
        )
        
        thread.iterations.append(iteration)
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert "qa_exchanges" in log_entry
        qa_entry = log_entry["qa_exchanges"][0]
        assert qa_entry["skipped"] is True
        assert qa_entry["answers"] is None
        assert qa_entry["note"] == "User skipped answering questions"
        assert "qa_pairs" not in qa_entry
    
    def test_log_valid_response_without_qa_exchange(self, tmp_path):
        """Test that log_valid_response works without Q&A exchanges."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        from backend.models.thread import TypedIteration, IterationType, ARIterationData
        
        thread = Thread(
            thread_id="thread-no-qa",
            user_prompt="Simple question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Simple answer"
        )
        
        # Add iteration without Q&A exchange (AR feedback iteration)
        iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.AR_FEEDBACK,
            original_answer="Original answer",
            rewritten_answer="Answer",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ARIterationData(
                findings=[],
                validation_output="VALID"
            )
        )
        
        thread.iterations.append(iteration)
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        # Should not include qa_exchanges field when there are none
        assert "qa_exchanges" not in log_entry
    
    def test_log_max_iterations_with_qa_exchange(self, tmp_path):
        """Test that log_max_iterations includes Q&A exchanges in summaries."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        from backend.models.thread import TypedIteration, IterationType, ClarificationIterationData, ARIterationData, QuestionAnswerExchange
        
        thread = Thread(
            thread_id="thread-max-qa",
            user_prompt="Complex question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Final attempt"
        )
        
        # Add multiple iterations, some with Q&A
        qa_exchange1 = QuestionAnswerExchange(
            questions=["Clarify X?"],
            answers=["X means A"],
            skipped=False
        )
        
        iteration1 = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer="Original answer",
            rewritten_answer="Need clarification",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange1,
                context_augmentation=None
            )
        )
        
        iteration2 = TypedIteration(
            iteration_number=2,
            iteration_type=IterationType.AR_FEEDBACK,
            original_answer="Need clarification",
            rewritten_answer="Still wrong",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ARIterationData(
                findings=[],
                validation_output="INVALID"
            )
        )
        
        qa_exchange3 = QuestionAnswerExchange(
            questions=["Another question?"],
            answers=None,
            skipped=True
        )
        
        iteration3 = TypedIteration(
            iteration_number=3,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer="Still wrong",
            rewritten_answer="More questions",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange3,
                context_augmentation=None
            )
        )
        
        thread.iterations.extend([iteration1, iteration2, iteration3])
        
        iteration_summaries = [
            "Iteration 1: TRANSLATION_AMBIGUOUS - needed clarification",
            "Iteration 2: INVALID - still incorrect",
            "Iteration 3: SATISFIABLE - partial correctness"
        ]
        
        last_finding = Finding(validation_output="SATISFIABLE", details={})
        
        # Act
        logger.log_max_iterations(thread, iteration_summaries, last_finding)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert "qa_exchanges" in log_entry
        assert len(log_entry["qa_exchanges"]) == 2
        
        # Check first Q&A exchange
        qa1 = log_entry["qa_exchanges"][0]
        assert qa1["iteration_number"] == 1
        assert qa1["clarification_requested"] is True
        assert qa1["skipped"] is False
        assert len(qa1["qa_pairs"]) == 1
        
        # Check second Q&A exchange (skipped)
        qa2 = log_entry["qa_exchanges"][1]
        assert qa2["iteration_number"] == 3
        assert qa2["skipped"] is True
        assert qa2["note"] == "User skipped answering questions"
    
    def test_log_max_iterations_without_qa_exchange(self, tmp_path):
        """Test that log_max_iterations works without Q&A exchanges."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        from backend.models.thread import TypedIteration, IterationType, ARIterationData
        
        thread = Thread(
            thread_id="thread-max-no-qa",
            user_prompt="Question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Final"
        )
        
        iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.AR_FEEDBACK,
            original_answer="Original answer",
            rewritten_answer="Response",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ARIterationData(
                findings=[],
                validation_output="INVALID"
            )
        )
        
        thread.iterations.append(iteration)
        
        iteration_summaries = ["Iteration 1: INVALID"]
        last_finding = Finding(validation_output="INVALID", details={})
        
        # Act
        logger.log_max_iterations(thread, iteration_summaries, last_finding)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        # Should not include qa_exchanges field when there are none
        assert "qa_exchanges" not in log_entry
    
    def test_qa_exchange_clarification_indicator(self, tmp_path):
        """Test that Q&A exchanges have clear clarification indicators."""
        # Arrange
        audit_log_path = tmp_path / "audit.log"
        logger = AuditLogger(str(audit_log_path))
        
        from backend.models.thread import TypedIteration, IterationType, ClarificationIterationData, QuestionAnswerExchange
        
        thread = Thread(
            thread_id="thread-indicator",
            user_prompt="Question",
            model_id="claude-3",
            status=ThreadStatus.COMPLETED,
            final_response="Answer"
        )
        
        qa_exchange = QuestionAnswerExchange(
            questions=["Q1?"],
            answers=["A1"],
            skipped=False
        )
        
        iteration = TypedIteration(
            iteration_number=1,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer="Original answer",
            rewritten_answer="Response",
            rewriting_prompt="Rewrite prompt",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange,
                context_augmentation=None
            )
        )
        
        thread.iterations.append(iteration)
        
        findings = [Finding(validation_output="VALID", details={})]
        
        # Act
        logger.log_valid_response(thread, findings)
        
        # Assert
        with open(audit_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        qa_entry = log_entry["qa_exchanges"][0]
        # Verify clear indicators for user clarification
        assert "clarification_requested" in qa_entry
        assert qa_entry["clarification_requested"] is True
        assert "iteration_number" in qa_entry
        assert qa_entry["iteration_number"] == 1
