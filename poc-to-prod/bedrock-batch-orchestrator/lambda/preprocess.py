import utils
from custom_types import JobInput, JobConfig, JobConfigList, PromptConfig, BatchInferenceRecord
from processor import get_processor_for_model_id, BaseProcessor
import prompt_templates as pt
import awswrangler as wr
import boto3
from typing import List, Dict, Optional
import os
import json
from uuid import uuid4
from datasets import load_dataset
import pandas as pd
import base64
from PIL import Image
from io import BytesIO


MAX_RECORDS_PER_JOB: int = os.getenv('MAX_RECORDS_PER_JOB', 1000)
BUCKET_NAME = os.getenv('BUCKET_NAME')

s3_client = boto3.client('s3')

logger = utils.get_logger()


def write_jsonl_to_s3(records: List[Dict], key: str) -> str:
    """write a JSONL file to S3 from a list of dicts. Returns the S3 URI"""
    jsonl_data = '\n'.join(json.dumps(item) for item in records)
    s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=jsonl_data)
    return f's3://{BUCKET_NAME}/{key}'


def discover_images_from_s3(s3_prefix: str, bucket_name: str) -> List[str]:
    """
    Recursively discover image files in an S3 prefix.
    
    Args:
        s3_prefix: S3 prefix/path to search for images
        bucket_name: S3 bucket name
        
    Returns:
        List of S3 URIs for discovered images
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    image_paths = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                # Check if file has a supported image extension
                if any(key.lower().endswith(ext) for ext in image_extensions):
                    image_paths.append(f's3://{bucket_name}/{key}')
        
        logger.info(f"Discovered {len(image_paths)} images in s3://{bucket_name}/{s3_prefix}")
        
    except Exception as e:
        logger.error(f"Error discovering images from s3://{bucket_name}/{s3_prefix}: {str(e)}")
        raise
    
    return image_paths


def encode_image_from_s3(s3_uri: str) -> Optional[str]:
    """
    Read and encode an image from S3 with validation.
    
    Validates:
    - File size (must be <= 3.75 MB)
    - Image dimensions (must be <= 8000px in both width and height)
    
    Args:
        s3_uri: S3 URI of the image
        
    Returns:
        Base64-encoded image string, or None if validation fails
    """
    try:
        bucket, key = utils.split_s3_uri(s3_uri)
        
        # Get object metadata first to check size
        head = s3_client.head_object(Bucket=bucket, Key=key)
        size_mb = head['ContentLength'] / (1024 * 1024)
        
        # Check file size limit (3.75 MB)
        if size_mb > 3.75:
            logger.warning(f'Image {s3_uri} exceeds 3.75 MB limit: {size_mb:.2f} MB - skipping')
            return None
        
        # Stream image data
        response = s3_client.get_object(Bucket=bucket, Key=key)
        image_bytes = response['Body'].read()
        
        # Validate dimensions using PIL
        try:
            image = Image.open(BytesIO(image_bytes))
            width, height = image.size
            
            if width > 8000 or height > 8000:
                logger.warning(f'Image {s3_uri} exceeds dimension limits: {width}x{height} - skipping')
                return None
        except Exception as img_error:
            logger.warning(f'Could not validate image dimensions for {s3_uri}: {str(img_error)} - skipping')
            return None
        
        # Encode to base64
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        return base64_encoded
        
    except Exception as e:
        logger.error(f'Error encoding image {s3_uri}: {str(e)}')
        return None


def resolve_prompt_config(event: JobInput) -> PromptConfig:
    """
    Resolve prompt configuration from event, handling backward compatibility.
    
    Checks for new-style prompt_config first, then falls back to legacy prompt_id.
    
    Args:
        event: JobInput event structure
        
    Returns:
        PromptConfig object
        
    Raises:
        ValueError: If neither prompt_config nor prompt_id is provided
    """
    # New style: explicit prompt_config
    if 'prompt_config' in event and event['prompt_config'] is not None:
        return event['prompt_config']
    
    # Backward compatibility: prompt_id only
    if 'prompt_id' in event and event['prompt_id'] is not None:
        return {
            'mode': 'single',
            'prompt_id': event['prompt_id']
        }
    
    raise ValueError('Either prompt_config or prompt_id must be provided in the event')


def apply_prompt_routing(
    input_records: List[Dict],
    prompt_config: PromptConfig,
    processor: BaseProcessor,
    image_data_map: Optional[Dict[str, str]] = None
) -> List[BatchInferenceRecord]:
    """
    Apply prompt routing based on configuration mode.
    
    Supports three modes:
    - single: Apply same prompt to all records
    - mapped: Read prompt_id from CSV column for each record
    - expanded: Create multiple entries per input using expansion rules
    
    Args:
        input_records: List of input record dictionaries
        prompt_config: Prompt configuration specifying routing mode
        processor: Model processor for formatting inputs
        image_data_map: Optional mapping of record_id to base64 image data
        
    Returns:
        List of BatchInferenceRecord objects ready for JSONL output
    """
    mode = prompt_config['mode']
    results = []
    
    if mode == 'single':
        # Apply same prompt to all records
        prompt_id = prompt_config['prompt_id']
        template_text = pt.get_template_text(prompt_id)
        
        for record in input_records:
            # Format prompt with record variables
            formatted_prompt = template_text.format(**record)
            record_id = record['record_id']
            image_data = image_data_map.get(record_id) if image_data_map else None
            
            if image_data_map and record_id not in image_data_map:
                logger.warning(f"record_id {record_id} not found in image_data_map!")
            
            batch_record = processor.process_input(
                input_text=formatted_prompt,
                record_id=record_id,
                image_data=image_data
            )
            results.append(batch_record)
    
    elif mode == 'mapped':
        # Each record specifies its prompt via a column
        column_name = prompt_config['column_name']
        
        for record in input_records:
            prompt_id = record.get(column_name)
            if not prompt_id:
                logger.warning(f'No prompt_id in column {column_name} for record {record["record_id"]} - skipping')
                continue
            
            try:
                template_text = pt.get_template_text(prompt_id)
            except (KeyError, ValueError) as e:
                logger.warning(f'Invalid prompt_id "{prompt_id}" for record {record["record_id"]}: {str(e)} - skipping')
                continue
            
            formatted_prompt = template_text.format(**record)
            image_data = image_data_map.get(record['record_id']) if image_data_map else None
            
            batch_record = processor.process_input(
                input_text=formatted_prompt,
                record_id=record['record_id'],
                image_data=image_data
            )
            results.append(batch_record)
    
    elif mode == 'expanded':
        # Multi-entry expansion: create multiple entries per input
        category_column = prompt_config['category_column']
        expansion_mapping = prompt_config['expansion_mapping']
        
        for record in input_records:
            category_value = record.get(category_column)
            
            # Look up expansion rule for this category
            expansion_rule_name = expansion_mapping.get(category_value)
            if not expansion_rule_name:
                # Try default fallback
                expansion_rule_name = expansion_mapping.get('default')
            
            if not expansion_rule_name:
                logger.warning(f'No expansion rule for category "{category_value}" in record {record["record_id"]} - skipping')
                continue
            
            # Get prompts from expansion rule
            try:
                prompt_ids = pt.get_expansion_rule(expansion_rule_name)
            except (KeyError, ValueError) as e:
                logger.warning(f'Invalid expansion rule "{expansion_rule_name}": {str(e)} - skipping record {record["record_id"]}')
                continue
            
            image_data = image_data_map.get(record['record_id']) if image_data_map else None
            
            # Create multiple entries with unique record_ids
            for idx, prompt_id in enumerate(prompt_ids, 1):
                try:
                    template_text = pt.get_template_text(prompt_id)
                except (KeyError, ValueError) as e:
                    logger.warning(f'Invalid prompt_id "{prompt_id}" in expansion rule: {str(e)} - skipping')
                    continue
                
                formatted_prompt = template_text.format(**record)
                
                # Create unique record_id with suffix (e.g., original_id-001, original_id-002)
                expanded_record_id = f"{record['record_id']}-{str(idx).zfill(3)}"
                
                batch_record = processor.process_input(
                    input_text=formatted_prompt,
                    record_id=expanded_record_id,
                    image_data=image_data
                )
                results.append(batch_record)
    
    else:
        raise ValueError(f'Unknown prompt_config mode: {mode}')
    
    return results


def lambda_handler(event: JobInput, context) -> JobConfigList:
    """
    Enhanced preprocessing with support for multimodal inputs and flexible prompt routing.

    Event structure for text-based models:
    {
      "s3_uri": "s3://bucket/inputs/data.csv",
      "job_name_prefix": "test-job",
      "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
      "prompt_id": "joke_about_topic"  # Legacy format
    }
    
    Or with new prompt_config:
    {
      "s3_uri": "s3://bucket/inputs/data.csv",
      "job_name_prefix": "test-job",
      "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
      "prompt_config": {
        "mode": "single",
        "prompt_id": "joke_about_topic"
      }
    }
    
    For image processing from S3 prefix:
    {
      "s3_uri": "s3://bucket/images/",
      "job_name_prefix": "image-classification",
      "model_id": "amazon.nova-lite-v1:0",
      "input_type": "image",
      "prompt_config": {
        "mode": "single",
        "prompt_id": "image_classification"
      }
    }
    
    For CSV with image paths:
    {
      "s3_uri": "s3://bucket/inputs/products.csv",
      "job_name_prefix": "product-analysis",
      "model_id": "amazon.nova-pro-v1:0",
      "input_type": "image",
      "image_column": "product_image_path",
      "prompt_config": {
        "mode": "expanded",
        "category_column": "product_category",
        "expansion_mapping": {
          "clothing": "detailed_clothing_analysis",
          "default": "comprehensive_product_review"
        }
      }
    }

    Returns a list of job configs for the step function map state.
    """

    if 'dataset_id' not in event and 's3_uri' not in event:
        raise ValueError("Either 'dataset_id' or 's3_uri' must be provided in the event.")

    model_id = event['model_id']
    processor = get_processor_for_model_id(model_id)

    max_num_jobs = event.get('max_num_jobs')
    max_records_per_job = event.get('max_records_per_job', MAX_RECORDS_PER_JOB)
    
    # Resolve prompt configuration (handles backward compatibility)
    prompt_config = resolve_prompt_config(event)
    
    # Determine input type (default to 'text' for backward compatibility)
    input_type = event.get('input_type', 'text')
    
    # Initialize image data map for multimodal inputs
    image_data_map: Optional[Dict[str, str]] = None

    # huggingface datasets - load and import to S3
    if dataset_id := event.get('dataset_id'):
        logger.info(f"Writing huggingface dataset {dataset_id} to S3")

        s3_uri = f"s3://{BUCKET_NAME}/hf/{dataset_id}"
        file_type = "parquet"

        batched_ds = load_dataset(dataset_id, split=event.get('split', 'train'), streaming=True).batch(batch_size=max_records_per_job)
        for idx, batch in enumerate(batched_ds):
            df = pd.DataFrame(batch)
            wr.s3.to_parquet(df, path=f"{s3_uri}/{str(idx).zfill(4)}.snappy.parquet", index=False, compression="snappy")

            if max_num_jobs:
                if idx >= max_num_jobs:
                    break
    else:
        # load directly from S3
        s3_uri = event['s3_uri']
        
        # Handle image mode
        if input_type == 'image':
            # Check if s3_uri points to a directory (image discovery) or CSV file
            if not s3_uri.endswith('.csv') and not s3_uri.endswith('.parquet'):
                # Image discovery mode: recursively find images in S3 prefix
                logger.info(f"Image discovery mode: scanning {s3_uri}")
                bucket, prefix = utils.split_s3_uri(s3_uri)
                image_paths = discover_images_from_s3(prefix, bucket)
                
                if not image_paths:
                    raise ValueError(f"No images found in {s3_uri}")
                
                # Create a temporary DataFrame with image paths
                input_df = pd.DataFrame({
                    'record_id': [str(uuid4()) for _ in range(len(image_paths))],
                    'image_path': image_paths,
                    'file_name': [path.split('/')[-1] for path in image_paths]
                })
                
                # Encode all images
                logger.info(f"Encoding {len(image_paths)} images...")
                image_data_map = {}
                valid_records = []
                
                for _, row in input_df.iterrows():
                    record_id = row['record_id']
                    image_path = row['image_path']
                    logger.info(f"Encoding image: {image_path} for record_id: {record_id}")
                    image_data = encode_image_from_s3(image_path)
                    if image_data:
                        image_data_map[record_id] = image_data
                        valid_records.append(row.to_dict())
                        logger.info(f"Successfully encoded {image_path}, data length: {len(image_data)}")
                    else:
                        logger.warning(f"Failed to encode {image_path}")
                
                logger.info(f"Successfully encoded {len(valid_records)} images")
                logger.info(f"image_data_map has {len(image_data_map)} entries")
                logger.info(f"First 3 record_ids in map: {list(image_data_map.keys())[:3]}")
                
                # Create temporary parquet file for processing
                temp_df = pd.DataFrame(valid_records)
                temp_s3_uri = f"s3://{BUCKET_NAME}/temp_image_inputs/{event['job_name_prefix']}/images.snappy.parquet"
                wr.s3.to_parquet(temp_df, path=temp_s3_uri, index=False, compression='snappy')
                
                s3_uri = temp_s3_uri
                file_type = 'parquet'
            else:
                # CSV/Parquet with image paths
                file_type = s3_uri.split('.')[-1]
                assert file_type in ['csv', 'parquet'], "File type must be csv or parquet"
                logger.info(f"Using CSV/Parquet with image paths at {s3_uri}")
        else:
            # Text mode (existing logic)
            file_type = s3_uri.split('.')[-1]
            assert file_type in ['csv', 'parquet'], "File type must be csv or parquet"
            logger.info(f"Using S3 dataset at {s3_uri}")

    # load input in chunks
    jobs_list: List[JobConfig] = []

    logger.info("Preparing batch inference job inputs (JSONL files)...")
    for idx, input_df in utils.load_files_in_chunks(s3_uri, file_type, chunk_size=max_records_per_job):

        if max_num_jobs:
            if idx >= max_num_jobs:
                logger.info(f"Reached max_num_jobs: {max_num_jobs}. Stopping here.")
                break

        # add a record_id to each row to allow for joining with outputs later
        if 'record_id' not in input_df.columns:
            input_df['record_id'] = [str(uuid4()) for _ in range(len(input_df))]
        
        # Handle image encoding for CSV/Parquet mode (if not already done in discovery mode)
        if input_type == 'image' and image_data_map is None:
            image_column = event.get('image_column', 'image_path')
            
            if image_column not in input_df.columns:
                raise ValueError(f"Image column '{image_column}' not found in input data. Available columns: {list(input_df.columns)}")
            
            logger.info(f"Encoding images from column '{image_column}'...")
            # Initialize image_data_map for the first chunk
            image_data_map = {}
            
            for _, row in input_df.iterrows():
                image_path = row[image_column]
                if pd.notna(image_path):  # Skip null/empty paths
                    image_data = encode_image_from_s3(image_path)
                    if image_data:
                        image_data_map[row['record_id']] = image_data
        elif input_type == 'image' and image_data_map is not None:
            # For subsequent chunks, encode images for this chunk only
            image_column = event.get('image_column', 'image_path')
            logger.info(f"Encoding images from column '{image_column}' for chunk {idx}...")
            
            for _, row in input_df.iterrows():
                image_path = row[image_column]
                if pd.notna(image_path):  # Skip null/empty paths
                    image_data = encode_image_from_s3(image_path)
                    if image_data:
                        image_data_map[row['record_id']] = image_data

        input_records = input_df.to_dict('records')
        
        # Apply prompt routing based on configuration
        if processor.model_type == 'embedding':
            # Embedding models don't use prompts
            records = [
                processor.process_input(
                    input_text=r['input_text'], 
                    record_id=r['record_id']
                ) for r in input_records
            ]
        else:
            # Use unified prompt routing for text-based models
            records = apply_prompt_routing(
                input_records=input_records,
                prompt_config=prompt_config,
                processor=processor,
                image_data_map=image_data_map
            )

        job_name = utils.create_job_name(event['job_name_prefix'], index=idx)

        input_parquet_path = f's3://{BUCKET_NAME}/batch_inputs_parquet/{event["job_name_prefix"]}/{str(idx).zfill(4)}.snappy.parquet'
        input_key = f'batch_inputs_json/{event["job_name_prefix"]}/{str(idx).zfill(4)}.jsonl'
        output_path = f's3://{BUCKET_NAME}/batch_outputs_json/{event["job_name_prefix"]}/{str(idx).zfill(4)}/'

        if 'Unnamed: 0' in input_df.columns:
            input_df = input_df.drop(columns=['Unnamed: 0'])
        # save this file and keep in the config to allow for joins to the output by record id
        wr.s3.to_parquet(input_df, path=input_parquet_path, index=False, compression='snappy')

        job_config: JobConfig = {
            'model_id': model_id,
            'job_name': job_name,
            'input_parquet_path': input_parquet_path,
            's3_uri_input': write_jsonl_to_s3(records, input_key),
            's3_uri_output': output_path,
        }
        jobs_list.append(job_config)

    return {
        'jobs': jobs_list
    }
