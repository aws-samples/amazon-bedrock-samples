"""
Strategy models for the BDA optimization application.
"""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field
import pandas as pd


class FieldData(BaseModel):
    """
    Represents data for a field.
    """
    instruction: str = Field(description="The instruction for extracting this field")
    expected_output: str = Field(description="The expected output for this field")
    data_in_document: bool = Field(description="Whether this field exists in the document")


class FieldStrategy(BaseModel):
    """
    Represents a strategy for a field.
    """
    field_name: str = Field(description="The name of the field")
    strategy: Literal["original", "direct", "context", "format", "document"] = Field(
        description="The current strategy for this field"
    )
    similarity: float = Field(default=0.0, description="The current similarity score")
    meets_threshold: bool = Field(default=False, description="Whether this field meets the threshold")
    ever_met_threshold: bool = Field(default=False, description="Whether this field has ever met the threshold")

    class Config:
        use_enum_values = True


class StrategyManager(BaseModel):
    """
    Manages strategies for fields.
    """
    strategies: Dict[str, FieldStrategy] = Field(default_factory=dict, description="Strategies by field name")
    threshold: float = Field(description="Similarity threshold")
    use_doc: bool = Field(default=False, description="Whether to use document-based strategy")
    
    @classmethod
    def initialize(cls, field_names: List[str], threshold: float, use_doc: bool = False) -> "StrategyManager":
        """
        Initialize strategies for fields.
        
        Args:
            field_names: List of field names
            threshold: Similarity threshold
            use_doc: Whether to use document-based strategy
            
        Returns:
            StrategyManager: Initialized strategy manager
        """
        strategies = {
            field_name: FieldStrategy(
                field_name=field_name,
                strategy="original"
            )
            for field_name in field_names
        }
        return cls(strategies=strategies, threshold=threshold, use_doc=use_doc)
    
    def update_similarities(self, similarities: Dict[str, float]) -> None:
        """
        Update similarity scores for fields.
        
        Args:
            similarities: Dictionary mapping field names to similarity scores
        """
        for field_name, similarity in similarities.items():
            if field_name in self.strategies:
                self.strategies[field_name].similarity = similarity
                meets_threshold = similarity >= self.threshold
                self.strategies[field_name].meets_threshold = meets_threshold
                
                # Once a field meets the threshold, mark it as having ever met the threshold
                if meets_threshold:
                    self.strategies[field_name].ever_met_threshold = True
    
    def update_strategies(self) -> bool:
        """
        Update strategies for fields that don't meet the threshold and have never met the threshold.
        
        Returns:
            bool: Whether any strategies were updated
        """
        from src.prompt_templates import get_next_strategy
        
        updated = False
        
        for field_name, strategy in self.strategies.items():
            # Only update strategies for fields that have never met the threshold and don't currently meet it
            if not strategy.meets_threshold and not strategy.ever_met_threshold:
                current_strategy = strategy.strategy
                next_strategy = get_next_strategy(current_strategy)
                
                # Skip document strategy if use_doc is False
                if next_strategy == "document" and not self.use_doc:
                    next_strategy = None
                    
                if next_strategy:
                    self.strategies[field_name].strategy = next_strategy
                    updated = True
                    print(f"Field '{field_name}' strategy updated: {current_strategy} → {next_strategy}")
                else:
                    print(f"No more strategies available for field '{field_name}'")
            elif strategy.ever_met_threshold and not strategy.meets_threshold:
                # Field has met threshold before but doesn't currently meet it (due to non-deterministic BDA output)
                print(f"Field '{field_name}' has met threshold before, keeping strategy: {strategy.strategy}")
        
        return updated
    
    def all_fields_meet_threshold(self) -> bool:
        """
        Check if all fields meet the threshold.
        
        Returns:
            bool: Whether all fields meet the threshold
        """
        return all(strategy.meets_threshold for strategy in self.strategies.values())
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert strategies to a DataFrame.
        
        Returns:
            pd.DataFrame: DataFrame with strategies
        """
        data = []
        for field_name, strategy in self.strategies.items():
            data.append({
                "Field": field_name,
                "Strategy": strategy.strategy,
                "Similarity": strategy.similarity,
                "Meets Threshold": strategy.meets_threshold,
                "Ever Met Threshold": strategy.ever_met_threshold
            })
        return pd.DataFrame(data)
    
    def save_report(self, output_path: str) -> str:
        """
        Save a report of field strategies and their performance.
        
        Args:
            output_path: Path to save the report
            
        Returns:
            str: Path to the saved report
        """
        from src.util_sequential import create_strategy_report
        
        # Convert strategies to dict format expected by create_strategy_report
        field_strategies = {field: strategy.strategy for field, strategy in self.strategies.items()}
        similarities = {field: strategy.similarity for field, strategy in self.strategies.items()}
        ever_met_thresholds = {field: strategy.ever_met_threshold for field, strategy in self.strategies.items()}
        
        return create_strategy_report(
            field_strategies, 
            similarities, 
            self.threshold, 
            output_path,
            ever_met_thresholds
        )
