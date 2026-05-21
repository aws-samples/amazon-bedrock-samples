import re
from uuid import uuid4
import logging
import awswrangler as wr
from typing import Literal


def create_job_name(job_name_prefix: str, index: int) -> str:
    """
    Cleans input string to conform to pattern: [a-zA-Z0-9]{1,63}(-*[a-zA-Z0-9\\+\\-\\.]){0,63}
    """
    suffix = f'-part-{str(index).zfill(4)}-{str(uuid4())[:6]}'
    job_name = job_name_prefix[:63-len(suffix)] + suffix

    # Remove invalid characters, keeping only allowed ones
    return re.sub(r'[^a-zA-Z0-9\-]', '', job_name)


def split_s3_uri(uri: str) -> tuple[str, str]:
    """Split S3 URI into bucket and key components.

    Args:
        uri: S3 URI in format s3://bucket/path/to/file

    Returns:
        Tuple of (bucket, key)
    """
    if not uri.startswith('s3://'):
        raise ValueError("URI must start with 's3://'")

    path = uri[5:]  # Remove 's3://'
    parts = path.split('/', 1)
    if len(parts) != 2:
        raise ValueError("URI must contain bucket and key")

    return parts[0], parts[1]


def get_logger(level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(level)
    return logger


def load_files_in_chunks(
    s3_uri: str,
    file_type: Literal["csv", "parquet"],
    chunk_size: int,
    **kwargs,
):
    """Load files from S3 in chunks.

    Args:
        s3_uri: S3 URI of file to load
        file_type: File type to load
        chunk_size: Chunk size to load
        **kwargs: Additional keyword arguments to pass to wr.s3.read_csv or wr.s3.read_parquet
    """

    if file_type == "csv":
        for idx, input_df in enumerate(wr.s3.read_csv(s3_uri, chunksize=chunk_size, **kwargs)):
            yield idx, input_df

    elif file_type == "parquet":
        for idx, input_df in enumerate(wr.s3.read_parquet(s3_uri, chunked=chunk_size, **kwargs)):
            yield idx, input_df

    else:
        raise ValueError(f"Unsupported file type: {file_type}")
