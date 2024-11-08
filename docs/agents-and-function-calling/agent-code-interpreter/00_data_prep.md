---
tags:
    - Agent/ Code-Interpreter
    - Agent/ Prompt-Engineering
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/agents-and-function-calling/agent-code-interpreter/00_data_prep.ipynb){:target="_blank"}

<h2>Overview</h2>

This repository demonstrates how to set up, use, and test an Amazon Bedrock Agent with Code Interpreter capabilities. The project is divided into three Jupyter notebooks, each focusing on a specific aspect of the process.


<h2>Context</h2>

This is the first notebook in the series to demonstrates how to set up and use an Amazon Bedrock Agent with Code Interpreter capabilities.

In this notebook we process open souce NYC Taxi and Limousine data to be used by our Amazon Bedrock Agent later
<h3>NYC TLC Trip Record Data</h3>

- **Source**: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- **Content**: Yellow and green taxi trip records (pickup/dropoff times, locations, fares, etc.)

<h3>Process</h3>
1. Download Parquet file for target date
2. Convert to CSV, reduce to <100MB
3. Upload to S3 for agent use

Note: Ensure S3 upload permissions

<h2>Prerequisites</h2>

Apart from the libraries that we will be installing, this notebook requires permissions to:

<ul>
<li>access Amazon Bedrock</li>
</ul>

If running on SageMaker Studio, you should add the following managed policies to your role:
<ul>
<li>AmazonBedrockFullAccess</li>
</ul>

<div class="alert alert-block alert-info">
<b>Note:</b> Please make sure to enable `Anthropic Claude 3.5 Sonnet` model access in Amazon Bedrock Console, as the later notebook will use Anthropic Claude 3.5 Sonnet model.
</div>

<h2>Setup</h2>

We need to import the necessary Python libraries 


```python
import os
import boto3
import logging
import requests
import pandas as pd
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime, timedelta
```


```python
# set a logger
logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
```


```python
import sagemaker

# Create a SageMaker session
sagemaker_session = sagemaker.Session()

# Get the default S3 bucket
default_bucket = sagemaker_session.default_bucket()

print(f"Default S3 bucket: {default_bucket}")

```


```python
# constants
CSV_DATA_FILE: str = 'nyc_taxi_subset.csv'
# Bucket and prefix name where this csv file will be uploaded and used as S3 source by code interpreter
S3_BUCKET_NAME: str = default_bucket
PREFIX: str = 'code-interpreter-demo-data'
# This is the size of the file that will be uploaded to s3 and used by the agent (in MB)
DATASET_FILE_SIZE: float = 99
```


```python
def download_nyc_taxi_data(start_date, end_date, data_types):
    base_url = "https://d37ci6vzurychx.cloudfront.net/trip-data/"
    
    current_date = start_date
    while current_date <= end_date:
        for data_type in data_types:
            file_name = f"{data_type}_tripdata_{current_date.strftime('%Y-%m')}.parquet"
            url = base_url + file_name
            
            print(f"Downloading {file_name}...")
            
            response = requests.get(url)
            if response.status_code == 200:
                output_dir = f"nyc_taxi_data/{data_type}/{current_date.year}"
                os.makedirs(output_dir, exist_ok=True)
                
                with open(os.path.join(output_dir, file_name), 'wb') as f:
                    f.write(response.content)
                print(f"Successfully downloaded {file_name}")
            else:
                print(f"Failed to download {file_name}. Status code: {response.status_code}")
        
        current_date += timedelta(days=32)
        current_date = current_date.replace(day=1)

# Set the date range for which you want to download data
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 31)

# Specify the types of data you want to download
data_types = ['yellow']

# Download the data
download_nyc_taxi_data(start_date, end_date, data_types)

```

<h2>Prepare the large data and send it to S3 to be used by the agent</h2>

Now, we will prepare the data and upload it to S3. This is the new york taxi dataset. S3 allows for larger files (100MB) to be used by the agent for code interpretation, so we will upload a CSV file that is `99.67 MB` in size.


```python
# Read the parquet file into a pandas DataFrame
nyc_taxi_df = pd.read_parquet("./nyc_taxi_data/yellow/2024/yellow_tripdata_2024-01.parquet")
nyc_taxi_df.head()
```


```python
def write_csv_with_size_limit(df: pd.DataFrame, 
                              output_file: str, 
                              size_limit_mb: float = 99):
    """
    This function writes a pandas DataFrame to a CSV file with a given limit
    in size (in MB)
    """
    try:
        chunk_size: int = 10000 
        total_rows = len(df)
        start_index: int = 0
        while start_index < total_rows:
            # Write a chunk of data
            end_index = min(start_index + chunk_size, total_rows)
            chunk = df.iloc[start_index:end_index]
            
            mode = 'w' if start_index == 0 else 'a'
            chunk.to_csv(output_file, mode=mode, header=(start_index == 0), index=False)
            
            # Check file size
            current_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            
            if current_size_mb >= size_limit_mb:
                logger.info(f"Reached size limit. Current file size: {current_size_mb:.2f} MB")
                break
            
            start_index = end_index
            
        final_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        logger.info(f"Final file size: {final_size_mb:.2f} MB")
        logger.info(f"Rows written: {end_index} out of {total_rows}")
    except Exception as e:
        logger.error(f"An error occurred while writing to the csv file with the limit of {size_limit_mb}: {e}")
```


```python
write_csv_with_size_limit(nyc_taxi_df, CSV_DATA_FILE, size_limit_mb=99)
```


```python
size_in_bytes = os.path.getsize(CSV_DATA_FILE)
# Convert to megabytes
size_in_mb = size_in_bytes / (1024 * 1024)
logger.info(f"Size of the {CSV_DATA_FILE} is: {size_in_mb}")
```


```python
s3_client = boto3.client('s3')
s3_client.upload_file(CSV_DATA_FILE, S3_BUCKET_NAME, f"{PREFIX}/{os.path.basename(CSV_DATA_FILE)}")
s3_uri: str = f"s3://{S3_BUCKET_NAME}/{PREFIX}/{os.path.basename(CSV_DATA_FILE)}"
logger.info(f"File uploaded successfully. S3 URI: {s3_uri}")
```


```python
# Write the S3 URI to a text file
with open('s3_uri.txt', 'w') as f:
    f.write(s3_uri)

print("S3 URI has been written to s3_uri.txt")
```
