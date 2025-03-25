import time
import uuid
import boto3
import json
import logging
from functools import wraps
from datetime import datetime
from opentelemetry import trace
from openinference.instrumentation import using_attributes
from opentelemetry.trace import Status, StatusCode
from openinference.semconv.trace import (
    OpenInferenceSpanKindValues,
    SpanAttributes,
)

# Import configuration
from config import create_tracer_provider
from processors import process_trace_event, set_tracer as set_processors_tracer
from handlers import set_tracer as set_handlers_tracer

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def initialize_tracer(provider=None):
    """Initialize and configure the tracer with the specified provider"""
    # Get tracer provider based on the selected provider
    tracer_provider = create_tracer_provider(provider)
    
    # Create tracer from provider
    tracer = trace.get_tracer(__name__, tracer_provider=tracer_provider)
    
    # Share tracer with other modules
    set_processors_tracer(tracer)
    set_handlers_tracer(tracer)
    
    return tracer

# Default tracer - will be replaced during invocation
tracer = None

def instrument_agent_invocation(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract and handle parameters that shouldn't be passed to the AWS API
        provider = kwargs.pop('provider', None)
        show_traces = kwargs.pop('show_traces', False)
        
        # Initialize the tracer with the specified provider
        global tracer
        tracer = initialize_tracer(provider)
        
        session_id = kwargs.get('sessionId', 'default-session')
        agent_id = kwargs.get('agentId', '')
        agent_alias_id = kwargs.get('agentAliasId', '')
        input_text = kwargs.get('inputText', '')
        
        # Enhanced metadata for better tracing
        metadata = {
            "agent_id": agent_id,
            "agent_alias_id": agent_alias_id,
            "service": "bedrock-agent",
            "environment": "production",
            "request_timestamp": datetime.now().isoformat()
        }
        
        # Tags for easier filtering and grouping
        tags = ["bedrock-agent", "aws", "llm-agent"]
        
        # Prompt template tracking
        prompt_template = "Agent Input: {input_text}"
        prompt_variables = {"input_text": input_text}
        
        with using_attributes(
            session_id=session_id,
            user_id=kwargs.pop('userId', 'anonymous'),
            metadata=metadata,
            tags=tags,
            prompt_template=prompt_template,
            prompt_template_version="1.0",
            prompt_template_variables=prompt_variables
        ):
            with tracer.start_as_current_span(
                name="agent_invocation",
                attributes={
                    SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.AGENT.value,
                    SpanAttributes.LLM_PROVIDER: "aws",
                    SpanAttributes.LLM_SYSTEM: "bedrock",
                    SpanAttributes.INPUT_VALUE: input_text,
                    SpanAttributes.SESSION_ID: session_id,
                    "agent.id": agent_id,
                    "agent.alias_id": agent_alias_id,
                    "agent.metadata": json.dumps(metadata),
                    "tracing.provider": provider or "arize_cloud",
                    "tracing.show_traces": show_traces
                }
            ) as root_span:
                try:
                    response = func(*args, **kwargs)
                    
                    if 'completion' in response:
                        # Process completion events
                        for idx, event in enumerate(response['completion']):
                            if 'chunk' in event:
                                chunk_data = event['chunk']
                                if 'bytes' in chunk_data:
                                    output_text = chunk_data['bytes'].decode('utf8')
                                    root_span.set_attribute(
                                        SpanAttributes.OUTPUT_VALUE,
                                        output_text
                                    )
                                    root_span.set_attribute(
                                        f"chunk.{idx}.content",
                                        output_text
                                    )                            
                            elif 'trace' in event:
                                if show_traces:
                                    print(json.dumps(event['trace'], indent=2, cls=DateTimeEncoder))
                                process_trace_event(event['trace']['trace'], root_span)
                    
                    # Set status to OK when successful
                    root_span.set_status(Status(StatusCode.OK))
                    return response

                except Exception as e:
                    logger.error(f"Error in agent invocation: {str(e)}")
                    root_span.set_status(Status(StatusCode.ERROR))
                    root_span.record_exception(e)
                    root_span.set_attribute("error.message", str(e))
                    root_span.set_attribute("error.type", e.__class__.__name__)
                    raise

    return wrapper

@instrument_agent_invocation
def invoke_bedrock_agent(inputText: str, agentId: str, agentAliasId: str, sessionId: str):
    bedrock_rt_client = boto3.client('bedrock-agent-runtime')
    response = bedrock_rt_client.invoke_agent(
        inputText=inputText,
        agentId=agentId,
        agentAliasId=agentAliasId,
        sessionId=sessionId,
        enableTrace=True
    )
    return response

if __name__ == "__main__":
    try:
        agentId='your-agent-id'
        agentAliasId='your-agent-alias-'
        trace_collector="arize_cloud" # langfuse or arize_local
        userId = "Somename"
        question = "what is the temperature in seattle right now?"
        sessionId= str(uuid.uuid4())
        project_name = f"Agent-Observability-{agentId}-{agentAliasId}"
        invoke_bedrock_agent(
                inputText=question,
                agentId=agentId,
                agentAliasId=agentAliasId,
                sessionId=sessionId,
                provider=trace_collector,
                show_traces=True,  # Control whether to print trace events in the logs or not
                userId=userId,
                project_name=project_name,  # Pass the custom project name,
                streamingConfigurations={
                    "applyGuardrailInterval": 1,
                    "streamFinalResponse": True
                }
            )
    except Exception as e:
        logger.error(f"Error invoking agent: {str(e)}")