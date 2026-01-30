"""
Data models for thread management in the AR Chatbot.
"""
from dataclasses import dataclass, field
from datetime import datetime as dt
import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

def datetime_utc():
    return dt.now(datetime.UTC)


class ThreadStatus(Enum):
    """Status of a conversation thread."""
    PROCESSING = "PROCESSING"
    AWAITING_USER_INPUT = "AWAITING_USER_INPUT"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class IterationType(Enum):
    """Type of iteration in the rewriting process."""
    AR_FEEDBACK = "ar_feedback"
    USER_CLARIFICATION = "user_clarification"


@dataclass
class Finding:
    """Represents a validation finding from AR checks."""
    validation_output: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "validation_output": self.validation_output,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Finding':
        """Create Finding from dictionary."""
        return cls(
            validation_output=data["validation_output"],
            details=data.get("details", {})
        )


@dataclass
class QuestionAnswerExchange:
    """Represents a question-answer exchange between LLM and user."""
    questions: List[str]
    answers: Optional[List[str]] = None
    skipped: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "questions": self.questions,
            "answers": self.answers,
            "skipped": self.skipped
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuestionAnswerExchange':
        """Create QuestionAnswerExchange from dictionary."""
        return cls(
            questions=data["questions"],
            answers=data.get("answers"),
            skipped=data.get("skipped", False)
        )


@dataclass
class ARIterationData:
    """Data specific to AR feedback iterations."""
    findings: List[Finding]
    validation_output: str
    processed_finding_index: int = 0  # NEW - which finding was processed in this iteration
    llm_decision: str = "REWRITE"  # NEW - LLM's decision: "REWRITE" or "ASK_QUESTIONS"
    iteration_type: str = "rewriting"  # NEW - iteration type: "initial", "rewriting", or "follow-up-question"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "validation_output": self.validation_output,
            "processed_finding_index": self.processed_finding_index,
            "llm_decision": self.llm_decision,
            "iteration_type": self.iteration_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ARIterationData':
        """Create ARIterationData from dictionary."""
        return cls(
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
            validation_output=data["validation_output"],
            processed_finding_index=data.get("processed_finding_index", 0),
            llm_decision=data.get("llm_decision", "REWRITE"),
            iteration_type=data.get("iteration_type", "rewriting")
        )


@dataclass
class ClarificationIterationData:
    """Data specific to user clarification iterations."""
    qa_exchange: QuestionAnswerExchange
    context_augmentation: Optional[str] = None
    processed_finding_index: Optional[int] = None
    llm_decision: Optional[str] = None
    validation_output: Optional[str] = None  # NEW - validation result after clarification
    validation_findings: List[Finding] = field(default_factory=list)  # NEW - findings after clarification
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "qa_exchange": self.qa_exchange.to_dict(),
            "context_augmentation": self.context_augmentation,
            "processed_finding_index": self.processed_finding_index,
            "llm_decision": self.llm_decision,
            "validation_output": self.validation_output,
            "validation_findings": [f.to_dict() for f in self.validation_findings]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClarificationIterationData':
        """Create ClarificationIterationData from dictionary."""
        return cls(
            qa_exchange=QuestionAnswerExchange.from_dict(data["qa_exchange"]),
            context_augmentation=data.get("context_augmentation"),
            processed_finding_index=data.get("processed_finding_index"),
            llm_decision=data.get("llm_decision"),
            validation_output=data.get("validation_output"),
            validation_findings=[Finding.from_dict(f) for f in data.get("validation_findings", [])]
        )


@dataclass
class TypedIteration:
    """Represents a single typed validation/rewriting iteration."""
    iteration_number: int
    iteration_type: IterationType
    original_answer: str  # The answer being rewritten
    rewritten_answer: str  # The new answer after rewriting
    rewriting_prompt: str  # The prompt that generated the rewritten answer
    type_specific_data: Any  # Union[ARIterationData, ClarificationIterationData]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "iteration_number": self.iteration_number,
            "iteration_type": self.iteration_type.value,
            "original_answer": self.original_answer,
            "rewritten_answer": self.rewritten_answer,
            "rewriting_prompt": self.rewriting_prompt,
            "type_specific_data": self.type_specific_data.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TypedIteration':
        """Create TypedIteration from dictionary."""
        iteration_type = IterationType(data["iteration_type"])
        
        # Deserialize type_specific_data based on iteration_type
        type_specific_data_dict = data["type_specific_data"]
        if iteration_type == IterationType.AR_FEEDBACK:
            type_specific_data = ARIterationData.from_dict(type_specific_data_dict)
        elif iteration_type == IterationType.USER_CLARIFICATION:
            type_specific_data = ClarificationIterationData.from_dict(type_specific_data_dict)
        else:
            raise ValueError(f"Unknown iteration type: {iteration_type}")
        
        return cls(
            iteration_number=data["iteration_number"],
            iteration_type=iteration_type,
            original_answer=data["original_answer"],
            rewritten_answer=data["rewritten_answer"],
            rewriting_prompt=data["rewriting_prompt"],
            type_specific_data=type_specific_data
        )


@dataclass
class Iteration:
    """Represents a single validation/rewriting iteration (legacy format)."""
    iteration_number: int
    llm_response: str
    validation_output: str
    findings: List[Finding] = field(default_factory=list)
    rewriting_prompt: Optional[str] = None
    qa_exchange: Optional[QuestionAnswerExchange] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "iteration_number": self.iteration_number,
            "llm_response": self.llm_response,
            "validation_output": self.validation_output,
            "findings": [f.to_dict() for f in self.findings],
            "rewriting_prompt": self.rewriting_prompt,
            "qa_exchange": self.qa_exchange.to_dict() if self.qa_exchange else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Iteration':
        """Create Iteration from dictionary."""
        qa_exchange_data = data.get("qa_exchange")
        return cls(
            iteration_number=data["iteration_number"],
            llm_response=data["llm_response"],
            validation_output=data["validation_output"],
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
            rewriting_prompt=data.get("rewriting_prompt"),
            qa_exchange=QuestionAnswerExchange.from_dict(qa_exchange_data) if qa_exchange_data else None
        )


@dataclass
class Thread:
    """Represents a conversation thread."""
    thread_id: str
    user_prompt: str
    model_id: str
    status: ThreadStatus
    final_response: Optional[str] = None
    warning_message: Optional[str] = None
    iterations: List[TypedIteration] = field(default_factory=list)  # MODIFIED - now uses TypedIteration
    iteration_counter: int = 0  # NEW - global counter for iterations
    max_iterations: int = 5  # NEW - maximum allowed iterations (loaded from config)
    processed_finding_indices: set = field(default_factory=set)  # NEW - track which findings have been processed
    current_findings: List[Finding] = field(default_factory=list)  # NEW - current findings from latest validation
    all_clarifications: List[QuestionAnswerExchange] = field(default_factory=list)  # NEW - all Q&A exchanges from clarifications
    schema_version: str = "2.0"  # NEW - for migration support
    created_at: datetime = field(default_factory=datetime_utc)
    completed_at: Optional[datetime] = None
    awaiting_input_since: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "thread_id": self.thread_id,
            "user_prompt": self.user_prompt,
            "model_id": self.model_id,
            "status": self.status.value,
            "final_response": self.final_response,
            "warning_message": self.warning_message,
            "iterations": [i.to_dict() for i in self.iterations],
            "iteration_counter": self.iteration_counter,
            "max_iterations": self.max_iterations,
            "processed_finding_indices": list(self.processed_finding_indices),
            "current_findings": [f.to_dict() for f in self.current_findings],
            "all_clarifications": [qa.to_dict() for qa in self.all_clarifications],
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "awaiting_input_since": self.awaiting_input_since.isoformat() if self.awaiting_input_since else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Thread':
        """Create Thread from dictionary with migration support."""
        schema_version = data.get("schema_version", "1.0")
        
        # Handle old format (schema_version 1.0)
        if schema_version == "1.0":
            return cls._migrate_from_old_format(data)
        
        # Handle new format (schema_version 2.0)
        return cls(
            thread_id=data["thread_id"],
            user_prompt=data["user_prompt"],
            model_id=data["model_id"],
            status=ThreadStatus(data["status"]),
            final_response=data.get("final_response"),
            warning_message=data.get("warning_message"),
            iterations=[TypedIteration.from_dict(i) for i in data.get("iterations", [])],
            iteration_counter=data.get("iteration_counter", 0),
            max_iterations=data.get("max_iterations", 5),
            processed_finding_indices=set(data.get("processed_finding_indices", [])),
            current_findings=[Finding.from_dict(f) for f in data.get("current_findings", [])],
            all_clarifications=[QuestionAnswerExchange.from_dict(qa) for qa in data.get("all_clarifications", [])],
            schema_version=data.get("schema_version", "2.0"),
            created_at=dt.fromisoformat(data["created_at"]),
            completed_at=dt.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            awaiting_input_since=dt.fromisoformat(data["awaiting_input_since"]) if data.get("awaiting_input_since") else None
        )
    
    @classmethod
    def _migrate_from_old_format(cls, data: Dict[str, Any]) -> 'Thread':
        """Migrate old thread format to new format."""
        old_iterations = [Iteration.from_dict(i) for i in data.get("iterations", [])]
        
        # Convert old iterations to new TypedIteration format
        new_iterations = []
        
        if old_iterations and old_iterations[0].iteration_number == 0:
            iteration_0 = old_iterations[0]
            
            # Convert remaining iterations to TypedIteration format
            for old_iter in old_iterations[1:]:
                # Determine iteration type based on presence of qa_exchange
                if old_iter.qa_exchange:
                    iteration_type = IterationType.USER_CLARIFICATION
                    type_specific_data = ClarificationIterationData(
                        qa_exchange=old_iter.qa_exchange,
                        context_augmentation=None
                    )
                else:
                    iteration_type = IterationType.AR_FEEDBACK
                    type_specific_data = ARIterationData(
                        findings=old_iter.findings,
                        validation_output=old_iter.validation_output
                    )
                
                # Get original answer from previous iteration
                prev_iter = old_iterations[old_iter.iteration_number - 1]
                original_answer_for_iter = prev_iter.llm_response
                
                new_iteration = TypedIteration(
                    iteration_number=old_iter.iteration_number,
                    iteration_type=iteration_type,
                    original_answer=original_answer_for_iter,
                    rewritten_answer=old_iter.llm_response,
                    rewriting_prompt=old_iter.rewriting_prompt or "",
                    type_specific_data=type_specific_data
                )
                new_iterations.append(new_iteration)
        
        # Set iteration_counter based on number of iterations
        iteration_counter = len(new_iterations)
        
        return cls(
            thread_id=data["thread_id"],
            user_prompt=data["user_prompt"],
            model_id=data["model_id"],
            status=ThreadStatus(data["status"]),
            final_response=data.get("final_response"),
            warning_message=data.get("warning_message"),
            iterations=new_iterations,
            iteration_counter=iteration_counter,
            max_iterations=data.get("max_iterations", 5),
            processed_finding_indices=set(),  # Initialize empty for old threads
            current_findings=[],  # Initialize empty for old threads
            all_clarifications=[],  # Initialize empty for old threads
            schema_version="2.0",  # Mark as migrated
            created_at=dt.fromisoformat(data["created_at"]),
            completed_at=dt.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            awaiting_input_since=dt.fromisoformat(data["awaiting_input_since"]) if data.get("awaiting_input_since") else None
        )
    
    @staticmethod
    def generate_id() -> str:
        """Generate a unique thread ID."""
        return str(uuid4())
