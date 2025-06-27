import json
import os
from pathlib import Path

# Project root directory
# Calculate project root - go up one level from the src directory
PROJECT_ROOT = Path(os.path.abspath(__file__)).parents[3]

# Default directories - using absolute paths
DEFAULT_OUTPUT_DIR = str(PROJECT_ROOT / "benchmark-results")
DEFAULT_PROMPT_EVAL_DIR = str(PROJECT_ROOT / "prompt-evaluations")
CONFIG_DIR = str(PROJECT_ROOT / "default-config")
LOGS_DIR = str(PROJECT_ROOT / "logs")
STATUS_FILES_DIR = str(PROJECT_ROOT / "logs")  # Status files now saved in logs directory

def get_config_path(filename):
    """Get absolute path to a config file"""
    return os.path.join(CONFIG_DIR, filename)

def generate_model_info(filename='models_profiles.jsonl'):
    """
    Load model information from config files using project-relative paths
    """
    file_path = get_config_path(filename)
    try:
        # Initialize empty structures
        bedrock_models = []
        openai_models = []
        cost_map = {}
        
        # Read and process the JSONL file
        with open(file_path, 'r') as file:
            for line in file:
                try:
                    data = json.loads(line)
                    model_id = data['model_id']
                    region = None
                    if 'region' in data and 'bedrock/' in model_id:
                        region = data['region']
                    elif 'region' in data and 'bedrock/' not in model_id:
                        region = "N/A"
                    # Categorize models based on prefix
                    if 'bedrock/' not in model_id:
                        openai_models.append([model_id, region])
                    else:
                        bedrock_models.append([model_id, region])

                    # Build cost map entry
                    # Handle the case where 'input_token_cost' might be misspelled as 'input'
                    input_cost_key = 'input_token_cost' if 'input_token_cost' in data else ('input_cost_per_1k' if 'input_cost_per_1k' in data else 'input')
                    output_token_key = 'output_token_cost' if 'output_token_cost' in data else ('output_cost_per_1k' if 'output_cost_per_1k' in data else 'output')
                    cost_map[model_id] = {
                        "input": data[input_cost_key],
                        "output": data[output_token_key]
                    }
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse line: {line}")
                except KeyError as e:
                    print(f"Warning: Missing key in data: {e} for line: {line}")

        # Return the generated structures
        return {
            "DEFAULT_BEDROCK_MODELS": bedrock_models,
            "DEFAULT_OPENAI_MODELS": openai_models,
            "DEFAULT_COST_MAP": cost_map
        }

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return {"DEFAULT_BEDROCK_MODELS": [], "DEFAULT_OPENAI_MODELS": [], "DEFAULT_COST_MAP": {}}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"DEFAULT_BEDROCK_MODELS": [], "DEFAULT_OPENAI_MODELS": [], "DEFAULT_COST_MAP": {}}

"""Constants for the Streamlit dashboard."""

# App title and information
APP_TITLE = "LLM Benchmarking Dashboard"
SIDEBAR_INFO = """
### LLM Benchmarking Dashboard

This dashboard provides an intuitive interface for:
- Setting up evaluations from CSV files
- Configuring model parameters
- Selecting judge models
- Monitoring evaluation progress
- Viewing results and reports

For more details, see the [README.md](https://github.com/aws-samples/amazon-bedrock-samples/tree/360-eval/poc-to-prod/360-eval)
"""

# Evaluation parameters
DEFAULT_PARALLEL_CALLS = 4
DEFAULT_INVOCATIONS_PER_SCENARIO = 3
DEFAULT_SLEEP_BETWEEN_INVOCATIONS = 3
DEFAULT_EXPERIMENT_COUNTS = 1
DEFAULT_TEMPERATURE_VARIATIONS = 0

# Default model regions
AWS_REGIONS = [
        # North America
        'us-east-1',  # N. Virginia
        'us-east-2',  # Ohio
        'us-west-1',  # N. California
        'us-west-2',  # Oregon

        # Africa
        'af-south-1',  # Cape Town

        # Asia Pacific
        'ap-east-1',  # Hong Kong
        'ap-south-2',  # Hyderabad
        'ap-southeast-3',  # Jakarta
        'ap-southeast-5',  # Malaysia
        'ap-southeast-4',  # Melbourne
        'ap-south-1',  # Mumbai
        'ap-northeast-3',  # Osaka
        'ap-northeast-2',  # Seoul
        'ap-southeast-1',  # Singapore
        'ap-southeast-2',  # Sydney
        'ap-southeast-7',  # Thailand
        'ap-northeast-1',  # Tokyo

        # Canada
        'ca-central-1',  # Central
        'ca-west-1',  # Calgary

        # Europe
        'eu-central-1',  # Frankfurt
        'eu-west-1',  # Ireland
        'eu-west-2',  # London
        'eu-south-1',  # Milan
        'eu-west-3',  # Paris
        'eu-south-2',  # Spain
        'eu-north-1',  # Stockholm
        'eu-central-2',  # Zurich

        # Israel
        'il-central-1',  # Tel Aviv

        # Mexico
        'mx-central-1',  # Central

        # Middle East
        'me-south-1',  # Bahrain
        'me-central-1',  # UAE

        # South America
        'sa-east-1',  # São Paulo

        # AWS GovCloud
        'us-gov-east-1',  # US-East
        'us-gov-west-1',  # US-West
    ]


# Load model data
defaults = generate_model_info('models_profiles.jsonl')
DEFAULT_BEDROCK_MODELS = defaults['DEFAULT_BEDROCK_MODELS']
DEFAULT_OPENAI_MODELS = defaults['DEFAULT_OPENAI_MODELS']
DEFAULT_COST_MAP = defaults['DEFAULT_COST_MAP']

# Load judge data
judges = generate_model_info('judge_profiles.jsonl')
DEFAULT_JUDGES = judges['DEFAULT_BEDROCK_MODELS']
DEFAULT_JUDGES_COST = judges['DEFAULT_COST_MAP']
