from custom_types import TaskItem
from processor import get_processor_for_model_id
import utils
from typing import List, Dict
import awswrangler as wr
import pandas as pd
import boto3
import json
import os


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


def lambda_handler(event: TaskItem, context):
    """
    Bedrock batch inference jobs are returned as JSONL files. This postprocessing step is necessary for parsing
    the output files AND joining the result back to the original input record via a join with the record_id.

    Final outputs are saved as Parquet files at the returned S3 paths.
    """

    logger.info(f'Postprocessing job:\n{event}')

    if not event['error_message']:
        processor = get_processor_for_model_id(event['model_id'])
        input_df = wr.s3.read_parquet(event['input_parquet_path'])

        output_prefix = os.path.join(event['s3_uri_output'], event['job_arn'].split('/')[-1])
        logger.info(f'Retrieving model output from {output_prefix}')
        model_output_uri = next(iter(wr.s3.list_objects(
            path=output_prefix,
            suffix='.jsonl.out',
        )))
        logger.info(f'Output URI: {model_output_uri}')
        output_records = read_jsonl_from_s3(model_output_uri)
        processed_outputs = [processor.process_output(r) for r in output_records]

        output_df = pd.DataFrame(processed_outputs).merge(input_df, on='record_id')
        output_parquet_path = os.path.join(f's3://{BUCKET_NAME}/batch_output_parquet/', *event['input_parquet_path'].split('/')[-2:])
        logger.info(f'Saving output parquet to {output_parquet_path}')

        wr.s3.to_parquet(
            output_df,
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

