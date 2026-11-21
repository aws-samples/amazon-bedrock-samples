"""
Template-based prompt generation for sequential BDA optimization.
"""
import json
from typing import Dict, List, Optional

def fill_template(template: str, params: Dict[str, str]) -> str:
    """
    Fill a template with parameters.
    
    Args:
        template (str): Template string with {param} placeholders
        params (Dict[str, str]): Dictionary of parameter values
        
    Returns:
        str: Filled template
    """
    try:
        return template.format(**params)
    except KeyError as e:
        print(f"Missing parameter in template: {e}")
        return template
    except Exception as e:
        print(f"Error filling template: {e}")
        return template

# Base template for all strategies
BASE_TEMPLATE = """You are a specialized AI agent focused on {task_type} extraction. Your role is to {action_verb} {target_information} from {document_type} documents following these parameters:

Context: {context_description}
Format Requirements: {format_specs}
Location Hints: {location_cues}
Expected Pattern: {pattern_description}
Output Constraints: {output_rules}

Apply these extraction rules while maintaining accuracy and consistency."""

# Strategy-specific parameter sets
STRATEGY_PARAMS = {
    "direct": {
        "task_type": "field",
        "action_verb": "identify and extract",
        "target_information": "{field_name}",
        "document_type": "structured",
        "context_description": "Find exact matches for {field_name}",
        "format_specs": "Match format like {expected_output}",
        "location_cues": "Look for standard document locations",
        "pattern_description": "Follow typical {field_name} patterns",
        "output_constraints": "Return only the extracted value"
    },
    "context": {
        "task_type": "contextual",
        "action_verb": "locate and extract",
        "target_information": "{field_name}",
        "document_type": "context-rich",
        "context_description": "Analyze document structure and surrounding content",
        "format_specs": "Match format like {expected_output}",
        "location_cues": "Look for sections containing related information",
        "pattern_description": "Consider typical placement patterns",
        "output_constraints": "Extract with contextual validation"
    },
    "format": {
        "task_type": "format-specific",
        "action_verb": "parse and extract",
        "target_information": "{field_name}",
        "document_type": "formatted",
        "context_description": "Focus on structural patterns",
        "format_specs": "Exactly match {expected_output} format",
        "location_cues": "Look for formatted sections",
        "pattern_description": "Identify specific formatting patterns",
        "output_constraints": "Ensure format compliance"
    },
    "document": {
        "task_type": "document-aware",
        "action_verb": "precisely extract",
        "target_information": "{field_name}",
        "document_type": "this specific",
        "context_description": "Use the document's actual content and structure",
        "format_specs": "Match format exactly like {expected_output}",
        "location_cues": "Look for content in sections that contain relevant information",
        "pattern_description": "Identify patterns specific to this document",
        "output_constraints": "Extract with high precision based on document context"
    }
}

def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing special characters.
    
    Args:
        text (str): Text to sanitize
        
    Returns:
        str: Sanitized text
    """
    # Replace newlines with spaces
    text = text.replace('\n', ' ')
    
    # Replace special quotes with regular quotes
    text = text.replace('\u2019', "'")
    text = text.replace('\u201c', '"')
    text = text.replace('\u201d', '"')
    
    return text

def generate_instruction(strategy: str, field_name: str, expected_output: str) -> str:
    """
    Generate a strategy-specific instruction using the field name and expected output.
    
    Args:
        strategy (str): Strategy name ('direct', 'context', 'format', or 'document')
        field_name (str): Name of the field to extract
        expected_output (str): Expected output format
        
    Returns:
        str: Generated instruction
    """
    # Sanitize inputs to avoid special characters
    field_name = sanitize_text(field_name)
    sanitized_output = sanitize_text(expected_output)
    
    # Create a short example from the expected output
    example = sanitized_output
    if len(example) > 30:  # Use a shorter snippet for examples
        example = example[:27] + "..."
    
    # Generate strategy-specific instructions that use the expected output
    if strategy == "original":
        return f"Extract the {field_name} from the document."
    elif strategy == "direct":
        return f"Directly extract the exact {field_name} from the document. Look for text that matches '{example}'."
    elif strategy == "context":
        return f"Analyze the document context to extract the {field_name}. Consider surrounding text and document structure to find information like '{example}'."
    elif strategy == "format":
        return f"Extract the {field_name} with attention to formatting. The output should follow the format pattern of '{example}'."
    elif strategy == "document":
        return f"Using the full document content and structure, extract the {field_name} field. The expected format is similar to '{example}'."
    else:
        print(f"Unknown strategy: {strategy}, using 'direct' instead")
        return f"Extract the {field_name} from the document."

# Define the strategy sequence
STRATEGY_SEQUENCE = ["original", "direct", "context", "format", "document"]

def get_next_strategy(current_strategy: str) -> Optional[str]:
    """
    Get the next strategy in the sequence.
    
    Args:
        current_strategy (str): Current strategy
        
    Returns:
        str or None: Next strategy, or None if there are no more strategies
    """
    try:
        current_index = STRATEGY_SEQUENCE.index(current_strategy)
        next_index = current_index + 1
        if next_index < len(STRATEGY_SEQUENCE):
            return STRATEGY_SEQUENCE[next_index]
        return None
    except ValueError:
        print(f"Unknown strategy: {current_strategy}")
        return "direct"  # Default to direct if strategy unknown
