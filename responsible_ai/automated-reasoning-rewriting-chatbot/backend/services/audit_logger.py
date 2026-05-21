"""
Audit logger for recording validation findings in the AR Chatbot.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from backend.models.thread import Thread, Finding


# Configure application logger
logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Handles audit logging for validated responses.
    
    This class writes structured JSON logs to a separate audit.log file,
    recording validation findings for VALID responses and summaries when
    maximum iterations are reached.
    """
    
    def __init__(self, audit_log_path: str = "audit.log"):
        """
        Initialize the audit logger.
        
        Args:
            audit_log_path: Path to the audit log file (default: "audit.log")
        """
        self.audit_log_path = Path(audit_log_path)
        
    def log_valid_response(self, thread: Thread, findings: List[Finding]) -> None:
        """
        Log a VALID response with its validation findings to the audit log.
        
        Args:
            thread: The thread containing the validated response
            findings: List of validation findings from the AR checks
        """
        try:
            audit_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "VALID_RESPONSE",
                "thread_id": thread.thread_id,
                "prompt": thread.user_prompt,
                "response": thread.final_response,
                "model_id": thread.model_id,
                "findings": [f.to_dict() for f in findings]
            }
            
            # Include Q&A exchanges from iterations if present
            qa_exchanges = self._extract_qa_exchanges(thread)
            if qa_exchanges:
                audit_entry["qa_exchanges"] = qa_exchanges
            
            self._write_audit_entry(audit_entry)
            
        except Exception as e:
            logger.error(
                f"Failed to write VALID response audit log for thread {thread.thread_id}: {e}",
                exc_info=True
            )
    
    def log_max_iterations(
        self, 
        thread: Thread, 
        iteration_summaries: List[str], 
        last_finding: Finding
    ) -> None:
        """
        Log a summary when maximum iterations are reached without achieving VALID.
        
        Args:
            thread: The thread that reached maximum iterations
            iteration_summaries: High-level summaries of findings from each iteration
            last_finding: The complete finding from the last iteration
        """
        try:
            audit_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "MAX_ITERATIONS_REACHED",
                "thread_id": thread.thread_id,
                "prompt": thread.user_prompt,
                "response": thread.final_response,
                "model_id": thread.model_id,
                "iteration_summaries": iteration_summaries,
                "last_finding": last_finding.to_dict()
            }
            
            # Include Q&A exchanges from iterations if present
            qa_exchanges = self._extract_qa_exchanges(thread)
            if qa_exchanges:
                audit_entry["qa_exchanges"] = qa_exchanges
            
            self._write_audit_entry(audit_entry)
            
        except Exception as e:
            logger.error(
                f"Failed to write max iterations audit log for thread {thread.thread_id}: {e}",
                exc_info=True
            )
    
    def _extract_qa_exchanges(self, thread: Thread) -> List[Dict[str, Any]]:
        """
        Extract Q&A exchanges from thread iterations with clear indicators.
        
        Args:
            thread: The thread to extract Q&A exchanges from
            
        Returns:
            List of formatted Q&A exchange dictionaries with iteration context
        """
        from backend.models.thread import IterationType, ClarificationIterationData
        
        qa_exchanges = []
        
        for iteration in thread.iterations:
            # Check if this is a clarification iteration with QA exchange
            if (iteration.iteration_type == IterationType.USER_CLARIFICATION and 
                isinstance(iteration.type_specific_data, ClarificationIterationData)):
                qa_exchange = iteration.type_specific_data.qa_exchange
                
                exchange_entry = {
                    "iteration_number": iteration.iteration_number,
                    "clarification_requested": True,
                    "questions": qa_exchange.questions,
                    "skipped": qa_exchange.skipped
                }
                
                if qa_exchange.skipped:
                    exchange_entry["answers"] = None
                    exchange_entry["note"] = "User skipped answering questions"
                else:
                    exchange_entry["answers"] = qa_exchange.answers
                    # Format Q&A pairs for readability
                    qa_pairs = []
                    for i, question in enumerate(qa_exchange.questions):
                        answer = qa_exchange.answers[i] if qa_exchange.answers else None
                        qa_pairs.append({
                            "Q": question,
                            "A": answer
                        })
                    exchange_entry["qa_pairs"] = qa_pairs
                
                qa_exchanges.append(exchange_entry)
        
        return qa_exchanges
    
    def _write_audit_entry(self, entry: Dict[str, Any]) -> None:
        """
        Write an audit entry to the audit log file.
        
        Args:
            entry: The audit entry dictionary to write
            
        Raises:
            Exception: If writing to the audit log fails
        """
        with open(self.audit_log_path, 'a', encoding='utf-8') as f:
            json.dump(entry, f)
            f.write('\n')
