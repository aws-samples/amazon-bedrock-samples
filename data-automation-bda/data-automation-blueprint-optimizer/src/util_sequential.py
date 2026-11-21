"""
Utility functions for sequential template-based BDA optimization.
"""
import json
import os
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

from src.prompt_templates import generate_instruction, get_next_strategy
from src.prompt_tuner import rewrite_prompt_bedrock_with_document

def initialize_field_strategies(fields: List[str]) -> Dict[str, str]:
    """
    Initialize strategy tracking for each field.
    
    Args:
        fields (List[str]): List of field names
        
    Returns:
        Dict[str, str]: Dictionary mapping field names to their current strategy
    """
    return {field: "original" for field in fields}

def update_field_strategies(
    field_strategies: Dict[str, str], 
    similarities: Dict[str, float], 
    threshold: float,
    use_doc: bool = False
) -> Tuple[Dict[str, str], bool]:
    """
    Update strategies for fields that don't meet the threshold.
    
    Args:
        field_strategies (Dict[str, str]): Current strategies for each field
        similarities (Dict[str, float]): Similarity scores for each field
        threshold (float): Similarity threshold
        use_doc (bool): Whether to use document-based strategy
        
    Returns:
        Tuple[Dict[str, str], bool]: Updated strategies and whether any strategies were updated
    """
    updated = False
    updated_strategies = field_strategies.copy()
    
    for field, similarity in similarities.items():
        if similarity < threshold:
            current_strategy = field_strategies.get(field, "original")
            next_strategy = get_next_strategy(current_strategy)
            
            # Skip document strategy if use_doc is False
            if next_strategy == "document" and not use_doc:
                next_strategy = None
                
            if next_strategy:
                updated_strategies[field] = next_strategy
                updated = True
                print(f"Field '{field}' strategy updated: {current_strategy} → {next_strategy}")
            else:
                print(f"No more strategies available for field '{field}'")
    
    return updated_strategies, updated

def generate_instructions_from_strategies(
    field_strategies: Dict[str, str],
    field_data: Dict[str, Dict[str, str]],
    original_instructions: Dict[str, str],
    doc_path: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate instructions for each field based on its current strategy.
    
    Args:
        field_strategies (Dict[str, str]): Current strategy for each field
        field_data (Dict[str, Dict[str, str]]): Field data including expected output
        original_instructions (Dict[str, str]): Original instructions for each field
        doc_path (str, optional): Path to document for document-based strategy
        
    Returns:
        Dict[str, str]: Generated instructions for each field
    """
    instructions = {}
    
    for field, strategy in field_strategies.items():
        if strategy == "original":
            instructions[field] = original_instructions.get(field, "")
        elif strategy == "document" and doc_path:
            # Use document-based strategy with the actual document
            instructions[field] = rewrite_prompt_bedrock_with_document(
                field, 
                original_instructions.get(field, ""),
                field_data.get(field, {}).get("expected_output", ""),
                doc_path
            )
        else:
            # Use template-based strategy
            instructions[field] = generate_instruction(
                strategy,
                field,
                field_data.get(field, {}).get("expected_output", "")
            )
    
    return instructions

def update_schema_with_field_instructions(
    schema_path: str,
    instructions: Dict[str, str],
    output_path: Optional[str] = None
) -> str:
    """
    Update schema file with new instructions for each field.
    
    Args:
        schema_path (str): Path to original schema file
        instructions (Dict[str, str]): New instructions for each field
        output_path (str, optional): Path to save updated schema
        
    Returns:
        str: Path to updated schema file
    """
    try:
        # Load schema
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Update instructions
        for field, instruction in instructions.items():
            if field in schema.get("properties", {}):
                schema["properties"][field]["instruction"] = instruction
        
        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/schemas/schema_sequential_{timestamp}.json"
        
        # Save updated schema
        with open(output_path, 'w') as f:
            json.dump(schema, f, indent=4)
        
        print(f"✅ Schema updated and saved to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        return schema_path

def update_input_file_with_instructions(
    input_path: str,
    instructions: Dict[str, str],
    output_path: Optional[str] = None
) -> str:
    """
    Update input file with new instructions for each field.
    
    Args:
        input_path (str): Path to original input file
        instructions (Dict[str, str]): New instructions for each field
        output_path (str, optional): Path to save updated input file
        
    Returns:
        str: Path to updated input file
    """
    try:
        # Load input file
        with open(input_path, 'r') as f:
            input_data = json.load(f)
        
        # Update instructions
        for item in input_data.get("inputs", []):
            field_name = item.get("field_name")
            if field_name in instructions:
                item["instruction"] = instructions[field_name]
        
        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/inputs/input_sequential_{timestamp}.json"
        
        # Save updated input file
        with open(output_path, 'w') as f:
            json.dump(input_data, f, indent=4)
        
        print(f"✅ Input file updated and saved to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error updating input file: {e}")
        return input_path

def extract_field_data_from_dataframe(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Extract field data from DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame with field data
        
    Returns:
        Dict[str, Dict[str, Any]]: Field data organized by field name
    """
    field_data = {}
    
    for _, row in df.iterrows():
        field_name = row.get('Field') or row.get('field_name')
        if field_name:
            field_data[field_name] = {
                "instruction": row.get('Instruction') or row.get('instruction', ""),
                "expected_output": row.get('Expected Output') or row.get('expected_output', ""),
                "data_in_document": row.get('Data in Document') or row.get('data_point_in_document', True)
            }
    
    return field_data

def extract_similarities_from_dataframe(df: pd.DataFrame) -> Dict[str, float]:
    """
    Extract similarity scores from DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame with similarity scores
        
    Returns:
        Dict[str, float]: Similarity scores organized by field name
    """
    similarities = {}
    
    for _, row in df.iterrows():
        field_name = row.get('Field')
        if field_name and 'semantic_similarity' in row:
            similarities[field_name] = float(row['semantic_similarity'])
    
    return similarities

def create_strategy_report(
    field_strategies: Dict[str, str],
    similarities: Dict[str, float],
    threshold: float,
    output_path: Optional[str] = None,
    ever_met_thresholds: Optional[Dict[str, bool]] = None
) -> str:
    """
    Create a report of field strategies and their performance.
    
    Args:
        field_strategies (Dict[str, str]): Current strategy for each field
        similarities (Dict[str, float]): Similarity scores for each field
        threshold (float): Similarity threshold
        output_path (str, optional): Path to save report
        ever_met_thresholds (Dict[str, bool], optional): Whether each field has ever met the threshold
        
    Returns:
        str: Path to report file
    """
    try:
        # Create report data
        report_data = []
        for field, strategy in field_strategies.items():
            similarity = similarities.get(field, 0.0)
            meets_threshold = similarity >= threshold
            
            # Create report entry
            report_entry = {
                "Field": field,
                "Strategy": strategy,
                "Similarity": similarity,
                "Meets Threshold": meets_threshold
            }
            
            # Add ever_met_threshold if provided
            if ever_met_thresholds is not None and field in ever_met_thresholds:
                report_entry["Ever Met Threshold"] = ever_met_thresholds[field]
                
            report_data.append(report_entry)
        
        # Convert to DataFrame
        report_df = pd.DataFrame(report_data)
        
        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/reports/strategy_report_{timestamp}.csv"
        
        # Save report
        report_df.to_csv(output_path, index=False)
        
        print(f"✅ Strategy report saved to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error creating strategy report: {e}")
        return ""
