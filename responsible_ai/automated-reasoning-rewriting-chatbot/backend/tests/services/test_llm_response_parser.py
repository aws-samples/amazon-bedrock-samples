"""
Tests for LLM Response Parser.

This file merges tests from:
- test_llm_decision_handler.py (decision parsing tests)
- test_thread_processor_questions.py (question detection tests - implicitly tested via QuestionDetector)
"""
import pytest

from backend.services.llm_response_parser import LLMResponseParser


# ============================================================================
# Decision Parsing Tests (from test_llm_decision_handler.py)
# ============================================================================

def test_parse_rewrite_decision_with_answer_marker():
    """Test parsing a REWRITE decision with ANSWER: marker."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
ANSWER: This is the rewritten answer with improved clarity."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert answer_text == "This is the rewritten answer with improved clarity."
    assert questions == []


def test_parse_rewrite_decision_multiline_answer():
    """Test parsing a REWRITE decision with multi-line answer."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
ANSWER: This is the first line of the answer.
This is the second line.
And this is the third line."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert "first line" in answer_text
    assert "second line" in answer_text
    assert "third line" in answer_text
    assert questions == []


def test_parse_ask_questions_decision():
    """Test parsing an ASK_QUESTIONS decision."""
    parser = LLMResponseParser()
    
    response = """DECISION: ASK_QUESTIONS
QUESTION: What do you mean by X?
QUESTION: Can you clarify Y?"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "ASK_QUESTIONS"
    assert answer_text == ""
    assert len(questions) == 2
    assert questions[0] == "What do you mean by X?"
    assert questions[1] == "Can you clarify Y?"


def test_parse_ask_questions_with_max_limit():
    """Test that ASK_QUESTIONS respects the MAX_QUESTIONS limit."""
    parser = LLMResponseParser()
    
    response = """DECISION: ASK_QUESTIONS
QUESTION: Question 1?
QUESTION: Question 2?
QUESTION: Question 3?
QUESTION: Question 4?
QUESTION: Question 5?
QUESTION: Question 6?
QUESTION: Question 7?"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "ASK_QUESTIONS"
    assert answer_text == ""
    assert len(questions) == 5  # MAX_QUESTIONS limit
    assert questions[0] == "Question 1?"
    assert questions[4] == "Question 5?"


def test_parse_no_decision_marker_defaults_to_rewrite():
    """Test that responses without DECISION marker default to REWRITE."""
    parser = LLMResponseParser()
    
    response = "This is just a plain response without any markers."
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert answer_text == "This is just a plain response without any markers."
    assert questions == []


def test_parse_rewrite_without_answer_marker():
    """Test parsing REWRITE decision without ANSWER: marker (fallback behavior)."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
This is the answer text without the ANSWER: marker.
It spans multiple lines."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert "answer text without the ANSWER: marker" in answer_text
    assert "multiple lines" in answer_text
    assert questions == []


def test_parse_empty_response():
    """Test parsing an empty response."""
    parser = LLMResponseParser()
    
    response = ""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert answer_text == ""
    assert questions == []


def test_parse_ask_questions_with_no_questions():
    """Test ASK_QUESTIONS decision with no actual questions."""
    parser = LLMResponseParser()
    
    response = """DECISION: ASK_QUESTIONS"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "ASK_QUESTIONS"
    assert answer_text == ""
    assert questions == []


def test_parse_rewrite_with_empty_answer():
    """Test REWRITE decision with empty answer."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
ANSWER:"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert answer_text == ""
    assert questions == []


def test_parse_case_insensitive_decision():
    """Test that decision parsing is case-insensitive."""
    parser = LLMResponseParser()
    
    response1 = """DECISION: rewrite
ANSWER: Test answer"""
    
    response2 = """DECISION: ask_questions
QUESTION: Test question?"""
    
    decision_type1, answer_text1, questions1 = parser.parse_decision(response1)
    assert decision_type1 == "REWRITE"
    assert answer_text1 == "Test answer"
    
    decision_type2, answer_text2, questions2 = parser.parse_decision(response2)
    assert decision_type2 == "ASK_QUESTIONS"
    assert len(questions2) == 1


def test_parse_with_extra_whitespace():
    """Test parsing with extra whitespace around markers."""
    parser = LLMResponseParser()
    
    response = """  DECISION:   REWRITE  
  ANSWER:   This is the answer.  """
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert answer_text == "This is the answer."
    assert questions == []


def test_parse_question_with_empty_text():
    """Test that empty questions are filtered out."""
    parser = LLMResponseParser()
    
    response = """DECISION: ASK_QUESTIONS
QUESTION: Valid question?
QUESTION:
QUESTION: Another valid question?"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "ASK_QUESTIONS"
    assert len(questions) == 2
    assert questions[0] == "Valid question?"
    assert questions[1] == "Another valid question?"


def test_parse_rewrite_preserves_formatting():
    """Test that REWRITE preserves answer formatting."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
ANSWER: Line 1
  Indented line 2
    More indented line 3
Back to normal"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert "Line 1" in answer_text
    assert "Indented line 2" in answer_text
    assert "More indented line 3" in answer_text
    assert "Back to normal" in answer_text


def test_parse_mixed_content_after_decision():
    """Test that only relevant markers are parsed after decision."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
ANSWER: This is the answer.
QUESTION: This should be ignored in REWRITE mode."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    # The QUESTION line should be included as part of the answer
    assert "This is the answer" in answer_text
    assert questions == []


def test_extract_answer_with_only_answer_marker():
    """Test extracting answer when only ANSWER: marker is present."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
ANSWER: Simple answer."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert answer_text == "Simple answer."


def test_extract_questions_single_question():
    """Test extracting a single question."""
    parser = LLMResponseParser()
    
    response = """DECISION: ASK_QUESTIONS
QUESTION: What is your name?"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "ASK_QUESTIONS"
    assert len(questions) == 1
    assert questions[0] == "What is your name?"


def test_parse_with_newlines_in_answer():
    """Test parsing answer with multiple newlines."""
    parser = LLMResponseParser()
    
    response = """DECISION: REWRITE
ANSWER: Paragraph 1 here.

Paragraph 2 here.

Paragraph 3 here."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "REWRITE"
    assert "Paragraph 1" in answer_text
    assert "Paragraph 2" in answer_text
    assert "Paragraph 3" in answer_text


def test_parse_impossible_decision():
    """Test parsing an IMPOSSIBLE decision."""
    parser = LLMResponseParser()
    
    response = """DECISION: IMPOSSIBLE

The question cannot be answered because the premises conflict with the rules."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "IMPOSSIBLE"
    assert "cannot be answered" in answer_text
    assert "premises conflict" in answer_text
    assert questions == []


def test_parse_impossible_decision_multiline():
    """Test parsing an IMPOSSIBLE decision with multi-line explanation."""
    parser = LLMResponseParser()
    
    response = """DECISION: IMPOSSIBLE

The question cannot be answered as stated for the following reasons:
1. The user's premise X conflicts with rule Y
2. The assumptions made are contradictory
Please rephrase your question."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "IMPOSSIBLE"
    assert "cannot be answered" in answer_text
    assert "premise X conflicts" in answer_text
    assert "contradictory" in answer_text
    assert "rephrase" in answer_text
    assert questions == []


def test_parse_impossible_decision_case_insensitive():
    """Test that IMPOSSIBLE decision parsing is case-insensitive."""
    parser = LLMResponseParser()
    
    response = """DECISION: impossible

This is not possible."""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "IMPOSSIBLE"
    assert "not possible" in answer_text
    assert questions == []


# ============================================================================
# Question Detection Tests (new tests for has_questions and detect_questions)
# ============================================================================

def test_has_questions_returns_true_when_questions_present():
    """Test that has_questions returns True when QUESTION: marker is present."""
    parser = LLMResponseParser()
    
    response = """Some response text.
QUESTION: What do you mean?"""
    
    assert parser.has_questions(response) is True


def test_has_questions_returns_false_when_no_questions():
    """Test that has_questions returns False when no QUESTION: marker."""
    parser = LLMResponseParser()
    
    response = "This is just a regular response without questions."
    
    assert parser.has_questions(response) is False


def test_has_questions_returns_false_for_empty_response():
    """Test that has_questions returns False for empty response."""
    parser = LLMResponseParser()
    
    assert parser.has_questions("") is False
    assert parser.has_questions(None) is False


def test_detect_questions_extracts_multiple_questions():
    """Test that detect_questions extracts multiple questions."""
    parser = LLMResponseParser()
    
    response = """Response text here.
QUESTION: First question?
QUESTION: Second question?
QUESTION: Third question?"""
    
    questions = parser.detect_questions(response)
    
    assert len(questions) == 3
    assert questions[0] == "First question?"
    assert questions[1] == "Second question?"
    assert questions[2] == "Third question?"


def test_detect_questions_returns_empty_list_when_no_questions():
    """Test that detect_questions returns empty list when no questions."""
    parser = LLMResponseParser()
    
    response = "This is a response without any questions."
    
    questions = parser.detect_questions(response)
    
    assert questions == []


def test_detect_questions_returns_empty_list_for_empty_response():
    """Test that detect_questions returns empty list for empty response."""
    parser = LLMResponseParser()
    
    assert parser.detect_questions("") == []
    assert parser.detect_questions(None) == []


def test_detect_questions_respects_max_limit():
    """Test that detect_questions respects MAX_QUESTIONS limit."""
    parser = LLMResponseParser()
    
    response = """Response text.
QUESTION: Q1?
QUESTION: Q2?
QUESTION: Q3?
QUESTION: Q4?
QUESTION: Q5?
QUESTION: Q6?
QUESTION: Q7?"""
    
    questions = parser.detect_questions(response)
    
    assert len(questions) == 5  # MAX_QUESTIONS limit
    assert questions[0] == "Q1?"
    assert questions[4] == "Q5?"


def test_detect_questions_filters_empty_questions():
    """Test that detect_questions filters out empty questions."""
    parser = LLMResponseParser()
    
    response = """Response text.
QUESTION: Valid question?
QUESTION:
QUESTION: Another valid question?
QUESTION:   """
    
    questions = parser.detect_questions(response)
    
    assert len(questions) == 2
    assert questions[0] == "Valid question?"
    assert questions[1] == "Another valid question?"


def test_detect_questions_handles_whitespace():
    """Test that detect_questions handles whitespace correctly."""
    parser = LLMResponseParser()
    
    response = """Response text.
  QUESTION:   What is this?  
QUESTION:How about this?"""
    
    questions = parser.detect_questions(response)
    
    assert len(questions) == 2
    assert questions[0] == "What is this?"
    assert questions[1] == "How about this?"


# ============================================================================
# Integration Tests (testing both methods work together)
# ============================================================================

def test_parse_decision_and_detect_questions_consistency():
    """Test that parse_decision and detect_questions return consistent results."""
    parser = LLMResponseParser()
    
    response = """DECISION: ASK_QUESTIONS
QUESTION: Question 1?
QUESTION: Question 2?"""
    
    # Using parse_decision
    decision_type, answer_text, questions_from_parse = parser.parse_decision(response)
    
    # Using detect_questions
    questions_from_detect = parser.detect_questions(response)
    
    # Both should return the same questions
    assert questions_from_parse == questions_from_detect
    assert len(questions_from_parse) == 2
    assert questions_from_parse[0] == "Question 1?"
    assert questions_from_parse[1] == "Question 2?"


def test_has_questions_and_detect_questions_consistency():
    """Test that has_questions and detect_questions are consistent."""
    parser = LLMResponseParser()
    
    response_with_questions = "Text\nQUESTION: A question?"
    response_without_questions = "Just text"
    
    # Response with questions
    assert parser.has_questions(response_with_questions) is True
    assert len(parser.detect_questions(response_with_questions)) > 0
    
    # Response without questions
    assert parser.has_questions(response_without_questions) is False
    assert len(parser.detect_questions(response_without_questions)) == 0


def test_parse_decision_with_markdown_headers():
    """Test parsing decisions with markdown headers (###, ##, #)."""
    parser = LLMResponseParser()
    
    # Test with ### header
    response1 = """### DECISION: ASK_QUESTIONS
QUESTION: Is your homework type a mathematical solution or a written response?
QUESTION: What is the submission date relative to the due date?"""
    
    decision_type1, answer_text1, questions1 = parser.parse_decision(response1)
    
    assert decision_type1 == "ASK_QUESTIONS"
    assert answer_text1 == ""
    assert len(questions1) == 2
    assert "homework type" in questions1[0]
    assert "submission date" in questions1[1]
    
    # Test with ## header
    response2 = """## DECISION: REWRITE
ANSWER: This is the corrected answer."""
    
    decision_type2, answer_text2, questions2 = parser.parse_decision(response2)
    
    assert decision_type2 == "REWRITE"
    assert answer_text2 == "This is the corrected answer."
    assert questions2 == []
    
    # Test with # header
    response3 = """# DECISION: IMPOSSIBLE
This cannot be answered due to conflicting requirements."""
    
    decision_type3, answer_text3, questions3 = parser.parse_decision(response3)
    
    assert decision_type3 == "IMPOSSIBLE"
    assert "conflicting requirements" in answer_text3
    assert questions3 == []


def test_parse_ask_questions_with_markdown_and_inline_format():
    """Test parsing the exact format from the user's example."""
    parser = LLMResponseParser()
    
    response = """### DECISION: ASK_QUESTIONS
QUESTION: Is your homework type a mathematical solution or a written response?
QUESTION: What is the submission date relative to the due date? (Please specify if it's on time, before the due date, or after the due date.)
QUESTION: Was the homework submitted through the official school portal?
QUESTION: Does the file name follow the required format 'AssignmentNumber_LastName_FirstName'?
QUESTION: Did you provide a valid doctor's note if you were sick before the original deadline?"""
    
    decision_type, answer_text, questions = parser.parse_decision(response)
    
    assert decision_type == "ASK_QUESTIONS"
    assert answer_text == ""
    assert len(questions) == 5
    assert "homework type" in questions[0]
    assert "submission date" in questions[1]
    assert "school portal" in questions[2]
    assert "file name" in questions[3]
    assert "doctor's note" in questions[4]
