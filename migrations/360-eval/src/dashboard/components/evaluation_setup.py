"""Evaluation setup component for the Streamlit dashboard."""

import streamlit as st
from ..utils.csv_processor import read_csv_file, get_csv_columns, preview_csv_data
from ..utils.constants import DEFAULT_OUTPUT_DIR
from ..utils.state_management import save_current_evaluation


class EvaluationSetupComponent:
    """Component for setting up a benchmark evaluation from CSV data."""
    
    def render(self):
        """Render the evaluation setup component."""
        
        # Check if we need to load configuration from another evaluation
        if "load_from_eval_config" in st.session_state:
            self._load_configuration(st.session_state.load_from_eval_config)
            del st.session_state.load_from_eval_config
            st.success("Configuration loaded! Please upload a CSV file and enter evaluation name.")
        
        # Evaluation name
        st.text_input(
            "Evaluation Name",
            value=st.session_state.current_evaluation_config["name"],
            key="eval_name",
            on_change=self._update_name,
            help="A descriptive name for this evaluation run. This will be used to identify results and generate reports. Example: 'Customer_Support_Bot_V2'"
        )
        
        # CSV Upload
        st.file_uploader(
            "Upload CSV with prompts and golden answers",
            type=["csv"],
            key="csv_upload",
            on_change=self._process_csv_upload,
            help="Upload a CSV file containing your test data. Each row should have a prompt (question/input) and the expected correct answer (golden answer)."
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
                    on_change=self._update_prompt_column,
                    help="Select the column containing the questions or inputs you want to test the AI model with."
                )
            
            with col2:
                golden_col = st.session_state.current_evaluation_config.get("golden_answer_column")
                st.selectbox(
                    "Golden Answer Column",
                    options=columns,
                    index=None if golden_col is None else columns.index(golden_col) if golden_col in columns else None,
                    key="golden_answer_column",
                    on_change=self._update_golden_answer_column,
                    help="Select the column containing the correct/expected answers that the AI model's responses will be compared against."
                )
            
            # Vision Model Configuration
            st.subheader("Vision Model Configuration")
            
            # Vision model checkbox
            vision_enabled = st.session_state.current_evaluation_config.get("vision_enabled", False)
            st.checkbox(
                "Vision Model",
                value=vision_enabled,
                key="vision_enabled",
                on_change=self._update_vision_enabled,
                help="Enable this option if you want to test vision models that can process images along with text prompts."
            )
            
            # Show image column selector only if vision is enabled
            if st.session_state.current_evaluation_config.get("vision_enabled", False):
                image_col = st.session_state.current_evaluation_config.get("image_column")
                st.selectbox(
                    "Image Column",
                    options=columns,
                    index=None if image_col is None else columns.index(image_col) if image_col in columns else None,
                    key="image_column",
                    on_change=self._update_image_column,
                    help="Select the column containing the base64-encoded images or image file paths to be used with vision models."
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
            help="How many different types of tasks to test. Each task can have different evaluation criteria, temperature, and metrics. Use 1 for simple testing, 2-3 for comprehensive evaluation."
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
                    placeholder="e.g., Summarization, Question-Answering",
                    help="What kind of task is this? Examples: Summarization, Translation, Creative Writing, Code Generation, Question-Answering, Classification"
                )
                
            with col2:
                task_criteria = st.text_area(
                    "Task Criteria",
                    value=task_eval.get("task_criteria", ""),
                    key=f"task_criteria_{i}",
                    placeholder="Specific evaluation instructions",
                    height=100,
                    help="Detailed instructions for how this task should be evaluated. Be specific about what makes a good vs. poor response. Example: 'Summarize the text while preserving all key facts and maintaining a professional tone.'"
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
                    help="Controls randomness in model responses (0.01 = deterministic, 1.0 = very creative)"
                )
                
            with col4:
                user_defined_metrics = st.text_input(
                    "User-Defined Metrics (optional)",
                    value=task_eval.get("user_defined_metrics", ""),
                    key=f"user_defined_metrics_{i}",
                    placeholder="e.g., business writing style, brand adherence",
                    help="Additional custom criteria to evaluate beyond the standard metrics (correctness, completeness, etc.). Separate multiple criteria with commas. Examples: 'professional tone', 'brand voice consistency', 'technical accuracy'"
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
                # Capture the original file name
                st.session_state.current_evaluation_config["csv_file_name"] = st.session_state.csv_upload.name
                # Reset column selections to ensure user explicitly chooses them
                st.session_state.current_evaluation_config["prompt_column"] = None
                st.session_state.current_evaluation_config["golden_answer_column"] = None
                
                # Note: CSV will be saved to disk when configuration is saved
                # This ensures we have a persistent copy for resuming evaluations
    
    def _update_prompt_column(self):
        st.session_state.current_evaluation_config["prompt_column"] = st.session_state.prompt_column
    
    def _update_golden_answer_column(self):
        st.session_state.current_evaluation_config["golden_answer_column"] = st.session_state.golden_answer_column
    
    def _update_vision_enabled(self):
        st.session_state.current_evaluation_config["vision_enabled"] = st.session_state.vision_enabled
        # Reset image column when vision is disabled
        if not st.session_state.vision_enabled:
            st.session_state.current_evaluation_config["image_column"] = None
    
    def _update_image_column(self):
        st.session_state.current_evaluation_config["image_column"] = st.session_state.image_column
    
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

    def _update_failure_threshold(self):
        st.session_state.current_evaluation_config["failure_threshold"] = st.session_state.failure_threshold

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
                # value=st.session_state.current_evaluation_config["parallel_calls"],
                key="adv_parallel_calls",
                on_change=self._update_parallel_calls_adv,
                help="How many API calls to run simultaneously. Higher values = faster execution but may hit rate limits. Start with 4 for most use cases."
            )
            
            # Invocations per scenario
            st.number_input(
                "Invocations per Scenario",
                min_value=1,
                max_value=20,
                value=st.session_state.current_evaluation_config["invocations_per_scenario"],
                key="adv_invocations_per_scenario",
                on_change=self._update_invocations_per_scenario_adv,
                help="How many times to run each test scenario. More invocations = more reliable results but longer execution time. Use 3-5 for production testing."
            )

            # Pass|Failure Threshold
            st.number_input(
                "Pass|Failure Threshold",
                min_value=2,
                max_value=4,
                value=st.session_state.current_evaluation_config["failure_threshold"],
                key="adv_failure_threshold",
                on_change=self._update_failure_threshold_adv,
                help="Value used to define whether an evaluation failed to meet standards, any evaluation metric below this number will be considered failure."
            )
        
        with col2:
            # Sleep between invocations
            st.number_input(
                "Sleep Between Invocations (seconds)",
                min_value=0,
                max_value=300,
                value=st.session_state.current_evaluation_config["sleep_between_invocations"],
                key="adv_sleep_between_invocations",
                on_change=self._update_sleep_between_invocations_adv,
                help="Pause time between API calls to avoid rate limits. Use 60-120 seconds for production APIs, 0-30 for testing. Higher values = slower but more reliable."
            )
            
            # Experiment counts
            st.number_input(
                "Experiment Counts",
                min_value=1,
                max_value=10,
                value=st.session_state.current_evaluation_config["experiment_counts"],
                key="adv_experiment_counts",
                on_change=self._update_experiment_counts_adv,
                help="Number of complete experiment runs to perform. Each run tests all scenarios. More runs = better statistical confidence. Use 1 for quick testing, 3-5 for production."
            )
            
            # Temperature variations
            st.number_input(
                "Temperature Variations",
                min_value=0,
                max_value=5,
                value=st.session_state.current_evaluation_config["temperature_variations"],
                key="adv_temperature_variations",
                on_change=self._update_temperature_variations_adv,
                help="Test different creativity levels automatically. 0 = use exact temperature set per task, 1+ = test additional temperature variants (above and below delta). Use 0 for precise control, 2-3 for comprehensive testing."
            )
            
            # Experiment wait time dropdown
            wait_time_options = {
                "No wait (0 minutes)": 0,
                "30 minutes": 1800,
                "1 hour": 3600,
                "1.5 hours": 5400,
                "2 hours": 7200,
                "2.5 hours": 9000,
                "3 hours": 10800
            }
            
            # Find current selection
            current_wait_time = st.session_state.current_evaluation_config.get("experiment_wait_time", 0)
            current_selection = "No wait (0 minutes)"
            for label, value in wait_time_options.items():
                if value == current_wait_time:
                    current_selection = label
                    break
            
            selected_wait_time = st.selectbox(
                "Experiment Wait Time",
                options=list(wait_time_options.keys()),
                index=list(wait_time_options.keys()).index(current_selection),
                key="adv_experiment_wait_time_dropdown",
                on_change=self._update_experiment_wait_time_adv,
                help="Time to wait between experiment runs. Useful for rate limiting or allowing system recovery between intensive evaluations. Select from 30-minute intervals up to 3 hours."
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

    def _update_failure_threshold_adv(self):
        st.session_state.current_evaluation_config["failure_threshold"] = st.session_state.adv_failure_threshold

    def _update_experiment_wait_time_adv(self):
        """Update experiment wait time based on dropdown selection."""
        wait_time_options = {
            "No wait (0 minutes)": 0,
            "30 minutes": 1800,
            "1 hour": 3600,
            "1.5 hours": 5400,
            "2 hours": 7200,
            "2.5 hours": 9000,
            "3 hours": 10800
        }
        selected_label = st.session_state.adv_experiment_wait_time_dropdown
        st.session_state.current_evaluation_config["experiment_wait_time"] = wait_time_options[selected_label]
    
    def _load_configuration(self, source_config):
        """Load configuration from another evaluation."""
        from datetime import datetime
        from ..utils.constants import (
            DEFAULT_OUTPUT_DIR, DEFAULT_PARALLEL_CALLS,
            DEFAULT_INVOCATIONS_PER_SCENARIO, DEFAULT_SLEEP_BETWEEN_INVOCATIONS,
            DEFAULT_EXPERIMENT_COUNTS, DEFAULT_TEMPERATURE_VARIATIONS, DEFAULT_FAILURE_THRESHOLD
        )
        
        # Just use the single task fields directly
        task_evaluations = [{
            "task_type": source_config.get("task_type", ""),
            "task_criteria": source_config.get("task_criteria", ""),
            "temperature": source_config.get("temperature", 0.7),
            "user_defined_metrics": source_config.get("user_defined_metrics", "")
        }]
        
        # Create a new evaluation config with loaded parameters
        new_config = {
            # New evaluation metadata
            "id": None,  # New evaluation
            "name": f"Benchmark-{datetime.now().strftime('%Y%m%d-%H%M%S')}",  # New default name
            "status": "configuring",
            "progress": 0,
            "created_at": None,
            "updated_at": None,
            "results": None,
            
            # Data fields - need new upload
            "csv_data": None,
            "csv_path": None,
            "csv_file_name": None,
            "prompt_column": None,  # User will select after upload
            "golden_answer_column": None,  # User will select after upload
            
            # Copy all configuration parameters
            "task_type": source_config.get("task_type", ""),
            "task_criteria": source_config.get("task_criteria", ""),
            "task_evaluations": task_evaluations,
            "temperature": source_config.get("temperature", 0.7),
            "user_defined_metrics": source_config.get("user_defined_metrics", ""),
            
            # Copy model and judge configurations - normalize the data structure
            "selected_models": self._normalize_models(source_config.get("selected_models", [])),
            "judge_models": self._normalize_judges(source_config.get("judge_models", [])),
            
            # Copy advanced parameters
            "output_dir": source_config.get("output_dir", DEFAULT_OUTPUT_DIR),
            "parallel_calls": source_config.get("parallel_calls", DEFAULT_PARALLEL_CALLS),
            "invocations_per_scenario": source_config.get("invocations_per_scenario", DEFAULT_INVOCATIONS_PER_SCENARIO),
            "sleep_between_invocations": source_config.get("sleep_between_invocations", DEFAULT_SLEEP_BETWEEN_INVOCATIONS),
            "experiment_counts": source_config.get("experiment_counts", DEFAULT_EXPERIMENT_COUNTS),
            "temperature_variations": source_config.get("temperature_variations", DEFAULT_TEMPERATURE_VARIATIONS),
            "failure_threshold": source_config.get("failure_threshold", DEFAULT_FAILURE_THRESHOLD),
            "experiment_wait_time": source_config.get("experiment_wait_time", 0),
            
            # Copy vision settings
            "vision_enabled": source_config.get("vision_enabled", False),
            "image_column": None  # User will select after upload if vision is enabled
        }
        
        # Update the current evaluation config
        st.session_state.current_evaluation_config = new_config
        
        # Also update the num_tasks to match the loaded task_evaluations
        st.session_state.num_tasks = len(task_evaluations)
        
        # Synchronize widget session state keys with loaded config
        # This ensures the Advanced Configuration tab displays the correct values
        st.session_state.adv_parallel_calls = new_config["parallel_calls"]
        st.session_state.adv_invocations_per_scenario = new_config["invocations_per_scenario"]
        st.session_state.adv_sleep_between_invocations = new_config["sleep_between_invocations"]
        st.session_state.adv_experiment_counts = new_config["experiment_counts"]
        st.session_state.adv_temperature_variations = new_config["temperature_variations"]
        st.session_state.adv_failure_threshold = new_config["failure_threshold"]
    
    def _normalize_models(self, models):
        """Normalize model data structure from loaded configuration."""
        normalized = []
        for model in models:
            # Handle both old format (from loaded profiles) and new format
            normalized.append({
                "id": model.get("model_id") or model.get("id"),
                "region": model.get("region", ""),
                "input_cost": model.get("input_token_cost") or model.get("input_cost", 0),
                "output_cost": model.get("output_token_cost") or model.get("output_cost", 0)
            })
        return normalized
    
    def _normalize_judges(self, judges):
        """Normalize judge data structure from loaded configuration."""
        normalized = []
        for judge in judges:
            # Handle both old format (from loaded profiles) and new format
            normalized.append({
                "id": judge.get("model_id") or judge.get("id"),
                "region": judge.get("region", ""),
                "input_cost": judge.get("input_cost_per_1k") or judge.get("input_cost", 0),
                "output_cost": judge.get("output_cost_per_1k") or judge.get("output_cost", 0)
            })
        return normalized
