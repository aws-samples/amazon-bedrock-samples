"""Evaluation setup component for the Streamlit dashboard."""

import streamlit as st
from ..utils.csv_processor import read_csv_file, get_csv_columns, preview_csv_data
from ..utils.constants import DEFAULT_OUTPUT_DIR
from ..utils.state_management import save_current_evaluation


class EvaluationSetupComponent:
    """Component for setting up a benchmark evaluation from CSV data."""
    
    def render(self):
        """Render the evaluation setup component."""
        
        # Evaluation name
        st.text_input(
            "Evaluation Name",
            value=st.session_state.current_evaluation_config["name"],
            key="eval_name",
            on_change=self._update_name
        )
        
        # CSV Upload
        st.file_uploader(
            "Upload CSV with prompts and golden answers",
            type=["csv"],
            key="csv_upload",
            on_change=self._process_csv_upload
        )
        
        # If CSV data is available, show column selection
        if st.session_state.current_evaluation_config["csv_data"] is not None:
            df = st.session_state.current_evaluation_config["csv_data"]
            columns = get_csv_columns(df)
            
            # Column selection
            col1, col2 = st.columns(2)
            with col1:
                prompt_col = st.session_state.current_evaluation_config.get("prompt_column")
                st.selectbox(
                    "Prompt Column",
                    options=columns,
                    index=None if prompt_col is None else columns.index(prompt_col) if prompt_col in columns else None,
                    key="prompt_column",
                    on_change=self._update_prompt_column
                )
            
            with col2:
                golden_col = st.session_state.current_evaluation_config.get("golden_answer_column")
                st.selectbox(
                    "Golden Answer Column",
                    options=columns,
                    index=None if golden_col is None else columns.index(golden_col) if golden_col in columns else None,
                    key="golden_answer_column",
                    on_change=self._update_golden_answer_column
                )
            
            # Preview CSV data
            st.subheader("Data Preview")
            st.dataframe(preview_csv_data(df), hide_index=True)
        
        # Task type and criteria
        st.text_input(
            "Task Type (e.g., Summarization, Question-Answering, etc.)",
            value=st.session_state.current_evaluation_config["task_type"],
            key="task_type",
            on_change=self._update_task_type
        )
        
        st.text_area(
            "Task Criteria (specific evaluation instructions)",
            value=st.session_state.current_evaluation_config["task_criteria"],
            key="task_criteria",
            on_change=self._update_task_criteria
        )
        
        # Advanced parameters (use subheader instead of expander to avoid nesting)
        st.subheader("Advanced Parameters")
        
        # Use columns for better organization
        col1, col2 = st.columns(2)
        
        with col1:
            # Output directory
            st.text_input(
                "Output Directory",
                value=st.session_state.current_evaluation_config["output_dir"],
                key="output_dir",
                on_change=self._update_output_dir
            )
            
            # Parallel calls
            st.number_input(
                "Parallel API Calls",
                min_value=1,
                max_value=20,
                value=st.session_state.current_evaluation_config["parallel_calls"],
                key="parallel_calls",
                on_change=self._update_parallel_calls
            )
            
            # Invocations per scenario
            st.number_input(
                "Invocations per Scenario",
                min_value=1,
                max_value=20,
                value=st.session_state.current_evaluation_config["invocations_per_scenario"],
                key="invocations_per_scenario",
                on_change=self._update_invocations_per_scenario
            )
        
        with col2:
            # Sleep between invocations
            st.number_input(
                "Sleep Between Invocations (seconds)",
                min_value=0,
                max_value=300,
                value=st.session_state.current_evaluation_config["sleep_between_invocations"],
                key="sleep_between_invocations",
                on_change=self._update_sleep_between_invocations
            )
            
            # Experiment counts
            st.number_input(
                "Experiment Counts",
                min_value=1,
                max_value=10,
                value=st.session_state.current_evaluation_config["experiment_counts"],
                key="experiment_counts",
                on_change=self._update_experiment_counts
            )
            
            # Temperature variations
            st.number_input(
                "Temperature Variations",
                min_value=0,
                max_value=5,
                value=st.session_state.current_evaluation_config["temperature_variations"],
                key="temperature_variations",
                on_change=self._update_temperature_variations
            )
        
        # Custom metrics (full width)
        st.text_input(
            "User-Defined Metrics (comma-separated)",
            value=st.session_state.current_evaluation_config["user_defined_metrics"],
            key="user_defined_metrics",
            help="Additional evaluation metrics beyond the default ones (comma-separated list)",
            on_change=self._update_user_defined_metrics
        )
    
    # Event handlers for state updates
    def _update_name(self):
        st.session_state.current_evaluation_config["name"] = st.session_state.eval_name
    
    def _process_csv_upload(self):
        if st.session_state.csv_upload is not None:
            df = read_csv_file(st.session_state.csv_upload)
            if df is not None:
                st.session_state.current_evaluation_config["csv_data"] = df
                # Reset column selections to ensure user explicitly chooses them
                st.session_state.current_evaluation_config["prompt_column"] = None
                st.session_state.current_evaluation_config["golden_answer_column"] = None
    
    def _update_prompt_column(self):
        st.session_state.current_evaluation_config["prompt_column"] = st.session_state.prompt_column
    
    def _update_golden_answer_column(self):
        st.session_state.current_evaluation_config["golden_answer_column"] = st.session_state.golden_answer_column
    
    def _update_task_type(self):
        st.session_state.current_evaluation_config["task_type"] = st.session_state.task_type
    
    def _update_task_criteria(self):
        st.session_state.current_evaluation_config["task_criteria"] = st.session_state.task_criteria
    
    def _update_output_dir(self):
        st.session_state.current_evaluation_config["output_dir"] = st.session_state.output_dir
    
    def _update_parallel_calls(self):
        st.session_state.current_evaluation_config["parallel_calls"] = st.session_state.parallel_calls
    
    def _update_invocations_per_scenario(self):
        st.session_state.current_evaluation_config["invocations_per_scenario"] = st.session_state.invocations_per_scenario
    
    def _update_sleep_between_invocations(self):
        st.session_state.current_evaluation_config["sleep_between_invocations"] = st.session_state.sleep_between_invocations
    
    def _update_experiment_counts(self):
        st.session_state.current_evaluation_config["experiment_counts"] = st.session_state.experiment_counts
    
    def _update_temperature_variations(self):
        st.session_state.current_evaluation_config["temperature_variations"] = st.session_state.temperature_variations
    
    def _update_user_defined_metrics(self):
        st.session_state.current_evaluation_config["user_defined_metrics"] = st.session_state.user_defined_metrics