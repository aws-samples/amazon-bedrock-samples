"""
Transform Stage Lambda Function

This Lambda function transforms the output from a previous pipeline stage
to prepare it as input for the next stage. It handles:
- Reading previous stage output from S3
- Applying column mappings if specified
- Preparing input configuration for next stage
"""

import json
import os
import boto3
import botocore
import awswrangler as wr
import pandas as pd
from typing import Dict, Any, Optional
from utils import split_s3_uri, get_logger

logger = get_logger()
s3_client = boto3.client('s3')


def apply_column_mappings(
    df,
    column_mappings: Dict[str, str]
) -> Any:
    """Apply column mappings to transform DataFrame columns.
    
    This is a simple column rename operation. The mapping specifies:
    - Key: target column name (what the prompt template expects)
    - Value: source column name (what exists in the dataframe) OR description (ignored)
    
    Args:
        df: Input DataFrame from previous stage
        column_mappings: Dictionary mapping target column names to source columns
        
    Returns:
        Transformed DataFrame with renamed columns
    """
    if not column_mappings:
        return df
    
    logger.info(f"Applying column mappings: {column_mappings}")
    logger.info(f"Available columns before mapping: {list(df.columns)}")
    
    # Build actual rename mapping (only for columns that exist)
    rename_map = {}
    for target_col, source_col in column_mappings.items():
        if source_col in df.columns:
            rename_map[source_col] = target_col
            logger.info(f"Will rename '{source_col}' → '{target_col}'")
        else:
            # Source doesn't exist - check if we should create it from 'response'
            logger.info(f"Source column '{source_col}' not found, will try to create '{target_col}' from 'response'")
            if 'response' in df.columns:
                # Use the response column as-is for the target
                df[target_col] = df['response']
                logger.info(f"Created '{target_col}' from 'response' column")
    
    # Apply renames
    if rename_map:
        df = df.rename(columns=rename_map)
        logger.info(f"Renamed columns: {rename_map}")
    
    logger.info(f"Available columns after mapping: {list(df.columns)}")
    
    return df


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Transform previous stage output for next stage input.
    
    Expected event structure from Step Functions Map itemSelector:
    {
        "stage_name": "stage2",
        "model_id": "...",
        "prompt_config": {...},
        "use_previous_output": true,
        "column_mappings": {"old_col": "new_col"},
        "pipeline_name": "my-pipeline",
        "all_stages": [...],
        "stage_index": 1,
        ...
    }
    
    Returns:
        Stage configuration with transformed input_s3_uri
    """
    try:
        # Handle nested structure from Map state spread operator
        # Event may have stage fields nested under '$' key
        stage_fields = event.get('$', event)  # Use nested fields if present, otherwise use event directly
        
        stage_name = stage_fields.get('stage_name', 'unknown')
        logger.info(f"Transforming input for stage: {stage_name}")
        logger.info(f"Event: {json.dumps(event, default=str)}")
        
        # Get previous stage info (these are at root level)
        stage_index = event.get('stage_index', 0)
        all_stages = event.get('all_stages', [])
        
        if stage_index == 0:
            logger.warning("This is the first stage, no previous output to transform")
            return event
        
        previous_stage = all_stages[stage_index - 1]
        previous_job_name_prefix = previous_stage.get('job_name_prefix')
        
        if not previous_job_name_prefix:
            logger.error("Previous stage missing job_name_prefix")
            return event
        
        # Construct previous output path based on naming convention
        # Output path format: s3://bucket/batch_output_parquet/{job_name_prefix}/0000.snappy.parquet
        bucket_name = event.get('BUCKET_NAME', os.environ.get('BUCKET_NAME'))
        if not bucket_name:
            logger.error("BUCKET_NAME not found in event or environment")
            return event
        
        previous_output = f's3://{bucket_name}/batch_output_parquet/{previous_job_name_prefix}/0000.snappy.parquet'
        logger.info(f"Determined previous output path: {previous_output}")
        
        # Check if previous output exists before attempting to read
        try:
            bucket, key = split_s3_uri(previous_output)
            s3_client.head_object(Bucket=bucket, Key=key)
            logger.info(f"Verified previous output exists: {previous_output}")
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                error_msg = f"Previous stage output not found: {previous_output}. Previous stage may have failed or not completed."
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                logger.error(f"Error checking previous output: {str(e)}")
                raise
        
        # Read previous stage output
        logger.info(f"Reading previous output from: {previous_output}")
        df = wr.s3.read_parquet(previous_output)
        logger.info(f"Loaded {len(df)} records with columns: {list(df.columns)}")
        
        # Extract category from response if it exists and category column doesn't
        if 'response' in df.columns and 'category' not in df.columns:
            logger.info("Attempting to extract 'category' from 'response' column")
            def extract_category(response_value):
                if not isinstance(response_value, str):
                    return None
                try:
                    response_json = json.loads(response_value)
                    if isinstance(response_json, dict) and 'category' in response_json:
                        return response_json['category']
                except (json.JSONDecodeError, ValueError):
                    pass
                return response_value  # Return as-is if not JSON
            
            category_values = df['response'].apply(extract_category)
            # Only create category column if we found actual category values
            if category_values.notna().any():
                df['category'] = category_values
                logger.info(f"Extracted 'category' column with {df['category'].notna().sum()} non-null values")
        
        # Apply column mappings if specified
        column_mappings = stage_fields.get('column_mappings')
        if column_mappings:
            df = apply_column_mappings(df, column_mappings)
        
        # Apply category-to-prompt mapping if specified
        category_to_prompt_mapping = stage_fields.get('category_to_prompt_mapping')
        if category_to_prompt_mapping:
            prompt_config = stage_fields.get('prompt_config', {})
            column_name = prompt_config.get('column_name')
            
            if column_name:
                logger.info(f"Applying category-to-prompt mapping to create column '{column_name}'")
                logger.info(f"Mapping: {category_to_prompt_mapping}")
                
                # Assume the 'response' column contains the category from previous stage
                if 'response' in df.columns:
                    # Map category to prompt_id
                    def map_category(response_value):
                        if not isinstance(response_value, str):
                            logger.warning(f"Non-string response: {response_value} (type: {type(response_value)})")
                            return category_to_prompt_mapping.get('default')
                        
                        # Try to parse as JSON first (in case response is structured)
                        try:
                            response_json = json.loads(response_value)
                            if isinstance(response_json, dict) and 'category' in response_json:
                                category = response_json['category']
                            else:
                                category = response_value
                        except (json.JSONDecodeError, ValueError):
                            # Not JSON, use the raw value
                            category = response_value
                        
                        normalized = category.lower().strip()
                        prompt_id = category_to_prompt_mapping.get(normalized, category_to_prompt_mapping.get('default'))
                        
                        if prompt_id is None:
                            logger.warning(f"No mapping found for category '{category}' (normalized: '{normalized}') from response: {response_value[:100]}")
                        
                        return prompt_id
                    
                    df[column_name] = df['response'].apply(map_category)
                    logger.info(f"Created column '{column_name}' with prompt mappings")
                    logger.info(f"Unique categories: {df['response'].unique().tolist()}")
                    logger.info(f"Unique prompt_ids: {df[column_name].unique().tolist()}")
                    logger.info(f"Sample mappings: {df[['response', column_name]].head(10).to_dict('records')}")
                else:
                    logger.warning("'response' column not found for category-to-prompt mapping")
            else:
                logger.warning(f"category_to_prompt_mapping specified but no column_name in prompt_config")
        
        # Save transformed data to S3
        bucket, key = split_s3_uri(previous_output)
        # Use a cleaner path structure
        current_job_name_prefix = stage_fields.get('job_name_prefix', 'unknown')
        transformed_key = f'batch_inputs_parquet/{previous_job_name_prefix}_to_{current_job_name_prefix}/transformed.snappy.parquet'
        transformed_s3_uri = f's3://{bucket}/{transformed_key}'
        
        logger.info(f"Saving transformed data to: {transformed_s3_uri}")
        wr.s3.to_parquet(
            df=df,
            path=transformed_s3_uri,
            index=False,
            compression='snappy'
        )
        
        # Update event with transformed input - this becomes the input_s3_uri for the next stage
        # Flatten the nested structure and add the transformed input_s3_uri
        result = dict(stage_fields)  # Start with stage fields
        result['input_s3_uri'] = transformed_s3_uri
        
        # Add back the context fields from root level
        result['stage_index'] = stage_index
        result['all_stages'] = all_stages
        result['pipeline_name'] = event.get('pipeline_name')
        
        logger.info(f"Transformation complete for stage: {stage_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error transforming stage input: {str(e)}", exc_info=True)
        raise
