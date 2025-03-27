"""
Handlers for different types of trace events following the exact hierarchy:

L1: Root span "Bedrock Agent: [agent_id]"
  L2: "guardrail_pre"
  L2: "orchestrationTrace"
    L3: "llm"
      L4: "OrchestrationModelInvocationOutput"
    L3: "rationale"
    L3: "CodeInterpreter"
      L4: "code_interpreter_result"
    L3: "action_group"
      L4: "action_result"
    L3: "knowledgeBaseLookupInput"
      L4: "knowledgeBaseLookupOutput"
  L2: "postProcessingTrace"
    L3: "llm"
      L4: "PostProcessingModelInvocationOutput"
  L2: "guardrail_post"
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

from .constants import SpanAttributes, SpanKindValues
from .tracing import set_span_attributes
from typing import Dict, Any
from .timer_lib import timer
from .agent import extract_trace_id
import time

# Initialize logging
logger = logging.getLogger(__name__)
# Global tracer reference
tracer = None

def set_span_timing(span, start_time_iso, end_time_iso, latency_ms, span_key=None):
    """Safely set span timing if not already set"""
    from .agent import span_manager

    if span_key and span_manager.can_set_timing(span_key):
        span.set_attribute(SpanAttributes.SPAN_START_TIME, start_time_iso)
        span.set_attribute(SpanAttributes.SPAN_END_TIME, end_time_iso)
        span.set_attribute(SpanAttributes.SPAN_DURATION, latency_ms)
        span_manager.protect_span_timing(span_key)
        return True
    return False

def set_tracer(tracer_instance):
    """Set tracer instance from main module"""
    global tracer
    tracer = tracer_instance

def handle_preprocessing(trace_data: Dict[str, Any], parent_span):
    """Handle pre-processing trace events with proper L2-L3-L4 hierarchy"""
    # Extract preprocessing trace data from the full trace object
    preprocessing_trace = trace_data.get("trace", {}).get("preProcessingTrace", {})
    # Extract trace ID from preprocessing trace
    trace_id = None
    if "modelInvocationOutput" in preprocessing_trace:
        trace_id = preprocessing_trace["modelInvocationOutput"].get(
            "traceId", "unknown"
        )
    elif "modelInvocationInput" in preprocessing_trace:
        trace_id = preprocessing_trace["modelInvocationInput"].get("traceId", "unknown")
    else:
        trace_id = f"preprocessing-{time.time()}"
    # Create L2 preprocessing span
    start_time, end_time, duration = timer.check_start_time(
        "handle_preprocessing", trace_data, trace_id
    )
    preprocessing_span = tracer.start_span(
        name="pre_processing",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
            SpanAttributes.TRACE_ID: trace_id,
            "trace.type": "PRE_PROCESSING",
            SpanAttributes.LLM_SYSTEM: "preprocessing",
            SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
            ),
            SpanAttributes.SPAN_NAME: "pre_processing",
            "stream_mode": parent_span.attributes.get("stream_mode", False),
            "metadata.streaming": parent_span.attributes.get(
                "metadata.streaming", False
            ),
        },
        context=trace.set_span_in_context(parent_span),
    )
    # Also add to parent span
    set_span_attributes(
        preprocessing_span,
        {
            SpanAttributes.SPAN_START_TIME: start_time,
            SpanAttributes.SPAN_END_TIME: end_time,
            SpanAttributes.SPAN_DURATION: duration,
        },
    )
    # Set and protect timing immediately
    span_key = f"preprocessing:{trace_id}"
    set_span_timing(preprocessing_span, start_time, end_time, duration, span_key)
    # Register the span in span_manager
    from .agent import span_manager
    if not preprocessing_span.is_recording():
        preprocessing_span.start()
    span_manager.spans[span_key] = preprocessing_span
    span_manager.active_traces["preprocessing"] = trace_id
    # Process model invocation input if available
    if "modelInvocationInput" in preprocessing_trace:
        model_input = preprocessing_trace["modelInvocationInput"]
        set_span_attributes(
            preprocessing_span,
            {
                "model.input.text": model_input.get("text", ""),
                "model.input.type": model_input.get("type", "PRE_PROCESSING"),
            },
        )
        preprocessing_span.set_attribute(
            SpanAttributes.LLM_PROMPTS, model_input.get("text", "")
        )
        # Add inference configuration if available
        if "inferenceConfiguration" in model_input:
            preprocessing_span.set_attribute(
                "model.input.inference_configuration",
                json.dumps(model_input["inferenceConfiguration"]),
            )
    # Check if we also have output data already in this trace
    if "modelInvocationOutput" in preprocessing_trace:
        update_preprocessing_span(trace_data, preprocessing_span)

def update_preprocessing_span(trace_data: Dict[str, Any], preprocessing_span):
    """Update an existing preprocessing span with output data"""
    preprocessing_trace = trace_data.get("trace", {}).get("preProcessingTrace", {})
    # Only process output updates
    if "modelInvocationOutput" not in preprocessing_trace:
        return
    model_output = preprocessing_trace["modelInvocationOutput"]
    # Get trace ID for span key
    trace_id = model_output.get("traceId", "unknown")
    span_key = f"preprocessing:{trace_id}"
    start_time, end_time, duration = timer.check_start_time(
        "update_preprocessing", trace_data, trace_id
    )
    pre_start_time, pre_end_time, pre_duration = timer.check_start_time(
        "handle_preprocessing", trace_data, trace_id
    )
    # Update timing only if not protected
    set_span_timing(
        preprocessing_span, pre_start_time, pre_end_time, pre_duration, span_key
    )
    # Create L3 LLM span with its own timing
    llm_span_key = f"preprocessing_llm:{trace_id}"
    with tracer.start_as_current_span(
        name="llm",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.LLM_SYSTEM: "aws.bedrock",
            SpanAttributes.LLM_REQUEST_MODEL: preprocessing_span.attributes.get(
                SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
            ),
            "trace.part": "preprocessing",
        },
        context=trace.set_span_in_context(preprocessing_span),
    ) as llm_span:
        # Set and protect LLM span timing
        set_span_timing(llm_span, start_time, end_time, duration, llm_span_key)
        # Add token usage information
        if "metadata" in model_output and "usage" in model_output["metadata"]:
            usage = model_output["metadata"]["usage"]
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            total_tokens = input_tokens + output_tokens
            set_span_attributes(
                llm_span,
                {
                    SpanAttributes.LLM_PROMPTS: preprocessing_span.attributes.get(
                        "model.input.text"
                    ),
                    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: input_tokens,
                    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: output_tokens,
                    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: total_tokens,
                },
            )
            # Also add to parent span
            set_span_attributes(
                preprocessing_span,
                {
                    SpanAttributes.LLM_USAGE_PROMPT_TOKENS: input_tokens,
                    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: output_tokens,
                    SpanAttributes.LLM_USAGE_TOTAL_TOKENS: total_tokens,
                },
            )
        # Add raw response to LLM span
        if "rawResponse" in model_output:
            raw_content = model_output["rawResponse"].get("content", "")
            llm_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, raw_content)
            preprocessing_span.set_attribute("model.output", raw_content)
        # Create L4 assessment span as child of LLM span
        with tracer.start_as_current_span(
            name="pre_proccessing_output",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
                "trace.type": "PRE_PROCESSING_MODEL_OUTPUT",
                "trace.part": "preprocessing",
            },
            context=trace.set_span_in_context(llm_span),
        ) as assessment_span:
            assessment_span.set_attribute(
                SpanAttributes.LLM_PROMPTS, "preprocessing_prompt- now-error"
            )
            # Add metadata
            if "metadata" in model_output:
                metadata = model_output["metadata"]
                assessment_span.set_attribute("metadata", json.dumps(metadata))
                # Add token usage directly
                if "usage" in metadata:
                    usage = metadata["usage"]
                    assessment_span.set_attribute(
                        "usage.inputTokens", usage.get("inputTokens", 0)
                    )
                    assessment_span.set_attribute(
                        "usage.outputTokens", usage.get("outputTokens", 0)
                    )
            # Add parsed response
            if "parsedResponse" in model_output:
                parsed_response = model_output["parsedResponse"]
                assessment_span.set_attribute(
                    "parsedResponse", json.dumps(parsed_response)
                )
                assessment_span.set_attribute("isValid", parsed_response.get("isValid"))
                # Add rationale directly
                if "rationale" in parsed_response:
                    assessment_span.set_attribute(
                        SpanAttributes.LLM_COMPLETIONS, parsed_response["rationale"]
                    )
                # Set status based on isValid
                is_valid = parsed_response.get("isValid", True)
                if is_valid:
                    assessment_span.set_status(Status(StatusCode.OK))
                else:
                    assessment_span.set_status(Status(StatusCode.ERROR))
                    assessment_span.set_attribute(
                        "error.message", "Invalid input in preprocessing"
                    )
        # Set LLM span status
        llm_span.set_status(Status(StatusCode.OK))
    preprocessing_span.set_status(Status(StatusCode.OK))


def handle_llm_invocation(
    trace_data: Dict[str, Any], parent_span, parent_component: str
):
    """Handle LLM invocation - fixes duplicate LLM spans issue"""
    trace_id = extract_trace_id(trace_data)
    name = f"{parent_component}_llm"
    start_time, end_time, duration = timer.check_start_time(name, trace_data, trace_id)
    # Determine which component and get trace from the full trace object
    if parent_component == "orchestration":
        component_trace = trace_data.get("trace", {}).get("orchestrationTrace", {})
        output_span_name = "OrchestrationModelInvocationOutput"
    else:
        component_trace = trace_data.get("trace", {}).get("postProcessingTrace", {})
        output_span_name = "PostProcessingModelInvocationOutput"
    # Store input on parent span instead of creating a separate LLM span
    if "modelInvocationInput" in component_trace:
        model_input = component_trace["modelInvocationInput"]
        # parent_span.set_attribute("model.input.text", model_input.get("text", ""))
        parent_span.set_attribute(
            SpanAttributes.LLM_PROMPTS, model_input.get("text", "")
        )
        if "inferenceConfiguration" in model_input:
            parent_span.set_attribute(
                "model.input.inference_configuration",
                json.dumps(model_input["inferenceConfiguration"]),
            )
    # Create LLM span only for output
    llm_span = None
    if "modelInvocationOutput" in component_trace:
        model_output = component_trace["modelInvocationOutput"]
        prompt = parent_span.attributes.get(SpanAttributes.LLM_PROMPTS, "")
        parent_context = trace.set_span_in_context(parent_span)
        # Use the parent context explicitly - this is the key fix
        with tracer.start_as_current_span(
            name="llm",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.LLM_SYSTEM: "aws.bedrock",
                SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                    SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                ),
                SpanAttributes.LLM_PROMPTS: prompt,
                "trace.part": parent_component,
                SpanAttributes.SPAN_NAME: f"{parent_component}_llm",
                SpanAttributes.SPAN_START_TIME: start_time,
                SpanAttributes.SPAN_END_TIME: end_time,
                SpanAttributes.SPAN_DURATION: duration,
            },
            context=parent_context,
        ) as current_llm_span:
            llm_span = current_llm_span
            # Add token usage information
            if "metadata" in model_output and "usage" in model_output["metadata"]:
                usage = model_output["metadata"]["usage"]
                set_span_attributes(
                    llm_span,
                    {
                        SpanAttributes.LLM_USAGE_PROMPT_TOKENS: usage.get(
                            "inputTokens", 0
                        ),
                        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: usage.get(
                            "outputTokens", 0
                        ),
                        SpanAttributes.LLM_USAGE_TOTAL_TOKENS: usage.get(
                            "inputTokens", 0
                        )
                        + usage.get("outputTokens", 0),
                        SpanAttributes.SPAN_START_TIME: start_time,
                        SpanAttributes.SPAN_END_TIME: end_time,
                        SpanAttributes.SPAN_DURATION: duration,
                    },
                )

            # Add raw response
            if "rawResponse" in model_output:
                raw_content = model_output["rawResponse"].get("content", "")
                llm_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, raw_content)
                parent_span.set_attribute("model.output", raw_content)
            else:
                raw_content = model_output["parsedResponse"].get("text", "")
                llm_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, raw_content)
                parent_span.set_attribute("model.output", raw_content)

            # Create L4 model output span (child of llm span)
            with tracer.start_as_current_span(
                name=output_span_name,
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
                    "trace.type": f"{parent_component.upper()}_MODEL_OUTPUT",
                    "trace.part": parent_component,
                    SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                        SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                    ),
                    SpanAttributes.LLM_SYSTEM: f"bedrock-{parent_component}",
                    SpanAttributes.SPAN_NAME: f"{parent_component}_output",
                    SpanAttributes.SPAN_START_TIME: start_time,
                    SpanAttributes.SPAN_END_TIME: end_time,
                    SpanAttributes.SPAN_DURATION: duration,
                },
                context=trace.set_span_in_context(
                    llm_span
                ),  # Important: attach to llm_span, not parent_span
            ) as output_span:
                # Add raw response
                if "rawResponse" in model_output:
                    raw_content = model_output["rawResponse"].get("content", "")
                    output_span.set_attribute(SpanAttributes.LLM_PROMPTS, prompt)
                    output_span.set_attribute(
                        SpanAttributes.LLM_COMPLETIONS, raw_content
                    )
                    output_span.set_attribute("output", raw_content)

                # Add metadata
                if "metadata" in model_output:
                    metadata = model_output["metadata"]
                    output_span.set_attribute("metadata", json.dumps(metadata))

                    # Add token usage directly
                    if "usage" in metadata:
                        usage = metadata["usage"]
                        output_span.set_attribute(
                            "usage.inputTokens", usage.get("inputTokens", 0)
                        )
                        output_span.set_attribute(
                            "usage.outputTokens", usage.get("outputTokens", 0)
                        )

                # Add parsed response
                if "parsedResponse" in model_output:
                    parsed_response = model_output["parsedResponse"]
                    output_span.set_attribute(
                        "parsedResponse", json.dumps(parsed_response)
                    )

                    # Set result output
                    if (
                        parent_component == "postprocessing"
                        and "text" in parsed_response
                    ):
                        output_span.set_attribute("result", parsed_response["text"])
                        parent_span.set_attribute("result", parsed_response["text"])
                        llm_span.set_attribute("result", parsed_response["text"])

            # Set LLM span status
            llm_span.set_status(Status(StatusCode.OK))


def handle_rationale(
    trace_data: Dict[str, Any], parent_span, llm_span=None, is_orphaned=False
):
    """Handle rationale span creation at L3 level after LLM span"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "rationale", trace_data, trace_id
    )
    orchestration_trace = trace_data.get("trace", {}).get("orchestrationTrace", {})

    if "rationale" in orchestration_trace:
        rationale_data = orchestration_trace["rationale"]
        trace_id = rationale_data.get("traceId", "unknown")

        # Determine the correct parent - prefer the LLM span if provided
        span_parent = llm_span if llm_span else parent_span

        # Create L3 rationale span with LLM span as parent if available
        with tracer.start_as_current_span(
            name="rationale",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
                "trace.type": "REASONING",
                SpanAttributes.TRACE_ID: trace_id,
                "has_llm_parent": llm_span is not None,
                "is_orphaned": is_orphaned,  # Track if this rationale had no parent LLM
                "trace.sequence": "post-llm",
                SpanAttributes.SPAN_START_TIME: start_time,
                SpanAttributes.SPAN_END_TIME: end_time,
                SpanAttributes.SPAN_DURATION: duration,
            },
            context=trace.set_span_in_context(span_parent),
        ) as rationale_span:
            # Add content
            rationale_span.set_attribute(SpanAttributes.LLM_PROMPTS, "NotApplicable")
            rationale_span.set_attribute(
                SpanAttributes.LLM_COMPLETIONS, rationale_data.get("text", "")
            )
            rationale_span.set_status(Status(StatusCode.OK))


def handle_knowledge_base(trace_data: Dict[str, Any], parent_span):
    """Handle knowledge base spans (input and output)"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time("kb", trace_data, trace_id)
    orchestration_trace = trace_data.get("trace", {}).get("orchestrationTrace", {})
    kb_query = None
    # Handle knowledge base lookup input
    if (
        "invocationInput" in orchestration_trace
        and "knowledgeBaseLookupInput" in orchestration_trace["invocationInput"]
    ):
        kb_input = orchestration_trace["invocationInput"]["knowledgeBaseLookupInput"]
        kb_query = kb_input.get("text", "")

        # Create L3 knowledgeBase span using start_span() for persistence
        kb_span = tracer.start_span(
            name="knowledgeBaseLookupInput",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.DATABASE,
                "retrieval.type": "semantic",
                SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                    SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                ),
                SpanAttributes.LLM_PROMPTS: kb_query,
                "trace.type": "KNOWLEDGE_BASE_LOOKUP",
                "query": kb_input.get("text", ""),
                "knowledge_base_id": kb_input.get("knowledgeBaseId", ""),
                SpanAttributes.SPAN_START_TIME: start_time,
                SpanAttributes.SPAN_END_TIME: end_time,
                SpanAttributes.SPAN_DURATION: duration,
            },
            context=trace.set_span_in_context(parent_span),  # Attach to parent
        )

        # Start the span manually
        kb_span.start()

        # Add richer metadata
        kb_metadata = {
            "knowledge_base_id": kb_input.get("knowledgeBaseId", ""),
            "retrieval_type": "semantic",
            "data_source": kb_input.get("dataSource", ""),
            "filter_criteria": kb_input.get("filters", {}),
            "invocation_type": "SEARCH",
            "query_text": kb_input.get("text", ""),
        }

        set_span_attributes(
            kb_span,
            {
                "metadata": json.dumps(kb_metadata),
                "kb.query.text": kb_input.get("text", ""),
                "kb.data_source": kb_input.get("dataSource", ""),
                "kb.filters": json.dumps(kb_input.get("filters", {})),
            },
        )
        from .agent import active_spans

        active_spans["kb_span"] = kb_span

    # Handle knowledge base lookup output
    if (
        "observation" in orchestration_trace
        and "knowledgeBaseLookupOutput" in orchestration_trace["observation"]
    ):
        kb_output = orchestration_trace["observation"]["knowledgeBaseLookupOutput"]
        # Retrieve the previously created kb_span
        from .agent import active_spans
        kb_span = active_spans.get("kb_span")
        if (
            not kb_span
            or not hasattr(kb_span, "is_recording")
            or not kb_span.is_recording()
        ):
            # If somehow we don't have a valid kb_span, we'll need to create one
            logger.warning("KB span not found or not recording, creating a new one")
            kb_span = tracer.start_span(
                name="knowledgeBaseLookupInput",
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.OPERATION_NAME: SpanKindValues.DATABASE,
                    "trace.type": "KNOWLEDGE_BASE_LOOKUP",
                    SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                        SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                    ),
                },
                context=trace.set_span_in_context(parent_span),
            )
            kb_span.start()

        # Create L4 results span as a child of knowledgeBase span
        with tracer.start_as_current_span(
            name="knowledgeBaseLookupOutput",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.DATABASE,
                "trace.type": "KNOWLEDGE_BASE_RESULT",
            },
            context=trace.set_span_in_context(
                kb_span
            ),  # Important: attach to kb_span, not parent_span
        ) as kb_result_span:
            kb_result_span.set_attribute(
                SpanAttributes.LLM_PROMPTS,
                kb_span.attributes.get(SpanAttributes.LLM_PROMPTS),
            )
            kb_result_span.set_attribute(
                SpanAttributes.LLM_SYSTEM, kb_output.get("text", "")
            )
            kb_result_span.set_attribute(
                SpanAttributes.LLM_REQUEST_MODEL,
                parent_span.attributes.get(
                    SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                ),
            )
            # Add results
            if "retrievedReferences" in kb_output:
                results = kb_output["retrievedReferences"]
                kb_result_span.set_attribute(
                    SpanAttributes.LLM_COMPLETIONS, json.dumps(results)
                )
                kb_result_span.set_attribute("result_count", len(results))

            # Add token usage if available
            if "totalTokens" in kb_output:
                kb_result_span.set_attribute(
                    "kb.total_tokens", kb_output.get("totalTokens", 0)
                )

            kb_result_span.set_status(Status(StatusCode.OK))

        # Now that we have results, update and set status on the parent kb_span
        kb_span.set_attribute(
            "kb.result_count", len(kb_output.get("retrievalResults", []))
        )
        kb_span.set_attribute("kb.total_tokens", kb_output.get("totalTokens", 0))

        kb_span.set_status(Status(StatusCode.OK))

        # End the kb_span now that we're done with it
        kb_span.end()

        # Clear the reference
        active_spans["kb_span"] = None


def handle_action_group(trace_data: Dict[str, Any], parent_span):
    """Handle action group spans (input and output)"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "action_group", trace_data, trace_id
    )
    orchestration_trace = trace_data.get("trace", {}).get("orchestrationTrace", {})

    # Handle action group input - using correct field name: actionGroupInvocationInput
    if (
        "invocationInput" in orchestration_trace
        and "actionGroupInvocationInput" in orchestration_trace["invocationInput"]
    ):
        action_input = orchestration_trace["invocationInput"][
            "actionGroupInvocationInput"
        ]

        # Create L3 action_group span using start_span() for persistence
        action_span = tracer.start_span(
            name="action_group",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TOOL,
                "tool.action_group_name": action_input.get("actionGroupName", {}),
                "tool.function": action_input.get("function", {}),
                "trace.type": action_input.get("executionType", {}),
                SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                    SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                ),
                "tool.parameters": json.dumps(action_input.get("parameters", {})),
                SpanAttributes.SPAN_START_TIME: start_time,
                SpanAttributes.SPAN_END_TIME: end_time,
                SpanAttributes.SPAN_DURATION: duration,
            },
            context=trace.set_span_in_context(parent_span),
        )
        # Start the span manually
        action_span.start()

        # Add additional metadata
        set_span_attributes(
            action_span,
            {
                "metadata": json.dumps(
                    {
                        "action_group": action_input.get("actionGroup", {}),
                        "api_schema": action_input.get("apiSchema", {}),
                        "tool_version": "1.0",
                    }
                ),
                SpanAttributes.LLM_PROMPTS: json.dumps(
                    action_input.get("parameters", {})
                ),
                SpanAttributes.LLM_COMPLETIONS: "NotApplicable",
            },
        )

        # Store the action span in the active_spans dictionary passed from agent.py
        # This will be retrieved later when output arrives
        from .agent import active_spans

        active_spans["action_span"] = action_span

    # Handle action group output - using correct field name: actionGroupInvocationOutput
    if (
        "observation" in orchestration_trace
        and "actionGroupInvocationOutput" in orchestration_trace["observation"]
    ):
        action_output = orchestration_trace["observation"][
            "actionGroupInvocationOutput"
        ]

        # Retrieve the previously created action_span
        from .agent import active_spans

        action_span = active_spans.get("action_span")

        if (
            not action_span
            or not hasattr(action_span, "is_recording")
            or not action_span.is_recording()
        ):
            # If somehow we don't have a valid action_span, we'll need to create one
            logger.warning(
                "Action group span not found or not recording, creating a new one"
            )
            action_span = tracer.start_span(
                name="action_group",
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.OPERATION_NAME: SpanKindValues.TOOL,
                    "trace.type": "ACTION_GROUP",
                    SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                        SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                    ),
                    "start_time": end_time,  # In fallback, use end time as start time
                },
                context=trace.set_span_in_context(parent_span),
            )
            action_span.start()

        # Create L4 result span as child of action_group
        with tracer.start_as_current_span(
            name="action_result",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TOOL,
                "trace.type": "ACTION_RESULT",
            },
            context=trace.set_span_in_context(
                action_span
            ),  # Important: attach to action_span, not parent_span
        ) as result_span:
            # Add response content
            if "text" in action_output:
                result_span.set_attribute(SpanAttributes.LLM_PROMPTS, "NotApplicable")
                result_span.set_attribute(
                    SpanAttributes.LLM_COMPLETIONS, action_output["text"]
                )

        # Set status on action_span
        action_span.set_status(Status(StatusCode.OK))

        # End the action_span now that we're done with it
        action_span.end()

        # Clear the reference
        active_spans["action_span"] = None


def handle_code_interpreter(trace_data: Dict[str, Any], parent_span):
    """Handle code interpreter spans (input and output)"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "CodeInterpreter", trace_data, trace_id
    )
    orchestration_trace = trace_data.get("trace", {}).get("orchestrationTrace", {})

    # Handle code interpreter input
    # Using correct field name: codeInterpreterInvocationInput
    if (
        "invocationInput" in orchestration_trace
        and "codeInterpreterInvocationInput" in orchestration_trace["invocationInput"]
    ):
        code_input = orchestration_trace["invocationInput"][
            "codeInterpreterInvocationInput"
        ]

        # Create L3 code_interpreter span using start_span() for persistence
        code_span = tracer.start_span(
            name="CodeInterpreter",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TOOL,
                "tool.name": "CodeInterpreter",
                "tool.description": "Executes Python code and returns results",
                SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                    SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                ),
                "gen_ai.tool_calls.0.arguments": json.dumps(
                    {"code": code_input.get("code", ""), "language": "python"}
                ),
                SpanAttributes.LLM_PROMPTS: code_input.get("code", ""),
                SpanAttributes.SPAN_START_TIME: start_time,
                SpanAttributes.SPAN_END_TIME: end_time,
                SpanAttributes.SPAN_DURATION: duration,
            },
            context=trace.set_span_in_context(parent_span),  # Attach to parent
        )

        # Start the span manually
        code_span.start()

        # Add code as an attribute
        if "code" in code_input:
            code_span.set_attribute("code", code_input["code"])
        code_span.set_attribute(SpanAttributes.SPAN_NAME, "CodeInterpreter")

        # Store the code span in the active_spans dictionary passed from agent.py
        # This will be retrieved later when output arrives
        from .agent import active_spans
        active_spans["code_span"] = code_span

    # Handle code interpreter output as a separate event
    # Using correct field name: codeInterpreterInvocationOutput
    if (
        "observation" in orchestration_trace
        and "codeInterpreterInvocationOutput" in orchestration_trace["observation"]
    ):
        code_output = orchestration_trace["observation"][
            "codeInterpreterInvocationOutput"
        ]

        # Retrieve the previously created code_span
        from .agent import active_spans

        code_span = active_spans.get("code_span")

        if (
            not code_span
            or not hasattr(code_span, "is_recording")
            or not code_span.is_recording()
        ):
            # If somehow we don't have a valid code_span, we'll need to create one
            logger.warning(
                "Code interpreter span not found or not recording, creating a new one"
            )
            code_span = tracer.start_span(
                name="CodeInterpreter",
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.OPERATION_NAME: SpanKindValues.TOOL,
                    "tool.name": "CodeInterpreter",
                    "tool.description": "Executes Python code and returns results",
                    SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                        SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                    ),
                },
                context=trace.set_span_in_context(parent_span),
            )
            code_span.start()

        # Create L4 result span as child of code_interpreter
        with tracer.start_as_current_span(
            name="code_interpreter_result",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TOOL,
                "trace.type": "CODE_INTERPRETER_RESULT",
            },
            context=trace.set_span_in_context(
                code_span
            ),  # Important: attach to code_span, not parent_span
        ) as result_span:
            # Add execution information - using the correct field name executionOutput
            if "executionOutput" in code_output:
                execution_output = code_output["executionOutput"]
                result_span.set_attribute("output", execution_output)
                result_span.set_attribute("result", execution_output)
                code_span.set_attribute("result", execution_output)

            # Add execution status
            if "executionStatus" in code_output:
                result_span.set_attribute(
                    "executionStatus", code_output["executionStatus"]
                )
                code_span.set_attribute(
                    "executionStatus", code_output["executionStatus"]
                )

            # Add error message if there was one
            if "errorMessage" in code_output and code_output["errorMessage"]:
                result_span.set_attribute("errorMessage", code_output["errorMessage"])
                code_span.set_attribute("errorMessage", code_output["errorMessage"])

            result_span.set_status(Status(StatusCode.OK))

        # Now that we have results, set status on the parent code_span
        code_span.set_status(Status(StatusCode.OK))

        # End the code_span now that we're done with it
        code_span.end()

        # Clear the reference
        active_spans["code_span"] = None

def process_guardrail_buffer(guardrail_buffer: Dict[str, list], parent_span):
    """Process buffered guardrail events for streaming responses"""
    # Process each unique base trace ID
    for base_trace_id, events in guardrail_buffer.items():
        if not events:
            continue

        # Get the first event to extract common information
        first_event = events[0]
        first_trace_data = first_event["trace_data"]
        guardrail_trace = first_trace_data.get("trace", {}).get("guardrailTrace", {})
        action = guardrail_trace.get("action", "NONE")

        # Get first and last timestamp
        first_timestamp = first_event.get("timestamp", datetime.now().isoformat())
        last_timestamp = (
            events[-1].get("timestamp", datetime.now().isoformat())
            if events
            else first_timestamp
        )

        # Create a single consolidated L2 guardrail_post span for this base trace ID
        with tracer.start_as_current_span(
            name="guardrail_post",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: "guardrail",
                "guardrail.type": "post",
                "guardrail.action": action,
                "guardrail.base_trace_id": base_trace_id,
                "guardrail.streaming": True,
                "guardrail.chunk_count": len(events),
                "guardrail.chunks_received": len(events),
                SpanAttributes.LLM_SYSTEM: "guardrails",
                SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                    SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                ),
            },
            context=trace.set_span_in_context(parent_span),
        ) as guardrail_span:
            # Combine assessments from all events (if any have real content)
            combined_assessments = []
            has_substantive_assessment = False

            for event in events:
                trace_data = event["trace_data"]
                guardrail_event = trace_data.get("trace", {}).get("guardrailTrace", {})
                assessments = guardrail_event.get("outputAssessments", [])

                # Check if this assessment has content
                for assessment in assessments:
                    if assessment and any(
                        key in assessment and assessment[key]
                        for key in [
                            "contentPolicy",
                            "topicPolicy",
                            "wordPolicy",
                            "sensitiveInformationPolicy",
                        ]
                    ):
                        has_substantive_assessment = True
                        if assessment not in combined_assessments:
                            combined_assessments.append(assessment)

            # Only create assessment span if we have substantive content
            if has_substantive_assessment:
                guardrail_span.set_attribute(
                    "guardrail.output_assessments", json.dumps(combined_assessments)
                )

                # Create a single assessment span with combined content
                with tracer.start_as_current_span(
                    name="output_assessment",
                    kind=SpanKind.CLIENT,
                    attributes={
                        SpanAttributes.OPERATION_NAME: "guardrail",
                        "trace.type": "OUTPUT_ASSESSMENT",
                        "guardrail.base_trace_id": base_trace_id,
                        "guardrail.streaming": True,
                        "guardrail.assessments_count": len(combined_assessments),
                        SpanAttributes.LLM_SYSTEM: "guardrails-assessment",
                        SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                            SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                        ),
                    },
                    context=trace.set_span_in_context(guardrail_span),
                ) as assessment_span:
                    # Add all relevant assessment details
                    for idx, assessment in enumerate(
                        combined_assessments[:3]
                    ):  # Limit to first 3
                        prefix = f"assessment.{idx}."

                        if "contentPolicy" in assessment:
                            assessment_span.set_attribute(
                                f"{prefix}content_policy",
                                json.dumps(assessment["contentPolicy"]),
                            )

                        if "topicPolicy" in assessment:
                            assessment_span.set_attribute(
                                f"{prefix}topic_policy",
                                json.dumps(assessment["topicPolicy"]),
                            )

                        if "wordPolicy" in assessment:
                            assessment_span.set_attribute(
                                f"{prefix}word_policy",
                                json.dumps(assessment["wordPolicy"]),
                            )

                        if "sensitiveInformationPolicy" in assessment:
                            assessment_span.set_attribute(
                                f"{prefix}sensitive_info_policy",
                                json.dumps(assessment["sensitiveInformationPolicy"]),
                            )

                    # Set status on assessment span
                    assessment_span.set_status(Status(StatusCode.OK))

            # Check if any guardrail action was GUARDRAIL_INTERVENED
            if any(
                event["trace_data"].get("guardrailTrace", {}).get("action", "")
                == "GUARDRAIL_INTERVENED"
                for event in events
            ):
                guardrail_span.set_status(Status(StatusCode.ERROR))
                guardrail_span.set_attribute(
                    "error.message", "Content blocked by guardrail"
                )
            else:
                guardrail_span.set_status(Status(StatusCode.OK))


def handle_failure(trace_data: Dict[str, Any], parent_span):
    """Handle failure trace events with proper L2 hierarchy"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_failure", trace_data, trace_id
    )
    failure_trace = trace_data.get("trace", {}).get("failureTrace", {})
    trace_id = failure_trace.get("traceId", "unknown")
    failure_reason = failure_trace.get("failureReason", "Unknown failure")

    # Create L2 failure span
    with tracer.start_as_current_span(
        name="failure",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
            SpanAttributes.TRACE_ID: trace_id,
            "error.type": "AgentProcessingFailure",
            "error.message": failure_reason,
        },
        context=trace.set_span_in_context(parent_span),  # Attach to root span
    ) as failure_span:
        # Record failure information
        failure_span.set_attribute("failure.reason", failure_reason)
        failure_span.record_exception(Exception(failure_reason))

        # Add step information if available
        if "preprocessing" in failure_reason.lower():
            failure_span.set_attribute("failure.step", "preprocessing")
        elif "orchestration" in failure_reason.lower():
            failure_span.set_attribute("failure.step", "orchestration")
        elif "postprocessing" in failure_reason.lower():
            failure_span.set_attribute("failure.step", "postprocessing")
        elif "action" in failure_reason.lower() or "tool" in failure_reason.lower():
            failure_span.set_attribute("failure.step", "action_group")
        elif "knowledge" in failure_reason.lower():
            failure_span.set_attribute("failure.step", "knowledge_base")

        # Set status to error
        failure_span.set_status(Status(StatusCode.ERROR))

        # Also add the failure to the parent span
        parent_span.set_attribute("error.message", failure_reason)
        parent_span.record_exception(Exception(failure_reason))
        parent_span.set_status(Status(StatusCode.ERROR))


def handle_final_response(trace_data: Dict[str, Any], parent_span):
    """Handle final response at L3 level under orchestration"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_final_response", trace_data, trace_id
    )
    orchestration_trace = trace_data.get("trace", {}).get("orchestrationTrace", {})

    if (
        "observation" in orchestration_trace
        and "finalResponse" in orchestration_trace["observation"]
    ):
        final_response = orchestration_trace["observation"]["finalResponse"]
        final_text = final_response.get("text", "")

        # Create L3 final response span
        with tracer.start_as_current_span(
            name="final_response",
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
                "trace.type": "FINAL_RESPONSE",
                "trace.part": "orchestration",
                SpanAttributes.SPAN_START_TIME: start_time,
                SpanAttributes.SPAN_END_TIME: end_time,
                SpanAttributes.SPAN_DURATION: duration,
                # 'endtime': datetime.fromtimestamp(time.time(), tz=timezone.utc).replace(tzinfo=None).isoformat()
            },
            context=trace.set_span_in_context(
                parent_span
            ),  # Attach to orchestration span
        ) as final_response_span:
            # Add content
            final_response_span.set_attribute(SpanAttributes.LLM_PROMPTS, "")
            final_response_span.set_attribute(
                SpanAttributes.LLM_COMPLETIONS, final_text
            )

            # Add any metadata if available
            if "metadata" in final_response:
                final_response_span.set_attribute(
                    "response.metadata", json.dumps(final_response["metadata"])
                )

            # Set status to OK
            final_response_span.set_status(Status(StatusCode.OK))

        # Also add to parent span
        parent_span.set_attribute("final_response", final_text)

        return True

    return False


def handle_guardrail_intervention(trace_data: Dict[str, Any], parent_span):
    """Handle guardrail interventions (blocking or modifying content)"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_guardrail_intervention", trace_data, trace_id
    )
    guardrail_trace = trace_data.get("trace", {}).get("guardrailTrace", {})
    trace_id = guardrail_trace.get("traceId", "unknown")
    action = guardrail_trace.get("action", "UNKNOWN")

    # Create L2 guardrail intervention span
    with tracer.start_as_current_span(
        name="guardrail_intervention",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.OPERATION_NAME: "guardrail",
            "guardrail.type": "pre" if "pre" in trace_id else "post",
            "guardrail.action": action,
            "guardrail.intervention": True,  # Mark as actual intervention
            SpanAttributes.TRACE_ID: trace_id,
            SpanAttributes.LLM_SYSTEM: "guardrails",
            SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
            ),
            SpanAttributes.SPAN_NAME: "guardrail_intervention",
            SpanAttributes.SPAN_START_TIME: start_time,
            SpanAttributes.SPAN_END_TIME: end_time,
            SpanAttributes.SPAN_DURATION: duration,
        },
        context=trace.set_span_in_context(parent_span),
    ) as guardrail_span:
        # Add assessment details
        assessments = []
        if "pre" in trace_id:
            assessments = guardrail_trace.get("inputAssessments", [])
        else:
            assessments = guardrail_trace.get("outputAssessments", [])

        guardrail_span.set_attribute(
            SpanAttributes.LLM_PROMPTS,
            parent_span.attributes.get(SpanAttributes.LLM_PROMPTS, ""),
        )
        guardrail_span.set_attribute(
            SpanAttributes.LLM_COMPLETIONS, json.dumps(assessments)
        )
        # Extract and add detailed information about what was blocked/modified
        blocked_items = []
        if assessments:
            for assessment in assessments:
                if (
                    "wordPolicy" in assessment
                    and "customWords" in assessment["wordPolicy"]
                ):
                    for word in assessment["wordPolicy"]["customWords"]:
                        if word.get("action") == "BLOCKED" and "match" in word:
                            blocked_items.append(f"Word '{word['match']}' blocked")

        if blocked_items:
            guardrail_span.set_attribute(
                "guardrail.blocked_items", json.dumps(blocked_items)
            )

        guardrail_span.set_status(Status(StatusCode.OK))


def handle_standard_preprocessing(trace_data: Dict[str, Any], parent_span):
    """Handle standard preprocessing traces (no guardrails)"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_standard_preprocessing", trace_data, trace_id
    )
    print("calling handle_standard_preprocessing", end_time, start_time, duration)
    preprocessing_trace = trace_data.get("trace", {}).get("preProcessingTrace", {})

    # Extract trace ID from preprocessing trace
    trace_id = "unknown"
    if "modelInvocationOutput" in preprocessing_trace:
        trace_id = preprocessing_trace["modelInvocationOutput"].get(
            "traceId", "unknown"
        )
    elif "modelInvocationInput" in preprocessing_trace:
        trace_id = preprocessing_trace["modelInvocationInput"].get("traceId", "unknown")

    # Create L2 preprocessing span
    with tracer.start_as_current_span(
        name="pre_processing",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
            SpanAttributes.TRACE_ID: trace_id,
            "trace.type": "PRE_PROCESSING",
            SpanAttributes.LLM_SYSTEM: "preprocessing",
            SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
            ),
            SpanAttributes.SPAN_NAME: "pre_processing",
            "stream_mode": parent_span.attributes.get("stream_mode", False),
            "metadata.streaming": parent_span.attributes.get(
                "metadata.streaming", False
            ),
            SpanAttributes.SPAN_START_TIME: start_time,
            SpanAttributes.SPAN_END_TIME: end_time,
            SpanAttributes.SPAN_DURATION: duration,
        },
        context=trace.set_span_in_context(parent_span),
    ) as preprocessing_span:
        # Set default prompts/completions
        preprocessing_span.set_attribute(SpanAttributes.LLM_PROMPTS, "NA")
        preprocessing_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, "NA")

        # Process model invocation input if available
        if "modelInvocationInput" in preprocessing_trace:
            model_input = preprocessing_trace["modelInvocationInput"]
            set_span_attributes(
                preprocessing_span,
                {
                    "model.input.text": model_input.get("text", ""),
                    "model.input.type": model_input.get("type", "PRE_PROCESSING"),
                },
            )

            # Add inference configuration if available
            if "inferenceConfiguration" in model_input:
                preprocessing_span.set_attribute(
                    "model.input.inference_configuration",
                    json.dumps(model_input["inferenceConfiguration"]),
                )

        # Process model invocation output if available
        if "modelInvocationOutput" in preprocessing_trace:
            model_output = preprocessing_trace["modelInvocationOutput"]

            # Create L3 LLM span
            with tracer.start_as_current_span(
                name="llm",
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.LLM_SYSTEM: "aws.bedrock",
                    SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                        SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
                    ),
                    "trace.part": "preprocessing",
                    SpanAttributes.SPAN_START_TIME: start_time,
                    SpanAttributes.SPAN_END_TIME: end_time,
                    SpanAttributes.SPAN_DURATION: duration,
                },
                context=trace.set_span_in_context(preprocessing_span),
            ) as llm_span:
                llm_span.set_attributes(
                    SpanAttributes.LLM_PROMPTS,
                    preprocessing_span.attributes.get(SpanAttributes.LLM_PROMPTS),
                )
                # Add token usage information
                if "metadata" in model_output and "usage" in model_output["metadata"]:
                    usage = model_output["metadata"]["usage"]
                    input_tokens = usage.get("inputTokens", 0)
                    output_tokens = usage.get("outputTokens", 0)
                    total_tokens = input_tokens + output_tokens

                    set_span_attributes(
                        llm_span,
                        {
                            SpanAttributes.LLM_USAGE_PROMPT_TOKENS: input_tokens,
                            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: output_tokens,
                            SpanAttributes.LLM_USAGE_TOTAL_TOKENS: total_tokens,
                        },
                    )

                    # Also add to parent span
                    set_span_attributes(
                        preprocessing_span,
                        {
                            SpanAttributes.LLM_USAGE_PROMPT_TOKENS: input_tokens,
                            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: output_tokens,
                            SpanAttributes.LLM_USAGE_TOTAL_TOKENS: total_tokens,
                        },
                    )

                # Add raw response to LLM span
                if "rawResponse" in model_output:
                    raw_content = model_output["rawResponse"].get("content", "")
                    llm_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, raw_content)
                    preprocessing_span.set_attribute("model.output", raw_content)

                # Create L4 assessment span as child of LLM span
                with tracer.start_as_current_span(
                    name="input_assessment",
                    kind=SpanKind.CLIENT,
                    attributes={
                        SpanAttributes.OPERATION_NAME: SpanKindValues.TASK,
                        "trace.type": "PRE_PROCESSING_MODEL_OUTPUT",
                        "trace.part": "preprocessing",
                    },
                    context=trace.set_span_in_context(llm_span),
                ) as assessment_span:
                    # Add raw response
                    if "rawResponse" in model_output:
                        raw_content = model_output["rawResponse"].get("content", "")
                        assessment_span.set_attribute("rawResponse", raw_content)
                        assessment_span.set_attribute("output", raw_content)

                    # Add metadata
                    if "metadata" in model_output:
                        metadata = model_output["metadata"]
                        assessment_span.set_attribute("metadata", json.dumps(metadata))

                        # Add token usage directly
                        if "usage" in metadata:
                            usage = metadata["usage"]
                            assessment_span.set_attribute(
                                "usage.inputTokens", usage.get("inputTokens", 0)
                            )
                            assessment_span.set_attribute(
                                "usage.outputTokens", usage.get("outputTokens", 0)
                            )

                    # Add parsed response
                    if "parsedResponse" in model_output:
                        parsed_response = model_output["parsedResponse"]
                        assessment_span.set_attribute(
                            "parsedResponse", json.dumps(parsed_response)
                        )
                        assessment_span.set_attribute(
                            "isValid", parsed_response.get("isValid", True)
                        )

                        # Add rationale directly
                        if "rationale" in parsed_response:
                            assessment_span.set_attribute(
                                "parsedResponse.rationale", parsed_response["rationale"]
                            )

                        # Set status based on isValid
                        is_valid = parsed_response.get("isValid", True)
                        if is_valid:
                            assessment_span.set_status(Status(StatusCode.OK))
                        else:
                            assessment_span.set_status(Status(StatusCode.ERROR))
                            assessment_span.set_attribute(
                                "error.message", "Invalid input in preprocessing"
                            )

                # Set LLM span status
                llm_span.set_status(Status(StatusCode.OK))

        # Set preprocessing span status
        if "modelInvocationOutput" in preprocessing_trace:
            preprocessing_span.set_status(Status(StatusCode.OK))
        else:
            preprocessing_span.set_status(Status(StatusCode.UNSET))


def handle_guardrail_pre(trace_data: Dict[str, Any], parent_span):
    """Handle pre-guardrail trace events as clean L2 spans"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_guardrail_pre", trace_data, trace_id
    )
    guardrail_trace = trace_data.get("trace", {}).get("guardrailTrace", {})
    trace_id = guardrail_trace.get("traceId", "unknown")
    action = guardrail_trace.get("action", "NONE")

    # Create L2 guardrail_pre span - completely separate from preprocessing
    with tracer.start_as_current_span(
        name="guardrail_pre",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.OPERATION_NAME: "guardrail",
            "guardrail.type": "pre",
            "guardrail.action": action,
            SpanAttributes.TRACE_ID: trace_id,
            SpanAttributes.LLM_SYSTEM: "guardrails",
            SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
            ),
            SpanAttributes.SPAN_NAME: "guardrail_pre",
            SpanAttributes.SPAN_START_TIME: start_time,
            SpanAttributes.SPAN_END_TIME: end_time,
            SpanAttributes.SPAN_DURATION: duration,
        },
        context=trace.set_span_in_context(parent_span),
    ) as guardrail_pre_span:
        # Add input assessment details
        input_assessments = guardrail_trace.get("inputAssessments", [])
        guardrail_pre_span.set_attribute(SpanAttributes.LLM_PROMPTS, "NA")
        guardrail_pre_span.set_attribute(
            SpanAttributes.LLM_COMPLETIONS, json.dumps(input_assessments)
        )

        # Store assessments information
        guardrail_pre_span.set_attribute(
            "guardrail.assessments",
            json.dumps({"input": guardrail_trace.get("inputAssessments", [])}),
        )

        # Set status based on action
        if action == "BLOCKED":
            guardrail_pre_span.set_status(Status(StatusCode.ERROR))
            guardrail_pre_span.set_attribute(
                "error.message", "Content blocked by guardrail"
            )
        else:
            guardrail_pre_span.set_status(Status(StatusCode.OK))

def handle_guardrail_post(trace_data: Dict[str, Any], parent_span):
    """Handle post-guardrail trace events with proper L2-L3 hierarchy (no LLM spans)"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_guardrail_post", trace_data, trace_id
    )
    guardrail_trace = trace_data.get("trace", {}).get("guardrailTrace", {})
    trace_id = guardrail_trace.get("traceId", "unknown")
    action = guardrail_trace.get("action", "NONE")

    # Create L2 guardrail_post span
    with tracer.start_as_current_span(
        name="guardrail_post",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.OPERATION_NAME: "guardrail",
            "guardrail.type": "post",
            "guardrail.action": action,
            SpanAttributes.TRACE_ID: trace_id,
            SpanAttributes.LLM_REQUEST_MODEL: parent_span.attributes.get(
                SpanAttributes.LLM_REQUEST_MODEL, "Not-Configured"
            ),
            SpanAttributes.SPAN_NAME: "guardrail_post",
            "stream_mode": parent_span.attributes.get("stream_mode", False),
            "metadata.streaming": parent_span.attributes.get(
                "metadata.streaming", False
            ),
            SpanAttributes.SPAN_START_TIME: start_time,
            SpanAttributes.SPAN_END_TIME: end_time,
            SpanAttributes.SPAN_DURATION: duration,
        },
        context=trace.set_span_in_context(parent_span),
    ) as guardrail_span:
        guardrail_span.set_attribute(SpanAttributes.LLM_PROMPTS, "NA")
        guardrail_span.set_attribute(SpanAttributes.LLM_COMPLETIONS, "NA")

        # Process assessments
        output_assessments = guardrail_trace.get("outputAssessments", [])

        if output_assessments:
            guardrail_span.set_attribute(
                "guardrail.output_assessments", json.dumps(output_assessments)
            )

            # Create L3 assessment span as a child of guardrail_span
            with tracer.start_as_current_span(
                name="output_assessment",
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.OPERATION_NAME: "guardrail",
                    "trace.type": "OUTPUT_ASSESSMENT",
                },
                context=trace.set_span_in_context(guardrail_span),
            ) as assessment_span:
                # Add first assessment details
                if output_assessments and len(output_assessments) > 0:
                    assessment = output_assessments[0]
                    # Add policy details
                    if "contentPolicy" in assessment:
                        assessment_span.set_attribute(
                            "content_policy", json.dumps(assessment["contentPolicy"])
                        )
                    if "topicPolicy" in assessment:
                        assessment_span.set_attribute(
                            "topic_policy", json.dumps(assessment["topicPolicy"])
                        )
                    if "wordPolicy" in assessment:
                        assessment_span.set_attribute(
                            "word_policy", json.dumps(assessment["wordPolicy"])
                        )
                    if "sensitiveInformationPolicy" in assessment:
                        assessment_span.set_attribute(
                            "sensitive_info_policy",
                            json.dumps(assessment["sensitiveInformationPolicy"]),
                        )

                # Set status on assessment span
                assessment_span.set_status(Status(StatusCode.OK))

        # Set status appropriately based on guardrail action
        if guardrail_trace.get("action", "") == "GUARDRAIL_INTERVENED":
            guardrail_span.set_status(Status(StatusCode.ERROR))
            guardrail_span.set_attribute(
                "error.message", "Content blocked by guardrail"
            )
        else:
            guardrail_span.set_status(Status(StatusCode.OK))

def handle_user_input_span(trace_data: Dict[str, Any], parent_span):
    """Handle user input as a tool invocation"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_user_input", trace_data, trace_id
    )
    
    # Extract observation data containing user question
    obs = trace_data.get("trace", {}).get("orchestrationTrace", {}).get("observation", {})
    final_response = obs.get('finalResponse', {})
    question_text = final_response.get('text', '')
    
    # Create user input span
    with tracer.start_as_current_span(
        name="askUser",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.OPERATION_NAME: SpanKindValues.TOOL,
            "tool.name": obs.get("type", "ASK_USER"),
            "tool.description": "Ask clarification question to the user",
            "trace_id": trace_id,
            "tool_type": obs.get("type", "ASK_USER"),
            "tool.parameters": json.dumps({
                "question": {
                    "type": "string",
                    "description": "Question to ask the user"
                }
            }),
            SpanAttributes.LLM_COMPLETIONS: question_text,
            SpanAttributes.LLM_PROMPTS: parent_span.attributes.get(SpanAttributes.LLM_PROMPTS, ""),
            SpanAttributes.SPAN_START_TIME: start_time,
            SpanAttributes.SPAN_END_TIME: end_time,
            SpanAttributes.SPAN_DURATION: duration,
        },
        context=trace.set_span_in_context(parent_span)
    ) as user_input_span:
        # Set all relevant attributes from observation data
        if obs:
            if "metadata" in final_response:
                user_input_span.set_attribute(
                    "response.metadata", json.dumps(final_response["metadata"])
                )
            
            if "ask_user_metadata" in obs:
                user_input_span.set_attribute(
                    "ask_user.metadata", json.dumps(obs["ask_user_metadata"])
                )
        user_input_span.set_status(Status(StatusCode.OK))

def handle_file_operations(trace_data: Dict[str, Any], parent_span):
    """Handle file operations in the trace"""
    trace_id = extract_trace_id(trace_data)
    start_time, end_time, duration = timer.check_start_time(
        "handle_file_operations", trace_data, trace_id
    )
    
    # Extract files data
    files_event = trace_data.get("files", {})
    if not files_event or "files" not in files_event:
        return
    
    files_list = files_event.get("files", [])
    
    # Create file processing span
    with tracer.start_as_current_span(
        name="file_processing",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.OPERATION_NAME: "file_operation",
            "file.count": len(files_list),
            "file.types": json.dumps([f.get("type", "unknown") for f in files_list]),
            SpanAttributes.SPAN_START_TIME: start_time,
            SpanAttributes.SPAN_END_TIME: end_time,
            SpanAttributes.SPAN_DURATION: duration,
        },
        context=trace.set_span_in_context(parent_span)
    ) as file_span:
        # Process individual files
        for idx, this_file in enumerate(files_list):
            file_span.set_attribute(f"file.{idx}.name", this_file.get("name", ""))
            file_span.set_attribute(f"file.{idx}.type", this_file.get("type", ""))
            file_span.set_attribute(f"file.{idx}.size", this_file.get("size", 0))
            
            # Add metadata if available
            if "metadata" in this_file:
                file_span.set_attribute(
                    f"file.{idx}.metadata",
                    json.dumps(this_file["metadata"])
                )
            
            # Add content info if available
            if "content" in this_file:
                content_info = this_file["content"]
                if isinstance(content_info, dict):
                    file_span.set_attribute(
                        f"file.{idx}.content_type", 
                        content_info.get("content_type", "")
                    )
                    
                    if "size" in content_info:
                        file_span.set_attribute(
                            f"file.{idx}.content_size", 
                            content_info["size"]
                        )
        file_span.set_status(Status(StatusCode.OK))