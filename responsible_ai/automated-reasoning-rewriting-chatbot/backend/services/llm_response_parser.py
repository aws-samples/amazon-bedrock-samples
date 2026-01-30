"""
LLM Response Parser for the AR Chatbot.

Unified parser for all LLM response formats including:
- Decision parsing (REWRITE vs ASK_QUESTIONS)
- Question detection and extraction
- Answer extraction
"""
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class LLMResponseParser:
    """
    Unified parser for all LLM response formats.
    
    This class provides methods for:
    - Parsing LLM decision type (REWRITE vs ASK_QUESTIONS)
    - Extracting rewritten answers from REWRITE decisions
    - Extracting questions from ASK_QUESTIONS decisions
    - Detecting if responses contain follow-up questions
    """
    
    # Decision markers
    DECISION_PREFIX = "DECISION:"
    DECISION_REWRITE = "REWRITE"
    DECISION_ASK_QUESTIONS = "ASK_QUESTIONS"
    DECISION_IMPOSSIBLE = "IMPOSSIBLE"
    
    # Content markers
    ANSWER_PREFIX = "ANSWER:"
    QUESTION_PREFIX = "QUESTION:"
    
    # Maximum number of questions to process
    MAX_QUESTIONS = 5
    
    def __init__(self):
        """Initialize the LLM response parser."""
        pass
    
    def parse_decision(self, llm_response: str) -> Tuple[str, str, List[str]]:
        """
        Parse the LLM's response to determine its decision.
        
        This method parses structured LLM responses in the following formats:
        
        REWRITE format:
            DECISION: REWRITE
            ANSWER: [rewritten answer text]
        
        ASK_QUESTIONS format:
            DECISION: ASK_QUESTIONS
            QUESTION: [question 1]
            QUESTION: [question 2]
            ...
        
        IMPOSSIBLE format:
            DECISION: IMPOSSIBLE
            [explanation of why the question cannot be answered]
        
        The parser is robust to markdown formatting and will correctly handle
        responses with markdown headers (e.g., ### DECISION: ASK_QUESTIONS).
        
        If the response cannot be parsed (no DECISION marker found), it defaults
        to REWRITE and treats the entire response as the answer.
        
        Args:
            llm_response: The LLM-generated response text
            
        Returns:
            Tuple of (decision_type, answer_text, questions):
            - decision_type: "REWRITE", "ASK_QUESTIONS", or "IMPOSSIBLE"
            - answer_text: The rewritten answer (if REWRITE), explanation (if IMPOSSIBLE), or empty string
            - questions: List of questions (if ASK_QUESTIONS) or empty list
        """
        if not llm_response:
            logger.warning("Empty LLM response, defaulting to REWRITE with empty answer")
            return (self.DECISION_REWRITE, "", [])
        
        try:
            # Parse the response line by line
            lines = llm_response.split('\n')
            
            # Look for DECISION marker (handle markdown headers like ### DECISION:)
            decision_type = None
            for line in lines:
                stripped_line = line.strip()
                # Remove markdown headers (###, ##, #) if present
                cleaned_line = stripped_line.lstrip('#').strip()
                
                if cleaned_line.startswith(self.DECISION_PREFIX):
                    # Extract decision type after the marker
                    decision_text = cleaned_line[len(self.DECISION_PREFIX):].strip()
                    
                    # Normalize decision type
                    if self.DECISION_REWRITE in decision_text.upper():
                        decision_type = self.DECISION_REWRITE
                    elif self.DECISION_ASK_QUESTIONS in decision_text.upper() or "ASK_QUESTIONS" in decision_text.upper():
                        decision_type = self.DECISION_ASK_QUESTIONS
                    elif self.DECISION_IMPOSSIBLE in decision_text.upper():
                        decision_type = self.DECISION_IMPOSSIBLE
                    break
            
            # If no decision marker found, default to REWRITE
            if decision_type is None:
                logger.warning(
                    "No DECISION marker found in LLM response, defaulting to REWRITE. "
                    "Treating entire response as answer."
                )
                return (self.DECISION_REWRITE, llm_response.strip(), [])
            
            # Parse based on decision type
            if decision_type == self.DECISION_REWRITE:
                answer_text = self._extract_answer(lines)
                logger.info(f"Parsed REWRITE decision with answer length: {len(answer_text)}")
                return (self.DECISION_REWRITE, answer_text, [])
            
            elif decision_type == self.DECISION_ASK_QUESTIONS:
                questions = self._extract_questions(lines)
                logger.info(f"Parsed ASK_QUESTIONS decision with {len(questions)} question(s)")
                return (self.DECISION_ASK_QUESTIONS, "", questions)
            
            elif decision_type == self.DECISION_IMPOSSIBLE:
                explanation = self._extract_explanation(lines)
                logger.info(f"Parsed IMPOSSIBLE decision with explanation length: {len(explanation)}")
                return (self.DECISION_IMPOSSIBLE, explanation, [])
            
            else:
                # Should not reach here, but handle gracefully
                logger.warning(f"Unknown decision type: {decision_type}, defaulting to REWRITE")
                return (self.DECISION_REWRITE, llm_response.strip(), [])
                
        except Exception as e:
            logger.error(f"Error parsing LLM decision: {str(e)}")
            logger.debug(f"Response that caused error: {llm_response[:200]}...")
            # Default to REWRITE on error
            return (self.DECISION_REWRITE, llm_response.strip(), [])
    
    def _extract_answer(self, lines: List[str]) -> str:
        """
        Extract answer text from a REWRITE decision.
        
        This method looks for the ANSWER: marker and extracts all text
        following it. If no ANSWER: marker is found, it returns all
        non-DECISION lines as the answer.
        
        Args:
            lines: List of lines from the LLM response
            
        Returns:
            The extracted answer text
        """
        answer_lines = []
        found_answer_marker = False
        
        for line in lines:
            stripped_line = line.strip()
            # Remove markdown headers if present
            cleaned_line = stripped_line.lstrip('#').strip()
            
            # Skip the DECISION line (check both original and cleaned)
            if cleaned_line.startswith(self.DECISION_PREFIX):
                continue
            
            # Check for ANSWER marker
            if cleaned_line.startswith(self.ANSWER_PREFIX):
                found_answer_marker = True
                # Extract text after ANSWER: marker
                answer_text = cleaned_line[len(self.ANSWER_PREFIX):].strip()
                if answer_text:
                    answer_lines.append(answer_text)
                continue
            
            # If we found the marker, collect all subsequent lines
            if found_answer_marker:
                answer_lines.append(line.rstrip())
            # If no marker yet, collect non-empty lines (fallback behavior)
            elif stripped_line and not cleaned_line.startswith(self.DECISION_PREFIX):
                answer_lines.append(line.rstrip())
        
        answer = '\n'.join(answer_lines).strip()
        
        if not answer:
            logger.warning("No answer text found in REWRITE decision")
        
        return answer
    
    def _extract_questions(self, lines: List[str]) -> List[str]:
        """
        Extract questions from an ASK_QUESTIONS decision.
        
        This method looks for QUESTION: markers and extracts the question
        text following each marker. It enforces the MAX_QUESTIONS limit.
        
        Args:
            lines: List of lines from the LLM response
            
        Returns:
            List of extracted question strings (max 5)
        """
        questions = []
        
        for line in lines:
            stripped_line = line.strip()
            
            # Check if line starts with QUESTION: marker
            if stripped_line.startswith(self.QUESTION_PREFIX):
                # Extract question text after the marker
                question_text = stripped_line[len(self.QUESTION_PREFIX):].strip()
                
                # Only add non-empty questions
                if question_text:
                    questions.append(question_text)
                    
                    # Check if we've reached the maximum
                    if len(questions) >= self.MAX_QUESTIONS:
                        logger.warning(
                            f"Question limit reached ({self.MAX_QUESTIONS}). "
                            f"Only processing first {self.MAX_QUESTIONS} questions."
                        )
                        break
        
        if not questions:
            logger.warning("No questions found in ASK_QUESTIONS decision")
        
        return questions
    
    def _extract_explanation(self, lines: List[str]) -> str:
        """
        Extract explanation text from an IMPOSSIBLE decision.
        
        This method extracts all text following the DECISION: IMPOSSIBLE marker.
        
        Args:
            lines: List of lines from the LLM response
            
        Returns:
            The extracted explanation text
        """
        explanation_lines = []
        found_decision = False
        
        for line in lines:
            stripped_line = line.strip()
            # Remove markdown headers if present
            cleaned_line = stripped_line.lstrip('#').strip()
            
            # Skip the DECISION line but mark that we found it
            if cleaned_line.startswith(self.DECISION_PREFIX):
                found_decision = True
                continue
            
            # Collect all lines after the DECISION marker
            if found_decision and stripped_line:
                explanation_lines.append(line.rstrip())
        
        explanation = '\n'.join(explanation_lines).strip()
        
        if not explanation:
            logger.warning("No explanation text found in IMPOSSIBLE decision")
        
        return explanation
    
    def has_questions(self, llm_response: str) -> bool:
        """
        Check if an LLM response contains follow-up questions.
        
        This is a quick check that looks for the presence of the
        QUESTION: marker without extracting the full question text.
        
        Args:
            llm_response: The LLM-generated response text
            
        Returns:
            True if questions are detected, False otherwise
        """
        if not llm_response:
            return False
        
        try:
            return self.QUESTION_PREFIX in llm_response
        except Exception as e:
            logger.error(f"Error checking for questions: {str(e)}")
            return False
    
    def detect_questions(self, llm_response: str) -> List[str]:
        """
        Detect and extract follow-up questions from an LLM response.
        
        This method:
        1. Parses the response line by line
        2. Identifies lines beginning with "QUESTION:"
        3. Extracts the question text following the marker
        4. Enforces the MAX_QUESTIONS limit
        5. Handles parsing errors gracefully
        
        Args:
            llm_response: The LLM-generated response text
            
        Returns:
            List of extracted question strings (max 5)
            Returns empty list if no questions found or on parsing error
        """
        if not llm_response:
            return []
        
        try:
            # Split response into lines and use shared extraction logic
            lines = llm_response.split('\n')
            questions = self._extract_questions(lines)
            
            if questions:
                logger.info(f"Detected {len(questions)} follow-up question(s)")
            
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing questions from LLM response: {str(e)}")
            logger.debug(f"Response that caused error: {llm_response[:200]}...")
            return []
