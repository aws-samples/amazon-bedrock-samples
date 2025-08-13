"""Utilities for processing CSV files in the Streamlit dashboard."""

import pandas as pd
import json
import os
from pathlib import Path
from uuid import uuid4
import streamlit as st

def read_csv_file(uploaded_file):
    """Read an uploaded CSV file and return a pandas DataFrame."""
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
        return None


def get_csv_columns(df):
    """Get a list of column names from a DataFrame."""
    if df is not None:
        return df.columns.tolist()
    return []


def preview_csv_data(df, max_rows=5):
    """Return a preview of the CSV data."""
    if df is not None:
        return df.head(max_rows)
    return None


def convert_to_jsonl(df, prompt_col, golden_answer_col, task_type, task_criteria, output_dir, name, temperature=0.7, user_defined_metrics="", vision_enabled=False, image_column=None):
    """
    Convert CSV data to JSONL format for LLM benchmarking.
    
    Args:
        df: Pandas DataFrame with CSV data
        prompt_col: Column name for prompts
        golden_answer_col: Column name for golden answers
        task_type: Type of task for evaluation
        task_criteria: Criteria for evaluating the task
        output_dir: Directory to save the JSONL file
        name: Name for the evaluation
        
    Returns:
        Path to the created JSONL file
    """
    if df is None:
        st.error("Invalid CSV data")
        return None
    
    if prompt_col is None or golden_answer_col is None:
        st.error("Please select both prompt and golden answer columns")
        return None
    
    # Check vision model requirements
    if vision_enabled and image_column is None:
        st.error("Vision model enabled but no image column selected")
        return None
        
    all_columns = df.columns.tolist()
    if prompt_col not in all_columns or golden_answer_col not in all_columns:
        # Check if this is potentially a merged dataframe with different column names
        has_prompt_rows = False
        has_answer_rows = False
        
        for col in all_columns:
            if col == prompt_col or "prompt" in col.lower():
                has_prompt_rows = True
            if col == golden_answer_col or "answer" in col.lower() or "golden" in col.lower():
                has_answer_rows = True
                
        if not (has_prompt_rows and has_answer_rows):
            st.error(f"Selected columns not found in CSV: {prompt_col}, {golden_answer_col}")
            return None

    # Use the absolute prompt-evaluations directory path from constants
    from ..utils.constants import PROJECT_ROOT, DEFAULT_PROMPT_EVAL_DIR
    prompt_eval_dir = Path(DEFAULT_PROMPT_EVAL_DIR)
    os.makedirs(prompt_eval_dir, exist_ok=True)
    
    # Generate JSONL file path - use a unique name for merged evaluations
    if "merged" in name:
        unique_suffix = str(uuid4()).split('-')[0]
        jsonl_path = prompt_eval_dir / f"{name}_{unique_suffix}.jsonl"
    else:
        jsonl_path = prompt_eval_dir / f"{name}.jsonl"
    
    # Convert DataFrame to JSONL format
    jsonl_data = []
    for _, row in df.iterrows():
        # Skip rows that don't have the necessary columns
        if prompt_col not in row or golden_answer_col not in row:
            continue
            
        # Handle NaN values
        prompt = row[prompt_col]
        answer = row[golden_answer_col]
        if pd.isna(prompt) or pd.isna(answer):
            continue
            
        entry = {
            "text_prompt": prompt,
            "expected_output_tokens": 4500,  # Default value
            "task": {
                "task_type": task_type,
                "task_criteria": task_criteria
            },
            "golden_answer": answer,
            "temperature": temperature,
            "user_defined_metrics": user_defined_metrics
        }
        
        # Add image data directly using the column name (like prompt and golden_answer)
        if vision_enabled and image_column and image_column in row:
            image_data = row[image_column]
            if not pd.isna(image_data):
                entry[image_column] = image_data
        jsonl_data.append(entry)
    
    # Write to JSONL file
    try:
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for entry in jsonl_data:
                f.write(json.dumps(entry) + '\n')
    except IOError as e:
        raise Exception(f"Failed to write JSONL file to {jsonl_path}: {e}")
    
    # Return both the absolute path and the filename for CLI compatibility
    return str(jsonl_path)


def create_model_profiles_jsonl(models, output_dir, custom_filename=None):
    """
    Create a JSONL file with model profiles.
    
    Args:
        models: List of dictionaries with model configuration
        output_dir: Directory to save the JSONL file
        
    Returns:
        Path to the created JSONL file
    """
    # Use the absolute prompt-evaluations directory path from constants
    from ..utils.constants import PROJECT_ROOT, DEFAULT_PROMPT_EVAL_DIR
    prompt_eval_dir = Path(DEFAULT_PROMPT_EVAL_DIR)
    os.makedirs(prompt_eval_dir, exist_ok=True)
    
    jsonl_path = prompt_eval_dir / (custom_filename or "model_profiles.jsonl")
    
    try:
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for model in models:
                entry = {
                    "model_id": model["id"],
                    "region": model["region"],
                    "inference_profile": "standard",
                    "input_token_cost": model["input_cost"],
                    "output_token_cost": model["output_cost"]
                }
                f.write(json.dumps(entry) + '\n')
    except IOError as e:
        raise Exception(f"Failed to write model profiles to {jsonl_path}: {e}")
    
    return str(jsonl_path)


def create_judge_profiles_jsonl(judges, output_dir, custom_filename=None):
    """
    Create a JSONL file with judge model profiles.
    
    Args:
        judges: List of dictionaries with judge model configuration
        output_dir: Directory to save the JSONL file
        
    Returns:
        Path to the created JSONL file
    """
    # Use the absolute prompt-evaluations directory path from constants
    from ..utils.constants import PROJECT_ROOT, DEFAULT_PROMPT_EVAL_DIR
    prompt_eval_dir = Path(DEFAULT_PROMPT_EVAL_DIR)
    os.makedirs(prompt_eval_dir, exist_ok=True)
    
    jsonl_path = prompt_eval_dir / (custom_filename or "judge_profiles.jsonl")
    
    try:
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for judge in judges:
                entry = {
                    "model_id": judge["id"],
                    "region": judge["region"],
                    "input_cost_per_1k": judge["input_cost"],  # Field is already 1k
                    "output_cost_per_1k": judge["output_cost"]  # Field is already 1k
                }
                f.write(json.dumps(entry) + '\n')
    except IOError as e:
        raise Exception(f"Failed to write judge profiles to {jsonl_path}: {e}")
    
    return str(jsonl_path)