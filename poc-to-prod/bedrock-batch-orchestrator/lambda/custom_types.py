from typing import TypedDict, List, Optional, Dict, Literal, Union


"""
Custom types for the Bedrock Batch Inference step function tasks.

These TypedDict's do not *enforce* any structure or perform validation, but they do help with type hints in your IDE, 
making it easier to follow the data structures throughout the lambda function.
"""


# ============================================================================
# PROMPT CONFIGURATION TYPES
# ============================================================================

class PromptConfigSingle(TypedDict):
    """Single prompt applied to all input records"""
    mode: Literal['single']
    prompt_id: str


class PromptConfigMapped(TypedDict):
    """Prompt ID read from a CSV column for each record"""
    mode: Literal['mapped']
    column_name: str
    image_column: Optional[str]  # Column containing image paths (for multimodal)


class PromptConfigExpanded(TypedDict):
    """Multiple prompts applied per input record based on category mapping"""
    mode: Literal['expanded']
    category_column: str  # Column to read category value from
    image_column: Optional[str]  # Column containing image paths (for multimodal)
    expansion_mapping: Dict[str, str]  # category_value -> expansion_rule_name


# Union type for all prompt configuration modes
PromptConfig = Union[PromptConfigSingle, PromptConfigMapped, PromptConfigExpanded]


# ============================================================================
# JOB INPUT TYPES
# ============================================================================

class JobInput(TypedDict):
    """Input to the step function - event structure for preprocess.py handler"""
    s3_uri: Optional[str]
    dataset_id: Optional[str]
    split: Optional[str]
    job_name_prefix: str
    model_id: str
    prompt_id: Optional[str]  # For backward compatibility
    prompt_config: Optional[PromptConfig]  # New unified prompt configuration
    input_type: Optional[Literal['text', 'image']]  # Type of input data
    image_column: Optional[str]  # Column name for image paths in CSV (default: 'image_path')
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


# ============================================================================
# PIPELINE CONFIGURATION TYPES
# ============================================================================

class PipelineStage(TypedDict):
    """Configuration for a single stage in a multi-stage pipeline"""
    stage_name: str
    model_id: str
    input_s3_uri: Optional[str]  # Explicit input S3 URI (if not using previous output)
    input_type: Optional[Literal['text', 'image']]  # Type of input data
    job_name_prefix: str
    prompt_config: PromptConfig
    use_previous_output: Optional[bool]  # If True, use output from previous stage as input
    column_mappings: Optional[Dict[str, str]]  # Rename/transform columns from previous stage


class PipelineConfig(TypedDict):
    """Configuration for a multi-stage batch inference pipeline"""
    pipeline_name: str
    presigned_url_expiry_days: Optional[int]  # Expiry for presigned URLs in notifications (default: 7)
    stages: List[PipelineStage]


# ============================================================================
# VALIDATION TYPES
# ============================================================================

class ValidationResult(TypedDict):
    """Result of pipeline configuration validation"""
    valid: bool
    errors: List[str]  # List of validation error messages
    warnings: List[str]  # List of validation warning messages
    estimated_records: Optional[int]  # Estimated total records to process
    estimated_cost_usd: Optional[float]  # Estimated cost in USD



