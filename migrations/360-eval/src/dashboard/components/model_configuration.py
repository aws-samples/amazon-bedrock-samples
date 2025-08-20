"""Model configuration component for the Streamlit dashboard."""

import streamlit as st
import pandas as pd
from ..utils.constants import (
    DEFAULT_BEDROCK_MODELS, 
    DEFAULT_OPENAI_MODELS,
    DEFAULT_COST_MAP,
    DEFAULT_JUDGES_COST,
    DEFAULT_JUDGES,
    AWS_REGIONS,
    MODEL_TO_REGIONS,
    REGION_TO_MODELS,
    JUDGE_MODEL_TO_REGIONS,
    JUDGE_REGION_TO_MODELS
)
from ..utils.state_management import save_current_evaluation


class ModelConfigurationComponent:
    """Component for configuring models and judge models."""
    
    def __init__(self):
        # Initialize session state for model/region filtering
        if 'selected_bedrock_model' not in st.session_state:
            st.session_state.selected_bedrock_model = None
        if 'filtered_regions' not in st.session_state:
            st.session_state.filtered_regions = list(REGION_TO_MODELS.keys()) if REGION_TO_MODELS else AWS_REGIONS
        if 'filtered_models' not in st.session_state:
            st.session_state.filtered_models = {}
    
    def _on_region_change(self):
        """Handle region selection change and auto-correct model selection."""
        selected_region = st.session_state.aws_region
        if selected_region in REGION_TO_MODELS:
            available_models = REGION_TO_MODELS[selected_region]
            # Auto-select first available model if current selection is invalid
            if st.session_state.selected_bedrock_model not in available_models and available_models:
                st.session_state.selected_bedrock_model = available_models[0]
            st.session_state.filtered_models = available_models
    
    def _on_model_change(self):
        """Handle model selection change and auto-correct region selection."""
        selected_model = st.session_state.bedrock_model_select
        if selected_model in MODEL_TO_REGIONS:
            available_regions = MODEL_TO_REGIONS[selected_model]
            # Auto-select first available region if current selection is invalid
            if st.session_state.aws_region not in available_regions and available_regions:
                st.session_state.aws_region = available_regions[0]
            st.session_state.filtered_regions = available_regions
    
    def render(self):
        """Render the model configuration component."""
        
        # Determine available regions based on selected model
        available_regions = st.session_state.filtered_regions if hasattr(st.session_state, 'filtered_regions') else list(REGION_TO_MODELS.keys())
        if not available_regions:
            available_regions = AWS_REGIONS
        
        # Region selection with dynamic filtering
        selected_region = st.selectbox(
            "AWS Region",
            options=available_regions,
            index=0 if available_regions else 0,
            key="aws_region",
            on_change=self._on_region_change
        )
        
        # Available models tabs (Bedrock, OpenAI)
        tab1, tab2 = st.tabs(["Bedrock Models", "Other Models"])
        
        with tab1:
            # Get models available in selected region
            if selected_region in REGION_TO_MODELS:
                bedrock_models = REGION_TO_MODELS[selected_region]
            else:
                bedrock_models = [model[0] for model in DEFAULT_BEDROCK_MODELS]
            self._render_model_dropdown(bedrock_models, "bedrock", selected_region)
        
        with tab2:
            openai_models = [model[0] for model in DEFAULT_OPENAI_MODELS]
            self._render_model_dropdown(openai_models, "openai", selected_region)
        
        # Selected models display
        st.subheader("Selected Models")
        if not st.session_state.current_evaluation_config["selected_models"]:
            st.info("No models selected. Please select at least one model to evaluate.")
        else:
            selected_models_df = pd.DataFrame(st.session_state.current_evaluation_config["selected_models"])
            selected_models_df = selected_models_df.rename(columns={
                "id": "Model ID",
                "region": "AWS Region",
                "input_cost": "Input Cost (per token)",
                "output_cost": "Output Cost (per token)"
            })
            st.dataframe(selected_models_df, hide_index=True)
            
            # Button to remove all selected models
            st.button(
                "Clear Selected Models",
                on_click=self._clear_selected_models
            )
        
        # Judge model selection
        st.subheader("Judge Models")
        self._render_judge_selection(selected_region)
        
        # If we have selected judge models, display them
        if st.session_state.current_evaluation_config["judge_models"]:
            judge_models_df = pd.DataFrame(st.session_state.current_evaluation_config["judge_models"])
            judge_models_df = judge_models_df.rename(columns={
                "id": "Model ID",
                "region": "AWS Region",
                "input_cost": "Input Cost (per token)",
                "output_cost": "Output Cost (per token)"
            })
            st.dataframe(judge_models_df, hide_index=True)
            
            # Button to remove all judge models
            st.button(
                "Clear Judge Models",
                on_click=self._clear_judge_models,
                key="clear_judges"
            )
        
        # Show validation status
        is_valid = self._is_configuration_valid()
        missing_items = self._get_missing_configuration_items()
        
        if not is_valid and missing_items:
            st.warning(f"Please complete the following before saving: {', '.join(missing_items)}")
        
        # Action buttons - only save and reset, no direct run
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "Save Configuration",
                disabled=not is_valid,
            ):
                save_current_evaluation()
                st.success(f"Configuration profile saved successfully!")
                # Debug information
                print(f"Saved configuration to session state. Total evaluations: {len(st.session_state.evaluations)}")
                print(f"Evaluation IDs: {[e['id'] for e in st.session_state.evaluations]}")
        
        with col2:
            st.button(
                "Reset Configuration",
                on_click=self._reset_configuration
            )
    
    def _render_model_dropdown(self, model_list, prefix, region):
        """Render the model selection UI with dropdown."""
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            if prefix == "bedrock":
                # For Bedrock models, add on_change callback
                selected_model = st.selectbox(
                    "Select Model",
                    options=model_list if model_list else ["No models available in this region"],
                    key=f"{prefix}_model_select",
                    on_change=self._on_model_change if model_list else None,
                    disabled=not model_list
                )
            else:
                # For non-Bedrock models, no region filtering
                selected_model = st.selectbox(
                    "Select Model",
                    options=model_list,
                    key=f"{prefix}_model_select"
                )
        
        # Get default costs
        default_input_cost = DEFAULT_COST_MAP.get(selected_model, {"input": 0.001, "output": 0.002})["input"]
        default_output_cost = DEFAULT_COST_MAP.get(selected_model, {"input": 0.001, "output": 0.002})["output"]
        
        with col2:
            input_cost = st.number_input(
                "Input Cost",
                min_value=0.0,
                max_value=1.0,
                value=default_input_cost,
                step=0.0001,
                format="%.6f",
                key=f"{prefix}_input_cost"
            )
        
        with col3:
            output_cost = st.number_input(
                "Output Cost",
                min_value=0.0,
                max_value=1.0,
                value=default_output_cost,
                step=0.0001,
                format="%.6f",
                key=f"{prefix}_output_cost"
            )
        
        with col4:
            st.button(
                "Add Model",
                key=f"{prefix}_add_model",
                on_click=self._add_model,
                args=(selected_model, region, input_cost, output_cost)
            )
    
    def _render_judge_selection(self, region):
        """Render the judge model selection UI."""
        # Ignore the passed region parameter - use judge's own regions from config
        judge_options = [m[0] for m in DEFAULT_JUDGES]
        judge_regions = {m[0]: m[1] for m in DEFAULT_JUDGES}
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            selected_judge = st.selectbox(
                "Select Judge Model",
                options=judge_options,
                key="judge_model_select"
            )
        
        # Handle case where selectbox returns index instead of value
        if isinstance(selected_judge, int):
            selected_judge = judge_options[selected_judge] if selected_judge < len(judge_options) else judge_options[0]
        
        # Get default costs and region from judge config
        default_input_cost = DEFAULT_JUDGES_COST.get(selected_judge, {"input": 0.001, "output": 0.002})["input"]
        default_output_cost = DEFAULT_JUDGES_COST.get(selected_judge, {"input": 0.001, "output": 0.002})["output"]
        # Use the judge's predefined region from the config file
        judge_region = judge_regions.get(selected_judge, "us-east-1")
        with col2:
            judge_input_cost = st.number_input(
                "Input Cost",
                min_value=0.0,
                max_value=1.0,
                value=default_input_cost,
                step=0.0001,
                format="%.6f",
                key="judge_input_cost"
            )
        
        with col3:
            judge_output_cost = st.number_input(
                "Output Cost",
                min_value=0.0,
                max_value=1.0,
                value=default_output_cost,
                step=0.0001,
                format="%.6f",
                key="judge_output_cost"
            )
        
        with col4:
            st.button(
                "Add Judge",
                key="add_judge",
                on_click=self._add_judge_model,
                args=(selected_judge, judge_region, judge_input_cost, judge_output_cost)
            )
    
    def _add_model(self, model_id, region, input_cost, output_cost):
        """Add a model to the selected models list."""
        # Check if model is already selected with same region
        for model in st.session_state.current_evaluation_config["selected_models"]:
            # Check if the model ID matches and either region matches or isn't present
            if model["id"] == model_id and model.get("region", "") == region:
                # Update costs and region if model already exists
                model["input_cost"] = input_cost
                model["output_cost"] = output_cost
                model["region"] = region
                return
        
        # Add new model
        st.session_state.current_evaluation_config["selected_models"].append({
            "id": model_id,
            "region": region,
            "input_cost": input_cost,
            "output_cost": output_cost
        })
    
    def _add_judge_model(self, model_id, region, input_cost, output_cost):
        """Add a judge model to the judge models list."""
        # Check if model is already selected with same region
        for model in st.session_state.current_evaluation_config["judge_models"]:
            # Check if the model ID matches and either region matches or isn't present
            if model["id"] == model_id and model.get("region", "") == region:
                # Update costs and region if model already exists
                model["input_cost"] = input_cost
                model["output_cost"] = output_cost
                model["region"] = region
                return
        
        # Add new model
        st.session_state.current_evaluation_config["judge_models"].append({
            "id": model_id,
            "region": region,
            "input_cost": input_cost,
            "output_cost": output_cost
        })
    
    def _clear_selected_models(self):
        """Clear all selected models."""
        st.session_state.current_evaluation_config["selected_models"] = []
    
    def _clear_judge_models(self):
        """Clear all judge models."""
        st.session_state.current_evaluation_config["judge_models"] = []
    
    def _reset_configuration(self):
        """Reset the current configuration to default values."""
        # Keep CSV data and column selections, reset everything else
        csv_data = st.session_state.current_evaluation_config["csv_data"]
        prompt_column = st.session_state.current_evaluation_config["prompt_column"]
        golden_answer_column = st.session_state.current_evaluation_config["golden_answer_column"]
        
        st.session_state.current_evaluation_config = {
            "id": None,
            "name": f"Benchmark-{pd.Timestamp.now().strftime('%Y%m%d')}",
            "csv_data": csv_data,
            "prompt_column": prompt_column,
            "golden_answer_column": golden_answer_column,
            "task_type": "",
            "task_criteria": "",
            "output_dir": st.session_state.current_evaluation_config["output_dir"],
            "parallel_calls": st.session_state.current_evaluation_config["parallel_calls"],
            "invocations_per_scenario": st.session_state.current_evaluation_config["invocations_per_scenario"],
            "sleep_between_invocations": st.session_state.current_evaluation_config["sleep_between_invocations"],
            "experiment_counts": st.session_state.current_evaluation_config["experiment_counts"],
            "temperature_variations": st.session_state.current_evaluation_config["temperature_variations"],
            "failure_threshold": st.session_state.current_evaluation_config["failure_threshold"],
            "selected_models": [],
            "judge_models": [],
            "user_defined_metrics": "",
            "status": "configuring",
            "progress": 0,
            "created_at": None,
            "updated_at": None,
            "results": None
        }
    
    def _get_missing_configuration_items(self):
        """Get a list of missing configuration items."""
        config = st.session_state.current_evaluation_config
        missing_items = []
        
        # Check for CSV data with prompt and golden answer columns
        if config["csv_data"] is None:
            missing_items.append("CSV data")
        elif not config["prompt_column"] or not config["golden_answer_column"]:
            missing_items.append("prompt and golden answer column selection")
        
        # Check for task type and criteria (support both old and new format)
        task_evaluations = config.get("task_evaluations", [])
        if task_evaluations:
            # New format: check each task evaluation
            for i, task_eval in enumerate(task_evaluations):
                if not task_eval.get("task_type", "").strip():
                    missing_items.append(f"task type for evaluation {i+1}")
                if not task_eval.get("task_criteria", "").strip():
                    missing_items.append(f"task criteria for evaluation {i+1}")
        else:
            # Fallback to old format for backward compatibility
            if not config.get("task_type", "").strip():
                missing_items.append("task type")
            if not config.get("task_criteria", "").strip():
                missing_items.append("task criteria")
        
        # Check for at least one target model
        if not config["selected_models"]:
            missing_items.append("at least one target model")
        
        # Check for at least one judge model
        if not config["judge_models"]:
            missing_items.append("at least one judge model")
        
        return missing_items
    
    def _is_configuration_valid(self):
        """Check if the current configuration is valid."""
        return len(self._get_missing_configuration_items()) == 0
    
