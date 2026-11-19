import argparse
import json
import re
from typing import List, Optional

from pydantic import BaseModel, ValidationError, ValidationInfo, field_validator, model_validator

IMAGE_FORMATS = ["jpeg", "png", "gif", "webp"]
VIDEO_FORMATS = ["mov", "mkv", "mp4", "webm"]
MAX_NUM_IMAGES = 10
MODEL_TO_NUM_SAMPLES_MAP = {"micro": (8, 20000), "lite": (8, 20000), "pro": (8, 20000)}

INVALID_TOKENS_TEXT = [
    "System:",
    "SYSTEM:",
    "User:",
    "USER:",
    "Bot:",
    "BOT:",
    "Assistant:",
    "ASSISTANT:",
    "Thought:",
    "[EOS]",
    "<image>",
    "<video>",
]


class ConverseRoles:
    """Defines the possible roles in a conversation according to converse format"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


CONVERSE_ROLES_WITHOUT_SYSTEM = [ConverseRoles.USER, ConverseRoles.ASSISTANT]


class NovaClientError(ValueError):
    """Custom exception for Nova client validation errors."""

    def __init__(self, message):
        super().__init__(message)


class NovaInternalError(Exception):
    """Base exception for Nova Fine Tuning validation errors"""

    pass


def check_jsonl_file(file_path):
    """Validates that the input file has a .jsonl extension."""
    if not file_path.endswith(".jsonl"):
        raise NovaClientError(f"File is not jsonl: {file_path}")


def load_jsonl_data(file_path: str):
    """Loads and validates JSON lines from the specified file path."""
    try:
        check_jsonl_file(file_path)
        data = []
        with open(file_path, "r") as file:
            for line_number, line in enumerate(file, 1):
                try:
                    parsed_line = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Line {line_number}: Invalid JSON syntax - {str(e)}\nLine content: {line}"
                    )
                data.append(parsed_line)
        return data
    except Exception as e:
        raise NovaClientError(f"Error loading data from {file_path}: {str(e)}")


class S3Location(BaseModel):
    """Represents and validates an S3 URI location."""

    uri: str

    @field_validator("uri")
    def validate_format(cls, uri):
        """Validates that the URI starts with 's3://'."""
        if not uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI, must start with 's3://'")
        is_valid_path(uri.replace("s3://", ""))
        return uri


class Source(BaseModel):
    """Defines the source location for media content."""

    s3Location: S3Location


class ImageContent(BaseModel):
    """Represents and validates image content with format and source."""

    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, image_format):
        """Validates that the image format is supported."""
        if image_format.lower() not in IMAGE_FORMATS:
            raise ValueError(f"Invalid image format, supported formats are {IMAGE_FORMATS}")
        return image_format


class VideoContent(BaseModel):
    """Represents and validates video content with format and source."""

    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, video_format):
        """Validates that the video format is supported."""
        if video_format.lower() not in VIDEO_FORMATS:
            raise ValueError(f"Invalid video format, supported formats are {VIDEO_FORMATS}")
        return video_format


class ContentItem(BaseModel):
    """Represents a content item that can contain text, image, or video."""

    text: Optional[str] = None
    image: Optional[ImageContent] = None
    video: Optional[VideoContent] = None

    @model_validator(mode="after")
    def validate_model_fields(cls, values):
        """Validates that at least one content type is provided."""
        if not any(getattr(values, field) is not None for field in cls.model_fields.keys()):
            raise ValueError(
                f"Invalid content, at least one of {list(cls.model_fields.keys())} must be provided"
            )
        return values

    @field_validator("text")
    def validate_text(cls, text: str):
        if not text:
            return text

        validate_invalid_tokens(text)
        return text


class Message(BaseModel):
    """Represents a conversation message with role and content."""

    role: str
    content: List[ContentItem]

    @field_validator("role")
    def validate_role(cls, role):
        """Validates that the role is either user or assistant."""
        if role.lower() not in CONVERSE_ROLES_WITHOUT_SYSTEM:
            raise ValueError(
                f"Invalid value for role, valid values are {CONVERSE_ROLES_WITHOUT_SYSTEM}"
            )
        return role

    @model_validator(mode="after")
    def validate_content_rules(cls, values):
        """Validates content rules for assistant messages."""
        content_items = values.content
        has_video = any(item.video is not None for item in content_items)
        has_image = any(item.image is not None for item in content_items)

        if has_image or has_video:
            if values.role.lower() == "assistant":
                raise ValueError(
                    "Invalid content, image/video cannot be included when role is 'assistant'"
                )

        return values

    @field_validator("content")
    def validate_content(cls, content, info: ValidationInfo):
        """Validates message content against Nova's rules for text, images, and videos.
        Ensures content follows size limits (max 10 images, 1 video), format restrictions,
        and model-specific constraints (no media for micro models). Checks that text content
        is not empty and media types don't mix (can't have both images and video).

        Args:
            content (List[ContentItem]): List of content items to validate
            info (ValidationInfo): Validation context with model_name

        Raises:
            ValueError: If content violates Nova's rules
            Exception: If validation context is missing
        """
        has_text = any(item.text is not None for item in content)
        has_video = any(item.video is not None for item in content)
        has_image = any(item.image is not None for item in content)

        total_text_length = sum(len(item.text) for item in content if item.text is not None)
        if has_text and not (has_image or has_video) and total_text_length == 0:
            raise ValueError("Invalid content, empty text content")

        if not info.context:
            raise NovaInternalError("context is not set for validating model type")

        is_micro_model = "micro" in info.context["model_name"]
        if is_micro_model and (has_image or has_video):
            raise ValueError(
                "Invalid content, image/video samples not supported by Nova Micro model"
            )

        if sum(1 for item in content if item.video is not None) > 1:
            raise ValueError("Only one video is allowed per sample")

        if has_video and has_image:
            raise ValueError(
                "'content' list cannot contain both video items and image items for a given sample"
            )

        num_images = sum(1 for item in content if item.image is not None)
        if num_images > MAX_NUM_IMAGES:
            raise ValueError(
                f"Invalid content, number of images {num_images} exceed maximum allowed limit of {MAX_NUM_IMAGES}"
            )

        return content


class SystemMessage(BaseModel):
    """Represents a system message with text content."""

    text: str

    @field_validator("text")
    def validate_text(cls, text: str):
        if not text:
            return text

        validate_invalid_tokens(text)
        return text


class ConverseDatasetSample(BaseModel):
    """Represents a complete conversation sample with system message and message turns."""

    schemaVersion: Optional[str] = None
    system: Optional[List[SystemMessage]] = None
    messages: List[Message]

    @field_validator("messages")
    def validate_data_sample_rules(cls, messages):
        """Validates the order and structure of messages in the conversation."""
        check_roles_order(messages)
        return messages


def validate_converse_dataset(args):
    """Validates the entire conversation dataset against Nova format requirements."""
    try:
        samples = load_jsonl_data(args.input_file)
        num_samples = len(samples)
        print(f"Loaded {num_samples} samples from {args.input_file}")
        validate_data_record_bounds(num_samples, args.model_name)
    except Exception as e:
        print(f"Error loading or validating file bounds: {e}")
        raise

    error_message = ""
    failed_samples_id_list = []

    print(f"Validating samples for model: {args.model_name}")
    for i, sample in enumerate(samples):
        try:
            ConverseDatasetSample.model_validate(sample, context={"model_name": args.model_name})
        except ValidationError as e:
            failed_samples_id_list.append(i)
            error_message += f"\nSample {i}:\n"
            for err in e.errors():
                err["msg"] = err["msg"].replace("Value error, ", "")
                sample_error_message = (
                    f"  - Location {err['loc']}: {err['msg']} (type={err['type']})\n"
                )
                error_message += sample_error_message
        except Exception as e:
            raise NovaInternalError(f"Unexpected error occurred in sample {i}: {e}")

    if error_message:

        if len(failed_samples_id_list) > 3:
            first_sample_id = failed_samples_id_list[0]
            second_sample_id = failed_samples_id_list[1]
            last_sample_id = failed_samples_id_list[-1]
            failed_samples_str = f"[{first_sample_id}, {second_sample_id}, ...{last_sample_id}]"
        else:
            failed_samples_str = f"{failed_samples_id_list}"

        final_err_msg = (
            f"Validation failed for samples: {failed_samples_str}\n\n"
            f"Note: Sample IDs are zero-indexed.\n"
            f"{error_message}"
        )
        raise NovaClientError(final_err_msg)
    else:
        print("Validation successful, all samples passed!")


def validate_invalid_tokens(text: str):
    """Validates that the input text does not contain any disallowed tokens"""

    stripped_text = text.strip()
    client_invalid_tokens = []
    for invalid_token in INVALID_TOKENS_TEXT:
        if invalid_token in stripped_text:
            client_invalid_tokens.append(f"`{invalid_token}`")

    if client_invalid_tokens:
        client_invalid_tokens_str = ", ".join(client_invalid_tokens)
        raise ValueError(
            f"Invalid text content, following tokens are invalid: {client_invalid_tokens_str}. Please check documentation for other invalid tokens"
        )


def check_roles_order(messages):
    """Validates that messages alternate between user and assistant roles."""

    if len(messages) < 2:
        raise ValueError(
            f"Invalid messages, both {CONVERSE_ROLES_WITHOUT_SYSTEM} are needed in sample"
        )

    for i, message in enumerate(messages):
        if i % 2 == 0 and message.role != ConverseRoles.USER:
            raise ValueError(
                f"Invalid messages, expected {ConverseRoles.USER} role but found {message.role}"
            )
        elif i % 2 == 1 and message.role != ConverseRoles.ASSISTANT:
            raise ValueError(
                f"Invalid messages, expected {ConverseRoles.ASSISTANT} role but found {message.role}"
            )

    # When turns are odd
    if messages[-1].role != ConverseRoles.ASSISTANT:
        raise ValueError(f"Invalid messages, last turn should have {ConverseRoles.ASSISTANT} role")


def is_valid_path(file_path):
    """Validates that file path contains only alphanumeric characters, underscores, hyphens, slashes, and dots."""
    pattern = r"^[\w\-/\.]+$"
    if not re.match(pattern, file_path):
        raise ValueError(
            "Invalid characters in 'uri'. Only alphanumeric, underscores, hyphens, slashes, and dots are allowed"
        )


def get_data_record_bounds(model_name: str):
    """Returns the minimum and maximum number of samples allowed for a given model."""
    return MODEL_TO_NUM_SAMPLES_MAP[model_name]


def validate_data_record_bounds(num_samples: int, model_name: str):
    """Validates that the number of samples is within allowed bounds for the model."""
    data_record_bounds = get_data_record_bounds(model_name)
    if num_samples < data_record_bounds[0] or num_samples > data_record_bounds[1]:
        raise NovaClientError(
            (
                f"Numer of samples {num_samples} out of bounds between {data_record_bounds[0]} and {data_record_bounds[1]} "
                f"for {model_name}"
            )
        )


if __name__ == "__main__":
    description = """
    This script is for validating Nova converse format.
    Takes input a jsonl file with samples in the Nova converse format:
    https://docs.aws.amazon.com/nova/latest/userguide/customize-fine-tune-prepare.html
    """
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-i",
        "--input_file",
        type=str,
        required=True,
        help="The input jsonl file in Nova converse format",
    )
    parser.add_argument(
        "-m",
        "--model_name",
        type=str,
        choices=["micro", "lite", "pro"],
        required=True,
        help="Choose a model from: micro, lite, pro",
    )
    args = parser.parse_args()
    validate_converse_dataset(args)
