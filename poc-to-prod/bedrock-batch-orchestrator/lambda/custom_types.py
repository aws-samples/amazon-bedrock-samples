from typing import TypedDict, List, Optional, Dict, Literal


"""
Custom types for the Bedrock Batch Inference step function tasks.

These TypedDict's do not *enforce* any structure or perform validation, but they do help with type hints in your IDE, 
making it easier to follow the data structures throughout the lambda function.
"""


class JobInput(TypedDict):
    """Input to the step function - event structure for preprocess.py handler"""
    s3_uri: Optional[str]
    dataset_id: Optional[str]
    split: Optional[str]
    job_name_prefix: str
    model_id: str
    prompt_id: Optional[str]
    max_num_jobs: Optional[int]
    max_records_per_job: Optional[int]


class BatchInferenceRecord(TypedDict):
    """Structure for each JSON document in the JSONL input files submitted with batch inference jobs."""
    recordId: str
    modelInput: Dict


class JobConfig(TypedDict):
    """
    Configuration required for bedrock:StartModelInvocation API call.
    Output from preprocess.py, input to start_batch_inference_job.py
    """
    model_id: str
    job_name: str
    input_parquet_path: str
    s3_uri_input: str
    s3_uri_output: str


class JobConfigList(TypedDict):
    """A collection of configurations for multiple batch processing jobs."""
    jobs: List[JobConfig]


class TaskItem(TypedDict):
    """
    Characterizes a submitted Bedrock Batch Inference job.
    Task Token is used to send progress updates (success, failure, heartbeat) back to the step function.

    Used as the output from start_batch_inference_job.py, the data model for items in the tasks DynamoDB table,
    and the output from get_batch_inference_job.py.

    Note that job_arn attribute is the partition key for the DDB table.
    """
    job_arn: str
    model_id: str
    input_parquet_path: str
    s3_uri_output: str
    status: Optional[Literal['Submitted', 'InProgress', 'Completed', 'Failed', 'Stopping', 'Stopped', 'PartiallyCompleted', 'Expired', 'Validating', 'Scheduled']]
    error_message: Optional[str]
    task_token: str


class CompletedJobsList(TypedDict):
    """Collection of completed jobs - input to postprocess.py"""
    completed_jobs: List[TaskItem]



