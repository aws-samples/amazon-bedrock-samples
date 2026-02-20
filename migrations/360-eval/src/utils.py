import pytz
import datetime
import json
import re
import time
import os
import random
import logging
import base64
import litellm
import requests
import requests.exceptions
from tenacity import retry, stop_after_delay, wait_exponential, retry_if_exception_type
from litellm import completion, RateLimitError, ServiceUnavailableError, APIError, APIConnectionError, BadRequestError
from litellm import token_counter
from botocore.exceptions import ClientError
import litellm

litellm.drop_params = True


logger = logging.getLogger(__name__)
litellm.drop_params = True

# ----------------------------------------
# Request Builders
# ----------------------------------------


def setup_logging(log_dir='logs', experiment='none'):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{log_dir}/360-benchmark-{ts}-{experiment}.log"

    # Reset root logger and handlers to avoid duplicate logs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure root logger
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filemode='w'
    )

    # Add console handler for warnings and above
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger('').addHandler(console)

    # Configure logger for this module
    module_logger = logging.getLogger(__name__)
    module_logger.info(f"Logging initialized. Log file: {log_file}")

    return ts, log_file


def get_timestamp():
    return datetime.datetime.fromtimestamp(time.time(), tz=pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def calculate_average_scores(dict_list):
    if not dict_list:
        return {}

    # Initialize result dictionary
    result = {}

    # Get the keys from the first dictionary (assuming all dictionaries have the same keys)
    keys = dict_list[0].keys()

    # Calculate the average for each key
    for key in keys:
        total = sum(d[key] for d in dict_list)
        average = total / len(dict_list)
        result[f'AVG_{key}'] = round(average, 4)
    return result


def extract_json_with_llm(all_metrics, text, judge_model_id, cfg):
    metrics_entries = [f'            "{metric}": <int>' for metric in all_metrics]
    metrics_string = ",\n".join(metrics_entries)

    prompt = f"""## Instruction
Extract and return the JSON object from the given text that matches the specified JSON schema. The schema is:
```json
{{
    "scores": {{
{metrics_string}
            }}
}}
```
## Text
{text}

Provide your response immediately without any preamble or additional information.
            """
    resp = run_inference(model_name=judge_model_id, prompt_text=prompt, provider_params=cfg, stream=False)
    text = resp['text']
    payload = extract_json_from_text(text)
    if not payload:
        return None
    return payload


def extract_json_from_text(text):
    pattern = re.compile(
        r'\{\s*"scores"\s*:\s*\{\s*(?:[^{}]*?)\s*\}\s*\}',
        re.VERBOSE | re.DOTALL
    )
    match = pattern.search(text)
    if match:
        json_text = match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            print("Found block but failed to parse JSON:", e)
            return None
    else:
        print("No matching JSON block found.")
        return None


def extract_json_response(all_metrics, text, judge_model_id, cfg):
    payload = extract_json_from_text(text)
    if not payload:
        payload = extract_json_with_llm(all_metrics, text, judge_model_id, cfg)
    return payload


def llm_judge_template(all_metrics,
                       task_types,
                       task_criteria,
                       prompt,
                       model_response,
                       golden_answer
                       ):
    metrics_list = "\n".join(f"- {m}" for m in all_metrics)
    metrics_entries = [f'            "{metric}": <int>' for metric in all_metrics]
    metrics_string = ",\n".join(metrics_entries)
    return f"""
    ## You are an expert evaluator.  
    # Task: {task_types}

    # Task description: {task_criteria}

    # Original Prompt:
    {prompt}

    # Model Response:
    {model_response}

    # Golden (Reference) Response:
    {golden_answer}

    # Please evaluate the model response on the following metrics:
    {metrics_list}

    # For each metric, assign an integer score from 1 (worst) to 5 (best).

    ## IMPORTANT: **Output JSON only** in this format:
    ```json
    {{
      "scores": {{
{metrics_string}
      }}
    }}
    ```
    """.strip()


# Define which exceptions should trigger a retry
RETRYABLE_EXCEPTIONS = (

    RateLimitError,
    ServiceUnavailableError,
    APIConnectionError,
    APIError,
    requests.exceptions.RequestException,
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError
)


# Create a class to track retry counts
class RetryTracker:
    def __init__(self):
        self.attempts = 0
        self.had_300_second_wait = False

    def increment(self, retry_state):
        self.attempts = retry_state.attempt_number
        wait_time = retry_state.next_action.sleep if retry_state.next_action else 0
        logger.info(f"Retry attempt {self.attempts}, sleeping for {wait_time} seconds")
        
        # If we're about to wait 300 seconds and already had one 300s wait, stop retrying
        if wait_time >= 300:
            if self.had_300_second_wait:
                logger.info("Already waited 300 seconds once, stopping retries")
                raise Exception("Max wait time reached - stopping after one 300-second retry")
            self.had_300_second_wait = True


# Retry decorator with exponential backoff
def _call_llm_with_retry(model_name, messages, provider_params, retry_tracker, stream):
    """Wrapper function to call LLM with retry logic"""

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        wait=wait_exponential(multiplier=2, min=1, max=300),  # Start at 1s, exponentially increase, max 60s per attempt
        stop=stop_after_delay(300),  # Total retry time of 5 minutes
        before_sleep=retry_tracker.increment
    )
    def _api_call():
        try:
            time_ = time.time()
            completed = completion(
                model=model_name,
                messages=messages,
                stream=stream,
                **provider_params
            )
            return completed, time_
        except BadRequestError as e:
            error_msg = str(e)
            has_image_content = any(
                isinstance(msg.get('content'), list) and
                any(part.get('type') == 'image_url' for part in msg.get('content', []))
                for msg in messages if isinstance(msg, dict)
            )

            if has_image_content and ("doesn't support the image content block" in error_msg or
                                      "image content block" in error_msg or
                                      "vision" in error_msg.lower() or
                                      "multimodal" in error_msg.lower()):
                logger.error(f"Model {model_name} does not support vision/image inputs: {error_msg}")
                # Create a more informative error message and don't retry
                raise
            else:
                # Other BadRequestErrors should not be retried either
                logger.error(f"BadRequestError (non-retryable): {error_msg}")
                raise
        except RETRYABLE_EXCEPTIONS as e:
            logger.warning(f"Retryable error occurred: {str(e)}")
            # Add jitter to avoid thundering herd
            jitter = random.uniform(0, 3)
            time.sleep(jitter)
            raise  # Re-raise for the retry decorator to catch
        except Exception as e:
            logger.error(f"Non-retryable error calling LLM: {str(e)}")
            raise

    return _api_call()


def encode_image(image_path):
    """Encode a local image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def validate_image_url(url, timeout=10):
    """
    Validate that a web URL is accessible and points to an image.

    Args:
        url: The URL to validate
        timeout: Request timeout in seconds

    Returns:
        bool: True if URL is valid and accessible

    Raises:
        ValueError: If URL is not accessible or not an image
    """
    try:
        logger.debug(f"Validating image URL: {url}")
        response = requests.head(url, timeout=timeout, allow_redirects=True)

        # Check if request was successful
        if response.status_code != 200:
            raise ValueError(f"URL returned status code {response.status_code}")

        # Check Content-Type header if available
        content_type = response.headers.get('Content-Type', '')
        if content_type and not content_type.startswith(('image/', 'application/octet-stream')):
            logger.warning(f"URL may not be an image. Content-Type: {content_type}")

        logger.debug(f"URL validation successful for: {url}")
        return True

    except requests.exceptions.Timeout:
        raise ValueError(f"URL request timed out after {timeout} seconds")
    except requests.exceptions.ConnectionError:
        raise ValueError(f"Failed to connect to URL: {url}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error accessing URL: {str(e)}")


def validate_local_image(file_path):
    """
    Validate that a local file exists and is a supported image format.

    Args:
        file_path: Path to the local image file

    Returns:
        str: The file extension (without dot)

    Raises:
        ValueError: If file doesn't exist or has unsupported format
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise ValueError(f"Image file not found: {file_path}")

    # Check if it's a file (not directory)
    if not os.path.isfile(file_path):
        raise ValueError(f"Path is not a file: {file_path}")

    # Check file extension
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension.startswith('.'):
        file_extension = file_extension[1:]

    supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    if file_extension not in supported_formats:
        raise ValueError(
            f"Unsupported image format: {file_extension}. Supported formats: {', '.join(supported_formats)}")

    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        raise ValueError(f"Image file is not readable: {file_path}")

    # Check file size (warn if too large)
    file_size = os.path.getsize(file_path)
    max_size_mb = 20
    if file_size > max_size_mb * 1024 * 1024:
        logger.warning(f"Image file is large ({file_size / 1024 / 1024:.2f} MB): {file_path}")

    logger.debug(f"Local image validation successful: {file_path}")
    return file_extension


def handle_vision(prompt_text, vision_enabled):
    image_path = vision_enabled.strip()

    if not image_path:
        logger.error("Empty image path provided for vision model")
        raise ValueError("Image path cannot be empty when vision is enabled")

    logger.info(f"Processing image for vision model: {image_path}")

    # Check if the image is a web URL using regex
    url_pattern = r'^https?://'

    if re.match(url_pattern, image_path):
        # It's a web URL, validate it's accessible
        logger.debug("Detected web URL for image")
        try:
            validate_image_url(image_path)
            image_url = image_path
            logger.info(f"Successfully validated web image URL: {image_path}")
        except ValueError as e:
            logger.error(f"Failed to validate image URL {image_path}: {e}")
            raise ValueError(f"Invalid or inaccessible image URL: {e}")
    else:
        # It's a local file, validate and encode it
        logger.debug("Detected local file path for image")
        try:
            # Validate the local image file
            file_extension = validate_local_image(image_path)

            # Map common extensions to MIME types
            mime_type_map = {
                'jpg': 'jpeg',
                'jpeg': 'jpeg',
                'png': 'png',
                'gif': 'gif',
                'webp': 'webp',
                'bmp': 'bmp'
            }
            mime_type = mime_type_map.get(file_extension, 'jpeg')

            # Encode the image
            logger.debug(f"Encoding local image file: {image_path}")
            base64_image = encode_image(image_path)
            image_url = f"data:image/{mime_type};base64,{base64_image}"
            logger.info(f"Successfully encoded local image: {image_path} (size: {len(base64_image)} bytes)")

        except ValueError as e:
            logger.error(f"Image validation failed for {image_path}: {e}")
            raise
        except IOError as e:
            logger.error(f"Failed to read image file {image_path}: {e}")
            raise ValueError(f"Failed to read image file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing image {image_path}: {e}")
            raise ValueError(f"Failed to process image file: {e}")

    # Create message for vision model with image and text
    image_content = {
        "type": "image_url",
        "image_url": {
            "url": image_url
        }
    }
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}, image_content]}]
    logger.debug("Created multimodal message with image and text")
    return messages


# Run streaming inference and collect metrics
def run_inference(model_name: str,
                  prompt_text: str,
                  input_cost: float = 0.00001,
                  output_cost: float = 0.00001,
                  provider_params: dict = dict,
                  stream: bool = True,
                  vision_enabled: str = None):
    # Concatenate user prompt for token counting
    if vision_enabled:
        messages = handle_vision(prompt_text, vision_enabled)
    else:
        messages = [{"content": prompt_text, "role": "user"}]
    response_chunks = []
    first = True
    # Create a retry tracker
    retry_tracker = RetryTracker()

    try:
        if 'gemini' in model_name:
            os.environ['GEMINI_API_KEY'] = provider_params['api_key']
            del provider_params['api_key']
            # Use the retry wrapper for the API call
        payload, start_time = _call_llm_with_retry(
            model_name=model_name,
            messages=messages,
            provider_params=provider_params,
            retry_tracker=retry_tracker,
            stream=stream
        )
        if not stream:
            response = dict()
            response["text"] = payload.choices[0].message.content
            response['outputTokens'] = payload.model_extra['usage']['completion_tokens']
            response['inputTokens'] = payload.model_extra['usage']['prompt_tokens']
            return response
        else:
            time_to_first_token = 0
            for chunk in payload:
                if first:
                    time_to_first_token = time.time() - start_time
                    first = False

                # Handle potential None or malformed chunks
                if not chunk or not hasattr(chunk, 'choices') or len(chunk.choices) == 0:
                    logger.warning("Received invalid chunk from API")
                    continue

                delta = chunk.choices[0].delta.get("content", "")
                if delta:
                    response_chunks.append(delta)

            end = time.time()
            time_to_last_byte = round(end - start_time, 4)
            total_runtime = end - start_time
            full_response = "".join(response_chunks)

            # Token counting with error handling
            try:
                counter_id = model_name.replace('converse/', '')  # Converse is needed for inference only
                output_tokens = token_counter(model=counter_id, messages=[{"user": "role", "content": full_response}])
                input_tokens = token_counter(model=counter_id, messages=[{"user": "role", "content": prompt_text}])
            except Exception as e:
                logger.error(f"Error counting tokens: {str(e)}")
                output_tokens = 0.0000001
                input_tokens = 0.0000001

            tokens_per_sec = output_tokens / total_runtime if total_runtime > 0 else 0
            tot_input_cost = input_tokens * (input_cost / 1000)
            tot_output_cost = output_tokens * (output_cost / 1000)

            return {
                "model_response": full_response,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_runtime": total_runtime,
                "time_to_first_byte": time_to_first_token,
                "time_to_last_byte": time_to_last_byte,
                "throughput_tps": tokens_per_sec,
                "total_cost": tot_output_cost + tot_input_cost,
                "retry_count": retry_tracker.attempts
            }

    except Exception as e:
        logger.error(f"Error during inference: {type(e).__name__}: {str(e)}")
        # Return partial results if available, or error information
        if response_chunks:
            partial_response = "".join(response_chunks)
            logger.info(f"Returning partial response of length {len(partial_response)}")
            return {
                "model_response": partial_response,
                "error": str(e),
                "error_type": type(e).__name__,
                "partial_result": True,
                "retry_count": retry_tracker.attempts  # Include the retry count even in error case
            }
        else:
            raise RuntimeError(f"Inference failed after {retry_tracker.attempts} retries: {str(e)}")


def report_summary_template(models, evaluations):
    models_str = '\n'.join(models)
    return f"""
## Task
Your task is to summarize the key findings from the provided LLM model/s evaluation dataset in a single, objective paragraph. The dataset contains information on performance (speed, tokens per minute, throttle errors), accuracy, and cost metrics across one-to-many #Task/s#.

## Guidelines
1. Read through the dataset carefully to understand the different metrics and their values.
2. Identify the main points and notable observations related to performance, accuracy, and cost, but do not reference analysis we do not have data for.
3. Write a concise paragraph summarizing these key findings using neutral, fact-based language.
4. Avoid subjective statements or judgments about what constitutes good/bad performance, reliability, or cost-effectiveness.
5. Condenses the entire data into a concise overview, highlighting key findings, methodologies, and conclusions.
6. Use plain language, when data uses explicit technical terms like "fat tails" use instead language like "highly likely to vary"
7. Use HTML tags "<b><i>TEXT</b></i>" to highlight #Model Name# and #Task Name# across your resonse

## Models:
{models_str}

## Dataset
{evaluations}

Please provide your summary paragraph immediately after reading the dataset, without any preamble.
    """.strip()


def convert_scientific_to_decimal(df):
    """
    Converts numeric columns with scientific notation to decimal representation.

    Parameters:
        df (pandas.DataFrame): Input dataframe

    Returns:
        pandas.DataFrame: DataFrame with converted values
    """
    # Create a copy of the dataframe to avoid modifying the original
    result_df = df.copy()
    # Iterate through columns
    for column in result_df.columns:
        try:
            result_df[column] = result_df[column].apply(lambda x: f"{x:.6f}" if x < 0.01 else x)
        except:
            pass

    return result_df


def check_model_access(provider_params, model_id):
    """
    Check if we have access to invoke a specific model
    """
    try:
        messages = [{"content": 'HI', "role": "user"}]
        completed = completion(
            model=model_id,
            messages=messages,
            stream=True,
            **provider_params
        )

        # If we get a response without error, access is granted
        return 'granted'

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'AccessDeniedException':
            return 'denied'
        elif error_code == 'ValidationException':
            return 'denied'
        elif error_code == 'ThrottlingException':
            return 'granted'
        else:
            return 'denied'
    except Exception:
        return 'denied'


