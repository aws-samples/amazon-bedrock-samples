"""
Thread manager for handling conversation threads in the AR Chatbot.
"""
from threading import Lock
from typing import Dict, List, Optional
from datetime import datetime as dt
import datetime

from backend.models.thread import Thread, Iteration, ThreadStatus, TypedIteration


class ThreadManager:
    """
    Manages conversation threads with thread-safe operations.
    
    This class provides thread-safe methods for creating, retrieving, updating,
    and listing conversation threads. It uses a lock to ensure concurrent access
    is handled correctly.
    """
    
    def __init__(self):
        """Initialize the thread manager with an empty thread store."""
        self._threads: Dict[str, Thread] = {}
        self._lock = Lock()
    
    def create_thread(self, prompt: str, model_id: str) -> Thread:
        """
        Create a new conversation thread.
        
        Args:
            prompt: The user's prompt that initiates the thread
            model_id: The LLM model ID to use for this thread
            
        Returns:
            The newly created Thread object
        """
        with self._lock:
            thread_id = Thread.generate_id()
            thread = Thread(
                thread_id=thread_id,
                user_prompt=prompt,
                model_id=model_id,
                status=ThreadStatus.PROCESSING,
                created_at=dt.now(datetime.UTC)
            )
            self._threads[thread_id] = thread
            return thread
    
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """
        Retrieve a thread by its ID.
        
        Args:
            thread_id: The unique identifier of the thread
            
        Returns:
            The Thread object if found, None otherwise
        """
        with self._lock:
            return self._threads.get(thread_id)
    
    def update_thread(self, thread_id: str, iteration: TypedIteration) -> bool:
        """
        Update a thread by adding a new iteration.
        
        Args:
            thread_id: The unique identifier of the thread
            iteration: The typed iteration to add to the thread
            
        Returns:
            True if the thread was updated successfully, False if thread not found
        """
        with self._lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                return False
            
            thread.iterations.append(iteration)
            return True
    
    def list_threads(self) -> List[Thread]:
        """
        List all threads.
        
        Returns:
            A list of all Thread objects
        """
        with self._lock:
            return list(self._threads.values())
    
    def update_thread_status(
        self, 
        thread_id: str, 
        status: ThreadStatus,
        final_response: Optional[str] = None,
        warning_message: Optional[str] = None
    ) -> bool:
        """
        Update the status and optional fields of a thread.
        
        Args:
            thread_id: The unique identifier of the thread
            status: The new status for the thread
            final_response: Optional final response to set
            warning_message: Optional warning message to set
            
        Returns:
            True if the thread was updated successfully, False if thread not found
        """
        with self._lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                return False
            
            thread.status = status
            if final_response is not None:
                thread.final_response = final_response
            if warning_message is not None:
                thread.warning_message = warning_message
            if status in (ThreadStatus.COMPLETED, ThreadStatus.ERROR):
                thread.completed_at = dt.now(datetime.UTC)
                thread.awaiting_input_since = None  # Clear timestamp when completed
            elif status == ThreadStatus.AWAITING_USER_INPUT:
                thread.awaiting_input_since = dt.now(datetime.UTC)  # Set timestamp when awaiting input
            elif status == ThreadStatus.PROCESSING and thread.awaiting_input_since is not None:
                thread.awaiting_input_since = None  # Clear timestamp when resuming processing
            
            return True
    
    def get_stale_awaiting_threads(self, timeout_minutes: int = 10) -> List[Thread]:
        """
        Get threads that have been awaiting user input for longer than the timeout.
        
        Args:
            timeout_minutes: Number of minutes before a thread is considered stale (default: 10)
            
        Returns:
            List of threads that have exceeded the timeout
        """
        with self._lock:
            stale_threads = []
            now = dt.now(datetime.UTC)
            timeout_delta = datetime.timedelta(minutes=timeout_minutes)
            
            for thread in self._threads.values():
                if (thread.status == ThreadStatus.AWAITING_USER_INPUT and 
                    thread.awaiting_input_since is not None):
                    time_waiting = now - thread.awaiting_input_since
                    if time_waiting >= timeout_delta:
                        stale_threads.append(thread)
            
            return stale_threads
