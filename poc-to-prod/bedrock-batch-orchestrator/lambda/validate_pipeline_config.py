import boto3
import json
import logging
from typing import List, Dict, Optional
from custom_types import (
    PipelineConfig,
    PipelineStage,
    PromptConfig,
    ValidationResult
)
import prompt_templates as pt
from utils import split_s3_uri


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_prompt_references(prompt_config: PromptConfig, stage_name: str) -> List[str]:
    """
    Validate all prompt_id references exist in prompt_templates.py.
    
    Args:
        prompt_config: The prompt configuration to validate
        stage_name: Name of the stage (for error messages)
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    mode = prompt_config['mode']
    
    if mode == 'single':
        # Validate single prompt_id exists
        prompt_id = prompt_config['prompt_id']
        if prompt_id not in pt.prompt_id_to_template:
            errors.append(f"Stage '{stage_name}': Prompt '{prompt_id}' not found in prompt_templates")
        elif pt.is_expansion_rule(prompt_id):
            errors.append(f"Stage '{stage_name}': '{prompt_id}' is an expansion rule, not a prompt template")
    
    elif mode == 'mapped':
        # Validate column_name is provided
        if 'column_name' not in prompt_config or not prompt_config['column_name']:
            errors.append(f"Stage '{stage_name}': 'column_name' is required for mapped mode")
    
    elif mode == 'expanded':
        # Validate category_column is provided
        if 'category_column' not in prompt_config or not prompt_config['category_column']:
            errors.append(f"Stage '{stage_name}': 'category_column' is required for expanded mode")
        
        # Validate expansion_mapping is provided
        if 'expansion_mapping' not in prompt_config or not prompt_config['expansion_mapping']:
            errors.append(f"Stage '{stage_name}': 'expansion_mapping' is required for expanded mode")
        else:
            expansion_mapping = prompt_config['expansion_mapping']
            
            # Validate each expansion rule reference
            for category, rule_name in expansion_mapping.items():
                # Check expansion rule exists
                if rule_name not in pt.prompt_id_to_template:
                    errors.append(f"Stage '{stage_name}': Expansion rule '{rule_name}' not found in prompt_templates")
                    continue
                
                # Check it's actually an expansion rule
                if not pt.is_expansion_rule(rule_name):
                    errors.append(f"Stage '{stage_name}': '{rule_name}' is not an expansion rule")
                    continue
                
                # Validate the expansion rule itself
                rule_errors = pt.validate_expansion_rule(rule_name)
                for error in rule_errors:
                    errors.append(f"Stage '{stage_name}': {error}")
    
    else:
        errors.append(f"Stage '{stage_name}': Invalid prompt_config mode '{mode}'")
    
    return errors


def validate_model_id(model_id: str, stage_name: str) -> List[str]:
    """
    Validate model_id format.
    
    Args:
        model_id: The model ID to validate
        stage_name: Name of the stage (for error messages)
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check for supported model providers
    supported_providers = ['anthropic.', 'amazon.nova', 'amazon.titan']
    
    if not any(model_id.startswith(provider) for provider in supported_providers):
        errors.append(
            f"Stage '{stage_name}': Model ID '{model_id}' does not match supported providers "
            f"(anthropic, amazon.nova, amazon.titan)"
        )
    
    return errors


def validate_stage_dependencies(stages: List[PipelineStage]) -> List[str]:
    """
    Validate stage dependencies and data flow.
    
    Args:
        stages: List of pipeline stages
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    for idx, stage in enumerate(stages):
        stage_name = stage['stage_name']
        
        # First stage cannot use previous output
        if idx == 0 and stage.get('use_previous_output'):
            errors.append(
                f"Stage '{stage_name}': First stage cannot use 'use_previous_output'"
            )
        
        # Stages after first must have either input_s3_uri or use_previous_output
        if idx > 0:
            has_input = 'input_s3_uri' in stage and stage['input_s3_uri']
            uses_previous = stage.get('use_previous_output', False)
            
            if not has_input and not uses_previous:
                errors.append(
                    f"Stage '{stage_name}': Must specify either 'input_s3_uri' or 'use_previous_output'"
                )
            
            if has_input and uses_previous:
                errors.append(
                    f"Stage '{stage_name}': Cannot specify both 'input_s3_uri' and 'use_previous_output'"
                )
    
    return errors


def calculate_expansion_multiplier(prompt_config: PromptConfig) -> float:
    """
    Calculate the expansion multiplier for a prompt configuration.
    
    Args:
        prompt_config: The prompt configuration
        
    Returns:
        Expansion multiplier (1.0 for single/mapped, average for expanded)
    """
    mode = prompt_config['mode']
    
    if mode in ['single', 'mapped']:
        return 1.0
    
    if mode == 'expanded':
        expansion_mapping = prompt_config.get('expansion_mapping', {})
        if not expansion_mapping:
            return 1.0
        
        # Calculate average number of prompts across all expansion rules
        total_prompts = 0
        valid_rules = 0
        
        for rule_name in expansion_mapping.values():
            try:
                prompts = pt.get_expansion_rule(rule_name)
                total_prompts += len(prompts)
                valid_rules += 1
            except (KeyError, ValueError):
                # Skip invalid rules (will be caught by validation)
                continue
        
        if valid_rules == 0:
            return 1.0
        
        return total_prompts / valid_rules
    
    return 1.0


def estimate_costs(pipeline_config: PipelineConfig) -> Dict:
    """
    Estimate record counts and costs for the pipeline.
    
    Note: This is a simplified estimation. Actual costs depend on:
    - Input token counts
    - Output token counts
    - Specific model versions
    
    Args:
        pipeline_config: The pipeline configuration
        
    Returns:
        Dictionary with estimated_records and estimated_cost_usd
    """
    # Simplified model pricing (per 1K input tokens)
    # These are approximate rates and should be updated based on actual pricing
    model_pricing = {
        'amazon.nova-lite': 0.00006,
        'amazon.nova-pro': 0.0008,
        'amazon.nova-micro': 0.00003,
        'anthropic.claude-3-haiku': 0.00025,
        'anthropic.claude-3-sonnet': 0.003,
        'anthropic.claude-3-opus': 0.015,
        'amazon.titan-embed-text': 0.0001
    }
    
    total_records = 0
    total_cost = 0.0
    
    # Note: Without access to actual input data, we can't provide accurate estimates
    # This would require reading the input files or getting record counts from metadata
    
    logger.info("Cost estimation requires access to input data - returning placeholder values")
    
    return {
        'estimated_records': None,  # Would need to read input files
        'estimated_cost_usd': None  # Would need record counts and token estimates
    }


def load_pipeline_config_from_s3(s3_uri: str) -> PipelineConfig:
    """
    Load pipeline configuration from S3.
    
    Args:
        s3_uri: S3 URI of the pipeline configuration file
        
    Returns:
        Pipeline configuration dictionary
        
    Raises:
        Exception: If file cannot be loaded or parsed
    """
    try:
        bucket, key = split_s3_uri(s3_uri)
        s3_client = boto3.client('s3')
        
        logger.info(f"Loading pipeline config from s3://{bucket}/{key}")
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        config_content = response['Body'].read().decode('utf-8')
        
        pipeline_config = json.loads(config_content)
        
        return pipeline_config
    
    except Exception as e:
        logger.error(f"Failed to load pipeline config from S3: {str(e)}")
        raise


def lambda_handler(event, context) -> ValidationResult:
    """
    Validate pipeline configuration before execution.
    
    Event can contain either:
    - pipeline_config_s3_uri: S3 URI to load config from
    - Direct pipeline configuration fields (pipeline_name, stages, etc.)
    
    Args:
        event: Lambda event containing pipeline config or S3 URI
        context: Lambda context
        
    Returns:
        ValidationResult with validation status, errors, warnings, and estimates
    """
    logger.info(f"Validating pipeline configuration")
    
    errors = []
    warnings = []
    
    try:
        # Load pipeline config from S3 or inline
        if 'pipeline_config_s3_uri' in event:
            pipeline_config = load_pipeline_config_from_s3(event['pipeline_config_s3_uri'])
        else:
            pipeline_config = event
        
        # Validate required top-level fields
        if 'pipeline_name' not in pipeline_config:
            errors.append("Pipeline configuration missing 'pipeline_name' field")
        
        if 'stages' not in pipeline_config or not pipeline_config['stages']:
            errors.append("Pipeline configuration missing 'stages' field or stages list is empty")
            # Cannot continue without stages
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings,
                'estimated_records': None,
                'estimated_cost_usd': None
            }
        
        stages = pipeline_config['stages']
        
        # Validate stage dependencies
        dependency_errors = validate_stage_dependencies(stages)
        errors.extend(dependency_errors)
        
        # Validate each stage
        for idx, stage in enumerate(stages):
            stage_name = stage.get('stage_name', f'Stage {idx + 1}')
            
            # Validate required stage fields
            if 'stage_name' not in stage:
                errors.append(f"Stage {idx + 1}: Missing 'stage_name' field")
            
            if 'model_id' not in stage:
                errors.append(f"Stage '{stage_name}': Missing 'model_id' field")
            else:
                # Validate model_id
                model_errors = validate_model_id(stage['model_id'], stage_name)
                errors.extend(model_errors)
            
            if 'job_name_prefix' not in stage:
                errors.append(f"Stage '{stage_name}': Missing 'job_name_prefix' field")
            
            if 'prompt_config' not in stage:
                errors.append(f"Stage '{stage_name}': Missing 'prompt_config' field")
            else:
                # Validate prompt_config
                prompt_errors = validate_prompt_references(stage['prompt_config'], stage_name)
                errors.extend(prompt_errors)
                
                # Check for high expansion multipliers
                multiplier = calculate_expansion_multiplier(stage['prompt_config'])
                if multiplier > 5:
                    warnings.append(
                        f"Stage '{stage_name}': High expansion multiplier ({multiplier:.1f}x) "
                        f"may significantly increase processing time and cost"
                    )
        
        # Estimate costs (if no errors so far)
        estimates = {}
        if not errors:
            estimates = estimate_costs(pipeline_config)
        else:
            estimates = {
                'estimated_records': None,
                'estimated_cost_usd': None
            }
        
        # Build result
        result: ValidationResult = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            **estimates
        }
        
        if result['valid']:
            logger.info(f"Pipeline configuration is valid")
            if warnings:
                logger.warning(f"Validation warnings: {warnings}")
        else:
            logger.error(f"Pipeline configuration validation failed: {errors}")
        
        return result
    
    except Exception as e:
        logger.error(f"Validation failed with exception: {str(e)}", exc_info=True)
        return {
            'valid': False,
            'errors': [f"Validation failed with exception: {str(e)}"],
            'warnings': warnings,
            'estimated_records': None,
            'estimated_cost_usd': None
        }
