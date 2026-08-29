"""
Schema models for the BDA optimization application.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class SchemaProperty(BaseModel):
    """
    Represents a property in the JSON schema.
    """
    type: str = Field(description="The data type of the property")
    inferenceType: str = Field(description="The inference type (e.g., 'explicit')")
    instruction: str = Field(description="The instruction for extracting this property")


class Schema(BaseModel):
    """
    Represents the JSON schema for the blueprint.
    """
    schema: str = Field(default="http://json-schema.org/draft-07/schema#", alias="$schema", description="The JSON schema version")
    description: str = Field(description="Description of the document")
    class_: str = Field(alias="class", description="The document class")
    type: str = Field(default="object", description="The schema type")
    definitions: Dict[str, Any] = Field(default_factory=dict, description="Schema definitions")
    properties: Dict[str, SchemaProperty] = Field(description="Schema properties")

    @classmethod
    def from_file(cls, file_path: str) -> "Schema":
        """
        Load schema from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Schema: Loaded schema
        """
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_file(self, file_path: str) -> None:
        """
        Save schema to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
        """
        import json
        with open(file_path, 'w') as f:
            json.dump(self.model_dump(by_alias=True), f, indent=4)
    
    def update_instruction(self, field_name: str, instruction: str) -> None:
        """
        Update the instruction for a field.
        
        Args:
            field_name: Name of the field
            instruction: New instruction
        """
        if field_name in self.properties:
            self.properties[field_name].instruction = instruction
