"""Session state management for the Streamlit dashboard."""

import streamlit as st
import uuid
import time
from datetime import datetime
import os
from .constants import (
    DEFAULT_OUTPUT_DIR, DEFAULT_PARALLEL_CALLS, 
    DEFAULT_INVOCATIONS_PER_SCENARIO, DEFAULT_SLEEP_BETWEEN_INVOCATIONS,
    DEFAULT_EXPERIMENT_COUNTS, DEFAULT_TEMPERATURE_VARIATIONS, STATUS_FILES_DIR
)

def initialize_session_state():
    """Initialize all session state variables with default values."""
    # Initialize evaluation settings
    if "evaluations" not in st.session_state:
        st.session_state.evaluations = []
    
    if "active_evaluations" not in st.session_state:
        st.session_state.active_evaluations = []
    
    if "completed_evaluations" not in st.session_state:
        st.session_state.completed_evaluations = []
    
    # Load evaluations from status files for persistence
    load_evaluations_from_files()
    
    if "current_evaluation_config" not in st.session_state:
        st.session_state.current_evaluation_config = {
            "id": None,
            "name": f"Benchmark-{datetime.now().strftime("%Y%m%d%H%M%S")}",
            "csv_data": None,
            "csv_file_name": None,
            "prompt_column": None,
            "golden_answer_column": None,
            "task_type": "",  # Keep for backward compatibility
            "task_criteria": "",  # Keep for backward compatibility
            "task_evaluations": [{"task_type": "", "task_criteria": "", "temperature": 0.7, "user_defined_metrics": ""}],
            "output_dir": DEFAULT_OUTPUT_DIR,
            "parallel_calls": DEFAULT_PARALLEL_CALLS,
            "invocations_per_scenario": DEFAULT_INVOCATIONS_PER_SCENARIO,
            "sleep_between_invocations": DEFAULT_SLEEP_BETWEEN_INVOCATIONS,
            "experiment_counts": DEFAULT_EXPERIMENT_COUNTS,
            "temperature_variations": DEFAULT_TEMPERATURE_VARIATIONS,
            "selected_models": [],
            "judge_models": [],
            "user_defined_metrics": "",
            "status": "configuring",
            "progress": 0,
            "created_at": None,
            "updated_at": None,
            "results": None
        }
    
    # Ensure output directory exists
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)


def create_new_evaluation():
    """Create a new evaluation configuration with default values."""
    return {
        "id": str(uuid.uuid4()),
        "name": f"Benchmark-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "csv_data": None,
        "csv_file_name": None,
        "prompt_column": None,
        "golden_answer_column": None,
        "task_type": "",  # Keep for backward compatibility
        "task_criteria": "",  # Keep for backward compatibility
        "task_evaluations": [{"task_type": "", "task_criteria": "", "temperature": 0.7, "user_defined_metrics": ""}],
        "output_dir": DEFAULT_OUTPUT_DIR,
        "parallel_calls": DEFAULT_PARALLEL_CALLS,
        "invocations_per_scenario": DEFAULT_INVOCATIONS_PER_SCENARIO,
        "sleep_between_invocations": DEFAULT_SLEEP_BETWEEN_INVOCATIONS,
        "experiment_counts": DEFAULT_EXPERIMENT_COUNTS,
        "temperature_variations": DEFAULT_TEMPERATURE_VARIATIONS,
        "selected_models": [],
        "judge_models": [],
        "user_defined_metrics": "",
        "status": "configuring",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "results": None
    }


def save_current_evaluation():
    """Save the current evaluation configuration to the list of evaluations.
    If multiple task evaluations are configured, creates separate evaluations for each."""
    # Debug current state
    print(f"Current session state before saving: {len(st.session_state.evaluations)} evaluations")
    
    # Get task evaluations, defaulting to single task if not present
    task_evaluations = st.session_state.current_evaluation_config.get("task_evaluations", 
        [{"task_type": st.session_state.current_evaluation_config.get("task_type", ""), 
          "task_criteria": st.session_state.current_evaluation_config.get("task_criteria", "")}])
    
    base_name = st.session_state.current_evaluation_config["name"]
    
    # Create separate evaluations for each task evaluation
    for i, task_eval in enumerate(task_evaluations):
        if st.session_state.current_evaluation_config["id"] is None:
            # This is a new evaluation
            new_eval = st.session_state.current_evaluation_config.copy()
            new_eval["id"] = str(uuid.uuid4())
            new_eval["created_at"] = datetime.now().isoformat()
            new_eval["updated_at"] = datetime.now().isoformat()
            new_eval["status"] = "configuring"  # Ensure status is set
            
            # Set individual task type, criteria, temperature, and user metrics for this evaluation
            new_eval["task_type"] = task_eval["task_type"]
            new_eval["task_criteria"] = task_eval["task_criteria"]
            new_eval["temperature"] = task_eval.get("temperature", 0.7)
            new_eval["user_defined_metrics"] = task_eval.get("user_defined_metrics", "")
            
            # Update evaluation name with index if multiple tasks
            if len(task_evaluations) > 1:
                new_eval["name"] = f"{base_name}_{i+1}"
            else:
                new_eval["name"] = base_name
            
            # Remove task_evaluations array from individual evaluation (not needed)
            if "task_evaluations" in new_eval:
                del new_eval["task_evaluations"]
            
            # Add to evaluations list
            st.session_state.evaluations.append(new_eval)
            print(f"Added new evaluation with ID: {new_eval['id']}, Name: {new_eval['name']}")
            
            # Save configuring evaluation to disk for persistence
            save_configuring_evaluation_to_disk(new_eval)
            
        else:
            # This is an update to an existing evaluation - only update if single task
            if len(task_evaluations) == 1:
                eval_id = st.session_state.current_evaluation_config["id"]
                updated = False
                
                # Update existing evaluation
                for j, eval_config in enumerate(st.session_state.evaluations):
                    if eval_config["id"] == eval_id:
                        updated_eval = st.session_state.current_evaluation_config.copy()
                        updated_eval["updated_at"] = datetime.now().isoformat()
                        updated_eval["task_type"] = task_eval["task_type"]
                        updated_eval["task_criteria"] = task_eval["task_criteria"]
                        updated_eval["temperature"] = task_eval.get("temperature", 0.7)
                        updated_eval["user_defined_metrics"] = task_eval.get("user_defined_metrics", "")
                        
                        # Remove task_evaluations array from individual evaluation
                        if "task_evaluations" in updated_eval:
                            del updated_eval["task_evaluations"]
                        
                        st.session_state.evaluations[j] = updated_eval
                        print(f"Updated evaluation with ID: {eval_id}, Name: {st.session_state.evaluations[j]['name']}")
                        updated = True
                        
                        # Save updated configuring evaluation to disk
                        save_configuring_evaluation_to_disk(updated_eval)
                        break
                        
                if not updated:
                    # If not found (unusual case), add as new
                    print(f"Evaluation with ID {eval_id} not found in list, adding as new")
                    new_eval = st.session_state.current_evaluation_config.copy()
                    new_eval["updated_at"] = datetime.now().isoformat()
                    new_eval["task_type"] = task_eval["task_type"]
                    new_eval["task_criteria"] = task_eval["task_criteria"]
                    new_eval["temperature"] = task_eval.get("temperature", 0.7)
                    new_eval["user_defined_metrics"] = task_eval.get("user_defined_metrics", "")
                    
                    # Remove task_evaluations array from individual evaluation
                    if "task_evaluations" in new_eval:
                        del new_eval["task_evaluations"]
                    
                    st.session_state.evaluations.append(new_eval)
                    
                    # Save configuring evaluation to disk for persistence
                    save_configuring_evaluation_to_disk(new_eval)
            else:
                print("Cannot update evaluation with multiple tasks - this should create new evaluations instead")
    
    print(f"Session state after adding: {len(st.session_state.evaluations)} evaluations")
    
    # Reset current config for next evaluation
    reset_current_evaluation()


def reset_current_evaluation():
    """Reset the current evaluation configuration to default values."""
    st.session_state.current_evaluation_config = create_new_evaluation()


def save_configuring_evaluation_to_disk(eval_config):
    """Save a configuring evaluation to disk for persistence across page refreshes."""
    try:
        import json
        from pathlib import Path
        
        # Create status file for configuring evaluation
        status_dir = Path(STATUS_FILES_DIR)
        status_dir.mkdir(exist_ok=True)
        
        eval_id = eval_config["id"]
        eval_name = eval_config["name"]
        composite_id = f"{eval_id}_{eval_name}"
        status_file = status_dir / f"eval_{composite_id}_status.json"
        
        # Create minimal status data for configuring evaluation
        status_data = {
            "status": "configuring",
            "updated_at": time.time(),
            "progress": 0,
            "evaluation_config": {
                "parallel_calls": eval_config.get("parallel_calls"),
                "invocations_per_scenario": eval_config.get("invocations_per_scenario"),
                "experiment_counts": eval_config.get("experiment_counts"),
                "temperature_variations": eval_config.get("temperature_variations"),
                "user_defined_metrics": eval_config.get("user_defined_metrics"),
                "sleep_between_invocations": eval_config.get("sleep_between_invocations"),
                "task_type": eval_config.get("task_type"),
                "task_criteria": eval_config.get("task_criteria"),
                "temperature": eval_config.get("temperature"),
                "csv_file_name": eval_config.get("csv_file_name")
            },
            # Store models and judges data for configuring evaluations
            "models_data": eval_config.get("selected_models", []),
            "judges_data": eval_config.get("judge_models", [])
        }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
            
        print(f"Saved configuring evaluation to disk: {status_file}")
        
    except Exception as e:
        import logging
        logging.warning(f"Could not save configuring evaluation to disk: {str(e)}")


def delete_evaluation_from_disk(eval_id, eval_name):
    """Delete all files related to an evaluation from disk."""
    try:
        from pathlib import Path
        import logging
        
        deleted_files = []
        composite_id = f"{eval_id}_{eval_name}"
        
        # 1. Delete status files from logs directory
        status_dir = Path(STATUS_FILES_DIR)
        
        # Try composite format first
        status_file = status_dir / f"eval_{composite_id}_status.json"
        if status_file.exists():
            status_file.unlink()
            deleted_files.append(f"Status: {status_file}")
        
        # Try legacy format
        legacy_status_file = status_dir / f"eval_{eval_id}_status.json"
        if legacy_status_file.exists():
            legacy_status_file.unlink()
            deleted_files.append(f"Legacy status: {legacy_status_file}")
        
        # 2. Delete CSV invocation files from benchmark-results directory
        benchmark_results_dir = Path(DEFAULT_OUTPUT_DIR)
        
        # Look for invocation CSV files with various patterns
        csv_patterns = [
            f"invocations_*{composite_id}*.csv",
            f"invocations_*{eval_id}*.csv", 
            f"*{eval_name}*.csv"
        ]
        
        for pattern in csv_patterns:
            csv_files = list(benchmark_results_dir.glob(pattern))
            for csv_file in csv_files:
                csv_file.unlink()
                deleted_files.append(f"CSV: {csv_file}")
        
        # 3. Delete HTML report files
        html_patterns = [
            f"*{composite_id}*.html",
            f"*{eval_id}*.html",
            f"*{eval_name}*.html"
        ]
        
        for pattern in html_patterns:
            html_files = list(benchmark_results_dir.glob(pattern))
            for html_file in html_files:
                html_file.unlink()
                deleted_files.append(f"HTML: {html_file}")
        
        # 4. Delete evaluation report status files
        eval_report_patterns = [
            f"evaluation_report_*{eval_id}*_status.json",
            f"evaluation_report_*{eval_name}*_status.json"
        ]
        
        for pattern in eval_report_patterns:
            report_files = list(benchmark_results_dir.glob(pattern))
            for report_file in report_files:
                report_file.unlink()
                deleted_files.append(f"Report: {report_file}")
        
        # 5. Delete unprocessed error files (in unprocessed subdirectory)
        unprocessed_dir = benchmark_results_dir / "unprocessed"
        if unprocessed_dir.exists():
            unprocessed_patterns = [
                f"unprocessed_*{eval_id[:8]}*.json",  # Use first 8 chars of eval_id
                f"*{composite_id[:16]}*.json"  # Use first 16 chars of composite_id
            ]
            
            for pattern in unprocessed_patterns:
                unprocessed_files = list(unprocessed_dir.glob(pattern))
                for unprocessed_file in unprocessed_files:
                    unprocessed_file.unlink()
                    deleted_files.append(f"Unprocessed: {unprocessed_file}")
        
        # 6. Delete JSONL prompt files from prompt-evaluations directory
        prompt_eval_dir = benchmark_results_dir.parent / "prompt-evaluations"
        if prompt_eval_dir.exists():
            jsonl_patterns = [
                f"{eval_name}.jsonl",
                f"*{composite_id}*.jsonl",
                f"model_profiles_{composite_id}.jsonl",
                f"judge_profiles_{composite_id}.jsonl",
                f"model_profiles_{eval_id}.jsonl",
                f"judge_profiles_{eval_id}.jsonl"
            ]
            
            for pattern in jsonl_patterns:
                jsonl_files = list(prompt_eval_dir.glob(pattern))
                for jsonl_file in jsonl_files:
                    jsonl_file.unlink()
                    deleted_files.append(f"JSONL: {jsonl_file}")
        
        if deleted_files:
            print(f"Deleted {len(deleted_files)} files for evaluation {eval_name}:")
            for file_info in deleted_files:
                print(f"  - {file_info}")
            return True
        else:
            print(f"No files found to delete for evaluation {eval_name}")
            return True  # Still consider it successful if no files found
        
    except Exception as e:
        import logging
        logging.warning(f"Could not delete evaluation files from disk: {str(e)}")
        return False



def update_evaluation_status(eval_id, status, progress=None, error=None, results=None):
    """Update the status of an evaluation with thread-safe error handling."""
    # Make sure session state is initialized
    if "evaluations" not in st.session_state:
        initialize_session_state()
        
    try:
        for i, eval_config in enumerate(st.session_state.evaluations):
            if eval_config["id"] == eval_id:
                st.session_state.evaluations[i]["status"] = status
                st.session_state.evaluations[i]["updated_at"] = datetime.now().isoformat()
                
                if progress is not None:
                    st.session_state.evaluations[i]["progress"] = progress
                    
                if error is not None:
                    st.session_state.evaluations[i]["error"] = error
                    
                if results is not None:
                    st.session_state.evaluations[i]["results"] = results
                
                # Update active and completed lists based on status
                if status == "running":
                    # Remove from active list first to avoid duplicates
                    st.session_state.active_evaluations = [e for e in st.session_state.active_evaluations if e["id"] != eval_id]
                    # Add current state to active list
                    st.session_state.active_evaluations.append(st.session_state.evaluations[i].copy())
                elif status in ["completed", "failed"]:
                    # Remove from active list
                    st.session_state.active_evaluations = [e for e in st.session_state.active_evaluations if e["id"] != eval_id]
                    # Add to completed list if not already there
                    if eval_id not in [e["id"] for e in st.session_state.completed_evaluations]:
                        st.session_state.completed_evaluations.append(st.session_state.evaluations[i].copy())
                    else:
                        # Update existing completed entry
                        for j, completed_eval in enumerate(st.session_state.completed_evaluations):
                            if completed_eval["id"] == eval_id:
                                st.session_state.completed_evaluations[j] = st.session_state.evaluations[i].copy()
                                break
                
                return
    except Exception as e:
        # Handle cases where session state might not be accessible (like in a thread)
        import logging
        logging.warning(f"Could not update session state for evaluation {eval_id}: {str(e)}")
        # Continue - the file-based status will be used instead


def load_evaluations_from_files():
    """Load evaluations from status files using composite naming for easy matching."""
    try:
        import json
        from pathlib import Path
        
        # Get the status files directory (now in logs)
        status_dir = Path(STATUS_FILES_DIR)
        if not status_dir.exists():
            os.makedirs(status_dir, exist_ok=True)
            return
        
        # Find all status files in logs directory
        status_files = list(status_dir.glob("eval_*_status.json"))
        
        # Get existing evaluation IDs to avoid duplicates
        existing_ids = {e["id"] for e in st.session_state.evaluations}
        
        for status_file in status_files:
            try:
                # Extract eval_id from filename
                filename = status_file.stem  # removes .json
                # filename format: eval_{id}_{name}_status or eval_{id}_status
                if filename.startswith("eval_") and filename.endswith("_status"):
                    # Remove "eval_" prefix and "_status" suffix
                    id_part = filename[5:-7]  # Remove "eval_" and "_status"
                    
                    # Split by underscore - first part is always the ID
                    parts = id_part.split("_", 1)
                    eval_id = parts[0]
                    eval_name = parts[1] if len(parts) > 1 else f"Evaluation_{eval_id[:8]}"
                    
                    # Skip if already in session state
                    if eval_id in existing_ids:
                        continue
                    
                    # Read status file
                    with open(status_file, 'r') as f:
                        status_data = json.load(f)
                    
                    # Try to extract task info from JSONL file or status data
                    stored_config = status_data.get("evaluation_config", {})
                    task_info = extract_task_info_from_jsonl_simple(eval_name)
                    
                    # Create evaluation config
                    eval_config = {
                        "id": eval_id,
                        "name": eval_name,
                        "status": status_data.get("status", "unknown"),
                        "progress": status_data.get("progress", 0),
                        "task_type": stored_config.get("task_type") or task_info.get("task_type", "Unknown"),
                        "task_criteria": stored_config.get("task_criteria") or task_info.get("task_criteria", "Unknown"),
                        "created_at": datetime.fromtimestamp(status_data.get("start_time", 0)).isoformat() if status_data.get("start_time") else datetime.now().isoformat(),
                        "updated_at": datetime.fromtimestamp(status_data.get("updated_at", 0)).isoformat() if status_data.get("updated_at") else datetime.now().isoformat(),
                        "start_time": status_data.get("start_time"),
                        "end_time": status_data.get("end_time"),
                        "duration": status_data.get("duration"),
                        "error": status_data.get("error"),
                        "results": status_data.get("results"),
                        "logs_dir": status_data.get("logs_dir"),
                        "output_dir": str(DEFAULT_OUTPUT_DIR),
                        "selected_models": extract_models_from_profile_files(eval_id, eval_name),
                        "judge_models": extract_judges_from_profile_files(eval_id, eval_name),
                        # Use stored config values or reasonable defaults
                        "parallel_calls": stored_config.get("parallel_calls", 4),
                        "invocations_per_scenario": stored_config.get("invocations_per_scenario", 1),
                        "sleep_between_invocations": stored_config.get("sleep_between_invocations", 3),
                        "experiment_counts": stored_config.get("experiment_counts", 1),
                        "temperature_variations": stored_config.get("temperature_variations", 0),
                        "user_defined_metrics": stored_config.get("user_defined_metrics", ""),
                        "temperature": stored_config.get("temperature"),
                        "csv_file_name": stored_config.get("csv_file_name")
                    }
                    
                    st.session_state.evaluations.append(eval_config)
                    
            except Exception as e:
                import logging
                logging.warning(f"Could not load evaluation from {status_file}: {str(e)}")
                continue
        
        # Rebuild lists
        rebuild_evaluation_lists()
        
    except Exception as e:
        import logging
        logging.warning(f"Error loading evaluations from files: {str(e)}")


def extract_task_info_from_jsonl_simple(eval_name):
    """Extract task info from JSONL files using the evaluation name."""
    try:
        import json
        from pathlib import Path
        
        # Look in prompt-evaluations directory
        prompt_eval_dir = Path(DEFAULT_OUTPUT_DIR).parent / "prompt-evaluations"
        if not prompt_eval_dir.exists():
            return {"task_type": "Unknown", "task_criteria": "Unknown"}
        
        # Try to find matching JSONL file
        jsonl_file = prompt_eval_dir / f"{eval_name}.jsonl"
        if jsonl_file.exists():
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line:
                    data = json.loads(first_line)
                    task_info = data.get("task", {})
                    return {
                        "task_type": task_info.get("task_type", "Unknown"),
                        "task_criteria": task_info.get("task_criteria", "Unknown")
                    }
        
    except Exception as e:
        import logging
        logging.warning(f"Could not extract task info for {eval_name}: {str(e)}")
    
    return {"task_type": "Unknown", "task_criteria": "Unknown"}


def extract_models_from_profile_files(eval_id, eval_name):
    """Extract complete model information from status file or fallback to profile files."""
    try:
        import json
        from pathlib import Path
        
        # First try to get from status file (now in logs directory)
        status_dir = Path(STATUS_FILES_DIR)
        composite_id = f"{eval_id}_{eval_name}"
        status_file = status_dir / f"eval_{composite_id}_status.json"
        
        # Try composite status file first
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
                if "models_data" in status_data and status_data["models_data"]:
                    return status_data["models_data"]
        
        # Fallback to legacy status file
        legacy_status_file = status_dir / f"eval_{eval_id}_status.json"
        if legacy_status_file.exists():
            with open(legacy_status_file, 'r') as f:
                status_data = json.load(f)
                if "models_data" in status_data and status_data["models_data"]:
                    return status_data["models_data"]
        
        # Fallback to old profile files method (for backward compatibility)
        prompt_eval_dir = Path(DEFAULT_OUTPUT_DIR).parent / "prompt-evaluations"
        if not prompt_eval_dir.exists():
            return [{"model_id": "Unknown Model", "region": "Unknown", "input_token_cost": 0, "output_token_cost": 0}]
        
        # Try composite naming first
        model_file = prompt_eval_dir / f"model_profiles_{composite_id}.jsonl"
        
        # Fallback to ID-only naming
        if not model_file.exists():
            model_file = prompt_eval_dir / f"model_profiles_{eval_id}.jsonl"
        
        if model_file.exists():
            models = []
            with open(model_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        model_data = json.loads(line)
                        # Extract complete model information
                        model_info = {
                            "model_id": model_data.get("model_id", "Unknown Model"),
                            "region": model_data.get("region", "Unknown"),
                            "inference_profile": model_data.get("inference_profile", ""),
                            "input_token_cost": model_data.get("input_token_cost", 0),
                            "output_token_cost": model_data.get("output_token_cost", 0)
                        }
                        models.append(model_info)
            return models
        
    except Exception as e:
        import logging
        logging.warning(f"Could not extract models for {eval_id}: {str(e)}")
    
    return [{"model_id": "Unknown Model", "region": "Unknown", "input_token_cost": 0, "output_token_cost": 0}]


def extract_judges_from_profile_files(eval_id, eval_name):
    """Extract complete judge information from status file or fallback to profile files."""
    try:
        import json
        from pathlib import Path
        
        # First try to get from status file (now in logs directory)
        status_dir = Path(STATUS_FILES_DIR)
        composite_id = f"{eval_id}_{eval_name}"
        status_file = status_dir / f"eval_{composite_id}_status.json"
        
        # Try composite status file first
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
                if "judges_data" in status_data and status_data["judges_data"]:
                    return status_data["judges_data"]
        
        # Fallback to legacy status file
        legacy_status_file = status_dir / f"eval_{eval_id}_status.json"
        if legacy_status_file.exists():
            with open(legacy_status_file, 'r') as f:
                status_data = json.load(f)
                if "judges_data" in status_data and status_data["judges_data"]:
                    return status_data["judges_data"]
        
        # Fallback to old profile files method (for backward compatibility)
        prompt_eval_dir = Path(DEFAULT_OUTPUT_DIR).parent / "prompt-evaluations"
        if not prompt_eval_dir.exists():
            return [{"model_id": "Unknown Judge", "region": "Unknown", "input_cost_per_1k": 0, "output_cost_per_1k": 0}]
        
        # Try composite naming first
        judge_file = prompt_eval_dir / f"judge_profiles_{composite_id}.jsonl"
        
        # Fallback to ID-only naming
        if not judge_file.exists():
            judge_file = prompt_eval_dir / f"judge_profiles_{eval_id}.jsonl"
        
        if judge_file.exists():
            judges = []
            with open(judge_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        judge_data = json.loads(line)
                        # Extract complete judge information
                        judge_info = {
                            "model_id": judge_data.get("model_id", "Unknown Judge"),
                            "region": judge_data.get("region", "Unknown"),
                            "input_cost_per_1k": judge_data.get("input_cost_per_1k", 0),
                            "output_cost_per_1k": judge_data.get("output_cost_per_1k", 0)
                        }
                        judges.append(judge_info)
            return judges
        
    except Exception as e:
        import logging
        logging.warning(f"Could not extract judges for {eval_id}: {str(e)}")
    
    return [{"model_id": "Unknown Judge", "region": "Unknown", "input_cost_per_1k": 0, "output_cost_per_1k": 0}]


def rebuild_evaluation_lists():
    """Rebuild active and completed evaluation lists."""
    try:
        st.session_state.active_evaluations = []
        st.session_state.completed_evaluations = []
        
        for eval_config in st.session_state.evaluations:
            status = eval_config.get("status", "unknown")
            if status in ["running", "queued", "in-progress"]:
                st.session_state.active_evaluations.append(eval_config.copy())
            elif status in ["completed", "failed"]:
                st.session_state.completed_evaluations.append(eval_config.copy())
                
    except Exception as e:
        import logging
        logging.warning(f"Error rebuilding evaluation lists: {str(e)}")