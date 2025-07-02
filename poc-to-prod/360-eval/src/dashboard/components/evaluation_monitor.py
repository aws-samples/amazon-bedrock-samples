"""Evaluation monitor component for the Streamlit dashboard."""

import streamlit as st
import pandas as pd
import time
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from ..utils.benchmark_runner import run_evaluations_linearly, sync_evaluations_from_files, dashboard_logger, get_queue_status

class EvaluationMonitorComponent:
    """Component for monitoring active evaluations."""
    
    def render(self):
        """Render the evaluation monitor component."""
        # Create a placeholder for notifications at the very top of the page
        notification_placeholder = st.empty()
        
        dashboard_logger.info("Rendering evaluation monitor component")
        
        # Debug information about current session state
        print(f"Current evaluations in session state: {len(st.session_state.evaluations)}")
        for i, eval_config in enumerate(st.session_state.evaluations):
            print(f"Evaluation {i+1}: ID={eval_config['id']}, Name={eval_config['name']}, Status={eval_config['status']}")
        
        # Sync evaluation statuses from files
        sync_evaluations_from_files()
        
        # Get queue status for display
        queue_status = get_queue_status()
        
        # Simple tracking of evaluation status without notifications
        if 'last_status_check' not in st.session_state:
            st.session_state.last_status_check = {}
            
        # Update tracked statuses but without creating notifications
        for eval_config in st.session_state.evaluations:
            eval_id = eval_config.get("id")
            current_status = eval_config.get("status")
            
            # Update tracked status
            if eval_id not in st.session_state.last_status_check:
                st.session_state.last_status_check[eval_id] = current_status
            elif st.session_state.last_status_check[eval_id] != current_status:
                # Status has changed - just log it
                dashboard_logger.info(f"Evaluation {eval_id} status changed: {st.session_state.last_status_check[eval_id]} -> {current_status}")
                st.session_state.last_status_check[eval_id] = current_status
                
        # No notifications or auto-refresh - just a manual refresh button
        st.button("Refresh Evaluations", on_click=sync_evaluations_from_files)
            
        # No auto-refresh - just display the last refresh time
        current_time = time.time()
        if 'last_refresh_time' not in st.session_state:
            st.session_state.last_refresh_time = current_time
            
        # Calculate time since last refresh
        time_since_refresh = current_time - st.session_state.last_refresh_time
        st.session_state.last_refresh_time = current_time
        
        # Show last refresh time
        st.caption(f"Last refreshed: {datetime.fromtimestamp(current_time).strftime('%H:%M:%S')}")
            
        # Add a UI indicator for the log file location
        from ..utils.constants import PROJECT_ROOT
        log_dir = os.path.join(PROJECT_ROOT, 'logs')

        # Get current session time
        current_session_start = st.session_state.get('session_start_time', time.time())
        if 'session_start_time' not in st.session_state:
            st.session_state.session_start_time = current_session_start
            dashboard_logger.info(f"Set session start time to {current_session_start}")
        
        # Retrieve all evaluations for this session
        dashboard_logger.debug("Retrieving session evaluations")
        session_evals = self._get_session_evaluations(current_session_start)
        
        
        # Display queue status if there are queued/running evaluations
        if queue_status["queue_length"] > 0 or queue_status["current_evaluation"]:
            st.subheader("🏃 Execution Queue Status")
            
            # Show currently running evaluation
            if queue_status["current_evaluation"]:
                current = queue_status["current_evaluation"]
                st.info(f"▶️ Currently Running: **{current['name']}**")
            
            # Show queued evaluations
            if queue_status["queue_length"] > 0:
                st.info(f"⏳ Queued Evaluations: **{queue_status['queue_length']}**")
                with st.expander("View Queued Evaluations"):
                    for i, queued_eval in enumerate(queue_status["queued_evaluations"], 1):
                        st.write(f"{i}. {queued_eval['name']}")
            
            st.divider()
        
        
        
        # Display Processing Evaluations Section
        st.subheader("Processing Evaluations")
        
        # Debug session state
        print(f"Checking for available evaluations in {len(st.session_state.evaluations)} total evaluations")
        
        # Get all evaluations regardless of status (we'll filter in the UI if needed)
        available_evals = list(st.session_state.evaluations)
        
        # Print available evaluations for debugging
        for i, e in enumerate(available_evals):
            print(f"Evaluation {i+1}: ID={e['id']}, Name={e['name']}, Status={e['status']}")
        
        if not available_evals:
            st.info("No available evaluations. Go to Setup tab to create new evaluations.")
        else:
            dashboard_logger.info(f"Found {len(available_evals)} available evaluations")
            # Create a table of available evaluations
            eval_data = []
            
            # First create a list of reports that are available
            report_links = {}
            completed_evals_without_reports = []
            for eval_config in available_evals:
                # Check if this evaluation has a report
                if (eval_config.get("status") == "completed" and 
                    'results' in eval_config and 
                    eval_config['results'] and 
                    os.path.exists(eval_config['results'])):
                    report_links[eval_config["id"]] = f"file://{os.path.abspath(eval_config['results'])}"
                elif eval_config.get("status") == "completed":
                    # Keep track of completed evaluations without reports
                    completed_evals_without_reports.append(eval_config["id"])
            
            # Then create the table data
            for eval_config in available_evals:
                # Prepare the name field - as a link if report exists
                if eval_config["id"] in report_links:
                    name_field = f"{eval_config['name']}"
                else:
                    name_field = eval_config["name"]
                
                    
                eval_data.append({
                    "Name": name_field,
                    "Task Type": eval_config["task_type"],
                    "Models": len(eval_config["selected_models"]),
                    "Status": eval_config["status"].capitalize(),
                    "Created": pd.to_datetime(eval_config["created_at"]).strftime("%Y-%m-%d %H:%M") if eval_config.get("created_at") else "N/A",
                })
            
            # Display the table
            eval_df = pd.DataFrame(eval_data)
            st.dataframe(eval_df, hide_index=True)

            # Add section to run selected evaluations
            st.subheader("Run Evaluations")

            # Filter evaluations for the dropdown - include configuring and failed evaluations
            # Exclude: completed, running, queued, in-progress (allow failed to be re-run)
            excluded_statuses = ["completed", "running", "queued", "in-progress"]
            runnable_evals = [e for e in available_evals if e.get("status", "").lower() not in excluded_statuses]

            # Multiselect for evaluation IDs - only show runnable evaluations
            selected_eval_ids = st.multiselect(
                "Select evaluations to run (will execute in order selected)",
                options=[e["id"] for e in runnable_evals],
                format_func=lambda x: next((e["name"] for e in runnable_evals if e["id"] == x), x)
            )

            if selected_eval_ids:
                st.info(f"Selected {len(selected_eval_ids)} evaluation(s).")

                # # Show warning if there are already evaluations in queue
                # if queue_status["queue_length"] > 0 or queue_status["current_evaluation"]:
                #     st.warning(f"⚠️ There are already evaluations running/queued. New evaluations will be added to the queue.")
                if queue_status["queue_length"] > 0 or queue_status["current_evaluation"]:
                    if st.button("🚀 Add to Execution Queue", key="run_evaluations_btn", type="primary"):
                        self._run_evaluations_linearly(selected_eval_ids)
                else:
                    if st.button("🚀 Execute Evaluation/s", key="run_evaluations_btn", type="primary"):
                        self._run_evaluations_linearly(selected_eval_ids)


            # Add section to delete evaluations
            st.subheader("Delete Evaluations")
            
            # Filter evaluations that can be deleted (exclude running, queued, in-progress)
            deletable_statuses = ["configuring", "failed", "completed"]
            deletable_evals = [e for e in available_evals if e.get("status", "").lower() in deletable_statuses]
            
            if deletable_evals:
                selected_delete_ids = st.multiselect(
                    "Select evaluations to delete permanently",
                    options=[e["id"] for e in deletable_evals],
                    format_func=lambda x: next((f"{e['name']} ({e['status']})" for e in deletable_evals if e["id"] == x), x),
                    help="⚠️ This will permanently delete the evaluation configuration and status files."
                )
                
                if selected_delete_ids:
                    st.warning(f"⚠️ You are about to delete {len(selected_delete_ids)} evaluation(s). This action cannot be undone.")
                    
                    if st.button("🗑️ Delete Selected Evaluations", type="secondary"):
                        self._delete_evaluations(selected_delete_ids)
                        st.info("Please refresh the page or navigate to another tab to see the updated list.")
            else:
                st.info("No evaluations available for deletion.")
            


    def _get_session_evaluations(self, session_start_time):
        """Get all evaluations for the current session, including completed ones."""
        session_evals = []
        
        # Get from session state
        if hasattr(st.session_state, 'evaluations'):
            for eval_config in st.session_state.evaluations:
                # Check if this evaluation was started in this session (now in logs directory)
                from ..utils.constants import STATUS_FILES_DIR
                status_file = Path(STATUS_FILES_DIR) / f"eval_{eval_config['id']}_status.json"
                if status_file.exists():
                    try:
                        with open(status_file, 'r') as f:
                            status_data = json.load(f)
                            # Include if started in this session
                            if status_data.get('start_time', 0) >= session_start_time:
                                # Merge status data with eval config
                                eval_data = eval_config.copy()
                                eval_data.update(status_data)
                                session_evals.append(eval_data)
                    except:
                        pass
                        
        return session_evals
        

    
    def _format_time(self, seconds):
        """Format seconds into a readable time string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def _show_logs(self, eval_config):
        """Show logs for an evaluation."""
        logs_dir = eval_config.get('logs_dir')
        if not logs_dir or not os.path.exists(logs_dir):
            st.error("Logs directory not found.")
            return
        
        # Search for benchmark log file
        from ..utils.constants import PROJECT_ROOT
        log_dir = os.path.join(PROJECT_ROOT, 'logs')
        benchmark_logs = list(Path(log_dir).glob(f"360-benchmark-*-{eval_config['name']}.log"))
        
        if benchmark_logs:
            benchmark_log = benchmark_logs[0]
            with st.expander("Benchmark Log", expanded=True):
                with open(benchmark_log, 'r') as f:
                    log_content = f.read()
                st.code(log_content)
        else:
            st.warning("No benchmark log file found for this evaluation. Only 360-benchmark logs are saved to disk.")
            
        # Access stdout/stderr captures if available 
        try:
            # This is a simplified approach - ideally we'd make these available through an API
            from ..utils.benchmark_runner import stdout_capture, stderr_capture
            
            if hasattr(stdout_capture, 'getvalue') and stdout_capture.getvalue():
                with st.expander("Standard Output (In-Memory)", expanded=True):
                    st.code(stdout_capture.getvalue())
            
            if hasattr(stderr_capture, 'getvalue') and stderr_capture.getvalue():
                with st.expander("Error Output (In-Memory)"):
                    st.code(stderr_capture.getvalue())
        except (ImportError, NameError, AttributeError):
            st.info("In-memory logs not available - only benchmark logs are saved to disk.")
    

    def _run_evaluations_linearly(self, eval_ids):
        """Run the selected evaluations one by one in a simple linear fashion.
        
        This simplified approach executes evaluations in the order they are listed,
        waiting for each to complete before starting the next.
        
        Args:
            eval_ids: List of evaluation IDs to run in order
        """
        dashboard_logger.info(f"Starting execution of evaluations: {eval_ids}")
        
        if not eval_ids:
            st.warning("No evaluations selected.")
            return
            
        # Get the evaluation configs to run
        evals_to_run = []
        for eval_id in eval_ids:
            for eval_config in st.session_state.evaluations:
                if eval_config["id"] == eval_id:
                    # Validate the configuration
                    if not eval_config.get("selected_models") or not eval_config.get("judge_models"):
                        st.error(f"Evaluation '{eval_config['name']}' is missing required configuration: models or judge models")
                        continue
                    evals_to_run.append(eval_config)
                    break
        
        # Check if we have valid evaluations to run
        if not evals_to_run:
            st.error("No valid evaluations found.")
            return
            
        # Start the linear execution
        try:
            # Show what will be executed
            eval_names = [e["name"] for e in evals_to_run]
            st.success(f"Starting execution of {len(evals_to_run)} evaluations: {', '.join(eval_names)}")
            
            # Show log file location to user
            from ..utils.constants import PROJECT_ROOT
            log_dir = os.path.join(PROJECT_ROOT, 'logs')
            st.info(f"Monitor progress in logs: {log_dir}")
            
            # Call the simplified linear execution function
            run_evaluations_linearly(evals_to_run)
            
        except Exception as e:
            st.error(f"Error starting execution: {str(e)}")
            dashboard_logger.exception(f"Error in linear execution: {str(e)}")
    
    def _delete_evaluations(self, eval_ids):
        """Delete selected evaluations from session state and disk."""
        from ..utils.state_management import delete_evaluation_from_disk
        
        deleted_count = 0
        for eval_id in eval_ids:
            # Find the evaluation to get its name
            eval_to_delete = None
            for eval_config in st.session_state.evaluations:
                if eval_config["id"] == eval_id:
                    eval_to_delete = eval_config
                    break
            
            if eval_to_delete:
                # Delete from disk
                if delete_evaluation_from_disk(eval_id, eval_to_delete["name"]):
                    # Remove from session state
                    st.session_state.evaluations = [
                        e for e in st.session_state.evaluations if e["id"] != eval_id
                    ]
                    
                    # Also remove from active and completed lists
                    st.session_state.active_evaluations = [
                        e for e in st.session_state.active_evaluations if e["id"] != eval_id
                    ]
                    st.session_state.completed_evaluations = [
                        e for e in st.session_state.completed_evaluations if e["id"] != eval_id
                    ]
                    
                    deleted_count += 1
                    dashboard_logger.info(f"Deleted evaluation: {eval_to_delete['name']} (ID: {eval_id})")
                else:
                    st.error(f"Failed to delete evaluation: {eval_to_delete['name']}")
            else:
                st.error(f"Evaluation with ID {eval_id} not found")
        
        if deleted_count > 0:
            st.success(f"Successfully deleted {deleted_count} evaluation(s)")
        else:
            st.error("No evaluations were deleted")
