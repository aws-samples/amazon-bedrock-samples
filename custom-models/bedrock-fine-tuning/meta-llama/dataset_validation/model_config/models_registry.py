from .model import Model
from .model_type import ModelType
from .input_type import InputType

MODELS = {
    "meta.llama3-1-8b-instruct-v1": Model(
        model_type=ModelType.TEXT,
        input_type=InputType.PROMPT_COMPLETION,
    ),
    "meta.llama3-1-70b-instruct-v1": Model(
        model_type=ModelType.TEXT,
        input_type=InputType.PROMPT_COMPLETION,
    ),
    "meta.llama3-2-1b-instruct-v1": Model(
        model_type=ModelType.TEXT,
        input_type=InputType.CONVERSE,
    ),
    "meta.llama3-2-3b-instruct-v1": Model(
        model_type=ModelType.TEXT,
        input_type=InputType.CONVERSE,
    ),
    "meta.llama3-2-11b-instruct-v1": Model(
        model_type=ModelType.MULTIMODAL,
        input_type=InputType.CONVERSE,
    ),
    "meta.llama3-2-90b-instruct-v1": Model(
        model_type=ModelType.MULTIMODAL,
        input_type=InputType.CONVERSE,
    ),
}
