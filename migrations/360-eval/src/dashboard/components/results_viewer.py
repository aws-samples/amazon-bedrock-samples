"""Results viewer component for the Streamlit dashboard."""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from ..utils.benchmark_runner import sync_evaluations_from_files
from ..utils.constants import DEFAULT_OUTPUT_DIR

class ResultsViewerComponent:
    """Component for viewing evaluation results."""
    
    def render(self):
        """Render the results viewer component."""
        # Sync evaluation statuses from files
        sync_evaluations_from_files()
        
        st.subheader("Completed Evaluations")
        
        # Check if there are any completed evaluations
        completed_evals = [
            e for e in st.session_state.evaluations 
            if e["status"] == "completed"
        ]
        
        if not completed_evals:
            st.info("No completed evaluations yet. Run evaluations to see results here.")
        else:
            # Create a table of completed evaluations
            eval_data = []
            for eval_config in completed_evals:
                # Get model and judge details for display
                models_info = eval_config.get("selected_models", [])
                judges_info = eval_config.get("judge_models", [])
                
                # Create model summary
                if isinstance(models_info, list) and len(models_info) > 0:
                    if isinstance(models_info[0], dict):
                        models_summary = f"{len(models_info)} models"
                        models_details = ", ".join([m.get("model_id", "Unknown") for m in models_info])
                    else:
                        models_summary = f"{len(models_info)} models"
                        models_details = ", ".join(models_info)
                else:
                    models_summary = "0 models"
                    models_details = "None"
                
                # Create judge summary
                if isinstance(judges_info, list) and len(judges_info) > 0:
                    if isinstance(judges_info[0], dict):
                        judges_summary = f"{len(judges_info)} judges"
                        judges_details = ", ".join([j.get("model_id", "Unknown") for j in judges_info])
                    else:
                        judges_summary = f"{len(judges_info)} judges"
                        judges_details = ", ".join(judges_info)
                else:
                    judges_summary = "0 judges"
                    judges_details = "None"
                
                # Extract file name from persistent storage or CSV data
                csv_file_name = "Unknown"
                
                # First check if we have the persisted file name (from status files)
                if eval_config.get("csv_file_name"):
                    csv_file_name = eval_config.get("csv_file_name")
                # Fallback to CSV data if available (for active session)
                elif eval_config.get("csv_data") is not None:
                    csv_file_name = eval_config.get("csv_file_name", "Uploaded CSV")
                elif hasattr(eval_config.get("csv_data"), "name"):
                    csv_file_name = eval_config["csv_data"].name
                
                # Get temperature used
                temperature = eval_config.get("temperature", "Not specified")
                
                # Check if custom metrics were used
                user_metrics = eval_config.get("user_defined_metrics", "")
                has_custom_metrics = "Yes" if user_metrics and user_metrics.strip() else "No"
                
                eval_data.append({
                    "Name": eval_config["name"],
                    "Task Type": eval_config["task_type"],
                    "Data File": csv_file_name,
                    "Temperature": temperature,
                    "Custom Metrics": has_custom_metrics,
                    "Models": models_summary,
                    "Judges": judges_summary,
                    "Completed": pd.to_datetime(eval_config["updated_at"]).strftime("%Y-%m-%d %H:%M")
                })
            
            eval_df = pd.DataFrame(eval_data)
            st.dataframe(eval_df, hide_index=True)
            
            # Add refresh button
            st.button(
                "Refresh Results",
                on_click=sync_evaluations_from_files
            )
            
            # Select an evaluation to view results
            selected_eval_id = st.selectbox(
                "Select evaluation to view results",
                options=[e["id"] for e in completed_evals],
                format_func=lambda x: next((e["name"] for e in completed_evals if e["id"] == x), x)
            )
            
            if selected_eval_id:
                self._show_evaluation_results(selected_eval_id)
    
    def _show_evaluation_results(self, eval_id):
        """Show detailed results for a specific evaluation."""
        # First try to find status file for the most up-to-date information (now in logs directory)
        from ..utils.constants import STATUS_FILES_DIR
        status_dir = Path(STATUS_FILES_DIR)
        
        # Try both composite and legacy formats for status file
        status_file = None
        # First try to find composite format by looking at evaluation name
        for eval_config in st.session_state.evaluations:
            if eval_config["id"] == eval_id:
                eval_name = eval_config.get("name", "")
                composite_id = f"{eval_id}_{eval_name}"
                composite_status_file = status_dir / f"eval_{composite_id}_status.json"
                if composite_status_file.exists():
                    status_file = composite_status_file
                    break
        
        # Fallback to legacy format
        if not status_file:
            legacy_status_file = status_dir / f"eval_{eval_id}_status.json"
            if legacy_status_file.exists():
                status_file = legacy_status_file
        
        
        # Find the evaluation configuration
        eval_config = None
        for e in st.session_state.evaluations:
            if e["id"] == eval_id:
                eval_config = e
                break
        
        if not eval_config:
            st.error("Evaluation not found")
            return
        
        # Display evaluation details
        st.subheader(f"📊 {eval_config['name']}")

        # Display basic info in columns for better layout
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Task Type:** {eval_config.get('task_type', 'Unknown')}")
            st.write(f"**Task Criteria:** {eval_config.get('task_criteria', 'Unknown')}")
            st.write(f"**Status:** {eval_config.get('status', 'Unknown')}")
            
            # Display data file name
            data_file = eval_config.get('csv_file_name', 'Unknown')
            st.write(f"**Data File:** {data_file}")
            
        with col2:
            st.write(f"**Created:** {pd.to_datetime(eval_config.get('created_at', '')).strftime('%Y-%m-%d %H:%M') if eval_config.get('created_at') else 'Unknown'}")
            st.write(f"**Completed:** {pd.to_datetime(eval_config.get('updated_at', '')).strftime('%Y-%m-%d %H:%M') if eval_config.get('updated_at') else 'Unknown'}")
            if eval_config.get('duration'):
                st.write(f"**Duration:** {eval_config['duration']:.1f} seconds")
            
            # Display temperature and custom metrics
            temperature = eval_config.get('temperature', 'Not specified')
            st.write(f"**Temperature:** {temperature}")
            
            user_metrics = eval_config.get('user_defined_metrics', '')
            if user_metrics and user_metrics.strip():
                st.write(f"**Custom Metrics:** {user_metrics}")
            else:
                st.write(f"**Custom Metrics:** None")
        
        # Show error if present
        if eval_config.get('error'):
            st.error(f"**Error:** {eval_config['error']}")
        
        # Display models used
        st.write("#### Models Evaluated")
        models_info = eval_config.get("selected_models", [])
        if isinstance(models_info, list) and len(models_info) > 0:
            if isinstance(models_info[0], dict):
                # New format with complete information
                models_df = pd.DataFrame(models_info)
                st.dataframe(models_df, use_container_width=True, hide_index=True)
            else:
                # Legacy format - just model IDs
                st.write("Models (legacy format):")
                for model in models_info:
                    st.write(f"- {model}")
        else:
            st.write("No model information available")
        
        # Display judges used
        st.write("#### Judge Models")
        judges_info = eval_config.get("judge_models", [])
        if isinstance(judges_info, list) and len(judges_info) > 0:
            if isinstance(judges_info[0], dict):
                # New format with complete information
                judges_df = pd.DataFrame(judges_info)
                st.dataframe(judges_df, use_container_width=True, hide_index=True)
            else:
                # Legacy format - just model IDs
                st.write("Judges (legacy format):")
                for judge in judges_info:
                    st.write(f"- {judge}")
        else:
            st.write("No judge information available")
        
        # Display additional evaluation metadata
        st.write("#### Evaluation Configuration")
        config_col1, config_col2 = st.columns(2)
        with config_col1:
            st.write(f"**Parallel API Calls:** {eval_config.get('parallel_calls', 'Unknown')}")
            st.write(f"**Invocations per Scenario:** {eval_config.get('invocations_per_scenario', 'Unknown')}")
            st.write(f"**Experiment Counts:** {eval_config.get('experiment_counts', 'Unknown')}")
        with config_col2:
            st.write(f"**Temperature Variations:** {eval_config.get('temperature_variations', 'Unknown')}")
            st.write(f"**Failure Threshold:** {eval_config.get('failure_threshold', 'Unknown')}")
            st.write(f"**Sleep Between Invocations:** {eval_config.get('sleep_between_invocations', 'Unknown')}s")
        
        if eval_config.get('user_defined_metrics'):
            st.write(f"**User-Defined Metrics:** {eval_config['user_defined_metrics']}")
        
        # Add Load Config button
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("📋 Load Config", key=f"load_config_{eval_id}", 
                        help="Load this evaluation's configuration to create a new evaluation"):
                st.session_state.load_from_eval_config = eval_config.copy()
                st.session_state.navigate_to_setup = True
                st.rerun()

    
