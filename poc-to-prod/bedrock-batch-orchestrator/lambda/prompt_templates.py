from typing import Dict, Union, List, Optional, TypedDict, Literal

"""
Add prompt templates for text-based and multimodal models here.

The following dict maps a `prompt_id` to a prompt template.

Prompt templates can be defined in two formats:
1. Simple string (backward compatible): Just the prompt text with {variable} placeholders
2. Dictionary with additional configuration:
   - template: The prompt text
   - output_schema: Optional schema for extracting structured fields from responses
   - expansion_rule: Set to True with a 'prompts' array to define multi-entry expansion rules

Supply the prompt_id in the state machine input and ensure that your CSV file
has columns for the required formatting keys (enclosed in curly braces {}) in that template.

e.g. For prompt_id=`joke_about_topic`, your input CSV must include a `topic` column in order to 
fill that key.
"""


class OutputSchemaField(TypedDict):
    """Defines how to extract structured fields from model responses"""
    type: Literal['json', 'regex']  # Extraction method
    fields: Dict[str, str]  # field_name -> extraction_pattern (JSON path or regex)


class ExpansionRule(TypedDict):
    """Defines a set of prompts for multi-entry expansion"""
    expansion_rule: bool  # Must be True
    prompts: List[str]  # List of prompt_ids to apply


class PromptTemplate(TypedDict):
    """Full prompt template with optional output schema"""
    template: str
    output_schema: Optional[OutputSchemaField]


# Support both string and dict formats for backward compatibility
PromptValue = Union[str, PromptTemplate, ExpansionRule]


prompt_id_to_template: Dict[str, PromptValue] = {
    # ============================================================================
    # SIMPLE STRING TEMPLATES (Backward Compatible)
    # ============================================================================
    # These templates work exactly as before - just text with {variable} placeholders
    
    'joke_about_topic': '''Tell me a joke about {topic} in less than 50 words.''',
    
    'sentiment_classifier': '''
        Classify the sentiment of the following text as `positive`, `negative`, or `neutral`. 
        Just give the sentiment, no preamble or explanation.
        
        Text:
        {input_text}''',
    
    'question_answering': '''You are an AI assistant tasked with providing accurate and justified answers to users' questions.
    
    You will be given a task, and you should respond with a chain-of-thought surrounded by <thinking> tags, then a final answer in <answer> tags.
    
    For example, given the following task:
    
    <task>
    You are given an original reference as well as a system generated reference. Your task is to judge the naturaleness of the system generated reference. If the utterance could have been produced by a native speaker output 1, else output 0. System Reference: may i ask near where? Original Reference: where do you need a hotel near?.
    </task>
    
    <thinking>
    The utterance "may i ask near where?" is not natural. 
    This utterance does not make sense grammatically.
    Thus we output 0.
    </thinking>
    
    <answer>0</answer>

    Your turn. Please respond to the following task:
    
    <task>
    {source}
    </task>
    
    ''',
    
    # ============================================================================
    # TEMPLATES WITH JSON OUTPUT SCHEMAS
    # ============================================================================
    # These templates include structured output extraction using JSON paths
    
    'classify_product': {
        'template': '''Analyze this product and return a JSON object with the category and confidence score.
        
Product: {product_name}
Description: {description}

Return your response in this exact JSON format:
{{
    "category": "electronics|clothing|food|other",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'category': '$.category',
                'confidence': '$.confidence',
                'reasoning': '$.reasoning'
            }
        }
    },
    
    'image_classification': {
        'template': '''What is the main subject of this image? Provide a structured response.

Return your response in this exact JSON format:
{{
    "main_subject": "description",
    "confidence": 0.0-1.0,
    "objects_detected": ["object1", "object2"]
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'main_subject': '$.main_subject',
                'confidence': '$.confidence',
                'objects_detected': '$.objects_detected'
            }
        }
    },
    
    # ============================================================================
    # TEMPLATES WITH REGEX OUTPUT SCHEMAS
    # ============================================================================
    # These templates extract fields using regex patterns
    
    'extract_color': {
        'template': '''What is the primary color of the item in this image? 
Respond in the format: "Color: [color_name]"''',
        'output_schema': {
            'type': 'regex',
            'fields': {
                'color': r'Color:\s*(\w+)'
            }
        }
    },
    
    'extract_size': {
        'template': '''What size is visible on this clothing item?
Respond in the format: "Size: [size]"''',
        'output_schema': {
            'type': 'regex',
            'fields': {
                'size': r'Size:\s*(\w+)'
            }
        }
    },
    
    'extract_brand': {
        'template': '''What brand or logo is visible in this image?
Respond in the format: "Brand: [brand_name]"''',
        'output_schema': {
            'type': 'regex',
            'fields': {
                'brand': r'Brand:\s*([\w\s]+)'
            }
        }
    },
    
    # ============================================================================
    # EXPANSION RULES
    # ============================================================================
    # These define sets of prompts for multi-entry expansion
    # When used, each input record generates multiple batch job entries
    
    'detailed_clothing_analysis': {
        'expansion_rule': True,
        'prompts': ['extract_color', 'extract_size', 'extract_brand']
    },
    
    'comprehensive_product_review': {
        'expansion_rule': True,
        'prompts': ['classify_product', 'sentiment_classifier']
    },
    
    # ============================================================================
    # CLOTHING IMAGE ANALYSIS PIPELINE PROMPTS
    # ============================================================================
    
    # Stage 1: Classify clothing category
    'classify_clothing_category': {
        'template': '''Analyze this clothing item image and classify it into one of these categories: shorts, shoes, pants, dress, t-shirt.

Return your response in this exact JSON format:
{{
    "category": "shorts|shoes|pants|dress|t-shirt",
    "confidence": 0.0-1.0
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'category': '$.category',
                'confidence': '$.confidence'
            }
        }
    },
    
    # Stage 2: Category-specific metadata extraction prompts
    
    # Shorts metadata
    'extract_shorts_metadata': {
        'template': '''Analyze this shorts image and extract the following details.

Return your response in this exact JSON format:
{{
    "color": "primary color",
    "length": "short|mid|long",
    "material": "denim|cotton|athletic|other",
    "pattern": "solid|striped|plaid|printed|other",
    "style": "casual|athletic|formal|other"
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'color': '$.color',
                'length': '$.length',
                'material': '$.material',
                'pattern': '$.pattern',
                'style': '$.style'
            }
        }
    },
    
    # Shoes metadata
    'extract_shoes_metadata': {
        'template': '''Analyze this shoes image and extract the following details.

Return your response in this exact JSON format:
{{
    "color": "primary color",
    "type": "sneakers|boots|sandals|heels|flats|loafers|other",
    "material": "leather|canvas|synthetic|suede|other",
    "style": "casual|athletic|formal|other",
    "closure": "laces|slip-on|velcro|buckle|zipper|other"
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'color': '$.color',
                'type': '$.type',
                'material': '$.material',
                'style': '$.style',
                'closure': '$.closure'
            }
        }
    },
    
    # Pants metadata
    'extract_pants_metadata': {
        'template': '''Analyze this pants image and extract the following details.

Return your response in this exact JSON format:
{{
    "color": "primary color",
    "fit": "skinny|slim|regular|relaxed|wide",
    "material": "denim|cotton|chino|dress|athletic|other",
    "pattern": "solid|striped|plaid|printed|other",
    "style": "casual|business|formal|athletic|other"
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'color': '$.color',
                'fit': '$.fit',
                'material': '$.material',
                'pattern': '$.pattern',
                'style': '$.style'
            }
        }
    },
    
    # Dress metadata
    'extract_dress_metadata': {
        'template': '''Analyze this dress image and extract the following details.

Return your response in this exact JSON format:
{{
    "color": "primary color",
    "length": "mini|knee|midi|maxi",
    "sleeve": "sleeveless|short|three-quarter|long",
    "pattern": "solid|floral|striped|polka-dot|printed|other",
    "style": "casual|cocktail|formal|maxi|sundress|other"
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'color': '$.color',
                'length': '$.length',
                'sleeve': '$.sleeve',
                'pattern': '$.pattern',
                'style': '$.style'
            }
        }
    },
    
    # T-shirt metadata
    'extract_tshirt_metadata': {
        'template': '''Analyze this t-shirt image and extract the following details.

Return your response in this exact JSON format:
{{
    "color": "primary color",
    "sleeve": "sleeveless|short|long",
    "neckline": "crew|v-neck|scoop|henley|polo|other",
    "pattern": "solid|striped|graphic|logo|printed|other",
    "fit": "fitted|regular|relaxed|oversized"
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'color': '$.color',
                'sleeve': '$.sleeve',
                'neckline': '$.neckline',
                'pattern': '$.pattern',
                'fit': '$.fit'
            }
        }
    },
    
    # Stage 3: Generate product title and description
    'generate_product_listing': {
        'template': '''Based on the following clothing item details, generate a compelling product title and description for an e-commerce listing.

Category: {category}
Metadata: {metadata}

Return your response in this exact JSON format:
{{
    "title": "concise product title (max 80 characters)",
    "description": "detailed product description (2-3 sentences)",
    "keywords": ["keyword1", "keyword2", "keyword3"]
}}''',
        'output_schema': {
            'type': 'json',
            'fields': {
                'title': '$.title',
                'description': '$.description',
                'keywords': '$.keywords'
            }
        }
    }
}


def get_template_text(prompt_id: str) -> str:
    """
    Extract template text from a prompt, handling both string and dict formats.
    
    Args:
        prompt_id: The prompt identifier
        
    Returns:
        The prompt template text
        
    Raises:
        KeyError: If prompt_id is not found
        ValueError: If prompt_id refers to an expansion rule
    """
    if prompt_id not in prompt_id_to_template:
        raise KeyError(f"Prompt ID '{prompt_id}' not found in prompt_templates")
    
    prompt_value = prompt_id_to_template[prompt_id]
    
    # Check if it's an expansion rule
    if isinstance(prompt_value, dict) and prompt_value.get('expansion_rule'):
        raise ValueError(f"'{prompt_id}' is an expansion rule, not a prompt template")
    
    # Handle string format (backward compatible)
    if isinstance(prompt_value, str):
        return prompt_value
    
    # Handle dict format
    if isinstance(prompt_value, dict) and 'template' in prompt_value:
        return prompt_value['template']
    
    raise ValueError(f"Invalid prompt format for '{prompt_id}'")


def get_output_schema(prompt_id: str) -> Optional[OutputSchemaField]:
    """
    Get the output schema for a prompt, if defined.
    
    Args:
        prompt_id: The prompt identifier
        
    Returns:
        OutputSchemaField if defined, None otherwise
        
    Raises:
        KeyError: If prompt_id is not found
    """
    if prompt_id not in prompt_id_to_template:
        raise KeyError(f"Prompt ID '{prompt_id}' not found in prompt_templates")
    
    prompt_value = prompt_id_to_template[prompt_id]
    
    # Only dict format can have output_schema
    if isinstance(prompt_value, dict) and 'output_schema' in prompt_value:
        return prompt_value['output_schema']
    
    return None


def get_expansion_rule(rule_name: str) -> List[str]:
    """
    Get the list of prompt_ids for an expansion rule.
    
    Args:
        rule_name: The expansion rule name
        
    Returns:
        List of prompt_ids to apply
        
    Raises:
        KeyError: If rule_name is not found
        ValueError: If rule_name is not an expansion rule
    """
    if rule_name not in prompt_id_to_template:
        raise KeyError(f"Expansion rule '{rule_name}' not found in prompt_templates")
    
    rule_value = prompt_id_to_template[rule_name]
    
    if not isinstance(rule_value, dict) or not rule_value.get('expansion_rule'):
        raise ValueError(f"'{rule_name}' is not an expansion rule")
    
    return rule_value['prompts']


def is_expansion_rule(name: str) -> bool:
    """
    Check if a name refers to an expansion rule.
    
    Args:
        name: The name to check
        
    Returns:
        True if name refers to an expansion rule, False otherwise
    """
    if name not in prompt_id_to_template:
        return False
    
    value = prompt_id_to_template[name]
    return isinstance(value, dict) and value.get('expansion_rule', False) is True


def validate_output_schema(output_schema: OutputSchemaField) -> List[str]:
    """
    Validate an output schema definition.
    
    Args:
        output_schema: The schema to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if 'type' not in output_schema:
        errors.append("output_schema missing 'type' field")
        return errors
    
    schema_type = output_schema['type']
    if schema_type not in ['json', 'regex']:
        errors.append(f"Invalid schema type '{schema_type}', must be 'json' or 'regex'")
    
    if 'fields' not in output_schema:
        errors.append("output_schema missing 'fields' field")
        return errors
    
    fields = output_schema['fields']
    if not isinstance(fields, dict):
        errors.append("output_schema 'fields' must be a dictionary")
        return errors
    
    if len(fields) == 0:
        errors.append("output_schema 'fields' cannot be empty")
    
    return errors


def validate_expansion_rule(rule_name: str) -> List[str]:
    """
    Validate an expansion rule definition.
    
    Args:
        rule_name: The expansion rule name
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if rule_name not in prompt_id_to_template:
        errors.append(f"Expansion rule '{rule_name}' not found")
        return errors
    
    rule_value = prompt_id_to_template[rule_name]
    
    if not isinstance(rule_value, dict):
        errors.append(f"Expansion rule '{rule_name}' must be a dictionary")
        return errors
    
    if not rule_value.get('expansion_rule'):
        errors.append(f"'{rule_name}' is not marked as an expansion rule")
    
    if 'prompts' not in rule_value:
        errors.append(f"Expansion rule '{rule_name}' missing 'prompts' field")
        return errors
    
    prompts = rule_value['prompts']
    if not isinstance(prompts, list):
        errors.append(f"Expansion rule '{rule_name}' 'prompts' must be a list")
        return errors
    
    if len(prompts) == 0:
        errors.append(f"Expansion rule '{rule_name}' 'prompts' cannot be empty")
    
    # Validate all referenced prompts exist
    for prompt_id in prompts:
        if prompt_id not in prompt_id_to_template:
            errors.append(f"Prompt '{prompt_id}' in rule '{rule_name}' not found")
        elif is_expansion_rule(prompt_id):
            errors.append(f"Prompt '{prompt_id}' in rule '{rule_name}' is itself an expansion rule")
    
    return errors
