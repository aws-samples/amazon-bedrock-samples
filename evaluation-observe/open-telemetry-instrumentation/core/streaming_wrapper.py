"""
Streaming wrapper for Bedrock Agent responses.
This module handles streaming responses from Bedrock Agent,
processing traces and completions as they are received.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
from wrapt import ObjectProxy

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .constants import SpanAttributes

# Add this import
from .agent import process_trace_event

# Initialize logging
logger = logging.getLogger(__name__)

def json_safe(obj):
    """Convert object to JSON-safe format, handling complex types."""
    if isinstance(obj, dict):
        return json.dumps(obj)
    return obj

class AgentStreamingWrapper(ObjectProxy):
    """Wrapper for Bedrock Agent streaming responses using wrapt.ObjectProxy."""

    def __init__(self, response, root_span=None, stream_done_callback=None):
        """
        Initialize the streaming wrapper.

        Args:
            response: The streaming response from Bedrock Agent
            root_span: The root OpenTelemetry span for the agent invocation
            stream_done_callback: Optional callback to execute after stream completes
        """
        super().__init__(response)
        self._root_span = root_span
        self._stream_done_callback = stream_done_callback
        self._completion_data = {"chunks": [], "traces": []}
        self._chunk_count = 0
        self._current_chunk = ""  # Current chunk for association with traces

        # Record metadata in root span
        if self._root_span:
            self._root_span.set_attribute("streaming", True)
            self._root_span.set_attribute("metadata.streaming", True)
            self._root_span.set_attribute(
                "streaming.start_time", datetime.now().isoformat()
            )

    def __iter__(self):
        """Process events while yielding them."""
        for event in self.__wrapped__:
            self._process_event(event)
            yield event

        # After all events are processed, handle end of stream
        self._handle_end_of_stream()

    def _handle_end_of_stream(self):
        """Handle the end of the stream."""
        # Process any buffered guardrails
        self._process_remaining_guardrails()

        # Update root span with final metrics
        if self._root_span:
            self._root_span.set_attribute("streaming.complete", True)
            self._root_span.set_attribute(
                "streaming.end_time", datetime.now().isoformat()
            )

        # Join collected chunks to create the complete answer
        answer_text = "".join(self._completion_data["chunks"])

        # Update root span with the complete response
        if self._root_span:
            self._root_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, answer_text)
            self._root_span.set_attribute(
                "streaming.total_chunks", len(self._completion_data["chunks"])
            )

        # Call completion callback if provided
        if self._stream_done_callback:
            self._stream_done_callback(self._completion_data)

    def _process_remaining_guardrails(self):
        """Process remaining guardrails at the end of the stream."""
        if not self._root_span:
            return

        # Import here to avoid circular imports
        from .handlers import process_guardrail_buffer
        from .agent import guardrail_buffer, span_manager

        # Process guardrails using handler
        if guardrail_buffer:
            process_guardrail_buffer(guardrail_buffer, self._root_span)

        # Also process from span manager's buffer
        if span_manager.guardrail_buffer:
            process_guardrail_buffer(span_manager.guardrail_buffer, self._root_span)

        # Clear buffers after processing
        guardrail_buffer.clear()
        span_manager.guardrail_buffer.clear()

    def _process_event(self, event):
        """
        Process a single event from the stream.

        Args:
            event: Event from the Bedrock Agent stream
        """
        try:
            # Convert event to dict if needed
            if hasattr(event, "to_dict"):
                event = event.to_dict()

            # Process text chunks
            if "chunk" in event:
                chunk_data = event["chunk"]
                if "bytes" in chunk_data:
                    output_bytes = chunk_data["bytes"]
                    # Convert bytes to string if needed
                    if isinstance(output_bytes, bytes):
                        output_text = output_bytes.decode("utf-8")
                    else:
                        output_text = str(output_bytes)

                    # Track chunks
                    self._chunk_count += 1
                    self._current_chunk = output_text
                    self._completion_data["chunks"].append(output_text)

                    # Update root span with basic metrics (don't overload with every chunk)
                    if self._root_span and self._chunk_count % 10 == 0:
                        self._root_span.set_attribute(
                            "streaming.chunks_received", self._chunk_count
                        )

            # Process trace events
            elif "trace" in event:
                self._completion_data["traces"].append(event["trace"])

                # Process trace through agent's process_trace_event
                if self._root_span:
                    from .agent import process_trace_event

                    try:
                        process_trace_event(event["trace"], self._root_span)
                    except Exception as e:
                        logger.error(
                            f"Error processing trace event in streaming: {str(e)}",
                            exc_info=True,
                        )

        except Exception as e:
            logger.error(f"Error processing streaming event: {str(e)}", exc_info=True)


def wrap_streaming_response(response, root_span=None):
    """
    Wrap streaming response with our streaming wrapper.

    Args:
        response: The response from Bedrock Agent
        root_span: The root OpenTelemetry span

    Returns:
        Wrapped response with streaming handler
    """
    if not isinstance(response, dict) or "completion" not in response:
        return response

    def on_stream_complete(completion_data):
        """Callback when stream is complete."""
        try:
            # Join collected chunks to create the complete answer
            answer_text = "".join(completion_data["chunks"])

            # Update root span with the complete response
            if root_span:
                root_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, answer_text)
                root_span.set_attribute(
                    "streaming.chunks", len(completion_data["chunks"])
                )
                root_span.set_attribute("streaming.completed", True)

                # Clean up spans
                from .agent import span_manager

                span_manager.reset()

                # Set end time
                end_timestamp, end_time_iso = (
                    time.time(),
                    datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                )
                root_span.set_attribute(SpanAttributes.LANGFUSE_END_TIME, end_time_iso)

                # Set final status
                root_span.set_status(Status(StatusCode.OK))

        except Exception as e:
            logger.error(f"Error in stream complete callback: {str(e)}", exc_info=True)

    # Wrap the completion with our wrapper
    wrapped = AgentStreamingWrapper(
        response["completion"],
        root_span=root_span,
        stream_done_callback=on_stream_complete,
    )

    # Replace the completion with our wrapped version
    response["completion"] = wrapped
    return response