"""Constants for the Bedrock Agent Langfuse integration"""


class SpanAttributes:
    """OpenTelemetry semantic conventions for AI operations"""
    # LLM attributes
    LLM_SYSTEM = "gen_ai.system"
    LLM_PROMPTS = "gen_ai.prompt"
    LLM_COMPLETIONS = "gen_ai.completion"
    LLM_USAGE_PROMPT_TOKENS = "gen_ai.usage.prompt_tokens"
    LLM_USAGE_COMPLETION_TOKENS = "gen_ai.usage.completion_tokens"
    LLM_USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"
    LLM_REQUEST_MODEL = "gen_ai.request.model"
    LLM_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    LLM_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    SESSION_ID = "gen_ai.session_id"

    # Span attributes
    TRACE_ID = "trace.id"

    # Tool attributes
    TOOL_NAME = "tool.name"
    TOOL_DESCRIPTION = "tool.description"
    TOOL_PARAMETERS = "tool.parameters"

    # Retriever attributes
    RETRIEVAL_DOCUMENTS = "retrieval.documents"

    # Langfuse specific attributes
    CUSTOM_TAGS = "langfuse.tags"
    USER_ID = "user.id"
    SESSION_ID = "session.id"
    SPAN_START_TIME = "langfuse.startTime"
    SPAN_END_TIME = "langfuse.endTime"
    SPAN_DURATION = "langfuse.duration_ms"
    SPAN_NAME = "langfuse.span.name"

    # Agent attributes
    OPERATION_NAME = "gen_ai.operation.name"

class SpanKindValues:
    """OpenLLMetry span kind values"""
    AGENT = "agent"
    TOOL = "tool"
    TASK = "task"
    DATABASE = "database"


class EventTypes:
    """Trace event types for Amazon Bedrock Agents"""
    PRE_PROCESSING = "preProcessingTrace"
    ORCHESTRATION = "orchestrationTrace"
    POST_PROCESSING = "postProcessingTrace"
    GUARDRAIL = "guardrailTrace"
    FAILURE = "failureTrace"

    # Subtypes
    MODEL_INPUT = "modelInvocationInput"
    MODEL_OUTPUT = "modelInvocationOutput"
    RATIONALE = "rationale"
    OBSERVATION = "observation"
    INVOCATION_INPUT = "invocationInput"
    GUARDRAIL_PRE = "pre"
    GUARDRAIL_POST = "post"