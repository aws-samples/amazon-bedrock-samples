import json
import logging
from opentelemetry import trace
from typing import Dict, Any
from opentelemetry.trace import Status, StatusCode
from openinference.semconv.trace import (
    OpenInferenceSpanKindValues,
    SpanAttributes,
    ToolCallAttributes,
)

from utils import trace_context, timing_metrics, safe_span_operation, enhance_span_attributes
from handlers import (
    handle_model_invocation_input,
    handle_model_invocation_output,
    handle_rationale,
    handle_invocation_input,
    handle_file_operations,
    handle_observation
)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracer = None
current_orchestration_data = {
    'span': None,
    'trace_id': None
}

current_post_processing_data = {
    'span': None,
    'trace_id': None
}

def set_tracer(tracer_instance):
    """Set tracer reference from main module"""
    global tracer
    tracer = tracer_instance

def process_preprocessing_trace(trace_data, parent_span):
    with timing_metrics.measure("preprocessing"):
        with tracer.start_as_current_span(
            name="preprocessing",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
            }
        ) as pre_span:
            with safe_span_operation():
                pre_span.set_attribute("preprocessing.details", 
                                    json.dumps(trace_data['preProcessingTrace']))
                enhance_span_attributes(pre_span, trace_data['preProcessingTrace'])
                pre_span.set_status(Status(StatusCode.OK))

def process_tool_span(tool_input, current_span):
    """Enhanced tool span creation with complete attributes"""
    with timing_metrics.measure("tool_execution"):
        with tracer.start_as_current_span(
            name="tool_execution",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                SpanAttributes.TOOL_NAME: tool_input.get('function', ''),
                SpanAttributes.TOOL_DESCRIPTION: tool_input.get('description', ''),
                SpanAttributes.TOOL_PARAMETERS: json.dumps(tool_input.get('parameters', {})),
                ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON: json.dumps(tool_input.get('arguments', {})),
                SpanAttributes.METADATA: json.dumps({
                    "action_group": tool_input.get('actionGroupName', ''),
                    "execution_type": tool_input.get('executionType', ''),
                    "tool_version": tool_input.get('version', '1.0')
                })
            },
            context=trace.set_span_in_context(current_span)
        ) as tool_span:
            enhance_span_attributes(tool_span, tool_input)
            return tool_span
    
def process_code_interpreter_span(code_input, current_span):
    """Enhanced code interpreter span with tool attributes"""
    with safe_span_operation():
        with timing_metrics.measure("code_interpreter"):
            with tracer.start_as_current_span(
                name="code_interpreter",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                    SpanAttributes.TOOL_NAME: "code_interpreter",
                    SpanAttributes.TOOL_DESCRIPTION: "Executes Python code and returns results",
                    SpanAttributes.TOOL_PARAMETERS: json.dumps({
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        },
                        "purpose": {
                            "type": "string",
                            "description": "Purpose of code execution"
                        }
                    }),
                    ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON: json.dumps({
                        "code": code_input.get('code', ''),
                        "purpose": code_input.get('purpose', ''),
                        "language": "python"
                    }),
                    SpanAttributes.INPUT_VALUE: code_input.get('code', ''),
                    SpanAttributes.METADATA: json.dumps({
                        "invocation_type": "code_execution",
                        "code_type": "python",
                        "execution_context": code_input.get('context', {}),
                        "tool_version": "1.0"
                    })
                },
                context=trace.set_span_in_context(current_span)
            ) as code_span:
                enhance_span_attributes(code_span, code_input)
                return code_span

def process_knowledge_base_span(kb_input, current_span):
    """Enhanced knowledge base span with retriever attributes"""
    with safe_span_operation():
        with timing_metrics.measure("knowledge_base"):
            kb_span = tracer.start_span(
                name="knowledge_base_lookup",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.RETRIEVER.value,
                    SpanAttributes.INPUT_VALUE: kb_input.get('text', ''),
                    SpanAttributes.METADATA: json.dumps({
                        "knowledge_base_id": kb_input.get('knowledgeBaseId', ''),
                        "invocation_type": "SEARCH",
                        "retrieval_type": "semantic",
                        "data_source": kb_input.get('dataSource', ''),
                        "filter_criteria": kb_input.get('filters', {})
                    })
                },
                context=trace.set_span_in_context(current_span)
            )
            enhance_span_attributes(kb_span, kb_input)
            return kb_span

def process_guardrail_trace(trace_data, parent_span):
    guardrail = trace_data['guardrailTrace']
    guardrail_type = "pre" if "pre" in guardrail.get('traceId', '') else "post"
    
    with timing_metrics.measure("guardrail"):
        with tracer.start_as_current_span(
            name=f"guardrail_{guardrail_type}",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.GUARDRAIL.value,
                "guardrail.type": guardrail_type,
                "guardrail.action": guardrail.get('action', ''),
                "guardrail.assessments": json.dumps({
                    "input": guardrail.get('inputAssessments', []),
                    "output": guardrail.get('outputAssessments', [])
                })
            }
        ) as guardrail_span:
            enhance_span_attributes(guardrail_span, guardrail)
            if guardrail.get('action', '') == 'BLOCKED':
                guardrail_span.set_status(Status(StatusCode.ERROR))
                guardrail_span.set_attribute("error.message", "Content blocked by guardrail")
            else:
                guardrail_span.set_status(Status(StatusCode.OK))

def process_failure_trace(trace_data, parent_span):
    with timing_metrics.measure("failure"):
        with tracer.start_as_current_span(
            name="failure",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
            }
        ) as failure_span:
            failure_span.set_attribute("failure.reason", 
                                    trace_data['failureTrace'].get('failureReason', ''))
            enhance_span_attributes(failure_span, trace_data['failureTrace'])
            failure_span.set_status(Status(StatusCode.ERROR))

def process_postprocessing_trace(trace_data, parent_span):
    """Process post-processing trace with the same pattern as orchestration trace"""
    global current_post_processing_data
    postProcessingTrace = trace_data['postProcessingTrace']
    
    def get_trace_info(data_part):
        """Extract trace ID from post-processing data"""
        if 'modelInvocationInput' in data_part:
            return {
                'trace_id': data_part['modelInvocationInput'].get('traceId', ''),
                'type': 'POST_PROCESSING'
            }
        elif 'modelInvocationOutput' in data_part:
            return {
                'trace_id': data_part['modelInvocationOutput'].get('traceId', ''),
                'type': 'POST_PROCESSING'
            }
        return None
    
    trace_info = get_trace_info(postProcessingTrace)
    if not trace_info:
        return
    
    trace_id = trace_info['trace_id']
    
    # Create new post-processing span only if we don't have one for this trace_id
    if trace_id != current_post_processing_data.get('trace_id'):
        if current_post_processing_data.get('span'):
            if current_post_processing_data.get('span').status.status_code == StatusCode.UNSET:
                current_post_processing_data.get('span').set_status(Status(StatusCode.OK))
            current_post_processing_data['span'].end()
        
        # Create new post-processing span
        post_processing_span = tracer.start_span(
            name="postProcessingTrace",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                SpanAttributes.METADATA: json.dumps({
                    "trace_id": trace_id,
                    "type": trace_info['type']
                })
            },
            context=trace.set_span_in_context(parent_span)
        )
        enhance_span_attributes(post_processing_span, trace_info)
        post_processing_span.start()
        
        current_post_processing_data = {
            'span': post_processing_span,
            'trace_id': trace_id
        }
        
        # Initialize trace storage
        trace_context.set(trace_id, {
            'llm_input': None,
            'parsed_response': None
        })
    
    current_trace_data = trace_context.get(trace_id)
    current_span = current_post_processing_data['span']
    
    # Handle model invocation input (preparation phase)
    if 'modelInvocationInput' in postProcessingTrace:
        model_input = postProcessingTrace['modelInvocationInput']
        current_trace_data['llm_input'] = model_input
        trace_context.set(trace_id, current_trace_data)
    
    # Handle model invocation output (generation phase)
    elif 'modelInvocationOutput' in postProcessingTrace and current_trace_data.get('llm_input'):
        with safe_span_operation():
            model_output = postProcessingTrace['modelInvocationOutput']

            with tracer.start_as_current_span(
                name="llm",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.LLM.value,
                    SpanAttributes.LLM_PROVIDER: "aws",
                    SpanAttributes.LLM_SYSTEM: "bedrock",
                    SpanAttributes.INPUT_VALUE: current_trace_data['llm_input'].get('text', ''),
                    SpanAttributes.LLM_INVOCATION_PARAMETERS: json.dumps(
                        current_trace_data['llm_input'].get('inferenceConfiguration', {})
                    )
                },
                context=trace.set_span_in_context(current_span)
            ) as llm_span:
                enhance_span_attributes(llm_span, model_output)
                
                if 'metadata' in model_output and 'usage' in model_output['metadata']:
                    usage = model_output['metadata']['usage']
                    set_common_attributes(llm_span, {
                        SpanAttributes.LLM_TOKEN_COUNT_PROMPT: usage['inputTokens'],
                        SpanAttributes.LLM_TOKEN_COUNT_COMPLETION: usage['outputTokens'],
                        SpanAttributes.LLM_TOKEN_COUNT_TOTAL: usage['inputTokens'] + usage['outputTokens']
                    })
                
                if 'rawResponse' in model_output:
                    raw_content = model_output['rawResponse'].get('content', '')
                    llm_span.set_attribute(SpanAttributes.OUTPUT_VALUE, raw_content)

                llm_span.set_status(Status(StatusCode.OK))
            
            # If there's a parsed response, create a final_response span
            if 'parsedResponse' in model_output:
                parsed_text = model_output['parsedResponse'].get('text', '')
                current_span.set_attribute(SpanAttributes.OUTPUT_VALUE, parsed_text)
                
                with tracer.start_as_current_span(
                    name="final_response",
                    attributes={
                        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                        SpanAttributes.INPUT_VALUE: model_output.get('rawResponse', {}).get('content', ''),
                        SpanAttributes.OUTPUT_VALUE: parsed_text,
                    },
                    context=trace.set_span_in_context(current_span)
                ) as final_response_span:
                    final_response_span.set_status(Status(StatusCode.OK))

            current_span.set_status(Status(StatusCode.OK))
            current_span.end()
            
            # Clean up
            trace_context.delete(trace_id)
            current_post_processing_data = {
                'span': None,
                'trace_id': None
            }

def set_common_attributes(span, attributes: Dict[str, Any]) -> None:
    for key, value in attributes.items():
        if value is not None and value != "":
            span.set_attribute(key, value)

def process_orchestration_trace(trace_data, parent_span):
    """Process orchestration trace with proper span hierarchy"""
    global current_orchestration_data    
    orch_trace = trace_data['orchestrationTrace']
    
    def get_trace_info(data_part):
        for field in ['modelInvocationInput', 'modelInvocationOutput', 'invocationInput', 'observation', 'rationale']:
            if field in data_part and 'traceId' in data_part[field]:
                return {
                    'trace_id': data_part[field]['traceId'],
                    'type': data_part[field].get('type', 'ORCHESTRATION')
                }
        return None

    trace_info = get_trace_info(orch_trace)
    if not trace_info:
        return

    trace_id = trace_info['trace_id']
    
    # Create new orchestration span only if we don't have one for this trace_id
    if trace_id != current_orchestration_data.get('trace_id'):
        if current_orchestration_data.get('span'):
            if current_orchestration_data.get('span').status.status_code == StatusCode.UNSET:
                current_orchestration_data.get('span').set_status(Status(StatusCode.OK))
            current_orchestration_data['span'].end()
        
        # Create new orchestration span
        orchestration_span = tracer.start_span(
            name="orchestrationTrace",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                SpanAttributes.METADATA: json.dumps({
                    "trace_id": trace_id,
                    "type": trace_info['type']
                })
            },
            context=trace.set_span_in_context(parent_span)
        )
        enhance_span_attributes(orchestration_span, trace_info)
        orchestration_span.start()
        
        current_orchestration_data = {
            'span': orchestration_span,
            'trace_id': trace_id
        }
        
        # Initialize trace storage
        trace_context.set(trace_id, {
            'llm_input': None,
            'tool_input': None,
            'kb_span': None
        })

    current_trace_data = trace_context.get(trace_id)
    current_span = current_orchestration_data['span']

    # Handle different trace types
    handle_model_invocation_input(orch_trace, current_trace_data)
    handle_model_invocation_output(orch_trace, current_trace_data, current_span, tracer)
    handle_rationale(orch_trace, current_span, tracer)
    handle_invocation_input(orch_trace, current_trace_data, current_span, tracer)
    
    # Handle file operations if present
    if "files" in trace_data:
        handle_file_operations(trace_data, current_span)
    
    final_response = handle_observation(orch_trace, current_trace_data, current_span, tracer)
    if final_response:
        if current_span.status.status_code == StatusCode.UNSET:
            current_span.set_status(Status(StatusCode.OK))
        
        current_orchestration_data = {
            'span': None,
            'trace_id': None
        }
        trace_context.delete(trace_id)

pending_guardrail_post = None
def process_trace_event(trace_data, root_span):
    """Process different types of trace events with controlled ordering"""
    global pending_guardrail_post
    
    # Check if this is a guardrail_post event
    if 'guardrailTrace' in trace_data:
        guardrail = trace_data['guardrailTrace']
        guardrail_type = "pre" if "pre" in guardrail.get('traceId', '') else "post"
        
        if guardrail_type == "post":
            pending_guardrail_post = trace_data
            return
        else:
            process_guardrail_trace(trace_data, root_span)
    
    # Process other trace events in normal order
    elif 'preProcessingTrace' in trace_data:
        process_preprocessing_trace(trace_data, root_span)
    elif 'orchestrationTrace' in trace_data:
        process_orchestration_trace(trace_data, root_span)
    elif 'postProcessingTrace' in trace_data:
        process_postprocessing_trace(trace_data, root_span)
        
        # After post-processing is complete, process any pending guardrail_post
        if pending_guardrail_post:
            process_guardrail_trace(pending_guardrail_post, root_span)
            pending_guardrail_post = None
    elif 'failureTrace' in trace_data:
        process_failure_trace(trace_data, root_span)
        
        # After failure is processed, process any pending guardrail_post
        if pending_guardrail_post:
            process_guardrail_trace(pending_guardrail_post, root_span)
            pending_guardrail_post = None