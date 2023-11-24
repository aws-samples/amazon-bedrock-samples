import os
import boto3
import asyncio
import logging
import pandas as pd
from typing import Dict, Generator

logger = logging.getLogger(__name__)

# download the files from s3 and convert them into base64 encoded images
def download_image_file(row_tuple: Dict, s3_bucket: str, s3_prefix: str, local_images_dir: str):
    s3 = boto3.client('s3')
    _, row = row_tuple
    # print(f"row type={type(row)}")
    path = row.get('path')
    if path is None:
        return
    local_path = os.path.join(local_images_dir, os.path.basename(path))
    key = f"{s3_prefix}/{path}"
    logger.info(f"going to download {s3_bucket}/{key} to {local_path}")
    with open(local_path, 'wb') as f:
        s3.download_fileobj(s3_bucket, key, f)

async def adownload_image_file(row_tuple: Dict, s3_bucket: str, s3_prefix: str, local_images_dir: str):
    return await asyncio.to_thread(download_image_file, row_tuple, s3_bucket, s3_prefix, local_images_dir)

async def adownload_all_image_files(rows: Generator, s3_bucket: str, s3_prefix: str, local_images_dir: str):
    return  await asyncio.gather(*[adownload_image_file(r, s3_bucket, s3_prefix, local_images_dir) for r in rows])


def download_images(image_count: int, image_data_fname: str, s3_bucket: str, s3_prefix: str, local_images_dir: str):
    image_data = pd.read_csv(image_data_fname)
    image_count = len(image_data) if image_count > len(image_data) else image_count
    _ = asyncio.run(adownload_all_image_files(image_data.sample(n=image_count).iterrows(), s3_bucket, s3_prefix, local_images_dir))
