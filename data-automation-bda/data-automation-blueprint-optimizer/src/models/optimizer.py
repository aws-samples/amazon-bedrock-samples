"""
Optimizer models for the BDA optimization application.
"""
import json
import traceback
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import os
import pandas as pd
import logging

from src.models.config import BDAConfig, InputField
from src.models.schema import Schema
from src.models.strategy import StrategyManager, FieldData
from src.models.aws import BDAClient
from src.models.field_history import FieldHistoryManager
from src.models.field_type import detect_field_type
from src.prompt_templates import generate_instruction
from src.services.llm_service import LLMService

# Configure logging
logger = logging.getLogger(__name__)


class SequentialOptimizer(BaseModel):
    """
    Sequential BDA optimizer with support for template-based and LLM-based instruction generation.
    """
    config: BDAConfig
    schema: Schema
    bda_client: BDAClient
    strategy_manager: StrategyManager
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime('%Y%m%d_%H%M%S'))
    iteration: int = 0
    use_template: bool = Field(default=False, description="Whether to use template-based instruction generation")
    model_choice: str = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0", description="LLM model to use")
    field_history_manager: FieldHistoryManager = Field(default_factory=FieldHistoryManager, description="Field history manager")
    max_iterations: int = Field(default=5, description="Maximum number of iterations")
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    @classmethod
    def from_config_file(cls, config_file: str, threshold: float = 0.8, use_doc: bool = False, 
                         use_template: bool = False, model_choice: str = None, max_iterations: int = 5) -> "SequentialOptimizer":
        """
        Create a sequential optimizer from a configuration file.
        
        Args:
            config_file: Path to the configuration file
            threshold: Similarity threshold
            use_doc: Whether to use document-based strategy
            use_template: Whether to use template-based instruction generation
            model_choice: LLM model to use
            max_iterations: Maximum number of iterations
            
        Returns:
            SequentialOptimizer: Sequential optimizer
        """
        # Load configuration
        config = BDAConfig.from_file(config_file)
        
        # Create BDA client
        bda_client = BDAClient.from_config(config_file)
        
        # Generate timestamp for this run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create schemas directory if it doesn't exist
        schema_run_dir = f"output/schemas/run_{timestamp}"
        os.makedirs(schema_run_dir, exist_ok=True)
        
        # Get schema from AWS API and save to file
        initial_schema_path = f"{schema_run_dir}/schema_initial.json"
        bda_client.get_blueprint_schema_to_file(initial_schema_path)
        
        # Load schema from the saved file
        schema = Schema.from_file(initial_schema_path)
        
        # Initialize strategy manager
        field_names = [field.field_name for field in config.inputs]
        strategy_manager = StrategyManager.initialize(field_names, threshold, use_doc)
        
        # Initialize field history manager
        field_history_manager = FieldHistoryManager()
        field_history_manager.initialize(field_names)
        
        # Use default model if not provided
        if model_choice is None:
            model_choice = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        return cls(
            config=config,
            schema=schema,
            bda_client=bda_client,
            strategy_manager=strategy_manager,
            timestamp=timestamp,
            use_template=use_template,
            model_choice=model_choice,
            field_history_manager=field_history_manager,
            max_iterations=max_iterations
        )
    
    def extract_field_data(self) -> Dict[str, FieldData]:
        """
        Extract field data from input fields.
        
        Returns:
            Dict[str, FieldData]: Field data by field name
        """
        field_data = {}
        for field in self.config.inputs:
            field_data[field.field_name] = FieldData(
                instruction=field.instruction,
                expected_output=field.expected_output,
                data_in_document=field.data_point_in_document
            )
        return field_data
    
    def generate_instructions(self) -> Dict[str, str]:
        """
        Generate instructions based on current strategies.
        
        Returns:
            Dict[str, str]: Instructions by field name
        """
        if self.use_template:
            return self._generate_template_instructions()
        else:
            return self._generate_llm_instructions()
    
    def _generate_template_instructions(self) -> Dict[str, str]:
        """
        Generate instructions using template-based approach.
        
        Returns:
            Dict[str, str]: Instructions by field name
        """
        field_data = self.extract_field_data()
        original_instructions = {field: data.instruction for field, data in field_data.items()}
        
        instructions = {}
        doc_path = self.config.input_document if self.strategy_manager.use_doc else None
        
        for field_name, strategy in self.strategy_manager.strategies.items():
            if strategy.strategy == "original":
                instructions[field_name] = original_instructions.get(field_name, "")
            elif strategy.strategy == "document" and doc_path:
                # Use document-based strategy with the actual document
                from src.prompt_tuner import rewrite_prompt_bedrock_with_document
                instructions[field_name] = rewrite_prompt_bedrock_with_document(
                    field_name, 
                    original_instructions.get(field_name, ""),
                    field_data.get(field_name).expected_output,
                    doc_path
                )
            else:
                # Use template-based strategy
                instructions[field_name] = generate_instruction(
                    strategy.strategy,
                    field_name,
                    field_data.get(field_name).expected_output
                )
        
        return instructions
    
    def _generate_llm_instructions(self) -> Dict[str, str]:
        """
        Generate instructions using LLM-based approach.
        
        Returns:
            Dict[str, str]: Instructions by field name
        """
        field_data = self.extract_field_data()
        original_instructions = {field: data.instruction for field, data in field_data.items()}
        
        instructions = {}
        doc_path = self.config.input_document if self.strategy_manager.use_doc else None
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        # Initialize LLM service
        llm_service = LLMService(model_id=self.model_choice, region=aws_region)
        # if use doc is on and this is the last iteration use this function to get the results
        if self.iteration > self.max_iterations and self.strategy_manager.use_doc and doc_path:
            # Last attempt with document
            logger.info(f"\n🔍 Using document-based strategy for the final iteration")
            try:
                # Extract document content
                from src.prompt_tuner import extract_text_from_document
                logger.info(f"  📄 Extracting document content from {doc_path}")
                document_content = extract_text_from_document(doc_path)
                logger.info(f"  ✅ Document content extracted ({len(document_content)} characters)")
                fields_not_met_threshold = []
                field_history_list = []
                for field_name, strategy in self.strategy_manager.strategies.items():
                    # Skip fields that meet threshold or have ever met threshold
                    if strategy.meets_threshold or strategy.ever_met_threshold:
                        instructions[field_name] = original_instructions.get(field_name, "")
                        continue
                    fields_not_met_threshold.append( field_name )
                    field_history = self.field_history_manager.get_field_history(field_name)
                    field_history_list.append( field_history )
                logger.info(f"  ✅ Document based strategy for fields {fields_not_met_threshold}")
                _instructions_from_llm = llm_service.generate_docu_based_instruction( fields=fields_not_met_threshold,
                                                                                     fields_datas=field_data,
                                                                                      fields_history_list=field_history_list,
                                                                                     document_content=document_content)
                    # Generate document-based instruction
                logger.info(f"  🧠 Generating document-based instruction ")
                logger.info(f"  🧠 Results from LLM: {_instructions_from_llm}")
                _instructions_from_llm = json.loads(_instructions_from_llm)
                for _instruction in _instructions_from_llm["results"]:
                    instructions[_instruction["field_name"]] = _instruction["instruction"]


                # update instruction for all fields
                #call llm to get the instructions
                logger.info(f"  ✅ Document-based instruction generated: {_instructions_from_llm}")
                return instructions
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error generating document-based instruction: {str(e)}")
                logger.error(f"  ❌ Error generating document-based instruction: {str(e)}")
                logger.info(f"  ⚠️ Falling back to improved instruction without document")
                #print stack trace

                # Fall back to improved instruction
        
        for field_name, strategy in self.strategy_manager.strategies.items():
            # Skip fields that meet threshold or have ever met threshold
            if strategy.meets_threshold or strategy.ever_met_threshold:
                instructions[field_name] = original_instructions.get(field_name, "")
                continue
            
            # Get field data
            expected_output = field_data.get(field_name).expected_output
            
            # Detect field type
            field_type = detect_field_type(field_name, expected_output)
            
            # Get field history
            field_history = self.field_history_manager.get_field_history(field_name)
            
            if not field_history or not field_history.instructions:
                # First attempt - generate initial instruction
                instructions[field_name] = llm_service.generate_initial_instruction(
                    field_name, expected_output, field_type
                )
            # elif self.iteration == self.max_iterations and self.strategy_manager.use_doc and doc_path:
            #     # Last attempt with document
            #     print(f"\n🔍 Using document-based strategy for field '{field_name}' in final iteration")
            #     try:
            #         # Extract document content
            #         from src.prompt_tuner import extract_text_from_document
            #         print(f"  📄 Extracting document content from {doc_path}")
            #         document_content = extract_text_from_document(doc_path)
            #         print(f"  ✅ Document content extracted ({len(document_content)} characters)")
            #
            #         # Generate document-based instruction
            #         print(f"  🧠 Generating document-based instruction for '{field_name}'")
            #         instructions[field_name] = llm_service.generate_document_based_instruction(
            #             field_name,
            #             field_history.instructions,
            #             field_history.results,
            #             expected_output,
            #             document_content,
            #             field_type
            #         )
            #         print(f"  ✅ Document-based instruction generated: '{instructions[field_name]}'")
            #     except Exception as e:
            #         logger.error(f"Error generating document-based instruction: {str(e)}")
            #         print(f"  ❌ Error generating document-based instruction: {str(e)}")
            #         print(f"  ⚠️ Falling back to improved instruction without document")
            #         # Fall back to improved instruction
            #         instructions[field_name] = llm_service.generate_improved_instruction(
            #             field_name,
            #             field_history.instructions,
            #             field_history.results,
            #             expected_output,
            #             field_type
            #         )
            else:
                # Generate improved instruction based on previous attempts
                instructions[field_name] = llm_service.generate_improved_instruction(
                    field_name,
                    field_history.instructions,
                    field_history.results,
                    expected_output,
                    field_type
                )
        
        return instructions
    
    def update_schema_with_instructions(self, instructions: Dict[str, str]) -> str:
        """
        Update schema with new instructions.
        
        Args:
            instructions: Instructions by field name
            
        Returns:
            str: Path to updated schema file
        """
        # Update schema with new instructions
        for field_name, instruction in instructions.items():
            self.schema.update_instruction(field_name, instruction)
        
        # Create run directory if it doesn't exist
        run_dir = f"output/schemas/run_{self.timestamp}"
        os.makedirs(run_dir, exist_ok=True)
        
        # Save updated schema
        output_path = f"{run_dir}/schema_{self.iteration}.json"
        self.schema.to_file(output_path)
        
        logger.info(f"✅ Schema updated and saved to {output_path}")
        return output_path
    
    def update_input_file_with_instructions(self, instructions: Dict[str, str]) -> str:
        """
        Update input file with new instructions.
        
        Args:
            instructions: Instructions by field name
            
        Returns:
            str: Path to updated input file
        """
        # Update input fields with new instructions
        for field in self.config.inputs:
            if field.field_name in instructions:
                field.instruction = instructions[field.field_name]
        
        # Create run directory if it doesn't exist
        run_dir = f"output/inputs/run_{self.timestamp}"
        os.makedirs(run_dir, exist_ok=True)
        
        # Save updated input file
        output_path = f"{run_dir}/input_{self.iteration}.json"
        self.config.to_file(output_path)
        
        logger.info(f"✅ Input file updated and saved to {output_path}")
        return output_path
    
    def run_iteration(self, iteration: int) -> bool:
        """
        Run a single optimization iteration.
        
        Args:
            iteration: Iteration number
            
        Returns:
            bool: Whether to continue optimization
        """
        self.iteration = iteration
        logger.info(f"\n\n🟡 STARTING ITERATION {iteration}")
        
        # Print current strategies
        logger.info("\n📝 Current strategies:")
        for field_name, strategy in self.strategy_manager.strategies.items():
            logger.info(f"  {field_name}: {strategy.strategy}")
        
        # Generate instructions based on current strategies
        instructions = self.generate_instructions()
        
        # Update schema with new instructions
        schema_path = self.update_schema_with_instructions(instructions)
        
        # Update blueprint with new schema
        update_response = self.bda_client.update_test_blueprint(schema_path)
        logger.info(f"Blueprint updated {update_response}")
        if not update_response:
            logger.error(f"❌ Failed to update blueprint for iteration {iteration}")
            return False
        
        # Update input file with new instructions
        input_path = self.update_input_file_with_instructions(instructions)
        
        # Extract input dataframe
        from src.util_sequential import extract_field_data_from_dataframe
        from src.util import extract_inputs_to_dataframe_from_file
        input_df = extract_inputs_to_dataframe_from_file(input_path)
        
        # Run BDA job
        df_with_similarity, similarities, job_success = self.bda_client.run_bda_job(
            input_df,
            iteration,
            self.timestamp
        )
        
        if not job_success:
            logger.error(f"❌ BDA job failed for iteration {iteration}")
            return False
        
        # Update field histories with results
        if df_with_similarity is not None:
            for field_name, similarity in similarities.items():
                instruction = instructions.get(field_name, "")
                result = ""
                
                # Find the result in the dataframe
                field_rows = df_with_similarity[df_with_similarity['Field'] == field_name]
                if not field_rows.empty:
                    result = field_rows.iloc[0].get('extracted_value', "")
                
                # Add attempt to field history
                self.field_history_manager.add_attempt(field_name, instruction, result, similarity)
        
        # Update similarities in strategy manager
        self.strategy_manager.update_similarities(similarities)
        
        # Check if all fields meet threshold
        if self.strategy_manager.all_fields_meet_threshold():
            logger.info(f"\n🎉 All fields meet the threshold! Optimization complete.")
            return False
        
        # If using template-based approach, update strategies
        if self.use_template:
            # Update strategies for fields that don't meet threshold
            strategies_updated = self.strategy_manager.update_strategies()
            
            # If no strategies were updated, we've exhausted all options
            if not strategies_updated:
                logger.info("\n⚠️ No more strategies available. Optimization complete with best effort.")
                return False
        
        # Create strategy report
        report_run_dir = f"output/reports/run_{self.timestamp}"
        os.makedirs(report_run_dir, exist_ok=True)
        report_path = self.strategy_manager.save_report(
            f"{report_run_dir}/report_{iteration}.csv"
        )
        
        return True
    
    def run(self, max_iterations: int = None) -> str:
        """
        Run the optimization process.
        
        Args:
            max_iterations: Maximum number of iterations
            
        Returns:
            str: Path to final strategy report
        """
        # Use instance max_iterations if not provided
        if max_iterations is not None:
            self.max_iterations = max_iterations
        
        logger.info(f"\n🕒 Starting optimization run at {self.timestamp}")
        
        # Create run directories
        schema_run_dir = f"output/schemas/run_{self.timestamp}"
        report_run_dir = f"output/reports/run_{self.timestamp}"
        os.makedirs(schema_run_dir, exist_ok=True)
        os.makedirs(report_run_dir, exist_ok=True)
        
        # Use the initial schema file that was saved during initialization
        initial_schema_path = f"{schema_run_dir}/schema_initial.json"
        
        # Create test blueprint in DEVELOPMENT mode for testing
        blueprint_name = "TestBlueprint-"
        now = datetime.now()
        date_time = now.strftime("%m%d%H%M%S")
        blueprint_name = f"TestBlueprint_{date_time}"
        test_project_name = f"TestBDAProject_{date_time}"
        logger.info(f"\n🔵 Resetting blueprint to original state: {blueprint_name}")
        update_blueprint_response = self.bda_client.create_test_blueprint(blueprint_name)
        blueprint_arn_development = update_blueprint_response["blueprint"]["blueprintArn"]

        if not blueprint_arn_development:
            logger.error("\n❌ Failed to reset blueprint to original state")
            return ""
        
        logger.info("\n🔵 Development Blueprint successfully reset to original")
        logger.info(f"\nThis process will use {'template-based' if self.use_template else 'LLM-based'} instruction generation with a threshold of {self.strategy_manager.threshold}")
        if not self.use_template:
            logger.info(f"Using LLM model: {self.model_choice}")
        if self.strategy_manager.use_doc:
            logger.info("Document-based strategy is enabled as a fallback")
        
        # Main optimization loop
        iteration = 1
        continue_optimization = True
        
        while continue_optimization and iteration <= self.max_iterations:
            continue_optimization = self.run_iteration(iteration)
            iteration += 1

        if continue_optimization and self.strategy_manager.use_doc:
            continue_optimization = self.run_iteration(iteration)

        # Create final strategy report
        final_report_path = self.strategy_manager.save_report(
            f"{report_run_dir}/final_report.csv"
        )
        
        # Save final schema
        final_schema_path = f"{schema_run_dir}/schema_final.json"
        self.schema.to_file(final_schema_path)
        
        logger.info(f"\n⚪️ OPERATION FULLY COMPLETED! Sequential optimization run {self.timestamp} finished.")
        logger.info(f"Final strategy report saved to {final_report_path}")
        
        # Print summary
        logger.info("\n📊 Final Results:")
        all_fields_meet_threshold = True
        for field_name, strategy in self.strategy_manager.strategies.items():
            status = "✅" if strategy.meets_threshold else "  "
            logger.info(f"  {status} {field_name}: {strategy.strategy} strategy, {strategy.similarity:.4f} similarity")
            if not strategy.meets_threshold:
                all_fields_meet_threshold = False

        if all_fields_meet_threshold:
            logger.info("Updating blueprint with optimized instructions meeting the defined threshold")
            self.bda_client.update_customer_blueprint( final_schema_path )

        self.bda_client.delete_test_blueprint()

        return final_report_path
