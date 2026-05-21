"""
Agent instrumentation for Bedrock Agent using OpenTelemetry for tracing.
This module processes events as they're received without collecting them.
"""

import json
import logging
import time
from datetime import datetime, timezone
from functools import wraps
import uuid
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind
from .configuration import create_tracer_provider
from .constants import SpanAttributes, SpanKindValues

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry global tracer
tracer = trace.get_tracer("bedrock-agent-tracing")

class DateTimeEncoder(json.JSONEncoder):
    """Helper class to serialize datetime objects to JSON."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
    
# Class to manage spans during processing
class SpanManager:
    """Manages spans and their relationships for the duration of processing."""

    def __init__(self):
        # Main spans dictionary - keyed by component_type:trace_id
        self.spans = {}

        # Track current trace_id for each component
        self.active_traces = {
            "orchestration": None,
            "postprocessing": None,
            "preprocessing": None,
            "guardrail_pre": None,
            "guardrail_post": None,
        }

        # Special spans tracked for direct access
        self.special_spans = {
            "kb_span": None,
            "code_span": None,
            "action_span": None,
            "llm_spans": {},  # Tracks LLM spans by trace_id
        }

        # Buffer for guardrail traces in streaming mode
        self.guardrail_buffer = {}
        # Track which spans have had their times set to prevent overwriting
        self.spans_with_set_times = set()

    def reset(self):
        """Reset the span manager, ending any active spans."""
        # End all active spans
        for span_id, span in list(self.spans.items()):
            if span and hasattr(span, "is_recording") and span.is_recording():
                try:
                    span.set_status(Status(StatusCode.OK))
                    span.end()
                except Exception as e:
                    logger.error(f"Error ending span {span_id}: {e}")

        # Reset all tracking collections
        self.spans.clear()
        self.active_traces = {
            "orchestration": None,
            "postprocessing": None,
            "preprocessing": None,
            "guardrail_pre": None,
            "guardrail_post": None,
        }

        self.special_spans = {
            "kb_span": None,
            "code_span": None,
            "action_span": None,
            "llm_spans": {},
        }

        self.guardrail_buffer.clear()
        self.spans_with_set_times.clear()

    def protect_span_timing(self, span_key: str):
        """Mark a span's timing as protected to prevent overwrites"""
        self.spans_with_set_times.add(span_key)

    def can_set_timing(self, span_key: str) -> bool:
        """Check if timing can be set for this span"""
        return span_key not in self.spans_with_set_times

    def get_or_create_span(
        self,
        component_type: str,
        trace_id: str,
        parent_span,
        attributes=None,
        timing_data=None,
    ):
        span_key = f"{component_type}:{trace_id}"

        # Check existing span
        if span_key in self.spans and self.spans[span_key].is_recording():
            span = self.spans[span_key]

            # Only update timing if allowed and provided
            if timing_data and self.can_set_timing(span_key):
                start_time_iso, end_time_iso, latency_ms = timing_data
                if start_time_iso and end_time_iso:
                    span.set_attribute(
                        SpanAttributes.SPAN_START_TIME, start_time_iso
                    )
                    span.set_attribute(SpanAttributes.SPAN_END_TIME, end_time_iso)
                    span.set_attribute(SpanAttributes.SPAN_DURATION, latency_ms)
                    self.protect_span_timing(span_key)

            return span

        # Create new span with proper context from parent
        span = tracer.start_span(
            name=component_type,
            kind=SpanKind.CLIENT,
            attributes=attributes or {},
            context=trace.set_span_in_context(parent_span),
        )

        # Start the span only if it's not already recording
        if not span.is_recording():
            span.start()

        # Set timing data if provided
        if timing_data:
            start_time_iso, end_time_iso, latency_ms = timing_data

            # Only set if values are valid
            if start_time_iso and end_time_iso:
                span.set_attribute(SpanAttributes.SPAN_START_TIME, start_time_iso)
                span.set_attribute(SpanAttributes.SPAN_END_TIME, end_time_iso)
                span.set_attribute(SpanAttributes.SPAN_DURATION, latency_ms)

                # Mark as having times set
                self.spans_with_set_times.add(span_key)
                logger.debug(f"Set timing on new span {span_key}")

        self.spans[span_key] = span
        self.active_traces[component_type] = trace_id
        return span

    def set_timing_if_not_set(
        self, span_key, span, start_time_iso, end_time_iso, latency_ms
    ):
        """Set timing data on a span if it hasn't been set already."""
        if span_key not in self.spans_with_set_times:
            span.set_attribute(SpanAttributes.SPAN_START_TIME, start_time_iso)
            span.set_attribute(SpanAttributes.SPAN_END_TIME, end_time_iso)
            span.set_attribute(SpanAttributes.SPAN_DURATION, latency_ms)
            self.spans_with_set_times.add(span_key)
            logger.debug(f"Set timing on span {span_key}")
            return True
        return False

    def add_guardrail_event(
        self, base_trace_id: str, trace_data: Dict, content: Optional[str] = None
    ) -> None:
        """Add event to guardrail buffer with associated content chunk"""
        if base_trace_id not in self.guardrail_buffer:
            self.guardrail_buffer[base_trace_id] = []

        # Store event with timestamp and content
        event_data = {
            "trace_data": trace_data,
            "timestamp": datetime.now().isoformat(),
            "content": content,
        }
        self.guardrail_buffer[base_trace_id].append(event_data)


# Create a global instance of SpanManager
span_manager = SpanManager()

# Global dictionary for backwards compatibility
active_spans = {
    "kb_span": None,
    "action_span": None,
    "code_span": None,
    "orchestration_span": None,
    "postprocessing_span": None,
    "active_traces": {
        "preprocessing": None,
        "orchestration": None,
        "postprocessing": None,
    },
}

# Global guardrail buffer for backward compatibility
guardrail_buffer = {}


def json_safe(obj):
    """Convert object to JSON-safe format, handling complex types."""
    if isinstance(obj, dict):
        return json.dumps(obj)
    return obj


def get_time():
    """Get the current time in timestamp and ISO format"""
    end_timestamp = time.time()
    end_time_iso = (
        datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
        .replace(tzinfo=None)
        .isoformat()
    )
    return end_timestamp, end_time_iso


def extract_trace_id(trace_data: Dict[str, Any], component_type: str = None) -> str:
    """Extract trace ID from any component trace"""
    # Handle the case where we're given the full trace object
    trace_obj = trace_data.get("trace", trace_data)

    # Check for event type based on component_type if provided
    if component_type:
        if component_type == "orchestration" and "orchestrationTrace" in trace_obj:
            component_trace = trace_obj["orchestrationTrace"]
        elif component_type == "preprocessing" and "preProcessingTrace" in trace_obj:
            component_trace = trace_obj["preProcessingTrace"]
        elif component_type == "postprocessing" and "postProcessingTrace" in trace_obj:
            component_trace = trace_obj["postProcessingTrace"]
        elif component_type == "guardrail_pre" or component_type == "guardrail_post":
            return trace_obj.get("guardrailTrace", {}).get(
                "traceId", f"guardrail-{time.time()}"
            )
        else:
            component_trace = {}
    else:
        # Try to infer component type from trace object
        if "orchestrationTrace" in trace_obj:
            component_trace = trace_obj["orchestrationTrace"]
        elif "preProcessingTrace" in trace_obj:
            component_trace = trace_obj["preProcessingTrace"]
        elif "postProcessingTrace" in trace_obj:
            component_trace = trace_obj["postProcessingTrace"]
        elif "guardrailTrace" in trace_obj:
            return trace_obj["guardrailTrace"].get(
                "traceId", f"guardrail-{time.time()}"
            )
        elif "failureTrace" in trace_obj:
            return trace_obj["failureTrace"].get("traceId", f"failure-{time.time()}")
        else:
            component_trace = {}

    # Try to extract from modelInvocation fields first
    if (
        "modelInvocationInput" in component_trace
        and "traceId" in component_trace["modelInvocationInput"]
    ):
        return component_trace["modelInvocationInput"]["traceId"]
    if (
        "modelInvocationOutput" in component_trace
        and "traceId" in component_trace["modelInvocationOutput"]
    ):
        return component_trace["modelInvocationOutput"]["traceId"]

    # Try other common fields
    for field in ["rationale", "invocationInput", "observation"]:
        if field in component_trace:
            if (
                isinstance(component_trace[field], dict)
                and "traceId" in component_trace[field]
            ):
                return component_trace[field]["traceId"]

    # Fall back to a generated ID
    return f"generated-{time.time()}"


def process_trace_event(trace_data: Dict[str, Any], parent_span):
    """
    Process a single trace event from Bedrock Agent.

    Parameters:
        trace_data: The trace data received from Bedrock Agent
        parent_span: The parent span for this trace event
    """
    from .handlers import handle_file_operations
    # Capture receive time if not already present
    if "received_timestamp" not in trace_data:
        received_timestamp = time.time()
        received_time_iso = (
            datetime.fromtimestamp(received_timestamp, tz=timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
        )
        trace_data["received_timestamp"] = received_timestamp
        trace_data["received_time_iso"] = received_time_iso
    
    if "files" in trace_data:
        handle_file_operations(trace_data, parent_span)

    # Log event time and receive time for debugging
    if "eventTime" in trace_data:
        event_time = trace_data["eventTime"]
        if isinstance(event_time, datetime):
            event_timestamp = event_time.timestamp()
            logger.debug(
                f"Event time: {event_time.isoformat()}, Received time: {trace_data['received_time_iso']}"
            )
            logger.debug(
                f"Event processing latency: {(trace_data['received_timestamp'] - event_timestamp) * 1000:.2f} ms"
            )

    # Determine the trace type
    trace = trace_data.get("trace", {})

    # Handle guardrail traces first (exclusive handling)
    if "guardrailTrace" in trace:
        # Import here to avoid circular imports
        from .handlers import (
            handle_guardrail_pre,
            handle_guardrail_post,
            handle_guardrail_intervention,
        )

        # Handle guardrail trace
        guardrail_trace = trace["guardrailTrace"]
        trace_id = guardrail_trace.get("traceId", "")
        action = guardrail_trace.get("action", "NONE")

        if "pre" in trace_id:
            # Pre-request guardrail
            if action in ["BLOCKED", "INTERVENED"]:
                # This is an actual guardrail intervention
                handle_guardrail_intervention(trace_data, parent_span)
            else:
                # Standard pre-request guardrail
                handle_guardrail_pre(trace_data, parent_span)
        else:
            # Post-response guardrail - buffer for later processing
            # Extract base trace ID
            base_trace_id = (
                trace_id.split("-guardrail-post-")[0]
                if "-guardrail-post-" in trace_id
                else trace_id
            )

            # Add to span manager's buffer
            span_manager.add_guardrail_event(base_trace_id, trace_data)

            # Also add to global buffer for backward compatibility
            if base_trace_id not in guardrail_buffer:
                guardrail_buffer[base_trace_id] = []

            buffer_entry = {
                "trace_data": trace_data,
                "timestamp": trace_data["received_time_iso"],
                "content": None,
            }
            guardrail_buffer[base_trace_id].append(buffer_entry)

    elif "preProcessingTrace" in trace:
        # Import here to avoid circular imports
        from .handlers import handle_preprocessing

        # Handle preprocessing trace (always separate from guardrails)
        handle_preprocessing(trace_data, parent_span)

    elif "orchestrationTrace" in trace:
        # Handle orchestration trace
        from .processes import process_orchestration_trace

        process_orchestration_trace(trace_data, parent_span, active_spans)

    elif "postProcessingTrace" in trace:
        # Handle post-processing trace
        from .processes import process_post_processing_trace

        process_post_processing_trace(trace_data, parent_span, active_spans)

    elif "failureTrace" in trace:
        # Import here to avoid circular imports
        from .handlers import handle_failure

        # Handle failure trace
        handle_failure(trace_data, parent_span)


def instrument_agent_invocation(func):
    """
    Decorator to instrument Bedrock Agent invocations with OpenTelemetry.
    """
    @wraps(func)
    def wrapper(inputText, agentId, agentAliasId, sessionId, **kwargs):
        # Extract configuration parameters from kwargs
        trace_id = kwargs.pop("trace_id", str(uuid.uuid4()))
        user_id = kwargs.pop("userId", "anonymous")
        tags = kwargs.pop("tags", [])
        show_traces = kwargs.pop("show_traces", False)
        streaming = kwargs.get("streaming", False)
        model_id = kwargs.pop("model_id", None)
        save_trace_logs = kwargs.pop("SAVE_TRACE_LOGS", False)

        # Create tracer provider:
        create_tracer_provider()

        # Import handlers and set tracer
        from .handlers import set_tracer
        set_tracer(tracer)

        # Reset span manager for a clean start
        span_manager.reset()

        # Get start time for the entire operation
        start_timestamp, start_time_iso = get_time()

        # Start root span for agent invocation - this is the parent for all other spans
        with tracer.start_as_current_span(
            name=f"Bedrock Agent: {agentId}",
            kind=SpanKind.CLIENT,
            attributes={
                "gen_ai.operation.name": SpanKindValues.AGENT,
                "agent.id": agentId,
                "agent.alias_id": agentAliasId,
                SpanAttributes.SESSION_ID: sessionId,
                SpanAttributes.USER_ID: user_id,
                "custom.trace_id": trace_id,
                SpanAttributes.CUSTOM_TAGS: json_safe(tags),
                "stream_mode": streaming,
                "metadata.streaming": streaming,
                SpanAttributes.LLM_SYSTEM: "aws.bedrock",
                SpanAttributes.LLM_REQUEST_MODEL: model_id or "bedrock-agent-default",
                SpanAttributes.LLM_PROMPTS: inputText,
                SpanAttributes.SESSION_ID: sessionId,
                SpanAttributes.SPAN_START_TIME: start_time_iso,
                "invoke_started_timestamp": start_timestamp,
                "invoke_started_time_iso": start_time_iso,
            },
        ) as root_span:
            try:
                # Execute the original function (bedrock agent invocation)
                response = func(
                    inputText=inputText,
                    agentId=agentId,
                    agentAliasId=agentAliasId,
                    sessionId=sessionId,
                    **kwargs,
                )

                # Record invoke complete time
                invoke_complete_timestamp, invoke_complete_time_iso = get_time()
                invoke_duration_ms = round(
                    (invoke_complete_timestamp - start_timestamp) * 1000, 2
                )
                root_span.set_attribute(
                    "invoke_complete_timestamp", invoke_complete_timestamp
                )
                root_span.set_attribute(
                    "invoke_complete_time_iso", invoke_complete_time_iso
                )
                root_span.set_attribute("invoke_duration_ms", invoke_duration_ms)

                # Handle streaming vs non-streaming differently
                if (
                    streaming
                    and isinstance(response, dict)
                    and "completion" in response
                ):
                    # For streaming mode, wrap the completion with our streaming wrapper
                    from .streaming_wrapper import wrap_streaming_response

                    response = wrap_streaming_response(response, root_span)
                    return response

                # Non-streaming mode - Process all completion events in batch
                extracted_completion = ""
                all_traces_start_time = None
                all_traces_end_time = None

                if isinstance(response, dict) and "completion" in response:
                    # Begin processing time
                    processing_start_timestamp, processing_start_time_iso = get_time()
                    root_span.set_attribute(
                        "processing_start_time_iso", processing_start_time_iso
                    )

                    # Process all completion events
                    for event in response["completion"]:
                        # Process text chunks
                        if "chunk" in event:
                            chunk_data = event["chunk"]
                            if "bytes" in chunk_data:
                                output_text = (
                                    chunk_data["bytes"].decode("utf8")
                                    if isinstance(chunk_data["bytes"], bytes)
                                    else str(chunk_data["bytes"])
                                )
                                extracted_completion += output_text

                        # Process trace events
                        elif "trace" in event:
                            # Capture the time when we received this trace
                            trace_receive_timestamp, trace_receive_time_iso = get_time()

                            trace_data = event["trace"]
                            # Store receive time in trace data
                            trace_data["received_timestamp"] = trace_receive_timestamp
                            trace_data["received_time_iso"] = trace_receive_time_iso

                            # Track earliest and latest trace times for latency measurement
                            if (
                                all_traces_start_time is None
                                or trace_receive_timestamp < all_traces_start_time
                            ):
                                all_traces_start_time = trace_receive_timestamp

                            if (
                                all_traces_end_time is None
                                or trace_receive_timestamp > all_traces_end_time
                            ):
                                all_traces_end_time = trace_receive_timestamp

                            # Extract event time if available
                            event_time = trace_data.get("eventTime")
                            if event_time and isinstance(event_time, datetime):
                                logger.debug(
                                    f"Trace event time: {event_time.isoformat()}, Received: {trace_receive_time_iso}"
                                )
                                logger.debug(
                                    f"Latency: {(trace_receive_timestamp - event_time.timestamp()) * 1000:.2f} ms"
                                )

                            # Save trace logs if requested
                            if show_traces:
                                logger.info(f"Trace event: {trace_data}")   
                            if save_trace_logs:
                                try:
                                    with open("trace_logs.json", "a") as f:
                                        f.write(json.dumps(trace_data, cls=DateTimeEncoder))
                                        f.write("\n---\n")
                                except Exception as e:
                                    logger.error(f"Failed to write trace logs: {str(e)}")

                            # Process trace events through our central processor
                            try:
                                process_trace_event(trace_data, root_span)
                            except Exception as e:
                                logger.error(
                                    f"Error processing trace event: {str(e)}",
                                    exc_info=True,
                                )

                    # End processing time
                    processing_end_timestamp, processing_end_time_iso = get_time()
                    processing_duration_ms = round(
                        (processing_end_timestamp - processing_start_timestamp) * 1000,
                        2,
                    )
                    root_span.set_attribute(
                        "processing_end_time_iso", processing_end_time_iso
                    )
                    root_span.set_attribute(
                        "processing_duration_ms", processing_duration_ms
                    )

                    # Calculate trace processing window
                    if all_traces_start_time and all_traces_end_time:
                        traces_window_ms = round(
                            (all_traces_end_time - all_traces_start_time) * 1000, 2
                        )
                        root_span.set_attribute("traces_window_ms", traces_window_ms)

                # Add the extracted completion to the response
                response["extracted_completion"] = extracted_completion
                if extracted_completion:
                    root_span.set_attribute(
                        SpanAttributes.LLM_COMPLETIONS, extracted_completion
                    )

                # Process any buffered guardrails
                from .handlers import process_guardrail_buffer
                process_guardrail_buffer(guardrail_buffer, root_span)

                # End all spans
                span_manager.reset()

                # Set success status and end time - don't overwrite SPAN_START_TIME
                end_timestamp, end_time_iso = get_time()
                duration_ms = round((end_timestamp - start_timestamp) * 1000, 2)

                # Set final metrics on root span
                root_span.set_attribute("duration_ms", duration_ms)
                root_span.set_attribute(SpanAttributes.SPAN_END_TIME, end_time_iso)
                root_span.set_attribute(SpanAttributes.SPAN_DURATION, duration_ms)
                root_span.set_attribute("total_time_ms", duration_ms)
                root_span.set_status(Status(StatusCode.OK))

                return response
            except Exception as e:
                # Handle exceptions
                root_span.record_exception(e)
                root_span.set_attribute("error.message", str(e))
                root_span.set_attribute("error.type", e.__class__.__name__)
                root_span.set_status(Status(StatusCode.ERROR))
                logger.error(f"Error during agent invocation: {str(e)}", exc_info=True)
                return {"error": str(e), "exception": str(e)}

    return wrapper

def flush_telemetry():
    """Force flush OpenTelemetry data to ensure exports complete."""
    from .tracing import flush_telemetry as flush
    flush()