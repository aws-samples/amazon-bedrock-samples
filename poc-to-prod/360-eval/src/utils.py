import pytz
import datetime
import boto3
import json
import tiktoken
import re
import time
import os
import random
import logging
import requests.exceptions
from tenacity import retry, stop_after_delay, wait_exponential, retry_if_exception_type
from litellm import completion, RateLimitError, ServiceUnavailableError, APIError, APIConnectionError
from litellm import token_counter
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)


# ----------------------------------------
# Request Builders
# ----------------------------------------
def get_body(prompt, max_tokens, temperature, top_p):
    sys = ""
    body = [{"role": "user", "content": [{"text": f"{sys}\n##USER:{prompt}"}]}]
    cfg = {"maxTokens": max_tokens, "temperature": temperature, "topP": top_p}
    return body, cfg


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


def get_bedrock_client(region):
    cfg = Config(retries={"max_attempts": 10})
    return boto3.client("bedrock-runtime", region_name=region, config=cfg)


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
    Exception,
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

    def increment(self, retry_state):
        self.attempts = retry_state.attempt_number
        logger.info(f"Retry attempt {self.attempts}, sleeping for {retry_state.next_action.sleep} seconds")


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
        # Create message for vision model with image and text
        image_content = {
            "type": "image_url",
            "image_url": {
                "url": vision_enabled.strip()
            }
        }
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}, image_content]}]
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
                counter_id = model_name.replace('converse/', '') # Converse is needed for inference only
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