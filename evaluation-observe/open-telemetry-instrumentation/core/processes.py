import time
import json
import time
import logging
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

from .constants import SpanAttributes, SpanKindValues
from .tracing import set_span_attributes
from .agent import extract_trace_id, span_manager
from .timer_lib import timer
from .agent import extract_trace_id


# Initialize logging
logger = logging.getLogger(__name__)

def get_time():
    "Get the time at which trace part was received"
    end_timestamp = time.time()
    end_time_iso = (
        datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
        .replace(tzinfo=None)
        .isoformat()
    )
    return end_timestamp, end_time_iso

def get_TraceEventtime(trace_data):
    # Get start timestamp from eventTime
    event_time = trace_data.get("eventTime")
    if event_time:
        start_timestamp = event_time.timestamp()
        start_time_iso = (
            datetime.fromtimestamp(start_timestamp, tz=timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
        )
        return start_timestamp, start_time_iso
    else:
        return None, None

def add_latency(trace_data):
    end_timestamp, end_time_iso = get_time()
    start_timestamp, start_time_iso = get_TraceEventtime(trace_data)
    if start_timestamp is None:
        return end_time_iso, end_time_iso, 0
    latency_ms = round((end_timestamp - start_timestamp) * 1000, 3)
    return end_time_iso, start_time_iso, latency_ms


def process_orchestration_trace(trace_data, parent_span, active_spans_dict):
    """Process orchestration trace with proper span hierarchy"""
    time_trace_id = extract_trace_id(trace_data, "orchestration")
    # logger.warning(f"Orchestration trace : {trace_data}")
    start_time, end_time, duration = timer.check_start_time(
        "orchestration", trace_data, time_trace_id
    )

    # Extract orchestration trace from the full trace object
    orchestration_trace = trace_data.get("trace", {}).get("orchestrationTrace", {})

    # Get trace ID consistently
    trace_id = extract_trace_id(trace_data, "orchestration")

    # Get or create orchestration span with proper hierarchy and timing
    orchestration_span = span_manager.get_or_create_span(
        "orchestration",
        trace_id,
        parent_span,
        {
            SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
            "trace.type": "ORCHESTRATION",
            SpanAttributes.TRACE_ID: trace_id,
            SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
            ),
            "stream_mode": parent_span.attributes.get("stream_mode", False),
        },  
    )
    # Store in global active_spans for backward compatibility
    active_spans_dict["orchestration_span"] = orchestration_span
    if "active_traces" not in active_spans_dict:
        active_spans_dict["active_traces"] = {}
    active_spans_dict["active_traces"]["orchestration"] = trace_id

    # CRITICAL: Use trace.use_span to work with the span within a context
    with trace.use_span(orchestration_span, end_on_exit=False) as current_span:
        # Import handlers
        from .handlers import (
            handle_llm_invocation,
            handle_rationale,
            handle_knowledge_base,
            handle_action_group,
            handle_code_interpreter,
            handle_final_response,
            handle_user_input_span,
            handle_file_operations,
        )

        # Check for file operations first (if present in the trace data)
        if "files" in trace_data:
            handle_file_operations(trace_data, current_span)

        # Process model invocation input (store for later)
        if "modelInvocationInput" in orchestration_trace:
            model_input_text = orchestration_trace["modelInvocationInput"].get(
                "text", ""
            )
            if model_input_text:  # Only set if not empty
                current_span.set_attribute("model.input.text", model_input_text)
            current_span.set_attribute(
                "model.input.type",
                orchestration_trace["modelInvocationInput"].get(
                    "type", "ORCHESTRATION"
                ),
            )

        # Process model invocation (LLM) first
        # Only process rationale if we have LLM output, ensuring rationale comes after LLM completion
        if (
            "modelInvocationInput" in orchestration_trace
            or "modelInvocationOutput" in orchestration_trace
        ):
            # Handle LLM invocation
            handle_llm_invocation(trace_data, current_span, "orchestration")

            # Process rationale immediately after LLM (at same L3 level)
            # but only if we have LLM output to ensure proper ordering
            if (
                "modelInvocationOutput" in orchestration_trace
                and "rationale" in orchestration_trace
            ):
                handle_rationale(trace_data, current_span)

        # Handle standalone rationale events (though in practice, they should come with LLM events)
        elif "rationale" in orchestration_trace:
            # Store a marker in the span to indicate this is a standalone rationale
            current_span.set_attribute("rationale.standalone", True)
            handle_rationale(trace_data, current_span)

        # Process knowledge base lookup
        if (
            "invocationInput" in orchestration_trace
            and "knowledgeBaseLookupInput" in orchestration_trace["invocationInput"]
        ):
            handle_knowledge_base(trace_data, current_span)

        if (
            "observation" in orchestration_trace
            and "knowledgeBaseLookupOutput" in orchestration_trace["observation"]
        ):
            handle_knowledge_base(trace_data, current_span)

        # Process action group - using correct field names
        if (
            "invocationInput" in orchestration_trace
            and "actionGroupInvocationInput" in orchestration_trace["invocationInput"]
        ):
            handle_action_group(trace_data, current_span)

        if (
            "observation" in orchestration_trace
            and "actionGroupInvocationOutput" in orchestration_trace["observation"]
        ):
            handle_action_group(trace_data, current_span)

        # Process code interpreter - using correct field names
        if (
            "invocationInput" in orchestration_trace
            and "codeInterpreterInvocationInput"
            in orchestration_trace["invocationInput"]
        ):
            handle_code_interpreter(trace_data, current_span)

        if (
            "observation" in orchestration_trace
            and "codeInterpreterInvocationOutput" in orchestration_trace["observation"]
        ):
            handle_code_interpreter(trace_data, current_span)

        if (
            "observation" in orchestration_trace
            and "finalResponse" in orchestration_trace["observation"]
            and orchestration_trace.get("observation", {}).get("type") == "ASK_USER"
        ):
            handle_user_input_span(trace_data, current_span)

        # Check if final response is in the observation
        if (
            "observation" in orchestration_trace
            and "finalResponse" in orchestration_trace["observation"]
        ):
            # Create a final response span
            final_response_processed = handle_final_response(trace_data, current_span)

            # Only if final response was successfully processed
            if final_response_processed:
                final_response = orchestration_trace["observation"]["finalResponse"]
                parent_span.set_attribute(
                    "final_response", final_response.get("text", "")
                )

                # Add final status and close this span
                current_span.set_status(Status(StatusCode.OK))

                # Capture timestamp to preserve timing information
                final_timestamp, final_time_iso = get_time()
                span_key = f"orchestration:{trace_id}"
                start_timestamp = datetime.fromisoformat(start_time)
                start_timestamp = start_timestamp.timestamp()

                # Set final timing if not already set
                span_manager.set_timing_if_not_set(
                    span_key,
                    current_span,
                    start_time,
                    final_time_iso,
                    round((final_timestamp - start_timestamp) * 1000, 3)
                    if start_timestamp
                    else 0,
                )

                # End the span
                current_span.end()

                # Clear active span references
                active_spans_dict["orchestration_span"] = None
                if "active_traces" in active_spans_dict:
                    active_spans_dict["active_traces"]["orchestration"] = None


def process_post_processing_trace(trace_data, root_span, active_spans_dict):
    """Process post-processing trace with proper span hierarchy"""
    # logger.warning(f"Post-processing trace : {trace_data}")
    time_trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "post_processing", trace_data, time_trace_id
    )
    # Extract post processing trace from the full trace object
    post_processing_trace = trace_data.get("trace", {}).get("postProcessingTrace", {})
    # Get trace ID
    trace_id = None
    for field in ["modelInvocationInput", "modelInvocationOutput"]:
        if field in post_processing_trace and "traceId" in post_processing_trace[field]:
            trace_id = post_processing_trace[field]["traceId"]
            break

    if not trace_id:
        # Couldn't find trace ID, skip this event
        return

    # Create or get post-processing span based on trace_id
    post_span = None
    current_trace_id = (
        active_spans_dict.get("active_traces", {}).get("postprocessing")
        if "active_traces" in active_spans_dict
        else None
    )
    # Check if we need to create a new span or reuse existing one
    if trace_id != current_trace_id:
        # End previous span if it exists
        prev_span = active_spans_dict.get("postprocessing_span")
        if (
            prev_span
            and hasattr(prev_span, "is_recording")
            and prev_span.is_recording()
        ):
            # Set status to OK before ending
            prev_span.set_status(Status(StatusCode.OK))
            prev_span.end()

        # Create new L2 post-processing span using start_span() for persistence
        # CRITICAL: We use start_span() (not start_as_current_span) because we need to store and reuse the span
        post_span = trace.get_tracer("bedrock-agent-langfuse").start_span(
            name="postProcessingTrace",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
                "trace.type": "POST_PROCESSING",
                SpanAttributes.TRACE_ID: trace_id,
            },
            context=trace.set_span_in_context(root_span),  # Link to parent
        )

        # Copy model_id and streaming metadata from root span if available
        if hasattr(root_span, "attributes"):
            # Copy model ID
            if SpanAttributes.LLM_REQUEST_MODEL in root_span.attributes:
                post_span.set_attribute(
                    SpanAttributes.LLM_REQUEST_MODEL,
                    root_span.attributes[SpanAttributes.LLM_REQUEST_MODEL],
                )

            # Copy streaming flag
            if "stream_mode" in root_span.attributes:
                post_span.set_attribute(
                    "stream_mode", root_span.attributes["stream_mode"]
                )

            # Copy streaming metadata
            if "metadata.streaming" in root_span.attributes:
                post_span.set_attribute(
                    "metadata.streaming", root_span.attributes["metadata.streaming"]
                )

        # Start the span manually - required when using start_span()
        post_span.start()

        # Store span and trace_id
        active_spans_dict["postprocessing_span"] = post_span
        if "active_traces" not in active_spans_dict:
            active_spans_dict["active_traces"] = {}
        active_spans_dict["active_traces"]["postprocessing"] = trace_id
    else:
        # Reuse existing span
        post_span = active_spans_dict.get("postprocessing_span")
        if (
            not post_span
            or not hasattr(post_span, "is_recording")
            or not post_span.is_recording()
        ):
            # Create new span if previous one is no longer valid
            post_span = trace.get_tracer("bedrock-agent-langfuse").start_span(
                name="postProcessingTrace",
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
                    "trace.type": "POST_PROCESSING",
                    SpanAttributes.TRACE_ID: trace_id,
                    # SpanAttributes.SPAN_START_TIME: start_time,
                    # SpanAttributes.SPAN_END_TIME: end_time,
                    # SpanAttributes.SPAN_DURATION: duration,
                },
                context=trace.set_span_in_context(root_span),
            )

            # Copy model_id from root span if available
            if (
                hasattr(root_span, "attributes")
                and SpanAttributes.LLM_REQUEST_MODEL in root_span.attributes
            ):
                post_span.set_attribute(
                    SpanAttributes.LLM_REQUEST_MODEL,
                    root_span.attributes[SpanAttributes.LLM_REQUEST_MODEL],
                )

            # Start the span manually - required when using start_span()
            post_span.start()

            active_spans_dict["postprocessing_span"] = post_span

    if post_span:
        # CRITICAL: Use trace.use_span to work with the span within a context
        with trace.use_span(post_span, end_on_exit=False) as current_span:
            # Import handlers here to avoid circular imports
            from .handlers import handle_llm_invocation

            # Process model invocation input (store for later)
            if "modelInvocationInput" in post_processing_trace:
                model_input = post_processing_trace["modelInvocationInput"]
                model_input_text = model_input.get("text", "")
                if model_input_text:  # Only set if not empty
                    current_span.set_attribute("model.input.text", model_input_text)
                current_span.set_attribute(
                    "model.input.type", model_input.get("type", "POST_PROCESSING")
                )

                # Add inference configuration if available
                if "inferenceConfiguration" in model_input:
                    current_span.set_attribute(
                        "model.input.inference_configuration",
                        json.dumps(model_input["inferenceConfiguration"]),
                    )
            # Process LLM invocation
            handle_llm_invocation(trace_data, current_span, "postprocessing")
            # Check if this is the final part of post-processing
            if "modelInvocationOutput" in post_processing_trace:
                # Get the final response
                output = post_processing_trace["modelInvocationOutput"]
                if "parsedResponse" in output and "text" in output["parsedResponse"]:
                    final_text = output["parsedResponse"]["text"]
                    current_span.set_attribute("final_response", final_text)
                    current_span.set_status(Status(StatusCode.OK))
                    current_span.end()
                    # Clear active span references
                    active_spans_dict["postprocessing_span"] = None
                    if "active_traces" in active_spans_dict:
                        active_spans_dict["active_traces"]["postprocessing"] = None