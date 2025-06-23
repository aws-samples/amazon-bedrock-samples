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
        
        # Separate active and recently completed evaluations
        active_evals = [e for e in session_evals if e.get('status') in ['in-progress', 'running']]
        completed_evals = [e for e in session_evals if e.get('status') == 'completed' and 
                          e.get('end_time', 0) > current_time - 60]  # Show completed in last minute
        failed_evals = [e for e in session_evals if e.get('status') == 'failed' and
                       e.get('end_time', 0) > current_time - 60]  # Show failed in last minute
        
        # Display queue status if there are queued/running evaluations
        if queue_status["queue_length"] > 0 or queue_status["current_evaluation"]:
            st.subheader("🏃 Execution Queue Status")
            
            # Show currently running evaluation
            if queue_status["current_evaluation"]:
                current = queue_status["current_evaluation"]
                st.info(f"▶️ Currently Running: **{current['name']}** (ID: {current['id']})")
            
            # Show queued evaluations
            if queue_status["queue_length"] > 0:
                st.info(f"⏳ Queued Evaluations: **{queue_status['queue_length']}**")
                with st.expander("View Queued Evaluations"):
                    for i, queued_eval in enumerate(queue_status["queued_evaluations"], 1):
                        st.write(f"{i}. {queued_eval['name']} (ID: {queued_eval['id']})") 
            
            st.divider()
        
        # Display active and recent evaluations
        st.subheader("Active & Recent Evaluations")
        all_display_evals = active_evals + completed_evals + failed_evals
        
        if not all_display_evals:
            st.info("No active evaluations in this session. Go to Setup tab to create and run evaluations.")
        else:
            dashboard_logger.info(f"Displaying {len(all_display_evals)} evaluations (Active: {len(active_evals)}, " +
                                  f"Recently Completed: {len(completed_evals)}, Failed: {len(failed_evals)})")
            
            # Display evaluations with status indicators
            for i, eval_config in enumerate(all_display_evals):
                # Highlight the evaluation if it matches the one clicked in a notification
                highlight_style = ""
                if "highlight_eval_id" in st.session_state and st.session_state.highlight_eval_id == eval_config["id"]:
                    highlight_style = "border: 2px solid #FFA500; background-color: rgba(255, 165, 0, 0.1); border-radius: 5px; padding: 10px;"
                    # Clear the highlight after showing it once
                    st.session_state.highlight_eval_id = None
                
                with st.container():
                    if highlight_style:
                        st.markdown(f'<div style="{highlight_style}">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        # Display status as colored indicator
                        status = eval_config.get('status', 'unknown')
                        
                        # Check if this evaluation has a report to link to
                        has_report = (status == "completed" and 
                                     'results' in eval_config and 
                                     eval_config['results'] and 
                                     os.path.exists(eval_config['results']))
                        
                        # Display name - as link if report exists
                        if has_report:
                            report_path = eval_config['results']
                            file_url = f"{os.path.abspath(report_path)}"
                            st.markdown(f"**[{eval_config['name']}]({file_url})**", unsafe_allow_html=True)
                        else:
                            st.write(f"**{eval_config['name']}**")
                        
                        # Display status indicator
                        if status in ['in-progress', 'running']:
                            st.markdown("🔄 **Status**: <span style='color:blue'>In Progress 🔄</span>", unsafe_allow_html=True)
                        elif status == "failed":
                            st.markdown("❌ **Status**: <span style='color:red'>Failed ❌</span>", unsafe_allow_html=True)
                        elif status == "completed":
                            st.markdown("✅ **Status**: <span style='color:green'>Completed ✅</span>", unsafe_allow_html=True)
                        elif status == "queued":
                            st.markdown("⏳ **Status**: <span style='color:purple'>Queued ⏳</span>", unsafe_allow_html=True)
                        elif status == "running":
                            st.markdown("🔄 **Status**: <span style='color:blue'>Running</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"⚠️ **Status**: {status.capitalize()}")
                    
                    with col2:
                        # Display details
                        st.write(f"Task: {eval_config['task_type']}")
                        st.write(f"Models: {len(eval_config['selected_models'])}")
                        
                        # Display elapsed time if available
                        if 'start_time' in eval_config:
                            end_time = eval_config.get('end_time', time.time())
                            elapsed = end_time - eval_config['start_time']
                            st.write(f"Elapsed: {self._format_time(elapsed)}")
                    
                    with col3:
                        # For completed evaluations, show report status
                        if status == "completed":
                            # Check if a report already exists
                            if 'results' in eval_config and eval_config['results'] and os.path.exists(eval_config['results']):
                                # Log that we have a report
                                dashboard_logger.info(f"Evaluation has report: {eval_config['results']}")
                                st.markdown("📊 **Report Available**", unsafe_allow_html=True)
                        
                        # Add view logs button
                        if 'logs_dir' in eval_config and os.path.exists(eval_config['logs_dir']):
                            if st.button("View Logs", key=f"logs_{i}"):
                                self._show_logs(eval_config)
                                dashboard_logger.info(f"Showing logs for evaluation {eval_config['id']}")
                        
                        # Debug button to view full evaluation details
                        if st.button("Debug Info", key=f"debug_{i}"):
                            dashboard_logger.info(f"Showing debug info for evaluation {eval_config['id']}")
                            with st.expander("Evaluation Details"):
                                st.json({k: str(v) if k == 'csv_data' else v for k, v in eval_config.items()})
                
                # Show error if present
                if 'error' in eval_config and eval_config['error']:
                    with st.expander("❌ Show Error Details", expanded=True):
                        st.error(f"**Error:** {eval_config['error']}")
                        if 'start_time' in eval_config:
                            error_time = datetime.fromtimestamp(eval_config.get('updated_at', time.time()) if isinstance(eval_config.get('updated_at'), (int, float)) else time.time())
                            st.caption(f"Error occurred at: {error_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        dashboard_logger.error(f"Evaluation {eval_config['id']} error: {eval_config['error']}")
                
                # Show additional status info for running/queued evaluations
                if status in ['running', 'queued']:
                    with st.expander("📊 Status Details"):
                        if 'start_time' in eval_config and eval_config['start_time']:
                            start_time = datetime.fromtimestamp(eval_config['start_time'])
                            st.write(f"**Started:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if 'updated_at' in eval_config:
                            if isinstance(eval_config['updated_at'], str):
                                try:
                                    updated_time = datetime.fromisoformat(eval_config['updated_at'])
                                    st.write(f"**Last Updated:** {updated_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                except:
                                    pass
                        
                        st.write(f"**Configuration:**")
                        st.write(f"- Models: {len(eval_config.get('selected_models', []))}")
                        st.write(f"- Judge Models: {len(eval_config.get('judge_models', []))}")
                        st.write(f"- Parallel Calls: {eval_config.get('parallel_calls', 'N/A')}")
                        st.write(f"- Invocations per Scenario: {eval_config.get('invocations_per_scenario', 'N/A')}")
                
                # Close the highlight div if it was opened
                if "highlight_eval_id" in st.session_state and st.session_state.highlight_eval_id == eval_config["id"]:
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.divider()
            
        
        # Display Available Evaluations Section
        st.subheader("Available Evaluations")
        
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
                    name_field = f"<a href='{report_links[eval_config['id']]}'>{eval_config['name']}</a>"
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
            
            # Add ability to generate comprehensive report from all evaluations
            st.subheader("📊 Generate Report")
            st.info("Generate a aggregated report from all completed evaluations.")
            
            if st.button("🔄 Generate Report", key="gen_comprehensive_report", type="secondary"):
                self._generate_comprehensive_report()
            
            # Add section to run selected evaluations
            st.subheader("Run Evaluations")
            
            # Multiselect for evaluation IDs
            selected_eval_ids = st.multiselect(
                "Select evaluations to run (will execute in order selected)",
                options=[e["id"] for e in available_evals],
                format_func=lambda x: next((e["name"] for e in available_evals if e["id"] == x), x)
            )
            
            if selected_eval_ids:
                st.info(f"Selected {len(selected_eval_ids)} evaluation(s).")
                
                # Show warning if there are already evaluations in queue
                if queue_status["queue_length"] > 0 or queue_status["current_evaluation"]:
                    st.warning(f"⚠️ There are already evaluations running/queued. New evaluations will be added to the queue.")
                
                if st.button("🚀 Add to Execution Queue", key="run_evaluations_btn", type="primary"):
                    self._run_evaluations_linearly(selected_eval_ids)

        st.info(f"📋 Evaluations logs available at: {log_dir}")

        # No automatic reruns - removed auto-refresh logic
    
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
    
    def _generate_comprehensive_report(self):
        """Generate a comprehensive report from all evaluation results in the directory."""
        try:
            # Import the visualize_results module
            from ...visualize_results import create_html_report
            from ..utils.constants import PROJECT_ROOT, DEFAULT_OUTPUT_DIR
            
            # Use the default output directory to look for all results
            output_dir = DEFAULT_OUTPUT_DIR
            if not os.path.isabs(output_dir):
                output_dir = os.path.join(PROJECT_ROOT, output_dir)
            
            # Check if output directory exists and has any CSV files
            if not os.path.exists(output_dir):
                st.error(f"Output directory not found: {output_dir}")
                return
                
            # Look for CSV result files
            csv_files = list(Path(output_dir).glob("*.csv"))
            if not csv_files:
                st.warning(f"No CSV result files found in {output_dir}. Please run some evaluations first.")
                return
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create status indicator
            with st.spinner(f"Generating report from {len(csv_files)} result files... This may take a moment."):
                # Call the report generator with the output directory
                report_path = create_html_report(output_dir, timestamp)
                
                # Find which CSV files were used to generate this comprehensive report
                import glob
                csv_files_used = glob.glob(str(Path(output_dir) / "invocations_*.csv"))
                csv_filenames = [os.path.basename(f) for f in csv_files_used]
                
                # Create a comprehensive report status entry (use timestamp as ID)
                evals_status = {
                    "status": "completed",
                    "results": str(report_path),
                    "evaluations_used_to_generate": csv_filenames,
                    "report_generated_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().timestamp(),
                    "progress": 100
                }
                
                # Save comprehensive report status
                evals_status_file = Path(output_dir) / f"evaluation_report_{timestamp}_status.json"
                try:
                    with open(evals_status_file, 'w') as f:
                        json.dump(evals_status, f)
                except Exception as e:
                    dashboard_logger.error(f"Error saving comprehensive report status: {str(e)}")


                st.success(f"- Report generated: {os.path.basename(str(report_path))}  \n- It includes data from {len(csv_files)} evaluation result files.  \n- Check the **Reports** tab to view all available reports.")

                # Show success message
                # st.success(f"Report generated: {os.path.basename(str(report_path))}")
                # st.info(f"Report includes data from {len(csv_files)} evaluation result files.")
                #
                # # Notify user about Reports tab
                # st.success("Report generated! Check the **Reports** tab to view all available reports.")

                # Set pending rerun to refresh UI
                st.session_state.pending_rerun = True
                
        except Exception as e:
            st.error(f"Error generating comprehensive report: {str(e)}")
            dashboard_logger.exception(f"Error generating comprehensive report: {str(e)}")

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
