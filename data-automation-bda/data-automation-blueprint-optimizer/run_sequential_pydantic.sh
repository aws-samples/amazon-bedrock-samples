#!/bin/bash

# Run the sequential optimization with Pydantic models
# Usage: ./run_sequential_pydantic.sh [--threshold 0.8] [--use-doc] [--use-template] [--model MODEL_ID] [--max-iterations N] [--clean]
#
# This script runs the BDA optimization process with the specified parameters.
# It will create the necessary directories if they don't exist.

# Function to clean up child processes when the script exits
cleanup() {
  echo "Cleaning up child processes..."
  # Kill all child processes
  pkill -P $$
  # Also try to kill any related processes
  pkill -f "app_sequential_pydantic.py"
  exit 0
}

# Set up trap to catch script termination
trap cleanup EXIT INT TERM

# Default values
THRESHOLD=0.8
USE_DOC=""
USE_TEMPLATE=""
MODEL="anthropic.claude-3-haiku-20240307-v1:0"
MAX_ITERATIONS=2
CLEAN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --threshold)
      THRESHOLD="$2"
      shift 2
      ;;
    --use-doc)
      USE_DOC="--use-doc"
      shift
      ;;
    --use-template)
      USE_TEMPLATE="--use-template"
      shift
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --max-iterations)
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --clean)
      CLEAN=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create necessary directories if they don't exist
echo "Setting up directories..."
mkdir -p output
mkdir -p output/schemas output/reports output/inputs output/bda_output output/html_output output/merged_df_output output/similarity_output logs

# Clean up if requested
if [ "$CLEAN" = true ]; then
  echo "Cleaning up previous runs..."
  python3 "$SCRIPT_DIR/cleanup.py"
fi

# Check if input file exists
if [ ! -f "input_0.json" ]; then
  echo "Error: input_0.json not found"
  echo "Please create an input_0.json file with your configuration."
  echo "See the README.md and DETAILED_GUIDE.md for more information."
  exit 1
fi

# Run the optimization
echo "Running sequential optimization with threshold $THRESHOLD"
if [ -n "$USE_DOC" ]; then
  echo "Using document-based strategy as fallback"
fi
if [ -n "$USE_TEMPLATE" ]; then
  echo "Using template-based instruction generation"
else
  echo "Using LLM-based instruction generation with model: $MODEL"
fi
echo "Logs will be written to the logs directory"

# Change to the script directory and run the Python script
cd "$SCRIPT_DIR"
python3 app_sequential_pydantic.py input_0.json --threshold $THRESHOLD $USE_DOC $USE_TEMPLATE --model "$MODEL" --max-iterations $MAX_ITERATIONS
