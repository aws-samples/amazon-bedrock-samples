from custom_types import TaskItem
from processor import get_processor_for_model_id
import utils
from typing import List, Dict, Optional, Any
import awswrangler as wr
import pandas as pd
import boto3
import json
import os
import re
from jsonpath_ng import parse as jsonpath_parse
import prompt_templates as pt


logger = utils.get_logger()
BUCKET_NAME = os.getenv('BUCKET_NAME')

s3_client = boto3.client('s3')


def read_jsonl_from_s3(s3_uri: str) -> List[Dict]:
    bucket, key = utils.split_s3_uri(s3_uri)
    object_body = s3_client.get_object(
        Bucket=bucket,
        Key=key,
    )['Body'].read().decode('utf-8')

    # Split on '}\n{' and restore the delimiters
    chunks = object_body.split('}\n{')

    # Restore the JSON structure for each chunk
    if len(chunks) > 1:
        chunks = [chunks[0] + '}'] + ['{' + chunk + '}' for chunk in chunks[1:-1]] + ['{' + chunks[-1]]

    # Parse each chunk
    data = [json.loads(chunk) for chunk in chunks]

    return data


def extract_fields_with_json_path(response: str, fields: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract fields from JSON response using JSON path expressions.
    
    Args:
        response: The model response text (should be valid JSON)
        fields: Dictionary mapping field_name to JSON path expression
        
    Returns:
        Dictionary with extracted field values (None for missing fields)
    """
    try:
        data = json.loads(response)
        extracted = {}
        
        for field_name, json_path in fields.items():
            try:
                parser = jsonpath_parse(json_path)
                matches = parser.find(data)
                
                if matches:
                    # Handle array results
                    if len(matches) > 1:
                        extracted[field_name] = [match.value for match in matches]
                    else:
                        extracted[field_name] = matches[0].value
                else:
                    extracted[field_name] = None
                    logger.warning(f'JSON path "{json_path}" not found for field "{field_name}"')
            except Exception as e:
                extracted[field_name] = None
                logger.warning(f'Error parsing JSON path "{json_path}" for field "{field_name}": {str(e)}')
        
        return extracted
    
    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse JSON response: {str(e)}')
        return {field_name: None for field_name in fields.keys()}
    except Exception as e:
        logger.error(f'Unexpected error in JSON path extraction: {str(e)}')
        return {field_name: None for field_name in fields.keys()}


def extract_fields_with_regex(response: str, patterns: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract fields from response text using regex patterns.
    
    Args:
        response: The model response text
        patterns: Dictionary mapping field_name to regex pattern
        
    Returns:
        Dictionary with extracted field values (None for non-matching patterns)
    """
    extracted = {}
    
    for field_name, pattern in patterns.items():
        try:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                # Use first group if available, otherwise full match
                extracted[field_name] = match.group(1) if match.groups() else match.group(0)
            else:
                extracted[field_name] = None
                logger.warning(f'Regex pattern "{pattern}" not found for field "{field_name}"')
        except Exception as e:
            extracted[field_name] = None
            logger.error(f'Error applying regex pattern "{pattern}" for field "{field_name}": {str(e)}')
    
    return extracted


def apply_output_schema(
    response: str,
    output_schema: Optional[pt.OutputSchemaField]
) -> Dict[str, Any]:
    """
    Apply output schema to extract structured fields from response.
    
    Args:
        response: The model response text
        output_schema: Optional schema definition with type and fields
        
    Returns:
        Dictionary with extracted fields (empty dict if no schema)
    """
    if not output_schema:
        return {}
    
    try:
        schema_type = output_schema.get('type')
        fields = output_schema.get('fields', {})
        
        if not fields:
            logger.warning('Output schema has no fields defined')
            return {}
        
        if schema_type == 'json':
            return extract_fields_with_json_path(response, fields)
        elif schema_type == 'regex':
            return extract_fields_with_regex(response, fields)
        else:
            logger.error(f'Unknown schema type: {schema_type}')
            return {}
    except Exception as e:
        logger.error(f'Error applying output schema: {str(e)}')
        return {}


def determine_prompt_id_from_record(record_id: str, input_df: pd.DataFrame, prompt_config: Optional[Dict] = None) -> Optional[str]:
    """
    Determine which prompt_id was used for a given record.
    
    For expanded entries, extracts the prompt from the record_id suffix mapping.
    For mapped mode, reads from the prompt column in input_df.
    For single mode, returns the single prompt_id.
    
    Args:
        record_id: The record identifier (may have suffix for expanded entries)
        input_df: Input dataframe with original records
        prompt_config: Optional prompt configuration to determine mode
        
    Returns:
        The prompt_id used for this record, or None if cannot be determined
    """
    # For backward compatibility, if no prompt_config, we can't determine prompt_id
    if not prompt_config:
        return None
    
    mode = prompt_config.get('mode')
    
    if mode == 'single':
        # All records use the same prompt
        return prompt_config.get('prompt_id')
    
    elif mode == 'mapped':
        # Look up the prompt from the input dataframe
        column_name = prompt_config.get('column_name')
        if not column_name:
            return None
        
        # Extract base record_id (remove suffix if present)
        base_record_id = record_id.split('-')[0] if '-' in record_id else record_id
        
        # Find the record in input_df
        matching_rows = input_df[input_df['record_id'] == base_record_id]
        if not matching_rows.empty and column_name in matching_rows.columns:
            return matching_rows.iloc[0][column_name]
        
        return None
    
    elif mode == 'expanded':
        # For expanded entries, we need to reconstruct which prompt was used
        # The record_id has format: original_id-001, original_id-002, etc.
        # The suffix corresponds to the index in the expansion rule's prompts array
        
        if '-' not in record_id:
            return None
        
        parts = record_id.rsplit('-', 1)
        base_record_id = parts[0]
        suffix = parts[1]
        
        try:
            prompt_index = int(suffix) - 1  # Convert 001 to index 0
        except ValueError:
            return None
        
        # Find the original record to get its category
        matching_rows = input_df[input_df['record_id'] == base_record_id]
        if matching_rows.empty:
            return None
        
        category_column = prompt_config.get('category_column')
        expansion_mapping = prompt_config.get('expansion_mapping', {})
        
        if not category_column or category_column not in matching_rows.columns:
            return None
        
        category_value = matching_rows.iloc[0][category_column]
        expansion_rule_name = expansion_mapping.get(category_value) or expansion_mapping.get('default')
        
        if not expansion_rule_name:
            return None
        
        try:
            prompt_ids = pt.get_expansion_rule(expansion_rule_name)
            if 0 <= prompt_index < len(prompt_ids):
                return prompt_ids[prompt_index]
        except (KeyError, ValueError):
            return None
        
        return None
    
    return None


def lambda_handler(event: TaskItem, context):
    """
    Enhanced postprocessing with output schema extraction support.
    
    Bedrock batch inference jobs are returned as JSONL files. This postprocessing step:
    1. Parses the output files
    2. Applies output schemas to extract structured fields (if defined)
    3. Joins results back to original input records via record_id
    4. Handles expanded entries (multiple outputs per input)
    
    Final outputs are saved as Parquet files at the returned S3 paths.
    """

    logger.info(f'Postprocessing job:\n{event}')

    if not event['error_message']:
        processor = get_processor_for_model_id(event['model_id'])
        input_df = wr.s3.read_parquet(event['input_parquet_path'])
        
        # Get prompt_config from event if available (for determining prompt_id)
        prompt_config = event.get('prompt_config')

        output_prefix = os.path.join(event['s3_uri_output'], event['job_arn'].split('/')[-1])
        logger.info(f'Retrieving model output from {output_prefix}')
        model_output_uri = next(iter(wr.s3.list_objects(
            path=output_prefix,
            suffix='.jsonl.out',
        )))
        logger.info(f'Output URI: {model_output_uri}')
        output_records = read_jsonl_from_s3(model_output_uri)
        
        # Process outputs with schema extraction
        processed_outputs = []
        for output_record in output_records:
            # Basic processing
            parsed = processor.process_output(output_record)
            record_id = parsed['record_id']
            response = parsed['response']
            
            # Determine which prompt was used for this record
            prompt_id = determine_prompt_id_from_record(record_id, input_df, prompt_config)
            
            # Apply output schema if defined
            extracted_fields = {}
            if prompt_id:
                try:
                    output_schema = pt.get_output_schema(prompt_id)
                    if output_schema:
                        logger.info(f'Applying output schema for prompt_id "{prompt_id}" to record "{record_id}"')
                        extracted_fields = apply_output_schema(response, output_schema)
                except (KeyError, ValueError) as e:
                    logger.warning(f'Could not get output schema for prompt_id "{prompt_id}": {str(e)}')
            
            # Combine raw response with extracted fields
            result = {
                'record_id': record_id,
                'response': response,
                **extracted_fields
            }
            processed_outputs.append(result)
        
        # Create output dataframe
        output_df = pd.DataFrame(processed_outputs)
        
        # Handle expanded entries: join on base_record_id
        # For expanded entries, record_id has format: original_id-001, original_id-002
        # We need to extract the base record_id for joining
        output_df['base_record_id'] = output_df['record_id'].apply(
            lambda x: x.split('-')[0] if '-' in x else x
        )
        input_df['base_record_id'] = input_df['record_id'].apply(
            lambda x: x.split('-')[0] if '-' in x else x
        )
        
        # Join with input data on base_record_id
        # Use left join to preserve all output records (including expanded ones)
        final_df = output_df.merge(
            input_df,
            on='base_record_id',
            how='left',
            suffixes=('', '_input')
        )
        
        # Clean up: remove duplicate record_id column if it exists
        if 'record_id_input' in final_df.columns:
            final_df = final_df.drop(columns=['record_id_input'])
        
        # Remove the temporary base_record_id column
        if 'base_record_id' in final_df.columns:
            final_df = final_df.drop(columns=['base_record_id'])
        
        output_parquet_path = os.path.join(f's3://{BUCKET_NAME}/batch_output_parquet/', *event['input_parquet_path'].split('/')[-2:])
        logger.info(f'Saving output parquet to {output_parquet_path}')

        wr.s3.to_parquet(
            final_df,
            output_parquet_path,
            index=False,
            compression='snappy',
        )
    else:
        # if an error occurred, skip processing
        output_parquet_path = None

    return {
        'output_path': output_parquet_path,
    }

