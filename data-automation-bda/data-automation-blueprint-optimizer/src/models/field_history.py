"""
Field history models for the BDA optimization application.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class FieldHistory(BaseModel):
    """
    Tracks the history of instructions, results, and similarities for a field.
    """
    field_name: str = Field(description="The name of the field")
    instructions: List[str] = Field(default_factory=list, description="History of instructions")
    results: List[str] = Field(default_factory=list, description="History of results")
    similarities: List[float] = Field(default_factory=list, description="History of similarity scores")
    
    def add_attempt(self, instruction: str, result: str, similarity: float) -> None:
        """
        Add an attempt to the history.
        
        Args:
            instruction: Instruction used
            result: Result obtained
            similarity: Similarity score
        """
        self.instructions.append(instruction)
        self.results.append(result)
        self.similarities.append(similarity)
    
    def get_best_instruction(self) -> Optional[str]:
        """
        Get the instruction with the highest similarity score.
        
        Returns:
            str or None: Best instruction, or None if no attempts
        """
        if not self.similarities:
            return None
        
        # Find index of highest similarity
        best_index = self.similarities.index(max(self.similarities))
        
        return self.instructions[best_index]
    
    def get_last_instruction(self) -> Optional[str]:
        """
        Get the most recent instruction.
        
        Returns:
            str or None: Last instruction, or None if no attempts
        """
        if not self.instructions:
            return None
        
        return self.instructions[-1]
    
    def get_all_attempts(self) -> List[dict]:
        """
        Get all attempts as a list of dictionaries.
        
        Returns:
            List[dict]: List of attempts
        """
        attempts = []
        for i, (instruction, result, similarity) in enumerate(zip(self.instructions, self.results, self.similarities)):
            attempts.append({
                "attempt": i + 1,
                "instruction": instruction,
                "result": result,
                "similarity": similarity
            })
        return attempts

class FieldHistoryManager(BaseModel):
    """
    Manages field histories for all fields.
    """
    histories: dict[str, FieldHistory] = Field(default_factory=dict, description="Field histories by field name")
    
    def initialize(self, field_names: List[str]) -> None:
        """
        Initialize histories for fields.
        
        Args:
            field_names: List of field names
        """
        for field_name in field_names:
            if field_name not in self.histories:
                self.histories[field_name] = FieldHistory(field_name=field_name)
    
    def add_attempt(self, field_name: str, instruction: str, result: str, similarity: float) -> None:
        """
        Add an attempt for a field.
        
        Args:
            field_name: Name of the field
            instruction: Instruction used
            result: Result obtained
            similarity: Similarity score
        """
        if field_name not in self.histories:
            self.histories[field_name] = FieldHistory(field_name=field_name)
        
        self.histories[field_name].add_attempt(instruction, result, similarity)
    
    def get_best_instruction(self, field_name: str) -> Optional[str]:
        """
        Get the best instruction for a field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            str or None: Best instruction, or None if no attempts
        """
        if field_name not in self.histories:
            return None
        
        return self.histories[field_name].get_best_instruction()
    
    def get_field_history(self, field_name: str) -> Optional[FieldHistory]:
        """
        Get the history for a field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            FieldHistory or None: Field history, or None if not found
        """
        return self.histories.get(field_name)
