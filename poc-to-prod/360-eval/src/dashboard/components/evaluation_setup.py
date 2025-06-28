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
        
        # Task evaluations section
        st.subheader("Task Evaluations")
        
        # Initialize session state for task counter if not present
        if "task_counter" not in st.session_state:
            st.session_state.task_counter = 1
        
        # Initialize task_evaluations if not present
        if "task_evaluations" not in st.session_state.current_evaluation_config:
            st.session_state.current_evaluation_config["task_evaluations"] = [{"task_type": "", "task_criteria": "", "temperature": 0.7, "user_defined_metrics": ""}]
        
        # Initialize number of tasks if not present
        if "num_tasks" not in st.session_state:
            st.session_state.num_tasks = len(st.session_state.current_evaluation_config["task_evaluations"])
        
        # Number input to control how many task evaluations
        new_num_tasks = st.number_input(
            "Number of Task Evaluations",
            min_value=1,
            max_value=10,
            value=st.session_state.num_tasks,
            step=1,
            help="Specify how many different task evaluations you want to create"
        )
        
        # Adjust the task evaluations list based on the number input
        if new_num_tasks != st.session_state.num_tasks:
            current_tasks = st.session_state.current_evaluation_config["task_evaluations"]
            
            if new_num_tasks > len(current_tasks):
                # Add new tasks
                for _ in range(new_num_tasks - len(current_tasks)):
                    current_tasks.append({"task_type": "", "task_criteria": "", "temperature": 0.7, "user_defined_metrics": ""})
            elif new_num_tasks < len(current_tasks):
                # Remove tasks
                st.session_state.current_evaluation_config["task_evaluations"] = current_tasks[:new_num_tasks]
            
            st.session_state.num_tasks = new_num_tasks
        
        # Display each task evaluation
        for i in range(st.session_state.num_tasks):
            if i < len(st.session_state.current_evaluation_config["task_evaluations"]):
                task_eval = st.session_state.current_evaluation_config["task_evaluations"][i]
            else:
                task_eval = {"task_type": "", "task_criteria": "", "temperature": 0.7, "user_defined_metrics": ""}
                st.session_state.current_evaluation_config["task_evaluations"].append(task_eval)
            
            # Task separator for visual clarity
            if i > 0:
                st.divider()
            
            st.markdown(f"**Task Evaluation {i + 1}**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                task_type = st.text_input(
                    "Task Type",
                    value=task_eval.get("task_type", ""),
                    key=f"task_type_{i}",
                    placeholder="e.g., Summarization, Question-Answering"
                )
                
            with col2:
                task_criteria = st.text_area(
                    "Task Criteria",
                    value=task_eval.get("task_criteria", ""),
                    key=f"task_criteria_{i}",
                    placeholder="Specific evaluation instructions",
                    height=100
                )
            
            # Second row for temperature and user-defined metrics
            col3, col4 = st.columns(2)
            
            with col3:
                temperature = st.slider(
                    "Temperature",
                    min_value=0.01,
                    max_value=1.0,
                    value=task_eval.get("temperature", 0.5),
                    step=0.1,
                    key=f"temperature_{i}",
                    help="Controls randomness in model responses (0.0 = deterministic, 2.0 = very random)"
                )
                
            with col4:
                user_defined_metrics = st.text_input(
                    "User-Defined Metrics (optional)",
                    value=task_eval.get("user_defined_metrics", ""),
                    key=f"user_defined_metrics_{i}",
                    placeholder="e.g., business writing style, brand adherence",
                    help="Comma-separated additional evaluation metrics for this task"
                )
            
            # Update the task evaluation in session state
            st.session_state.current_evaluation_config["task_evaluations"][i] = {
                "task_type": task_type,
                "task_criteria": task_criteria,
                "temperature": temperature,
                "user_defined_metrics": user_defined_metrics
            }
    
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
    
    # No longer need add/remove methods - handled by number input
    
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
    
    def render_advanced_config(self):
        """Render the advanced configuration section as a separate tab."""
        
        st.markdown("### Advanced Parameters")
        st.markdown("Configure advanced settings for your evaluation.")
        
        # Use columns for better organization
        col1, col2 = st.columns(2)
        
        with col1:
            # Parallel calls
            st.number_input(
                "Parallel API Calls",
                min_value=1,
                max_value=20,
                value=st.session_state.current_evaluation_config["parallel_calls"],
                key="adv_parallel_calls",
                on_change=self._update_parallel_calls_adv
            )
            
            # Invocations per scenario
            st.number_input(
                "Invocations per Scenario",
                min_value=1,
                max_value=20,
                value=st.session_state.current_evaluation_config["invocations_per_scenario"],
                key="adv_invocations_per_scenario",
                on_change=self._update_invocations_per_scenario_adv
            )
        
        with col2:
            # Sleep between invocations
            st.number_input(
                "Sleep Between Invocations (seconds)",
                min_value=0,
                max_value=300,
                value=st.session_state.current_evaluation_config["sleep_between_invocations"],
                key="adv_sleep_between_invocations",
                on_change=self._update_sleep_between_invocations_adv
            )
            
            # Experiment counts
            st.number_input(
                "Experiment Counts",
                min_value=1,
                max_value=10,
                value=st.session_state.current_evaluation_config["experiment_counts"],
                key="adv_experiment_counts",
                on_change=self._update_experiment_counts_adv
            )
            
            # Temperature variations
            st.number_input(
                "Temperature Variations",
                min_value=0,
                max_value=5,
                value=st.session_state.current_evaluation_config["temperature_variations"],
                key="adv_temperature_variations",
                on_change=self._update_temperature_variations_adv
            )
        
    
    # Advanced configuration event handlers with different keys
    def _update_parallel_calls_adv(self):
        st.session_state.current_evaluation_config["parallel_calls"] = st.session_state.adv_parallel_calls
    
    def _update_invocations_per_scenario_adv(self):
        st.session_state.current_evaluation_config["invocations_per_scenario"] = st.session_state.adv_invocations_per_scenario
    
    def _update_sleep_between_invocations_adv(self):
        st.session_state.current_evaluation_config["sleep_between_invocations"] = st.session_state.adv_sleep_between_invocations
    
    def _update_experiment_counts_adv(self):
        st.session_state.current_evaluation_config["experiment_counts"] = st.session_state.adv_experiment_counts
    
    def _update_temperature_variations_adv(self):
        st.session_state.current_evaluation_config["temperature_variations"] = st.session_state.adv_temperature_variations
    
