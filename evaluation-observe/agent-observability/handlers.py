import json
from opentelemetry.trace import Status, StatusCode
from datetime import datetime
from opentelemetry import trace
from openinference.semconv.trace import (
    DocumentAttributes,
    OpenInferenceSpanKindValues,
    SpanAttributes,
    ToolCallAttributes,
)

from utils import ActionGroupTiming, timing_metrics, trace_context, enhance_span_attributes, safe_span_operation, set_common_attributes

tracer = None
def set_tracer(tracer_instance):
    """Set tracer reference from main module"""
    global tracer
    tracer = tracer_instance

def handle_user_input_span(obs: dict, current_span: trace.Span) -> None:
    """Handle user input as a tool invocation"""
    # Key observation: the original implementation creates a dedicated span
    with timing_metrics.measure("user_input"):
        with tracer.start_as_current_span(
            name="askuser",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                SpanAttributes.TOOL_NAME: "user::askuser",
                SpanAttributes.TOOL_DESCRIPTION: "Asks a question to the user",
                SpanAttributes.TOOL_PARAMETERS: json.dumps({
                    "question": {
                        "type": "string",
                        "description": "Question to ask the user"
                    }
                }),
                ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON: json.dumps({
                    "question": obs.get('finalResponse', {}).get('text', '')
                }),
                SpanAttributes.INPUT_VALUE: obs.get('finalResponse', {}).get('text', ''),
                SpanAttributes.METADATA: json.dumps({
                    "tool_type": "user_interaction",
                    "invocation_type": "ASK_USER",
                    "timestamp": datetime.now().isoformat(),
                    "trace_id": obs.get('traceId', '')
                })
            },
            context=trace.set_span_in_context(current_span)
        ) as user_input_span:
            enhance_span_attributes(user_input_span, obs)
            user_input_span.set_status(Status(StatusCode.OK))

def handle_file_operations(event: dict, current_span):
    """Handles file operations in the trace"""
    if "files" in event:
        with tracer.start_as_current_span(
            name="file_processing",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: "file_operation",
                "file.count": len(event["files"]["files"]),
                "file.types": json.dumps([f.get("type", "unknown") for f in event["files"]["files"]])
            }
        ) as file_span:
            files_event = event["files"]
            files_list = files_event["files"]
            
            for idx, this_file in enumerate(files_list):
                file_span.set_attribute(f"file.{idx}.name", this_file.get("name", ""))
                file_span.set_attribute(f"file.{idx}.type", this_file.get("type", ""))
                file_span.set_attribute(f"file.{idx}.size", this_file.get("size", 0))
                
                if "metadata" in this_file:
                    file_span.set_attribute(
                        f"file.{idx}.metadata",
                        json.dumps(this_file["metadata"])
                    )
            file_span.set_status(Status(StatusCode.OK))

def handle_code_interpreter_output(obs, current_trace_data, tracer):
    """Handle code interpreter output processing"""
    with safe_span_operation():
        with timing_metrics.measure("code_interpreter_output"):
            code_output = obs['codeInterpreterInvocationOutput']
            code_span = current_trace_data['code_span']
            
            if code_span:
                execution_output = code_output.get('executionOutput', '')
                execution_status = code_output.get('executionStatus', '')
                error_message = code_output.get('errorMessage', '')
                
                output_value = {
                    "execution_output": execution_output,
                    "status": execution_status,
                    "error": error_message if error_message else None
                }

                result_span = tracer.start_span(
                    name="code_interpreter_result",
                    attributes={
                        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                        SpanAttributes.OUTPUT_VALUE: json.dumps(output_value),
                        SpanAttributes.METADATA: json.dumps({
                            "execution_status": execution_status,
                            "error_message": error_message,
                            "output_type": "code_execution_result",
                            "execution_time": code_output.get('executionTime', 0)
                        })
                    },
                    context=trace.set_span_in_context(code_span)
                )
                enhance_span_attributes(result_span, code_output)
                result_span.start()
                # Set status based on execution status
                if execution_status == 'FAILED':
                    result_span.set_status(Status(StatusCode.ERROR))
                    result_span.set_attribute("error.message", error_message)
                else:
                    result_span.set_status(Status(StatusCode.OK))
                result_span.end()
                
                code_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(output_value))
                
                if execution_status == 'FAILED':
                    code_span.set_status(Status(StatusCode.ERROR))
                    code_span.set_attribute("error.message", error_message)
                else:
                    code_span.set_status(Status(StatusCode.OK))
                
                code_span.end()
                current_trace_data['code_span'] = None

def handle_knowledge_base_output(obs, current_trace_data, tracer):
    """Handle knowledge base output processing"""
    with safe_span_operation():
        with timing_metrics.measure("knowledge_base_output"):
            kb_output = obs['knowledgeBaseLookupOutput']
            kb_span = current_trace_data['kb_span']            
            if kb_span:
                retrieved_refs = kb_output.get('retrievedReferences', [])
                
                # Process each retrieved document
                for i, ref in enumerate(retrieved_refs):
                    kb_span.set_attribute(
                        f"{SpanAttributes.RETRIEVAL_DOCUMENTS}.{i}.{DocumentAttributes.DOCUMENT_ID}", 
                        ref.get('metadata', {}).get('x-amz-bedrock-kb-chunk-id', '')
                    )
                    kb_span.set_attribute(
                        f"{SpanAttributes.RETRIEVAL_DOCUMENTS}.{i}.{DocumentAttributes.DOCUMENT_CONTENT}", 
                        ref.get('content', {}).get('text', '')
                    )
                    kb_span.set_attribute(
                        f"{SpanAttributes.RETRIEVAL_DOCUMENTS}.{i}.{DocumentAttributes.DOCUMENT_SCORE}", 
                        ref.get('score', 0.0)
                    )
                    kb_span.set_attribute(
                        f"{SpanAttributes.RETRIEVAL_DOCUMENTS}.{i}.{DocumentAttributes.DOCUMENT_METADATA}", 
                        json.dumps({
                            "data_source_id": ref.get('metadata', {}).get('x-amz-bedrock-kb-data-source-id', ''),
                            "location": ref.get('location', {}),
                            "chunk_size": ref.get('metadata', {}).get('chunk_size', 0),
                            "file_type": ref.get('metadata', {}).get('file_type', '')
                        })
                    )
                
                kb_result_span = tracer.start_span(
                    name="knowledge_base_result",
                    attributes={
                        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.RETRIEVER.value,
                        SpanAttributes.OUTPUT_VALUE: json.dumps(retrieved_refs),
                        SpanAttributes.METADATA: json.dumps({
                            "num_results": len(retrieved_refs),
                            "data_sources": list(set(
                                ref.get('metadata', {}).get('x-amz-bedrock-kb-data-source-id', '')
                                for ref in retrieved_refs
                            )),
                            "total_tokens": kb_output.get('totalTokens', 0)
                        })
                    },
                    context=trace.set_span_in_context(kb_span)
                )
                enhance_span_attributes(kb_result_span, kb_output)
                kb_result_span.start()
                # Set status to OK
                kb_result_span.set_status(Status(StatusCode.OK))
                kb_result_span.end()
                
                # Set status based on whether we got results or not
                if retrieved_refs:
                    kb_span.set_status(Status(StatusCode.OK))
                else:
                    kb_span.set_status(Status(StatusCode.OK))
                    kb_span.set_attribute("retrieval.no_results", True)
                
                kb_span.end()
                current_trace_data['kb_span'] = None

def handle_action_group_output(obs, current_trace_data, tracer):
    """Handle action group output processing with timing"""
    with safe_span_operation():
        tool_output = obs['actionGroupInvocationOutput']
        tool_span = current_trace_data.get('tool_span')
        action_group_timing = current_trace_data.get('action_group_timing')
        
        if tool_span and action_group_timing:
            # Record timing for this event
            action_group_timing.record_event()
            
            # Add timing information to the span
            total_duration = action_group_timing.get_total_duration()
            tool_span.set_attribute("duration_ms", total_duration * 1000)  # Convert to milliseconds
            
            # Add detailed timing information
            timing_details = {
                "events": action_group_timing.timings,
                "total_duration": total_duration,
                "start_time": action_group_timing.start_time,
                "end_time": action_group_timing.last_event_time
            }
            
            result_span = tracer.start_span(
                name="tool_result",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                    SpanAttributes.OUTPUT_VALUE: json.dumps(tool_output),
                    SpanAttributes.METADATA: json.dumps({
                        "result_type": "tool_execution_result",
                        "status": tool_output.get('status', 'SUCCESS'),
                        "timing_details": timing_details
                    })
                },
                context=trace.set_span_in_context(tool_span)
            )
            
            enhance_span_attributes(result_span, tool_output)
            result_span.start()
            # Set status based on tool output status
            if tool_output.get('status') == 'FAILED':
                result_span.set_status(Status(StatusCode.ERROR))
                result_span.set_attribute("error.message", tool_output.get('error', ''))
            else:
                result_span.set_status(Status(StatusCode.OK))
            result_span.end()
            
            tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(tool_output))
            
            if tool_output.get('status') == 'FAILED':
                tool_span.set_status(Status(StatusCode.ERROR))
                tool_span.set_attribute("error.message", tool_output.get('error', ''))
            else:
                tool_span.set_status(Status(StatusCode.OK))
            
            tool_span.end()
            
            # Clean up stored data
            current_trace_data['tool_span'] = None
            current_trace_data.pop('action_group_timing', None)

def handle_model_invocation_input(orch_trace, current_trace_data):
    """Handle model invocation input processing"""
    with timing_metrics.measure("model_invocation_input"):
        if 'modelInvocationInput' in orch_trace:
            current_trace_data['llm_input'] = orch_trace['modelInvocationInput']

def handle_model_invocation_output(orch_trace, current_trace_data, current_span, tracer):
    """Handle model invocation output processing"""
    if 'modelInvocationOutput' in orch_trace and current_trace_data.get('llm_input'):
        with safe_span_operation():
            with timing_metrics.measure("model_invocation_output"):
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
                    model_output = orch_trace['modelInvocationOutput']
                    enhance_span_attributes(llm_span, model_output)
                    
                    if 'metadata' in model_output and 'usage' in model_output['metadata']:
                        usage = model_output['metadata']['usage']
                        set_common_attributes(llm_span, {
                            SpanAttributes.LLM_TOKEN_COUNT_PROMPT: usage['inputTokens'],
                            SpanAttributes.LLM_TOKEN_COUNT_COMPLETION: usage['outputTokens'],
                            SpanAttributes.LLM_TOKEN_COUNT_TOTAL: usage['inputTokens'] + usage['outputTokens']
                        })
                    
                    if 'rawResponse' in model_output:
                        llm_span.set_attribute(SpanAttributes.OUTPUT_VALUE, 
                                            model_output['rawResponse'].get('content', ''))
                    
                    # Create reasoning span as child of LLM span if rationale exists
                    if 'rationale' in orch_trace:
                        with tracer.start_as_current_span(
                            name="reasoning",
                            attributes={
                                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                                SpanAttributes.INPUT_VALUE: orch_trace['rationale'].get('text', ''),
                                SpanAttributes.OUTPUT_VALUE: orch_trace['rationale'].get('text', '')
                            },
                            context=trace.set_span_in_context(llm_span)
                        ) as reasoning_span:
                            enhance_span_attributes(reasoning_span, orch_trace['rationale'])
                            reasoning_span.set_status(Status(StatusCode.OK))
                    llm_span.set_status(Status(StatusCode.OK))
                    current_trace_data['llm_input'] = None

def handle_rationale(orch_trace, current_span, tracer):
    """Handle rationale processing"""
    if 'rationale' in orch_trace:
        with safe_span_operation():
            with timing_metrics.measure("rationale"):
                rational_span = tracer.start_span(
                    name="rational",
                    attributes={
                        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
                        SpanAttributes.INPUT_VALUE: orch_trace['rationale'].get('text', ''),
                        SpanAttributes.OUTPUT_VALUE: orch_trace['rationale'].get('text', '')
                    },
                    context=trace.set_span_in_context(current_span)
                )
                enhance_span_attributes(rational_span, orch_trace['rationale'])
                rational_span.start()
                rational_span.set_status(Status(StatusCode.OK))
                rational_span.end()

def handle_invocation_input(orch_trace, current_trace_data, current_span, tracer):
    """Handle different types of invocation inputs without redundant spans"""
    if 'invocationInput' in orch_trace:
        inv_input = orch_trace['invocationInput']
        
        # Process tools directly under the parent orchestration span
        if 'codeInterpreterInvocationInput' in inv_input:
            from processors import process_code_interpreter_span
            code_input = inv_input['codeInterpreterInvocationInput']
            code_span = process_code_interpreter_span(code_input, current_span)
            code_span.start()
            current_trace_data['code_span'] = code_span
        
        elif 'knowledgeBaseLookupInput' in inv_input:
            from processors import process_knowledge_base_span
            kb_input = inv_input['knowledgeBaseLookupInput']
            kb_span = process_knowledge_base_span(kb_input, current_span)
            kb_span.start()
            current_trace_data['kb_span'] = kb_span
        
        elif 'actionGroupInvocationInput' in inv_input:
            handle_action_group_input(inv_input, current_trace_data, current_span, tracer)

def handle_action_group_input(inv_input, current_trace_data, current_span, tracer):
    """Handle action group invocation input with timing"""
    with safe_span_operation():
        action_input = inv_input['actionGroupInvocationInput']
        
        # Initialize timing tracker
        action_group_timing = ActionGroupTiming()
        action_group_timing.start()
        
        # Store timing tracker in trace data
        current_trace_data['action_group_timing'] = action_group_timing
        
        tool_span = tracer.start_span(
            name="tool_execution",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                SpanAttributes.TOOL_NAME: action_input.get('function', ''),
                SpanAttributes.TOOL_DESCRIPTION: action_input.get('description', ''),
                SpanAttributes.TOOL_PARAMETERS: json.dumps(action_input.get('parameters', [])),
                ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON: json.dumps({
                    'name': action_input.get('function', ''),
                    'arguments': action_input.get('parameters', {})
                }),
                SpanAttributes.METADATA: json.dumps({
                    "action_group": action_input.get('actionGroupName', ''),
                    "execution_type": action_input.get('executionType', ''),
                    "invocation_type": inv_input.get('invocationType', ''),
                    "tool_version": action_input.get('version', '1.0'),
                    "start_time": action_group_timing.start_time
                })
            },
            context=trace.set_span_in_context(current_span)
        )
        
        enhance_span_attributes(tool_span, action_input)
        tool_span.start()
        current_trace_data['tool_span'] = tool_span

def handle_observation(orch_trace, current_trace_data, current_span, tracer):
    """Handle observation processing with user input support"""
    if 'observation' in orch_trace:
        with timing_metrics.measure("observation"):
            obs = orch_trace['observation']
            
            # Handle different types of observations
            if obs.get('type') == 'ASK_USER':
                handle_user_input_span(obs, current_span)
            
            elif 'codeInterpreterInvocationOutput' in obs and 'code_span' in current_trace_data:
                handle_code_interpreter_output(obs, current_trace_data, tracer)
            
            elif 'knowledgeBaseLookupOutput' in obs and 'kb_span' in current_trace_data:
                handle_knowledge_base_output(obs, current_trace_data, tracer)
            
            elif 'actionGroupInvocationOutput' in obs and 'tool_span' in current_trace_data:
                handle_action_group_output(obs, current_trace_data, tracer)

            # Process final response if present
            return handle_final_response(obs, current_span)
    
    return False

def handle_final_response(obs, current_span):
    """Handle final response processing"""
    if 'finalResponse' in obs:
        with timing_metrics.measure("final_response"):
            final_response = obs['finalResponse'].get('text', '')
            if current_span:
                current_span.set_attribute(SpanAttributes.OUTPUT_VALUE, final_response)
                enhance_span_attributes(current_span, obs['finalResponse'])
                current_span.set_status(Status(StatusCode.OK))
                current_span.end()
                return True
    return False