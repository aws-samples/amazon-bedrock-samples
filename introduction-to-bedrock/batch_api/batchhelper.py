from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union
from enum import Enum
import pandas as pd
import json


class ModelType(Enum):
    CLAUDE = "claude"
    TITAN = "titan"
    LLAMA = "llama"
    NOVA = "nova"

# Base configuration
class BaseGenerationConfig(BaseModel):
    temperature: float = 0.0
    top_p: float = 0.99
    max_tokens: int = 256
    stop_sequences: Optional[List[str]] = Field(default_factory=list)
    top_k: Optional[int] = None
    system: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True
    )

# Model-specific prompts
class TitanPrompt(BaseModel):
    inputText: str
    textGenerationConfig: dict

    def model_dump(self, *args, **kwargs) -> dict:
        return {
            "inputText": self.inputText,
            "textGenerationConfig": {
                "temperature": self.textGenerationConfig["temperature"],
                "topP": self.textGenerationConfig["top_p"],
                "maxTokenCount": self.textGenerationConfig["max_tokens"],
                "stopSequences": self.textGenerationConfig["stop_sequences"]
            }
        }

class LlamaPrompt(BaseModel):
    prompt: str
    temperature: float
    top_p: float
    max_gen_len: int

    def model_dump(self, *args, **kwargs) -> dict:
        return {
            "prompt": self.prompt,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_gen_len": self.max_gen_len
        }

class ClaudePrompt(BaseModel):
    anthropic_version: str = "bedrock-2023-05-31"
    # anthropic_beta: List[str] = Field(default_factory=lambda: ["computer-use-2024-10-22"])
    max_tokens: int
    system: Optional[str] = None
    messages: List[dict]
    temperature: float
    top_p: float
    top_k: int

    def model_dump(self, *args, **kwargs) -> dict:
        return {
            "anthropic_version": self.anthropic_version,
            # "anthropic_beta": self.anthropic_beta,
            "max_tokens": self.max_tokens,
            "system": self.system,
            "messages": self.messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k
        }

class NovaTextContent(BaseModel):
    text: str

class NovaMessage(BaseModel):
    role: str = "user"
    content: List[NovaTextContent]

class NovaInferenceConfig(BaseModel):
    max_new_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stopSequences: Optional[List[str]] = None

class NovaSystemMessage(BaseModel):
    text: str

class NovaPrompt(BaseModel):
    system: Optional[List[NovaSystemMessage]] = None
    messages: List[NovaMessage]
    inferenceConfig: Optional[NovaInferenceConfig] = None

    def model_dump(self, *args, **kwargs) -> dict:
        base_dict = super().model_dump(*args, **kwargs)
        # Remove None values
        return {k: v for k, v in base_dict.items() if v is not None}

def get_request_body(text: str, model_type: ModelType, config: Optional[BaseGenerationConfig] = None) -> Union[TitanPrompt, LlamaPrompt, ClaudePrompt, NovaPrompt]:
    if config is None:
        config = BaseGenerationConfig()

    if model_type == ModelType.TITAN:
        return TitanPrompt(
            inputText=text,
            textGenerationConfig={
                "temperature": config.temperature,
                "top_p": config.top_p,
                "max_tokens": config.max_tokens,
                "stop_sequences": config.stop_sequences
            }
        ).model_dump()
    
    elif model_type == ModelType.LLAMA:
        return LlamaPrompt(
            prompt=text,
            temperature=config.temperature,
            top_p=config.top_p,
            max_gen_len=config.max_tokens
        ).model_dump()
    
    elif model_type == ModelType.CLAUDE:
        return ClaudePrompt(
            max_tokens=config.max_tokens,
            system=config.system,
            messages=[{
                "role": "user",
                "content": [{"type": "text", "text": text}]
            }],
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k or 50
        ).model_dump()
    
    elif model_type == ModelType.NOVA:
        nova_config = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_new_tokens": config.max_tokens,
            "top_k": config.top_k,
            "stopSequences": config.stop_sequences
        }
        
        prompt = NovaPrompt(
            messages=[
                NovaMessage(
                    content=[NovaTextContent(text=text)]
                )
            ],
            inferenceConfig=NovaInferenceConfig(**nova_config)
        )
        
        # Add system message if provided
        if config.system:
            prompt.system = [NovaSystemMessage(text=config.system)]
        
        return prompt.model_dump()
    
    raise ValueError(f"Unknown model type: {model_type}")



def generate_record_id(index: int, prefix: str = "REC") -> str:
    """Generate an 11 character alphanumeric record ID."""
    return f"{prefix}{str(index).zfill(8)}"

def dataframe_to_jsonl(
    df: pd.DataFrame,
    model_type: ModelType,
    output_file: str,
    text_column: str = "text",
    record_id_column: Optional[str] = None,
    base_config: Optional[BaseGenerationConfig] = None
) -> None:
    """
    Convert a DataFrame to a JSONL file for batch inference.
    
    Args:
        df: Input DataFrame containing text and optional configuration columns
        model_type: Type of model to generate prompts for
        output_file: Path to save the JSONL file
        text_column: Name of the column containing input text
        record_id_column: Optional column name containing record IDs
        base_config: Default configuration to use for missing values
    """
    if base_config is None:
        base_config = BaseGenerationConfig()
    
    with open(output_file, 'w') as f:
        for idx, row in df.iterrows():
            # Get or generate record ID
            record_id = str(row[record_id_column]) if record_id_column and record_id_column in row else generate_record_id(idx)
            
            # Create config from row data, falling back to base_config for missing values
            config_dict = base_config.model_dump()
            for field in config_dict.keys():
                if field in row and pd.notna(row[field]):
                    config_dict[field] = row[field]
            
            row_config = BaseGenerationConfig(**config_dict)
            
            # Create batch inference record
            record = {
                "recordId": record_id,
                "modelInput": get_request_body(
                    text=str(row[text_column]),
                    model_type=model_type,
                    config=row_config
                )
            }
            
            # Write to JSONL file
            f.write(json.dumps(record) + '\n')
