"""
Thread processor for orchestrating validation and rewriting logic.

Uses a state machine pattern for clear, maintainable control flow.
"""
import logging
from enum import Enum, auto
from typing import Optional, List

from backend.models.thread import (
    Thread, ThreadStatus, Finding, QuestionAnswerExchange,
    TypedIteration, IterationType, ARIterationData, ClarificationIterationData
)
from backend.services.thread_manager import ThreadManager
from backend.services.llm_service import LLMService
from backend.services.validation_service import ValidationService, ValidationResult
from backend.services.audit_logger import AuditLogger
from backend.services.policy_service import PolicyService
from backend.services.llm_response_parser import LLMResponseParser
from backend.services.prompt_template_manager import PromptTemplateManager

logger = logging.getLogger(__name__)


class ProcessingState(Enum):
    """States for the thread processing state machine."""
    INIT = auto()
    GENERATE_INITIAL = auto()
    VALIDATE = auto()
    CHECK_QUESTIONS = auto()
    HANDLE_RESULT = auto()
    REWRITING_LOOP = auto()
    AWAITING_INPUT = auto()
    COMPLETED = auto()
    ERROR = auto()


class ThreadProcessor:
    """
    Processes threads through validation and rewriting using a state machine.
    
    This class consolidates all thread processing logic including:
    - Initial response generation
    - Validation handling
    - Rewriting loop execution
    - Follow-up question handling
    """
    
    def __init__(
        self,
        thread: Thread,
        thread_manager: ThreadManager,
        llm_service: LLMService,
        validation_service: ValidationService,
        audit_logger: AuditLogger,
        policy_service: Optional[PolicyService] = None,
        config_manager=None
    ):
        self.thread = thread
        self.thread_manager = thread_manager
        self.llm_service = llm_service
        self.validation_service = validation_service
        self.audit_logger = audit_logger
        self.policy_service = policy_service
        self.config_manager = config_manager
        
        # Shared utilities
        self.parser = LLMResponseParser()
        self.template_manager = PromptTemplateManager()
        
        # Processing state
        self.state = ProcessingState.INIT
        self.current_response = ""
        self.current_validation: Optional[ValidationResult] = None
        self.enriched_findings: List[Finding] = []
        self.iteration_summaries: List[str] = []
    
    @property
    def thread_id(self) -> str:
        return self.thread.thread_id
    
    def process(self) -> None:
        """Execute the state machine until completion or awaiting input."""
        handlers = {
            ProcessingState.INIT: self._handle_init,
            ProcessingState.GENERATE_INITIAL: self._handle_generate_initial,
            ProcessingState.VALIDATE: self._handle_validate,
            ProcessingState.CHECK_QUESTIONS: self._handle_check_questions,
            ProcessingState.HANDLE_RESULT: self._handle_result,
            ProcessingState.REWRITING_LOOP: self._handle_rewriting_loop,
        }
        
        try:
            while self.state not in (ProcessingState.COMPLETED, ProcessingState.ERROR, ProcessingState.AWAITING_INPUT):
                handler = handlers.get(self.state)
                if handler:
                    self.state = handler()
                else:
                    logger.error(f"Thread {self.thread_id} - Unknown state: {self.state}")
                    self.state = ProcessingState.ERROR
        except Exception as e:
            logger.error(f"Error processing thread {self.thread_id}: {e}", exc_info=True)
            self._complete_with_error(str(e))
    
    # === State Handlers ===
    
    def _handle_init(self) -> ProcessingState:
        """Initialize processing: load config and set up thread."""
        max_iterations = 5
        if self.config_manager:
            config = self.config_manager.get_current_config()
            if config:
                max_iterations = config.max_iterations
                logger.info(f"Loaded max_iterations from config: {max_iterations}")
        
        self.thread.max_iterations = max_iterations
        return ProcessingState.GENERATE_INITIAL
    
    def _handle_generate_initial(self) -> ProcessingState:
        """Generate initial LLM response."""
        logger.info(f"Thread {self.thread_id} - Generating initial response")
        
        policy_context = ""
        if self.policy_service:
            policy_context = self.policy_service.format_policy_context()
        
        initial_template = self.template_manager.load_template_by_name("initial_response")
        wrapped_prompt = self.template_manager.render_template(
            initial_template,
            user_prompt=self.thread.user_prompt,
            policy_context=policy_context
        )
        
        self.current_response = self.llm_service.generate_response(wrapped_prompt)
        logger.info(f"Thread {self.thread_id} - Received initial response from LLM")
        
        # Store wrapped prompt for iteration 0
        self._wrapped_prompt = wrapped_prompt
        return ProcessingState.VALIDATE
    
    def _handle_validate(self) -> ProcessingState:
        """Validate the current response."""
        logger.info(f"Thread {self.thread_id} - Validating response")
        self.current_validation = self.validation_service.validate(
            self.thread.user_prompt, 
            self.current_response
        )
        logger.info(f"Thread {self.thread_id} - Validation result: {self.current_validation.output}")
        
        # Enrich findings
        self.enriched_findings = self.current_validation.findings
        if self.policy_service:
            self.enriched_findings = self.policy_service.enrich_findings(self.current_validation.findings)
        
        # Store initial iteration (iteration 0)
        if self.thread.iteration_counter == 0:
            self.thread.iteration_counter = 1
            initial_iteration = TypedIteration(
                iteration_number=0,
                iteration_type=IterationType.AR_FEEDBACK,
                original_answer="",
                rewritten_answer=self.current_response,
                rewriting_prompt=getattr(self, '_wrapped_prompt', ''),
                type_specific_data=ARIterationData(
                    findings=self.enriched_findings,
                    validation_output=self.current_validation.output,
                    processed_finding_index=None,
                    llm_decision="INITIAL",
                    iteration_type="initial"
                )
            )
            self.thread.iterations.append(initial_iteration)
            logger.info(f"Thread {self.thread_id} - Created iteration 0 (initial)")
        
        return ProcessingState.CHECK_QUESTIONS
    
    def _handle_check_questions(self) -> ProcessingState:
        """Check for follow-up questions in the response."""
        if not self._should_check_for_questions(self.current_validation.output):
            return ProcessingState.HANDLE_RESULT
        
        questions = self.parser.detect_questions(self.current_response)
        if not questions:
            return ProcessingState.HANDLE_RESULT
        
        logger.info(f"Thread {self.thread_id} - Detected {len(questions)} follow-up question(s)")
        self._pause_for_questions(questions, None)
        return ProcessingState.AWAITING_INPUT
    
    def _handle_result(self) -> ProcessingState:
        """Handle validation result and determine next state."""
        output = self.current_validation.output
        
        # Check NO_TRANSLATIONS cases
        if self._is_no_translations_case():
            self._handle_no_translations()
            return ProcessingState.COMPLETED
        
        if output == "NO_TRANSLATIONS":
            self._complete_with_response(self.current_response)
            return ProcessingState.COMPLETED
        
        if output == "VALID":
            self._handle_valid()
            return ProcessingState.COMPLETED
        
        if output == "TOO_COMPLEX":
            self._handle_too_complex()
            return ProcessingState.ERROR
        
        # Invalid cases: proceed to rewriting
        logger.info(f"Thread {self.thread_id} requires rewriting (output: {output})")
        self.thread.current_findings = self.enriched_findings
        return ProcessingState.REWRITING_LOOP
    
    def _handle_rewriting_loop(self) -> ProcessingState:
        """Execute one iteration of the rewriting loop."""
        # Check max iterations
        if self.thread.iteration_counter >= self.thread.max_iterations:
            self._complete_max_iterations()
            return ProcessingState.COMPLETED
        
        # Filter findings
        findings_to_process = [
            f for f in self.thread.current_findings 
            if f.validation_output != "NO_TRANSLATIONS"
        ]
        
        if not findings_to_process:
            self._complete_no_findings()
            return ProcessingState.COMPLETED
        
        # Sort and select top finding
        sorted_findings = findings_to_process
        if self.policy_service:
            sorted_findings = self.policy_service.sort_findings(findings_to_process)
        selected_finding = sorted_findings[0]
        
        # Increment counter and generate prompt
        self.thread.iteration_counter += 1
        current_iteration = self.thread.iteration_counter
        logger.info(f"Thread {self.thread_id} - Iteration {current_iteration}/{self.thread.max_iterations}")
        
        rewriting_prompt = self.llm_service.generate_rewriting_prompt(
            findings=[selected_finding],
            original_prompt=self.thread.user_prompt,
            original_response=self.current_response,
            all_clarifications=self.thread.all_clarifications
        )
        
        llm_response = self.llm_service.generate_response(rewriting_prompt)
        decision_type, answer_text, questions = self.parser.parse_decision(llm_response)
        logger.info(f"Thread {self.thread_id} - LLM decision: {decision_type}")
        
        # Handle decision
        if decision_type == self.parser.DECISION_IMPOSSIBLE:
            return self._handle_impossible_decision(answer_text, rewriting_prompt, current_iteration)
        
        if decision_type == self.parser.DECISION_ASK_QUESTIONS and questions:
            self._pause_for_questions(questions, rewriting_prompt, 0, decision_type, current_iteration)
            return ProcessingState.AWAITING_INPUT
        
        # REWRITE decision (or ASK_QUESTIONS without questions)
        new_response = answer_text if decision_type == self.parser.DECISION_REWRITE else llm_response
        return self._handle_rewrite_decision(new_response, rewriting_prompt, current_iteration)
    
    # === Result Handlers ===
    
    def _handle_valid(self) -> None:
        """Handle VALID validation result."""
        logger.info(f"Thread {self.thread_id} received VALID response")
        self._complete_with_response(self.current_response)
        self.audit_logger.log_valid_response(self.thread, self.enriched_findings)
    
    def _handle_too_complex(self) -> None:
        """Handle TOO_COMPLEX validation result."""
        logger.info(f"Thread {self.thread_id} received TOO_COMPLEX response")
        error_message = (
            "Your request is too complex for the automated reasoning system to handle. "
            "Please try simplifying your question or breaking it into smaller parts."
        )
        self.thread_manager.update_thread_status(
            self.thread_id, ThreadStatus.ERROR, final_response=error_message
        )
    
    def _handle_no_translations(self) -> None:
        """Handle NO_TRANSLATIONS validation result."""
        logger.info(f"Thread {self.thread_id} has NO_TRANSLATIONS findings")
        
        has_valid_with_no_translations = (
            self.current_validation.output == "VALID" and
            any(f.validation_output == "NO_TRANSLATIONS" for f in self.enriched_findings)
        )
        
        if has_valid_with_no_translations:
            warning = (
                "Note: This response could not be fully validated by the automated reasoning system. "
                "Some aspects of your question may not be covered by the validation policy."
            )
            self._complete_with_response(self.current_response, warning)
            self.audit_logger.log_valid_response(self.thread, self.enriched_findings)
        else:
            self._complete_with_response(self.current_response)
    
    def _handle_impossible_decision(
        self, explanation: str, rewriting_prompt: str, iteration_num: int
    ) -> ProcessingState:
        """Handle IMPOSSIBLE decision from LLM."""
        logger.info(f"Thread {self.thread_id} - IMPOSSIBLE decision, returning explanation")
        
        iteration = TypedIteration(
            iteration_number=iteration_num,
            iteration_type=IterationType.AR_FEEDBACK,
            original_answer=self.current_response,
            rewritten_answer=explanation,
            rewriting_prompt=rewriting_prompt,
            type_specific_data=ARIterationData(
                findings=self.thread.current_findings,
                validation_output="IMPOSSIBLE",
                processed_finding_index=0,
                llm_decision=self.parser.DECISION_IMPOSSIBLE,
                iteration_type="impossible"
            )
        )
        self.thread.iterations.append(iteration)
        self._complete_with_response(explanation)
        return ProcessingState.COMPLETED
    
    def _handle_rewrite_decision(
        self, new_response: str, rewriting_prompt: str, iteration_num: int
    ) -> ProcessingState:
        """Handle REWRITE decision from LLM."""
        # Validate new response
        new_validation = self.validation_service.validate(self.thread.user_prompt, new_response)
        new_findings = new_validation.findings
        if self.policy_service:
            new_findings = self.policy_service.enrich_findings(new_validation.findings)
        
        # Create iteration
        iteration = TypedIteration(
            iteration_number=iteration_num,
            iteration_type=IterationType.AR_FEEDBACK,
            original_answer=self.current_response,
            rewritten_answer=new_response,
            rewriting_prompt=rewriting_prompt,
            type_specific_data=ARIterationData(
                findings=new_findings,
                validation_output=new_validation.output,
                processed_finding_index=0,
                llm_decision=self.parser.DECISION_REWRITE,
                iteration_type="rewriting"
            )
        )
        self.thread.iterations.append(iteration)
        
        self.iteration_summaries.append(
            f"Iteration {iteration_num}: {new_validation.output} (REWRITE) - {len(new_findings)} finding(s)"
        )
        
        logger.info(f"Thread {self.thread_id} - REWRITE processed, validation: {new_validation.output}")
        
        if new_validation.output == "VALID":
            self._complete_with_response(new_response)
            self.audit_logger.log_valid_response(self.thread, new_findings)
            return ProcessingState.COMPLETED
        
        # Update state for next iteration
        self.current_response = new_response
        self.current_validation = new_validation
        self.enriched_findings = new_findings
        self.thread.current_findings = new_findings
        
        return ProcessingState.REWRITING_LOOP
    
    # === Completion Helpers ===
    
    def _complete_with_response(self, response: str, warning: str = None) -> None:
        """Complete thread with a response."""
        self.thread_manager.update_thread_status(
            self.thread_id, ThreadStatus.COMPLETED,
            final_response=response, warning_message=warning
        )
    
    def _complete_with_error(self, error_msg: str) -> None:
        """Complete thread with an error."""
        self.thread_manager.update_thread_status(
            self.thread_id, ThreadStatus.ERROR,
            final_response=f"An error occurred while processing your request: {error_msg}"
        )
        self.state = ProcessingState.ERROR
    
    def _complete_max_iterations(self) -> None:
        """Complete thread when max iterations reached."""
        logger.warning(f"Thread {self.thread_id} reached max iterations ({self.thread.max_iterations})")
        warning = (
            f"Warning: This response may be unsafe. The system reached the maximum "
            f"iteration limit ({self.thread.max_iterations}) while attempting to validate "
            "the response. Please review the response carefully."
        )
        self._complete_with_response(self.current_response, warning)
        
        if self.current_validation and self.current_validation.findings:
            self.audit_logger.log_max_iterations(
                self.thread, self.iteration_summaries, self.current_validation.findings[-1]
            )
    
    def _complete_no_findings(self) -> None:
        """Complete thread when no more findings to process."""
        logger.info(f"Thread {self.thread_id} - No more findings to process")
        
        if self.current_validation.output != "VALID":
            warning = (
                "Warning: This response may be unsafe. The system processed all validation findings "
                "but could not achieve a fully validated response."
            )
            self._complete_with_response(self.current_response, warning)
        else:
            self._complete_with_response(self.current_response)
    
    # === Question Handling ===
    
    def _pause_for_questions(
        self,
        questions: List[str],
        rewriting_prompt: Optional[str],
        finding_index: int = None,
        decision_type: str = "ASK_QUESTIONS",
        iteration_num: int = None
    ) -> None:
        """Pause processing to await user answers to questions."""
        logger.info(f"Thread {self.thread_id} - Pausing for {len(questions)} question(s)")
        
        qa_exchange = QuestionAnswerExchange(questions=questions, answers=None, skipped=False)
        
        iteration = TypedIteration(
            iteration_number=iteration_num or self.thread.iteration_counter,
            iteration_type=IterationType.USER_CLARIFICATION,
            original_answer=self.current_response,
            rewritten_answer="",
            rewriting_prompt=rewriting_prompt or "",
            type_specific_data=ClarificationIterationData(
                qa_exchange=qa_exchange,
                context_augmentation=None,
                processed_finding_index=finding_index,
                llm_decision=decision_type
            )
        )
        self.thread_manager.update_thread(self.thread_id, iteration)
        self.thread_manager.update_thread_status(self.thread_id, ThreadStatus.AWAITING_USER_INPUT)
    
    # === Helper Methods ===
    
    def _should_check_for_questions(self, validation_output: str) -> bool:
        """Check if follow-up question detection should be enabled."""
        return validation_output in ["TRANSLATION_AMBIGUOUS", "SATISFIABLE"]
    
    def _is_no_translations_case(self) -> bool:
        """Check if this is a NO_TRANSLATIONS case."""
        if not self.enriched_findings:
            return False
        
        all_no_translations = all(
            f.validation_output == "NO_TRANSLATIONS" for f in self.enriched_findings
        )
        
        if len(self.enriched_findings) == 1 and all_no_translations:
            return True
        
        if self.current_validation.output == "VALID" and any(
            f.validation_output == "NO_TRANSLATIONS" for f in self.enriched_findings
        ):
            return True
        
        return False


# === Public API Functions ===

def process_thread(
    thread_id: str,
    thread_manager: ThreadManager,
    llm_service: LLMService,
    validation_service: ValidationService,
    audit_logger: AuditLogger,
    policy_service: Optional[PolicyService] = None,
    config_manager=None
) -> None:
    """
    Process a thread through validation and rewriting iterations.
    
    This is the main entry point for thread processing.
    """
    thread = thread_manager.get_thread(thread_id)
    if thread is None:
        logger.error(f"Thread {thread_id} not found")
        return
    
    processor = ThreadProcessor(
        thread=thread,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger,
        policy_service=policy_service,
        config_manager=config_manager
    )
    processor.process()


def resume_thread_with_answers(
    thread_id: str,
    answers: List[str],
    skipped: bool,
    thread_manager: ThreadManager,
    llm_service: LLMService,
    validation_service: ValidationService,
    audit_logger: AuditLogger,
    policy_service: Optional[PolicyService] = None,
    config_manager=None
) -> None:
    """
    Resume validation after receiving user answers to follow-up questions.
    """
    thread = thread_manager.get_thread(thread_id)
    if thread is None:
        raise ValueError(f"Thread {thread_id} not found")
    
    if thread.status != ThreadStatus.AWAITING_USER_INPUT:
        raise ValueError(f"Thread {thread_id} is not awaiting user input. Current status: {thread.status.value}")
    
    if not thread.iterations:
        raise ValueError(f"Thread {thread_id} has no iterations")
    
    last_iteration = thread.iterations[-1]
    if last_iteration.iteration_type != IterationType.USER_CLARIFICATION:
        raise ValueError(f"Thread {thread_id} last iteration is not a clarification iteration")
    
    clar_data = last_iteration.type_specific_data
    if not isinstance(clar_data, ClarificationIterationData):
        raise ValueError(f"Thread {thread_id} has invalid clarification data")
    
    questions = clar_data.qa_exchange.questions
    
    # Validate answer count
    if not skipped and len(answers) != len(questions):
        raise ValueError(f"Answer count ({len(answers)}) does not match question count ({len(questions)})")
    
    # Update Q&A exchange
    clar_data.qa_exchange.answers = answers if not skipped else None
    clar_data.qa_exchange.skipped = skipped
    
    # Add to thread's all_clarifications list if not skipped
    if not skipped:
        thread.all_clarifications.append(clar_data.qa_exchange)
        logger.info(f"Thread {thread_id} - Added clarification to all_clarifications (total: {len(thread.all_clarifications)})")
    
    thread_manager.update_thread_status(thread_id, ThreadStatus.PROCESSING)
    logger.info(f"Thread {thread_id} - Resuming validation (skipped: {skipped})")
    
    # Create context augmentation
    template_manager = PromptTemplateManager()
    context_augmentation = None
    if not skipped:
        context_augmentation = template_manager.create_context_augmentation(questions, answers)
    
    original_response = last_iteration.original_answer
    
    # Generate regeneration prompt
    if not skipped and context_augmentation:
        clarification_template = template_manager.load_template_by_name("clarification_regeneration")
        regeneration_prompt = template_manager.render_template(
            clarification_template,
            user_prompt=thread.user_prompt,
            original_response=original_response,
            context_augmentation=context_augmentation
        )
    else:
        skipped_template = template_manager.load_template_by_name("clarification_skipped")
        regeneration_prompt = template_manager.render_template(
            skipped_template,
            user_prompt=thread.user_prompt,
            original_response=original_response
        )
    
    # Get new response
    new_response = llm_service.generate_response(regeneration_prompt)
    logger.info(f"Thread {thread_id} - Received new response from LLM")
    
    # Update clarification iteration
    last_iteration.rewritten_answer = new_response
    last_iteration.rewriting_prompt = regeneration_prompt
    clar_data.context_augmentation = context_augmentation
    
    # Validate new response
    new_validation = validation_service.validate(thread.user_prompt, new_response)
    enriched_findings = new_validation.findings
    if policy_service:
        enriched_findings = policy_service.enrich_findings(new_validation.findings)
    
    clar_data.validation_output = new_validation.output
    clar_data.validation_findings = enriched_findings
    
    logger.info(f"Thread {thread_id} - Post-clarification validation: {new_validation.output}")
    
    # Check if VALID
    if new_validation.output == "VALID":
        thread_manager.update_thread_status(thread_id, ThreadStatus.COMPLETED, final_response=new_response)
        audit_logger.log_valid_response(thread, new_validation.findings)
        return
    
    # Check max iterations
    if thread.iteration_counter >= thread.max_iterations:
        warning = (
            "Warning: This response may be unsafe. The system was unable to fully validate "
            "the response after multiple attempts. Please review the response carefully."
        )
        thread_manager.update_thread_status(
            thread_id, ThreadStatus.COMPLETED, final_response=new_response, warning_message=warning
        )
        return
    
    # Check for actionable findings
    thread.current_findings = enriched_findings
    findings_to_process = [f for f in enriched_findings if f.validation_output != "NO_TRANSLATIONS"]
    
    if not findings_to_process:
        thread_manager.update_thread_status(thread_id, ThreadStatus.COMPLETED, final_response=new_response)
        return
    
    # Continue with rewriting loop
    processor = ThreadProcessor(
        thread=thread,
        thread_manager=thread_manager,
        llm_service=llm_service,
        validation_service=validation_service,
        audit_logger=audit_logger,
        policy_service=policy_service,
        config_manager=config_manager
    )
    processor.current_response = new_response
    processor.current_validation = new_validation
    processor.enriched_findings = enriched_findings
    processor.state = ProcessingState.REWRITING_LOOP
    processor.process()
