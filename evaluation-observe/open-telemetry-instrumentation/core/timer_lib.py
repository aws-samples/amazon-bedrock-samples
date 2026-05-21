import time
import logging
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional, Any

# Initialize logging
logger = logging.getLogger(__name__)

class FunctionTimer:
    def __init__(self):
        """Initialize the timer storage."""
        self._timers: Dict[Tuple[str, str], float] = {}

    def start(
        self, function_name: str, trace_id: str, start_time: Optional[float] = None
    ) -> float:
        """
        Set the start time for a function/trace_id combination if it's not already set.

        Args:
            function_name: The name of the function to track
            trace_id: Unique trace identifier for this execution context
            start_time: Optional custom start time, defaults to current time if None

        Returns:
            The start time value
        """
        key = (function_name, trace_id)
        if key not in self._timers:
            self._timers[key] = start_time if start_time is not None else time.time()
        return self._timers[key]

    def _to_iso_format(self, timestamp: float) -> str:
        """Convert a timestamp to ISO 8601 format without timezone info."""
        return (
            datetime.fromtimestamp(timestamp, tz=timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
        )

    def end(self, function_name: str, trace_id: str) -> Tuple[str, str, float]:
        """
        Record the end time (always current time) and calculate the duration in milliseconds.

        Args:
            function_name: The name of the function to track
            trace_id: Unique trace identifier for this execution context

        Returns:
            Tuple of (start_time_iso, end_time_iso, duration_ms)
            where duration_ms is the duration in milliseconds

        Raises:
            KeyError: If start() was not called for this function/trace_id
        """
        key = (function_name, trace_id)
        if key not in self._timers:
            raise KeyError(
                f"No start time recorded for function {function_name} with trace_id {trace_id}"
            )

        start_time = self._timers[key]
        end_time = time.time()

        # Calculate duration in milliseconds (seconds * 1000)
        duration_ms = (end_time - start_time) * 1000

        if duration_ms < 0:
            duration_ms = -1 * duration_ms

        # Convert timestamps to ISO format
        start_time_iso = self._to_iso_format(start_time)
        end_time_iso = self._to_iso_format(end_time)

        return start_time_iso, end_time_iso, duration_ms

    def reset(self, function_name: str, trace_id: str) -> None:
        """
        Reset the timer for a function/trace_id combination.

        Args:
            function_name: The name of the function to reset
            trace_id: Unique trace identifier for this execution context
        """
        key = (function_name, trace_id)
        if key in self._timers:
            del self._timers[key]

    def reset_trace(self, trace_id: str) -> None:
        """
        Reset all timers for a specific trace_id.

        Args:
            trace_id: Unique trace identifier to reset
        """
        keys_to_delete = [key for key in self._timers.keys() if key[1] == trace_id]
        for key in keys_to_delete:
            del self._timers[key]

    def reset_function(self, function_name: str) -> None:
        """
        Reset all timers for a specific function across all trace_ids.

        Args:
            function_name: The name of the function to reset
        """
        keys_to_delete = [key for key in self._timers.keys() if key[0] == function_name]
        for key in keys_to_delete:
            del self._timers[key]

    def reset_all(self) -> None:
        """Reset all timers."""
        self._timers.clear()

    def get_start_time(self, function_name: str, trace_id: str) -> Optional[str]:
        """
        Get the start time for a function/trace_id without modifying it.

        Args:
            function_name: The name of the function
            trace_id: Unique trace identifier for this execution context

        Returns:
            The start time in ISO format or None if not set
        """
        timestamp = self._timers.get((function_name, trace_id))
        return self._to_iso_format(timestamp) if timestamp is not None else None

    def is_started(self, function_name: str, trace_id: str) -> bool:
        """
        Check if a timer is started for a function/trace_id.

        Args:
            function_name: The name of the function
            trace_id: Unique trace identifier for this execution context

        Returns:
            True if timer is started, False otherwise
        """
        return (function_name, trace_id) in self._timers

    def get_all_timers_for_trace(self, trace_id: str) -> Dict[str, str]:
        """
        Get all timers for a specific trace_id.

        Args:
            trace_id: Unique trace identifier for this execution context

        Returns:
            Dictionary mapping function names to their start times in ISO format for this trace_id
        """
        return {
            key[0]: self._to_iso_format(value)
            for key, value in self._timers.items()
            if key[1] == trace_id
        }

    def get_all_timers_for_function(self, function_name: str) -> Dict[str, str]:
        """
        Get all timers for a specific function across all trace_ids.

        Args:
            function_name: The name of the function

        Returns:
            Dictionary mapping trace_ids to their start times in ISO format for this function
        """
        return {
            key[1]: self._to_iso_format(value)
            for key, value in self._timers.items()
            if key[0] == function_name
        }

    def extract_event_time(self, trace_data: Dict[str, Any]) -> Tuple[float, str]:
        """Extract event time from trace data.

        Args:
            trace_data: Dictionary containing trace information with eventTime

        Returns:
            Tuple containing (unix_timestamp, iso8601_string) - uses current time if other times not found
        """
        # Try to get event time directly from the trace data
        event_time = trace_data.get("eventTime")
        if event_time:
            # Handle datetime conversion correctly with timezone
            if isinstance(event_time, datetime):
                try:
                    # Ensure timestamp conversion uses proper timezone handling
                    if event_time.tzinfo is None:
                        # Assume UTC for naive datetime objects
                        event_time = event_time.replace(tzinfo=timezone.utc)

                    timestamp = event_time.timestamp()
                    # Format ISO string according to specified format - convert to UTC, remove tz info, then format
                    time_iso = (
                        datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        .replace(tzinfo=None)
                        .isoformat()
                    )

                    logger.debug(
                        f"Successfully extracted eventTime: {time_iso}, timestamp: {timestamp}"
                    )
                    return timestamp, time_iso
                except Exception as e:
                    logger.warning(f"Error processing eventTime {event_time}: {str(e)}")

        # Return current time as fallback if both eventTime and received_timestamp are not found
        current_time = time.time()
        # Format current time according to the specified format
        current_time_iso = (
            datetime.fromtimestamp(current_time, tz=timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
        )
        logger.debug(f"No event time found, using current time: {current_time_iso}")

        return current_time, current_time_iso

    def check_start_time(
        self, name: str, trace_data: Dict[str, Any], trace_id: str
    ) -> Tuple[Optional[str], Optional[str], Optional[float]]:
        current_start_time, current_start_time_iso = self.extract_event_time(trace_data)
        if self.is_started(name, trace_id):
            start_time, end_time, duration = self.end(name, trace_id)
            return start_time, end_time, duration
        else:
            self.start(name, trace_id, current_start_time)
            start_time, end_time, duration = self.end(name, trace_id)
            return start_time, end_time, duration

    def get_endtime(self) -> Tuple[float, str]:
        """Get the time at which trace part was received"""
        end_timestamp = time.time()
        end_time_iso = (
            datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
        )
        return end_timestamp, end_time_iso


# Create a global instance for easy import
timer = FunctionTimer()