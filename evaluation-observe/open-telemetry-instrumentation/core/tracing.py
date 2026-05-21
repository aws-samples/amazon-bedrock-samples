"""
Core tracing functionality for Bedrock Agent Langfuse integration.
"""
import json
import logging
from datetime import datetime
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Constants for document attributes to match OpenInference standards
class DocumentAttributes:
    """Document attribute constants for OpenInference compatibility"""

    DOCUMENT_ID = "document.id"
    DOCUMENT_SCORE = "document.score"
    DOCUMENT_CONTENT = "document.content"
    DOCUMENT_METADATA = "document.metadata"

from .constants import SpanAttributes

# Initialize logging
logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def get_tracer(tracer_name="bedrock-agent-langfuse"):
    """Get a tracer instance"""
    return trace.get_tracer(tracer_name)


def set_span_attributes(span, attributes):
    """Set multiple attributes on a span, skipping None/empty values"""
    for key, value in attributes.items():
        if value is not None and value != "":
            span.set_attribute(key, value)


def enhance_span_attributes(span, trace_data):
    """Enhances span with comprehensive attributes from trace data"""
    common_attributes = {
        "trace.step_number": trace_data.get("step_number", 0),
        "trace.component_type": trace_data.get("type", "unknown"),
        "trace.timestamp": datetime.now().isoformat(),
    }

    if "metadata" in trace_data and "usage" in trace_data["metadata"]:
        usage = trace_data["metadata"]["usage"]
        common_attributes.update(
            {
                "llm.token_count.input": usage.get("inputTokens", 0),
                "llm.token_count.output": usage.get("outputTokens", 0),
                "llm.token_count.total": usage.get("inputTokens", 0)
                + usage.get("outputTokens", 0),
            }
        )

    if "duration" in trace_data:
        common_attributes["trace.duration"] = trace_data["duration"]

    if "metadata" in trace_data:
        common_attributes["trace.metadata"] = json.dumps(
            trace_data["metadata"], cls=DateTimeEncoder
        )

    set_span_attributes(span, common_attributes)


def format_token_usage(input_tokens, output_tokens):
    """Format token usage for Langfuse in the expected format"""
    total_tokens = input_tokens + output_tokens
    return f"{input_tokens} → {output_tokens} (∑ {total_tokens})"


@contextmanager
def span_context(span):
    """Context manager for OpenTelemetry span operations"""
    try:
        yield span
    except Exception as e:
        logger.exception(f"Error in span operation: {e}")
        if span:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
    finally:
        if span and span.is_recording():
            span.end()


def flush_telemetry():
    """Force flush all pending telemetry data to Langfuse"""
    try:
        # Get the tracer provider
        trace_provider = trace.get_tracer_provider()

        # Check if we have processors with the exporter
        if hasattr(trace_provider, "_active_span_processor"):
            processor = trace_provider._active_span_processor

        # Set a longer timeout (30 seconds) to ensure all data is flushed
        success = trace_provider.force_flush(timeout_millis=30000)

        if success:
            logger.info("🟢 Telemetry data flushed successfully to Langfuse")
        else:
            logger.warning(
                "🔶 Telemetry flush timed out or failed - data may not have been sent completely"
            )

        # Also try to force the process to be more aggressive
        from opentelemetry.sdk.trace.export import (
            SimpleSpanProcessor,
            BatchSpanProcessor,
        )

        if hasattr(trace_provider, "_active_span_processor"):
            processor = trace_provider._active_span_processor
            if hasattr(processor, "force_flush"):
                try:
                    processor.force_flush(300)
                except Exception as e:
                    logger.warning(f"Error during explicit processor flush: {e}")
    except Exception as e:
        logger.error(f"🔴 Error flushing telemetry: {str(e)}", exc_info=True)