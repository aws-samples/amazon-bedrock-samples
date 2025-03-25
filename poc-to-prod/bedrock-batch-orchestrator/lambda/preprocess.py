import utils
from custom_types import JobInput, JobConfig, JobConfigList
from processor import get_processor_for_model_id
import prompt_templates as pt
import awswrangler as wr
import boto3
from typing import List, Dict
import os
import json
from uuid import uuid4
from datasets import load_dataset
import pandas as pd


MAX_RECORDS_PER_JOB: int = os.getenv('MAX_RECORDS_PER_JOB', 1000)
BUCKET_NAME = os.getenv('BUCKET_NAME')

s3_client = boto3.client('s3')

logger = utils.get_logger()


def write_jsonl_to_s3(records: List[Dict], key: str) -> str:
    """write a JSONL file to S3 from a list of dicts. Returns the S3 URI"""
    jsonl_data = '\n'.join(json.dumps(item) for item in records)
    s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=jsonl_data)
    return f's3://{BUCKET_NAME}/{key}'


def lambda_handler(event: JobInput, context) -> JobConfigList:
    """
    Preprocessing of input CSV files and preparation of JSONL batch input files for bedrock batch inference.

    Event structure is a JobInput TypedDict, e.g. for Titan-V2 embedding jobs
    {
      "s3_uri": "s3://batch-inference-bucket-xxxxxxxxx/inputs/embeddings/embedding_input.csv",
      "job_name_prefix": "test-embeddings-job1",
      "model_id": "amazon.titan-embed-text-v2:0",
      "prompt_id": null
    }
    The s3_uri must point to a CSV file with an `input_text` column for embedding models.

    For text-based models like the Anthropic Claude family, you must supply a value for prompt_id that is associated
    with a prompt template in `prompt_templates.prompt_id_to_template`.
    The input CSV must have columns for each formatting key in the prompt template.
    {
      "s3_uri": "s3://batch-inference-bucket-xxxxxxxxx/inputs/jokes/topics.csv",
      "job_name_prefix": "test-joke-job1",
      "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
      "prompt_id": "joke_about_topic"
    }

    Returns a list of job configs which will be passed to the start_batch_inference_job.py function via a step function
    map, which manages concurrency of the requests.
    """

    if 'dataset_id' not in event and 's3_uri' not in event:
        raise ValueError("Either 'dataset_id' or 's3_uri' must be provided in the event.")

    model_id = event['model_id']
    processor = get_processor_for_model_id(model_id)

    max_num_jobs = event.get('max_num_jobs')
    max_records_per_job = event.get('max_records_per_job', MAX_RECORDS_PER_JOB)

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

        input_records = input_df.to_dict('records')
        # transformation function
        if processor.model_type == 'embedding':
            records = [
                processor.process_input(
                    input_text=r['input_text'], record_id=r['record_id']
                ) for r in input_records
            ]

        else:
            # format the prompt - input df must have columns that match the formatting keys in the prompt
            records = [
                processor.process_input(
                    input_text=pt.prompt_id_to_template[event['prompt_id']].format(**r),
                    record_id=r['record_id']
                ) for r in input_records
            ]

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
