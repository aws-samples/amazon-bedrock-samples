"""
AWS Glue ETL Job for processing JSON data from S3 to Parquet format.

Handles optional requestMetadata field and partitions data by timestamp.
"""  # noqa: INP001

import sys
from datetime import datetime

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import (
    col,
    dayofmonth,
    explode,
    from_json,
    input_file_name,
    lit,
    map_entries,
    month,
    to_json,
    to_timestamp,
    when,
    year,
)
from pyspark.sql.types import MapType, StringType

# ---------------------------
# Initialization & Configuration
# ---------------------------

# Retrieve Glue job parameters
args = getResolvedOptions(sys.argv, ["JOB_NAME","source_bucket","target_bucket"])

# Generate unique batch ID for tracking
batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005

# Initialize Spark and Glue contexts
sc = SparkContext()
gluecontext = GlueContext(sc)
spark = gluecontext.spark_session
job = Job(gluecontext)

# Enable Adaptive Query Execution
spark.conf.set("spark.sql.adaptive.enabled", "true")

# Initialize job with parameters and bookmarks
job.init(args["JOB_NAME"], args)

# Configure source and target S3 paths
source_bucket = args["source_bucket"]
target_bucket = args["target_bucket"]

# ---------------------------
# Data Ingestion
# ---------------------------

# Read compressed JSON data from S3
print("Reading data from source bucket...")
datasource = gluecontext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [f"s3://{source_bucket}/"],
        "recurse": True,
        "compression": "gzip",
    },
    format="json",
    transformation_ctx="datasource",
)

# Convert to Spark DataFrame for complex transformations
df = datasource.toDF()  # noqa: PD901

# Filter out files from /data/ folder and cache for reuse
df = df.filter(~input_file_name().contains("/data/")).cache()  # noqa: PD901

# ---------------------------
# Helper Function Definition
# ---------------------------

def extract_field(df, path, field_name, default_value=""):  # noqa: D417
    """
    Safely extracts nested fields from DataFrame with error handling.

    Returns default value if field doesn't exist or is null.

    Parameters
    ----------
    - df: Spark DataFrame
    - path: Dot-separated path to nested field (e.g., 'identity.arn')
    - field_name: Desired output column name
    - default_value: Fallback value if field is missing

    Returns: Column expression for safe field extraction

    """
    if default_value is None:
        default_value = ""

    try:
        parts = path.split(".")
        root = parts[0]

        # Handle missing root field
        if root not in df.columns:
            return lit(default_value).cast("string").alias(field_name)

        # Handle nested fields
        if len(parts) > 1:
            try:
                # Verify nested path exists
                df.select(col(path))
                return when(col(path).isNotNull(),
                           col(path).cast("string")).otherwise(
                           lit(default_value).cast("string")).alias(field_name)
            except Exception:  # noqa: BLE001
                # Path doesn't exist in schema
                return lit(default_value).cast("string").alias(field_name)
        else:
            # Handle root-level field
            return when(col(root).isNotNull(),
                       col(root).cast("string")).otherwise(
                       lit(default_value).cast("string")).alias(field_name)
    except Exception as e:  # noqa: BLE001
        print(f"Error extracting field {path}: {e!s}")
        return lit(default_value).cast("string").alias(field_name)

# ---------------------------
# Main Data Processing
# ---------------------------

print("Processing main dataset...")

# Create flattened DataFrame with essential fields
flattened_df = df.select(
    # Core metadata fields
    extract_field(df, "schemaType", "schemaType"),
    extract_field(df, "schemaVersion", "schemaVersion"),
    extract_field(df, "timestamp", "timestamp"),

    # AWS context fields
    extract_field(df, "accountId", "accountId"),
    extract_field(df, "region", "region"),
    extract_field(df, "requestId", "requestId"),

    # Service operation details
    extract_field(df, "operation", "operation"),
    extract_field(df, "modelId", "modelId"),

    # Identity information
    extract_field(df, "identity.arn", "identity_arn"),

    # Input metrics
    extract_field(df, "input.inputContentType", "input_contentType"),

    extract_field(df, "input.inputBodyJson.taskType", "task_type"),
    extract_field(df, "input.inputTokenCount", "input_tokenCount"),

    # Image metrics
    extract_field(df, "input.inputBodyJson.imageGenerationConfig.width", "image_width"),
    extract_field(df, "input.inputBodyJson.imageGenerationConfig.height", "image_height"),
    extract_field(df, "input.inputBodyJson.imageGenerationConfig.numberOfImages", "numberOfImages"),

    # Video metrics
    extract_field(df, "input.inputBodyJson.duration", "input_duration"),
    extract_field(df, "input.inputBodyJson.resolution", "input_resolution"),
    extract_field(df, "output.outputVideoDurationSeconds", "output_duration"),
    extract_field(df, "output.outputVideoFramesPerSecond", "output_FPS"),
    extract_field(df, "output.outputVideoWidth", "output_videoWidth"),
    extract_field(df, "output.outputVideoHeight", "output_videoHeight"),


    # Output metrics
    extract_field(df, "output.outputContentType", "output_contentType"),
    extract_field(df, "output.outputTokenCount", "output_tokenCount"),

    # Performance metrics
    extract_field(df, "output.outputBodyJson.metrics.latencyMs", "output_latencyMs"),

    # Token usage statistics
    extract_field(df, "output.outputBodyJson.usage.inputTokens", "usage_inputTokens"),
    extract_field(df, "output.outputBodyJson.usage.outputTokens", "usage_outputTokens"),
    extract_field(df, "output.outputBodyJson.usage.totalTokens", "usage_totalTokens"),
    extract_field(df, "output.outputBodyJson.usage.cacheReadInputTokens", "cache_readtokens"),
    extract_field(df, "output.outputBodyJson.usage.cacheWriteInputTokens", "cache_writetokens"),

    # Metadata fields
    extract_field(df, "requestMetadata.TenantID", "tenantId","None"),

)

# ---------------------------
# Time Partition Handling
# ---------------------------

print("Handling timestamp partitioning...")

# Create parsed timestamp column without fallback
partitioned_df = flattened_df.withColumn(
    "parsed_timestamp",
    when(
        col("timestamp").isNotNull() & (col("timestamp") != ""),
        to_timestamp(col("timestamp")),
    ).otherwise(lit(None)),  # Use null instead of fallback timestamp
)

# Extract temporal partition columns
partitioned_df = partitioned_df.withColumn("Year", year(col("parsed_timestamp"))) \
                               .withColumn("Month", month(col("parsed_timestamp"))) \
                               .withColumn("Date", dayofmonth(col("parsed_timestamp"))) \
                               .withColumn("batchid", lit(batch_id))

# Filter out invalid partition values and cache for reuse
partitioned_df = partitioned_df.filter(
    col("parsed_timestamp").isNotNull() &
    col("Year").isNotNull() &
    col("Month").isNotNull() &
    col("Date").isNotNull(),
).cache()


# ---------------------------
# Main Data Output
# ---------------------------

print("Writing main dataset to S3...")
partitioned_df.repartition(col("tenantId")).write \
    .mode("append") \
    .option("compression", "snappy") \
    .partitionBy("Year", "Month", "Date", "tenantId", "batchid") \
    .parquet(f"s3://{target_bucket}/main/")


# ---------------------------
# Metadata Processing
# ---------------------------

print("Processing request metadata...")

# Prepare base metadata columns
metadata_base_columns = [
    extract_field(df, "timestamp", "timestamp"),
    extract_field(df, "requestId", "requestId"),
    extract_field(df, "accountId", "accountId"),
    extract_field(df, "requestMetadata.TenantID", "tenantId", "None"),
]

# Safely handle optional requestMetadata field
if "requestMetadata" in df.columns:
    print("Found requestMetadata column in source data")
    metadata_base_columns.append(col("requestMetadata"))
else:
    print("requestMetadata column not found - creating empty map")
    metadata_base_columns.append(
        lit(None).cast(MapType(StringType(), StringType())).alias("requestMetadata"),
    )

# Create metadata base DataFrame
metadata_base_df = df.select(*metadata_base_columns)

# Filter out records without metadata
metadata_base_df = metadata_base_df.filter(col("requestMetadata").isNotNull())

# ---------------------------
# Metadata Transformation
# ---------------------------

try:
    print("Attempting direct map processing...")
    # Try processing as native map type
    metadata_kvp_df = metadata_base_df.select(
        col("timestamp"),
        col("requestId"),
        col("accountId"),
        col("tenantId"),
        explode(map_entries(col("requestMetadata"))).alias("metadata_entry"),
    )

    # Extract key-value pairs from map entries
    metadata_kvp_df = metadata_kvp_df.select(
        col("timestamp"),
        col("requestId"),
        col("accountId"),
        col("tenantId"),
        col("metadata_entry.key").alias("metadata_key"),
        col("metadata_entry.value").alias("metadata_value"),
    )
except Exception as e:  # noqa: BLE001
    print(f"Map processing failed ({e!s}), trying JSON conversion...")
    # Fallback processing for struct types
    metadata_base_df = metadata_base_df.withColumn("metadata_json", to_json(col("requestMetadata")))

    # Define schema for JSON conversion
    metadata_schema = MapType(StringType(), StringType())

    # Convert JSON string to map structure
    metadata_base_df = metadata_base_df.withColumn(
        "metadata_map",
        from_json(col("metadata_json"), metadata_schema),
    )

    # Explode map entries
    metadata_kvp_df = metadata_base_df.select(
        col("timestamp"),
        col("requestId"),
        col("accountId"),
        col("tenantId"),
        explode(map_entries(col("metadata_map"))).alias("metadata_entry"),
    )

    # Extract key-value pairs
    metadata_kvp_df = metadata_kvp_df.select(
        col("timestamp"),
        col("requestId"),
        col("accountId"),
        col("tenantId"),
        col("metadata_entry.key").alias("metadata_key"),
        col("metadata_entry.value").alias("metadata_value"),
    )

# ---------------------------
# Metadata Output
# ---------------------------

print("Processing metadata timestamps...")

# Apply timestamp handling without fallback
metadata_kvp_df = metadata_kvp_df.withColumn(
    "parsed_timestamp",
    when(
        col("timestamp").isNotNull() & (col("timestamp") != ""),
        to_timestamp(col("timestamp")),
    ).otherwise(lit(None)),  # Use null instead of fallback timestamp
)

# Add partition columns
metadata_kvp_df = metadata_kvp_df.withColumn("Year", year(col("parsed_timestamp"))) \
                               .withColumn("Month", month(col("parsed_timestamp"))) \
                               .withColumn("Date", dayofmonth(col("parsed_timestamp"))) \
                               .withColumn("batchid", lit(batch_id))

# Validate partitions and filter out records with missing timestamps
metadata_kvp_df = metadata_kvp_df.filter(
    col("parsed_timestamp").isNotNull() &
    col("Year").isNotNull() &
    col("Month").isNotNull() &
    col("Date").isNotNull(),
)


print("Writing metadata to S3...")
metadata_kvp_df.repartition(col("tenantId")).write \
    .mode("append") \
    .option("compression", "snappy") \
    .partitionBy("Year", "Month", "Date", "tenantId", "batchid") \
    .parquet(f"s3://{target_bucket}/metadata/")

# ---------------------------
# Job Finalization
# ---------------------------

print("Committing job...")
job.commit()

print("ETL job completed successfully")
