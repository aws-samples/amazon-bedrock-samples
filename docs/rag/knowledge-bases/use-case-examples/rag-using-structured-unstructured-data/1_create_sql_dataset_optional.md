---
tags:
    - RAG/ Data-Ingestion
    - RAG/ Knowledge-Bases
---

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/use-case-examples/rag-using-structured-unstructured-data/1_create_sql_dataset_optional.ipynb){:target="_blank"}"

<h2>Create structured SQL dataset [Optional]</h2>

This is a optional notebook to create dummy structured dataset and create a table in Amazon Athena for Text-2-SQL Retrieval.

**Pre-requisite:**
1. Run `0-create-dummy-structured-data.ipynb` notebook to generate synthetic tabular data or,
2. Bring your own tabular data to a folder in the current directory.


```python
import boto3
import json
import zipfile
import os
import time

<h2>Define the path to files</h2>
directory = 'sds/' # <folder in which you have saved your tabular data>

<h2>define a project name:</h2>
aws_account_id = boto3.client('sts').get_caller_identity()['Account']
project_name = 'advanced-rag-text2sql-{}'

<h2>S3 bucket for Firehose destination</h2>
bucket_name = project_name.format('s3-bucket')

<h2>Define the Glue role name</h2>
glue_role_name = project_name.format('glue-role')

<h2>Glue database name</h2>
glue_database_name = project_name.format('glue-database')

<h2>Glue crawler name</h2>
glue_crawler_name = project_name.format('glue-crawler')
```


```python
<h2>Create AWS clients</h2>
s3_client = boto3.client('s3')
glue_client = boto3.client('glue')
iam_client = boto3.client('iam')
boto3_session = boto3.session.Session()
region = boto3_session.region_name
```

<h3>Create S3 Bucket and upload data to it</h3>


```python
<h2>Create S3 bucket</h2>
s3_client.create_bucket(Bucket=bucket_name)
```


```python
<h2>This function uploads all files to their respective folders in an Amazon S3 bucket.</h2>
def upload_to_s3(path, bucket_name, bucket_subfolder=None):
    """
    Upload a file or directory to an AWS S3 bucket.

    :param path: Path to the file or directory to be uploaded
    :param bucket_name: Name of the S3 bucket
    :param bucket_subfolder: Name of the subfolder within the S3 bucket (optional)
    :return: True if the file(s) were uploaded successfully, False otherwise
    """
    s3 = boto3.client('s3')

    if os.path.isfile(path):
        # If the path is a file, create a folder for the file and upload it
        folder_name = os.path.basename(path).split('.')[0]  # Get the file name without extension"
        object_name = f"{folder_name}/{os.path.basename(path)}" if bucket_subfolder is None else f"{bucket_subfolder}/{folder_name}/{os.path.basename(path)}"
        try:
            s3.upload_file(path, bucket_name, object_name)
            print(f"Successfully uploaded {path} to {bucket_name}/{object_name}")
            return None
        except Exception as e:
            print(f"Error uploading {path} to S3: {e}")
            return None
    elif os.path.isdir(path):
        # If the path is a directory, recursively upload all files within it and create a folder for each file
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, path)
                folder_name = relative_path.split('.')[0]  # Get the folder name for the current file
                object_name = f"{folder_name}/{relative_path}" if bucket_subfolder is None else f"{bucket_subfolder}/{folder_name}/{relative_path}"
                try:
                    s3.upload_file(file_path, bucket_name, object_name)
                    print(f"Successfully uploaded {file_path} to {bucket_name}/{object_name}")
                except Exception as e:
                    print(f"Error uploading {file_path} to S3: {e}")
        return None
    else:
        print(f"{path} is not a file or directory.")
        return None

<h2>Upload the files:</h2>
upload_to_s3(directory, bucket_name)
```

<h3>Create Glue database and crawler</h3>


```python
glue_role_assume_policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "glue.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

glue_role_response = iam_client.create_role(
    RoleName=glue_role_name,
    AssumeRolePolicyDocument=json.dumps(glue_role_assume_policy_document)
)

<h2>Attach managed policies to the Glue role</h2>
iam_client.attach_role_policy(
    RoleName=glue_role_name,
    PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
)

iam_client.attach_role_policy(
    RoleName=glue_role_name,
    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole'
)

glue_role_arn = glue_role_response['Role']['Arn']

<h2>Create Glue database</h2>
glue_response = glue_client.create_database(DatabaseInput={'Name': glue_database_name})
time.sleep(30)
```


```python
<h2>Create Glue crawler</h2>
glue_client.create_crawler(
    Name=glue_crawler_name,
    Role=glue_role_arn,
    DatabaseName=glue_database_name,
    Description='Crawl Firehose S3 data to create a table in Athena',
    Targets={
        'S3Targets': [
            {
                'Path': f's3://{bucket_name}/'
            }
        ]
    }
)


<h2>Lets trigger the Glue Crawler so that we can query the data using SQL and create a dashboard in Quicksight:</h2>
try:
    response = glue_client.start_crawler(
        Name=glue_crawler_name
    )
    print(f"Crawler {glue_crawler_name} started successfully.")
except Exception as e:
    print(f"Error starting crawler {glue_crawler_name}: {e}")
```


```python
<h2>Wait for the crawler to complete</h2>
crawler_state = 'RUNNING'
while crawler_state == 'RUNNING':
    time.sleep(15)  # Wait for 15 seconds before checking the status again
    crawler_response = glue_client.get_crawler(
        Name=glue_crawler_name
    )
    crawler_state = crawler_response['Crawler']['State']

<h2>Print the final status of the crawler</h2>
if crawler_state in ['SUCCEEDED', 'STOPPING']:
    print(f"Crawler {glue_crawler_name} completed successfully.")
else:
    print(f"Crawler {glue_crawler_name} failed with state: {crawler_state}")
```

Lets save the database name in local variables such that its available directly in the `MultiRetreiverQAChain` notebook.


```python
%store glue_database_name
```

<h3>Next Steps:</h3>

Once the cralwer has run successfully, you should now see 4 tables created in Athena with the same names as your files. Now, you should be able to use the `MultiRetrievalQAChain` using this dummy dataset.
