"""Utilities for running benchmark evaluations from the dashboard."""

import subprocess
import threading
import time
import os
import json
import logging
import sys
from pathlib import Path
import streamlit as st
from datetime import datetime
from .state_management import update_evaluation_status
from .constants import DEFAULT_OUTPUT_DIR, STATUS_FILES_DIR
from .csv_processor import (
    convert_to_jsonl, 
    create_model_profiles_jsonl, 
    create_judge_profiles_jsonl
)

# Set up dashboard logger
from .constants import PROJECT_ROOT
DASHBOARD_LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(DASHBOARD_LOG_DIR, exist_ok=True)

# Configure root logger for dashboard using in-memory logging
dashboard_logger = logging.getLogger('dashboard')
dashboard_logger.setLevel(logging.DEBUG)

# Use in-memory logging
from io import StringIO

# Stream handler for console output
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_format = logging.Formatter('%(levelname)s - %(message)s')
stream_handler.setFormatter(stream_format)
dashboard_logger.addHandler(stream_handler)

dashboard_logger.info("Dashboard logger initialized (in-memory mode)")

# Store evaluation configs locally for thread safety
_thread_local_evaluations = {}

# Evaluation queue and status tracking
_evaluation_queue = []
_current_evaluation = None
_execution_thread = None
_execution_lock = threading.Lock()

def run_evaluations_linearly(evaluation_configs):
    """Queue evaluations for linear execution.
    
    This adds evaluations to a queue and starts the execution thread if not running.
    Only one evaluation runs at a time with proper status tracking.
    
    Args:
        evaluation_configs: List of evaluation configuration dictionaries
    """
    global _evaluation_queue, _execution_thread
    
    if not evaluation_configs:
        dashboard_logger.error("No evaluations provided for linear execution")
        return
    
    with _execution_lock:
        # Add evaluations to queue
        for eval_config in evaluation_configs:
            eval_id = eval_config["id"]
            # Mark as queued
            update_evaluation_status(eval_id, "queued", 0)
            _evaluation_queue.append(eval_config.copy())
            dashboard_logger.info(f"Queued evaluation: '{eval_config['name']}' (ID: {eval_id})")
        
        # Start execution thread if not running
        if _execution_thread is None or not _execution_thread.is_alive():
            _execution_thread = threading.Thread(target=_process_evaluation_queue, daemon=True)
            _execution_thread.start()
            dashboard_logger.info("Started evaluation execution thread")

def _process_evaluation_queue():
    """Process evaluations from the queue one by one."""
    global _evaluation_queue, _current_evaluation
    
    dashboard_logger.info("Evaluation queue processor started")
    
    while True:
        with _execution_lock:
            if not _evaluation_queue:
                break
            
            _current_evaluation = _evaluation_queue.pop(0)
            eval_id = _current_evaluation["id"]
            eval_name = _current_evaluation["name"]
        
        dashboard_logger.info(f"Starting evaluation: '{eval_name}' (ID: {eval_id})")
        
        try:
            # Update status to running
            update_evaluation_status(eval_id, "running", 5)
            
            # Store evaluation config
            _thread_local_evaluations[eval_id] = _current_evaluation.copy()
            
            # Run the benchmark process synchronously
            success = run_benchmark_process(eval_id)
            
            if success:
                dashboard_logger.info(f"Completed evaluation: '{eval_name}' (ID: {eval_id})")
            else:
                dashboard_logger.error(f"Failed evaluation: '{eval_name}' (ID: {eval_id})")
                
        except Exception as e:
            dashboard_logger.error(f"Error executing evaluation '{eval_name}' (ID: {eval_id}): {str(e)}")
            update_evaluation_status(eval_id, "failed", 0, error=str(e))
        
        # Small delay between evaluations
        time.sleep(2)
    
    with _execution_lock:
        _current_evaluation = None
    
    dashboard_logger.info("Evaluation queue processor finished")

def get_queue_status():
    """Get current queue status for UI display."""
    with _execution_lock:
        return {
            "queue_length": len(_evaluation_queue),
            "current_evaluation": _current_evaluation.copy() if _current_evaluation else None,
            "queued_evaluations": [e.copy() for e in _evaluation_queue]
        }



def run_benchmark_process(eval_id):
    """
    Run the benchmark evaluation in a subprocess.
    
    Args:
        eval_id: ID of the evaluation to run
        
    Returns:
        bool: True if successful, False if failed
    """
    # Get the evaluation config from thread-local storage
    if eval_id not in _thread_local_evaluations:
        dashboard_logger.error(f"Evaluation {eval_id} not found in thread-local storage")
        return False
        
    evaluation_config = _thread_local_evaluations[eval_id]
    eval_name = evaluation_config["name"]
    
    # Create composite identifier for consistent file naming
    composite_id = f"{eval_id}_{eval_name}"
    dashboard_logger.info(f"Using composite identifier: {composite_id}")
    
    try:
        # Get project root
        from .constants import PROJECT_ROOT, DEFAULT_OUTPUT_DIR
        
        # Create output directory if it doesn't exist (using absolute path)
        output_dir = Path(DEFAULT_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        
        # Use main logs directory where benchmark actually writes logs
        from .constants import PROJECT_ROOT
        logs_dir = Path(PROJECT_ROOT) / "logs"
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create a status file to track progress using composite ID (stored in logs directory)
        status_file = Path(STATUS_FILES_DIR) / f"eval_{composite_id}_status.json"
        _update_status_file(status_file, "in-progress", 0, logs_dir=str(logs_dir))
        
        # Start time to track session evaluations
        eval_start_time = time.time()
        _update_status_file(status_file, "in-progress", 0, logs_dir=str(logs_dir), start_time=eval_start_time)
        
        # Convert CSV data to JSONL
        dashboard_logger.info(f"Converting CSV data to JSONL for evaluation {eval_id}")
        try:
            jsonl_path = convert_to_jsonl(
                evaluation_config["csv_data"],
                evaluation_config["prompt_column"],
                evaluation_config["golden_answer_column"],
                evaluation_config["task_type"],
                evaluation_config["task_criteria"],
                "",
                evaluation_config["name"]
            )
            if not jsonl_path:
                dashboard_logger.error(f"Failed to convert CSV data to JSONL for evaluation {eval_id}")
                error_msg = "Failed to convert CSV data to JSONL format"
                _update_status_file(status_file, "failed", 0, error=error_msg)
                update_evaluation_status(eval_id, "failed", 0, error=error_msg)
                return False
            dashboard_logger.info(f"Successfully created JSONL file at {jsonl_path}")
        except Exception as e:
            dashboard_logger.exception(f"Exception while converting CSV data to JSONL: {str(e)}")
            error_msg = f"CSV conversion error: {str(e)}"
            _update_status_file(status_file, "failed", 0, error=error_msg)
            update_evaluation_status(eval_id, "failed", 0, error=error_msg)
            return False
        
        # Create unique model profiles JSONL for this evaluation
        dashboard_logger.info(f"Creating model profiles JSONL for evaluation {eval_id}")
        try:
            # Generate unique filenames for this evaluation using composite ID
            model_file_name = f"model_profiles_{composite_id}.jsonl"
            judge_file_name = f"judge_profiles_{composite_id}.jsonl"
            
            models_jsonl = create_model_profiles_jsonl(
                evaluation_config["selected_models"],
                "",
                custom_filename=model_file_name
            )
            dashboard_logger.info(f"Successfully created model profiles at {models_jsonl}")
        except Exception as e:
            dashboard_logger.exception(f"Exception while creating model profiles: {str(e)}")
            error_msg = f"Model profiles error: {str(e)}"
            _update_status_file(status_file, "failed", 0, error=error_msg)
            update_evaluation_status(eval_id, "failed", 0, error=error_msg)
            return False
        
        # Create unique judge profiles JSONL
        dashboard_logger.info(f"Creating judge profiles JSONL for evaluation {eval_id}")
        try:
            judges_jsonl = create_judge_profiles_jsonl(
                evaluation_config["judge_models"],
                "",
                custom_filename=judge_file_name
            )
            dashboard_logger.info(f"Successfully created judge profiles at {judges_jsonl}")
        except Exception as e:
            dashboard_logger.exception(f"Exception while creating judge profiles: {str(e)}")
            error_msg = f"Judge profiles error: {str(e)}"
            _update_status_file(status_file, "failed", 0, error=error_msg)
            update_evaluation_status(eval_id, "failed", 0, error=error_msg)
            return False
        
        # Get current script directory for reliable relative paths
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


        cmd = [
            "python", 
            os.path.join(script_dir, "benchmarks_run.py"),
            jsonl_path,
            "--output_dir", str(output_dir),
            "--report", "False",
            "--parallel_calls", str(evaluation_config["parallel_calls"]),
            "--invocations_per_scenario", str(evaluation_config["invocations_per_scenario"]),
            "--sleep_between_invocations", str(evaluation_config["sleep_between_invocations"]),
            "--experiment_counts", str(evaluation_config["experiment_counts"]),
            "--experiment_name", composite_id,
            "--temperature_variations", str(evaluation_config["temperature_variations"]),
            "--model_file_name", model_file_name,
            "--judge_file_name", judge_file_name
        ]
        
        if evaluation_config["user_defined_metrics"]:
            cmd.extend(["--user_defined_metrics", evaluation_config["user_defined_metrics"]])

        # Log the command being executed
        dashboard_logger.info(f"Executing benchmark command for evaluation {eval_id}:")
        dashboard_logger.info(" ".join(cmd))
        dashboard_logger.info(f"Working directory: {os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}")
        dashboard_logger.info(f"Output directory: {output_dir}")
        dashboard_logger.info(f"Expected files: model={model_file_name}, judge={judge_file_name}")
        
        # Create stdout/stderr capture variables
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        # Run the benchmark command with output capture
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Run from src directory
            )
            
            dashboard_logger.info(f"Started subprocess with PID {process.pid}")
            dashboard_logger.info(f"Command: python {os.path.join(script_dir, 'benchmarks_run.py')} {jsonl_path} --output_dir {output_dir} --experiment_name {evaluation_config['name']}")
            
            # Set up threads to read process output
            def read_stdout():
                for line in iter(process.stdout.readline, ''):
                    stdout_capture.write(line)
                    dashboard_logger.debug(f"STDOUT: {line.strip()}")
            
            def read_stderr():
                for line in iter(process.stderr.readline, ''):
                    stderr_capture.write(line)
                    # Only log as debug - stderr often contains normal info, not errors
                    dashboard_logger.debug(f"STDERR: {line.strip()}")
            
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            # Monitor evaluation state - simplified approach
            poll_count = 0
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    dashboard_logger.info(f"Process completed with return code {process.returncode}")
                    break
                
                # Periodically log that we're still monitoring the process
                if poll_count % 6 == 0:  # Every minute (6 * 10 seconds)
                    dashboard_logger.info(f"Process {process.pid} still running (poll count: {poll_count})")
                    
                    # Update status to show progress
                    _update_status_file(status_file, "running", min(poll_count * 2, 90), logs_dir=str(logs_dir))
                    update_evaluation_status(eval_id, "running", min(poll_count * 2, 90))
                    
                    # Periodically check for reports being generated
                    csv_files = list(output_dir.glob(f"*{evaluation_config['name']}*.csv"))
                    html_files = list(output_dir.glob(f"*{evaluation_config['name']}*.html"))
                    if csv_files or html_files:
                        dashboard_logger.info(f"Found {len(csv_files)} CSV files and {len(html_files)} HTML files while process is running")
                
                # Wait before checking again
                time.sleep(10)
                poll_count += 1
            
            # Make sure we've read all output
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            # Process completed - check final status
            return_code = process.wait()
            
            # Get final output content for logging
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()
            
            dashboard_logger.info(f"Process completed with return code {return_code}")
            
            # Log final output for debugging
            if stdout_content:
                dashboard_logger.debug(f"Final STDOUT content (last 500 chars): {stdout_content[-500:]}")
            if stderr_content:
                dashboard_logger.debug(f"Final STDERR content (last 500 chars): {stderr_content[-500:]}")
            
            # Check for actual errors - only fail on non-zero return code
            if return_code != 0:
                dashboard_logger.error(f"Process failed with return code {return_code}")
                error_msg = f"Process failed with return code {return_code}"
                if stderr_content and any(critical in stderr_content.lower() for critical in ['fatal', 'critical error', 'traceback', 'exception']):
                    error_msg += f". Error details: {stderr_content[:300]}"
                _update_status_file(status_file, "failed", 0, 
                                  logs_dir=str(logs_dir),
                                  error=error_msg)
                update_evaluation_status(eval_id, "failed", 0, error=error_msg)
                return False
            
            dashboard_logger.info(f"Process completed successfully with return code 0")
            
        except Exception as e:
            dashboard_logger.exception(f"Exception during subprocess execution: {str(e)}")
            error_msg = f"Subprocess error: {str(e)}"
            _update_status_file(status_file, "failed", 0, 
                              logs_dir=str(logs_dir),
                              error=error_msg)
            update_evaluation_status(eval_id, "failed", 0, error=error_msg)
            return False
        
        # Look for generated results
        dashboard_logger.info(f"Looking for results in {output_dir}")
        
        # Check for CSV results (the main output) using composite ID
        csv_files = list(output_dir.glob(f"invocations_*{composite_id}*.csv"))
        if not csv_files:
            # Fallback to original name pattern
            csv_files = list(output_dir.glob(f"*{evaluation_config['name']}*.csv"))
        
        # Check for HTML reports using composite ID
        html_reports = list(output_dir.glob(f"*{composite_id}*.html"))
        if not html_reports:
            # Fallback to original name pattern
            html_reports = list(output_dir.glob(f"*{evaluation_config['name']}*.html"))
        
        dashboard_logger.info(f"Found {len(csv_files)} CSV files and {len(html_reports)} HTML reports")
        
        if csv_files or html_reports:
            # Success - found output files
            results_info = []
            latest_csv = None
            latest_html = None
            
            if csv_files:
                latest_csv = max(csv_files, key=os.path.getmtime)
                results_info.append(f"CSV: {latest_csv}")
            if html_reports:
                latest_html = max(html_reports, key=os.path.getmtime)
                results_info.append(f"HTML: {latest_html}")
                
            results_path = str(latest_html) if latest_html else str(latest_csv) if latest_csv else None
            
            _update_status_file(status_file, "completed", 100, 
                               logs_dir=str(logs_dir),
                               results=results_path,
                               end_time=time.time(),
                               eval_id=eval_id,
                               eval_name=evaluation_config.get("name"),
                               output_dir=str(output_dir),
                               evaluation_config=evaluation_config)
            update_evaluation_status(eval_id, "completed", 100, results=results_path)
            dashboard_logger.info(f"Evaluation completed successfully. Results: {'; '.join(results_info)}")
        else:
            # No output files found - this might still be success if the process completed normally
            dashboard_logger.warning(f"Process completed but no output files found in {output_dir}")
            _update_status_file(status_file, "completed", 100, 
                               logs_dir=str(logs_dir),
                               end_time=time.time(),
                               eval_id=eval_id,
                               eval_name=evaluation_config.get("name"),
                               output_dir=str(output_dir),
                               evaluation_config=evaluation_config)
            update_evaluation_status(eval_id, "completed", 100)
            
        return True
    
    except Exception as e:
        dashboard_logger.exception(f"Unexpected error in run_benchmark_process: {str(e)}")
        error_msg = str(e)
        _update_status_file(status_file, "failed", 0, 
                           logs_dir=str(logs_dir) if 'logs_dir' in locals() else None,
                           error=error_msg)
        update_evaluation_status(eval_id, "failed", 0, error=error_msg)
        return False
    finally:
        # Clean up thread-local storage
        if eval_id in _thread_local_evaluations:
            del _thread_local_evaluations[eval_id]


def _store_model_judge_data_and_cleanup(eval_id, eval_name, output_dir):
    """
    Store model and judge data in the status file and clean up the separate files.
    
    Args:
        eval_id: Evaluation ID
        eval_name: Evaluation name
        output_dir: Output directory path
    
    Returns:
        dict: Dictionary containing models_data and judges_data
    """
    models_data = []
    judges_data = []
    
    try:
        # Construct file paths
        prompt_eval_dir = Path(output_dir).parent / "prompt-evaluations"
        composite_id = f"{eval_id}_{eval_name}"
        
        # Try to find model profiles file
        model_file_paths = [
            prompt_eval_dir / f"model_profiles_{composite_id}.jsonl",
            prompt_eval_dir / f"model_profiles_{eval_id}.jsonl"
        ]
        
        for model_file in model_file_paths:
            if model_file.exists():
                dashboard_logger.info(f"Reading model profiles from {model_file}")
                with open(model_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            models_data.append(json.loads(line))
                
                # Delete the file after reading
                dashboard_logger.info(f"Deleting model profiles file: {model_file}")
                model_file.unlink()
                break
        
        # Try to find judge profiles file
        judge_file_paths = [
            prompt_eval_dir / f"judge_profiles_{composite_id}.jsonl",
            prompt_eval_dir / f"judge_profiles_{eval_id}.jsonl"
        ]
        
        for judge_file in judge_file_paths:
            if judge_file.exists():
                dashboard_logger.info(f"Reading judge profiles from {judge_file}")
                with open(judge_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            judges_data.append(json.loads(line))
                
                # Delete the file after reading
                dashboard_logger.info(f"Deleting judge profiles file: {judge_file}")
                judge_file.unlink()
                break
        
        dashboard_logger.info(f"Stored {len(models_data)} models and {len(judges_data)} judges in status file")
        
    except Exception as e:
        dashboard_logger.error(f"Error storing model/judge data: {str(e)}")
    
    return {"models_data": models_data, "judges_data": judges_data}


def _update_status_file(status_file, status, progress, results=None, logs_dir=None, error=None, start_time=None, end_time=None, eval_id=None, eval_name=None, output_dir=None, evaluation_config=None):
    """
    Update the status file with the current status.
    
    Args:
        status_file: Path to the status file
        status: Current status (in-progress, failed, completed)
        progress: Progress percentage (0-100)
        results: Path to results file if available
        logs_dir: Directory containing log files
        error: Error message if status is failed
        start_time: Start time of the evaluation
        end_time: End time of the evaluation
        eval_id: Evaluation ID (for storing model/judge data)
        eval_name: Evaluation name (for storing model/judge data)
        output_dir: Output directory (for storing model/judge data)
        evaluation_config: Full evaluation configuration (for storing settings)
    """
    status_data = {
        "status": status,
        "updated_at": time.time()
    }
    
    # Only include progress for backward compatibility
    if progress is not None:
        status_data["progress"] = progress
    
    # Add optional fields if provided
    if results:
        status_data["results"] = results
    if logs_dir:
        status_data["logs_dir"] = logs_dir
    if error:
        status_data["error"] = error
    if start_time:
        status_data["start_time"] = start_time
    if end_time:
        status_data["end_time"] = end_time
        status_data["duration"] = end_time - status_data.get("start_time", start_time or end_time)
    
    # If evaluation is completed, store model and judge data and clean up files
    if status == "completed" and eval_id and eval_name and output_dir:
        model_judge_data = _store_model_judge_data_and_cleanup(eval_id, eval_name, output_dir)
        status_data["models_data"] = model_judge_data["models_data"]
        status_data["judges_data"] = model_judge_data["judges_data"]
        
        # Store evaluation configuration parameters
        if evaluation_config:
            status_data["evaluation_config"] = {
                "parallel_calls": evaluation_config.get("parallel_calls"),
                "invocations_per_scenario": evaluation_config.get("invocations_per_scenario"),
                "experiment_counts": evaluation_config.get("experiment_counts"),
                "temperature_variations": evaluation_config.get("temperature_variations"),
                "user_defined_metrics": evaluation_config.get("user_defined_metrics"),
                "sleep_between_invocations": evaluation_config.get("sleep_between_invocations"),
                "task_type": evaluation_config.get("task_type"),
                "task_criteria": evaluation_config.get("task_criteria")
            }
    
    with open(status_file, 'w') as f:
        json.dump(status_data, f)



def _read_status_file(status_file):
    """Read the status file."""
    if not status_file.exists():
        return {"status": "unknown", "progress": 0}
    
    try:
        with open(status_file, 'r') as f:
            return json.load(f)
    except:
        return {"status": "unknown", "progress": 0}


def sync_evaluations_from_files():
    """
    Sync evaluation statuses from status files.
    Call this function periodically from the main thread.
    """
    # Make sure session state is initialized
    if "evaluations" not in st.session_state:
        dashboard_logger.warning("No evaluations found in session state")
        print("No evaluations found in session state")
        return
        
    # Get all evaluations and print for debugging
    evaluations = st.session_state.evaluations
    dashboard_logger.info(f"Syncing status for {len(evaluations)} evaluations")
    print(f"Syncing status for {len(evaluations)} evaluations with IDs: {[e['id'] for e in evaluations]}")
    
    for eval_config in evaluations:
        eval_id = eval_config["id"]
        eval_name = eval_config.get("name", "")
        
        # Try both composite ID format and legacy format
        from .constants import DEFAULT_OUTPUT_DIR
        output_dir = Path(DEFAULT_OUTPUT_DIR)
        
        # First try composite format: eval_{id}_{name}_status.json
        composite_id = f"{eval_id}_{eval_name}"
        status_file = Path(STATUS_FILES_DIR) / f"eval_{composite_id}_status.json"
        
        # If composite format doesn't exist, try legacy format
        if not status_file.exists():
            status_file = Path(STATUS_FILES_DIR) / f"eval_{eval_id}_status.json"
        
        dashboard_logger.debug(f"Checking status file for evaluation {eval_id}: {status_file}")
        
        if status_file.exists():
            dashboard_logger.debug(f"Status file found for evaluation {eval_id}")
            status_data = _read_status_file(status_file)
            
            # Log status changes
            old_status = eval_config.get("status", "unknown")
            new_status = status_data.get("status", old_status)
            
            if old_status != new_status:
                dashboard_logger.info(f"Evaluation {eval_id} status changed: {old_status} -> {new_status}")
            
            # Update evaluation status in session state
            update_evaluation_status(
                eval_id, 
                new_status,
                status_data.get("progress", eval_config.get("progress", 0))
            )
            
            # Update additional fields from status file
            for key in ["logs_dir", "error", "start_time", "end_time", "duration"]:
                if key in status_data:
                    for i, e in enumerate(st.session_state.evaluations):
                        if e["id"] == eval_id:
                            st.session_state.evaluations[i][key] = status_data[key]
            
            # Update results if available
            if "results" in status_data and status_data["results"]:
                dashboard_logger.info(f"Results found for evaluation {eval_id}: {status_data['results']}")
                for i, e in enumerate(st.session_state.evaluations):
                    if e["id"] == eval_id:
                        st.session_state.evaluations[i]["results"] = status_data["results"]
                        break
        else:
            dashboard_logger.debug(f"No status file found for evaluation {eval_id} (tried both composite and legacy formats)")
            
    dashboard_logger.info("Status sync completed")


def get_evaluation_progress(eval_id):
    """Get the progress of an evaluation."""
    # First try to get from session state
    if "evaluations" in st.session_state:
        for eval_config in st.session_state.evaluations:
            if eval_config["id"] == eval_id:
                return eval_config["progress"]
    
    # If not in session state, try status file (now in logs directory)
    status_file = Path(STATUS_FILES_DIR) / f"eval_{eval_id}_status.json"
    if status_file.exists():
        status_data = _read_status_file(status_file)
        return status_data.get("progress", 0)
    
    return 0