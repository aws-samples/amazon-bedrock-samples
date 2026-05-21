"""
Timeout handler for managing stale AWAITING_USER_INPUT threads.

This module provides a background task that periodically checks for threads
that have been awaiting user input for too long and automatically skips
their questions to continue validation.
"""
import logging
import threading
import time
from typing import Optional

from backend.services.thread_manager import ThreadManager
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService
from backend.models.thread import ThreadStatus, IterationType, ClarificationIterationData
from backend.services.audit_logger import AuditLogger
from backend.services.policy_service import PolicyService
from backend.services.thread_processor import resume_thread_with_answers

logger = logging.getLogger(__name__)


class TimeoutHandler:
    """
    Handles timeout for threads awaiting user input.
    
    This class runs a background task that periodically checks for threads
    that have been in AWAITING_USER_INPUT status for longer than the timeout
    period and automatically skips their questions.
    """
    
    def __init__(
        self,
        thread_manager: ThreadManager,
        timeout_minutes: int = 10,
        check_interval_seconds: int = 60
    ):
        """
        Initialize the timeout handler.
        
        Args:
            thread_manager: ThreadManager instance to check for stale threads
            timeout_minutes: Number of minutes before auto-skipping (default: 10)
            check_interval_seconds: How often to check for stale threads (default: 60)
        """
        self.thread_manager = thread_manager
        self.timeout_minutes = timeout_minutes
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self) -> None:
        """Start the background timeout checking task."""
        if self._running:
            logger.warning("TimeoutHandler is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(
            f"TimeoutHandler started (timeout: {self.timeout_minutes} minutes, "
            f"check interval: {self.check_interval_seconds} seconds)"
        )
    
    def stop(self) -> None:
        """Stop the background timeout checking task."""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("TimeoutHandler stopped")
    
    def _run(self) -> None:
        """Main loop for checking stale threads."""
        while self._running and not self._stop_event.is_set():
            try:
                self._check_and_handle_timeouts()
            except Exception as e:
                logger.error(f"Error in timeout handler: {e}", exc_info=True)
            
            # Wait for the check interval or until stop is requested
            self._stop_event.wait(self.check_interval_seconds)
    
    def _check_and_handle_timeouts(self) -> None:
        """Check for stale threads and handle timeouts."""
        stale_threads = self.thread_manager.get_stale_awaiting_threads(self.timeout_minutes)
        
        if not stale_threads:
            return
        
        logger.info(f"Found {len(stale_threads)} stale thread(s) awaiting user input")
        
        for thread in stale_threads:
            try:
                self._handle_timeout(thread.thread_id)
            except Exception as e:
                logger.error(
                    f"Error handling timeout for thread {thread.thread_id}: {e}",
                    exc_info=True
                )
    
    def _handle_timeout(self, thread_id: str) -> None:
        """
        Handle timeout for a specific thread by auto-skipping questions.
        
        This method marks the questions as skipped and triggers the resume callback
        if one is registered.
        
        Args:
            thread_id: The thread identifier
        """
        logger.info(f"Thread {thread_id} - Timeout reached, auto-skipping questions")
        
        # Get the thread to log timeout event
        thread = self.thread_manager.get_thread(thread_id)
        if not thread:
            logger.warning(f"Thread {thread_id} not found during timeout handling")
            return
        
        # Log timeout event
        logger.warning(
            f"Thread {thread_id} - User did not respond within {self.timeout_minutes} minutes. "
            f"Auto-skipping questions and continuing validation."
        )
        
        # Get the last iteration with questions
        if not thread.iterations:
            logger.error(f"Thread {thread_id} has no iterations during timeout")
            return
        
        last_iteration = thread.iterations[-1]
        
        # Verify it's a clarification iteration
        if last_iteration.iteration_type != IterationType.USER_CLARIFICATION:
            logger.error(
                f"Thread {thread_id} last iteration is not a clarification iteration during timeout. "
                f"Type: {last_iteration.iteration_type}"
            )
            return
        
        # Get the clarification data
        clar_data = last_iteration.type_specific_data
        if not isinstance(clar_data, ClarificationIterationData):
            logger.error(f"Thread {thread_id} has invalid clarification data during timeout")
            return
        
        # Mark questions as skipped in the thread data
        clar_data.qa_exchange.skipped = True
        clar_data.qa_exchange.answers = None
        
        # Call the resume callback if registered
        if hasattr(self, '_resume_callback') and self._resume_callback:
            try:
                logger.info(f"Thread {thread_id} - Calling resume callback for auto-skip")
                self._resume_callback(thread_id, [], True)
            except Exception as e:
                logger.error(
                    f"Thread {thread_id} - Error calling resume callback: {e}",
                    exc_info=True
                )
        else:
            logger.warning(
                f"Thread {thread_id} - No resume callback registered. "
                f"Questions marked as skipped but thread not resumed."
            )
    
    def set_resume_callback(self, callback):
        """
        Set a callback function to resume threads after timeout.
        
        The callback should accept (thread_id: str, answers: List[str], skipped: bool).
        
        Args:
            callback: Function to call when resuming a thread after timeout
        """
        self._resume_callback = callback
        logger.info("Resume callback registered for timeout handler")


def create_timeout_handler(
    thread_manager: ThreadManager,
    timeout_minutes: int = 10,
    check_interval_seconds: int = 60
) -> TimeoutHandler:
    """
    Create and start a timeout handler.
    
    Args:
        thread_manager: ThreadManager instance
        timeout_minutes: Timeout in minutes (default: 10)
        check_interval_seconds: Check interval in seconds (default: 60)
        
    Returns:
        Started TimeoutHandler instance
    """
    handler = TimeoutHandler(thread_manager, timeout_minutes, check_interval_seconds)
    handler.start()
    return handler
