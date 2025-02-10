"""
Module for managing question-answer interactions and conversations.

This module provides classes to handle Q&A interactions and conversations in a structured way.
It includes functionality to format interactions for use with the Amazon Bedrock API and
guardrail validation.

Classes:
    Interaction: Represents a single Q&A exchange with question, answer and optional rewritten answer
    Conversation: Manages a collection of Interaction objects as a conversation thread

The module is designed to simplify working with Q&A pairs by providing:
- Structured storage of questions and answers
- Formatting for Bedrock API integration 
- Support for answer rewriting and validation
- Conversation history management

Example:
    conversation = Conversation()
    interaction = Interaction("What is the weather?", "It's sunny")
    conversation.add_interaction(interaction)
"""
from typing import List


class Interaction:
    """
    A class representing a single interaction in a conversation.
    
    Contains the question asked, the answer provided, and optionally a rewritten version of the answer.
    
    Attributes:
        question (str): The question text
        answer (str): The answer text, can be None initially
        rewritten_answer (str): An optional rewritten version of the answer, defaults to None
    """

    def __init__(self, question: str, answer: str = None) -> None:
        """
        Initialize an Interaction with a question and optional answer.

        Args:
            question (str): The question text
            answer (str, optional): The answer text. Defaults to None.
        """
        self.question = question
        self.answer = answer
        self.rewritten_answer = None

    def set_answer(self, answer):
        """Set the answer text for this interaction."""
        self.answer = answer

    def set_rewritten_answer(self, rewritten_answer):
        """Set a rewritten version of the answer text."""
        self.rewritten_answer = rewritten_answer

    def get_bedrock_question(self):
        """
        Format the question for Bedrock API.
        
        Returns:
            dict: Question formatted for Bedrock API
        """
        return {
            "role": "user", "content": [{"text": self.question}]
        }

    def get_bedrock_answer(self):
        """
        Format the answer for Bedrock API.
        
        Returns:
            dict: Answer formatted for Bedrock API
        """
        return {
            "role": "assistant", "content": [{"text": self.answer}]
        }

    def to_guardrail_input(self):
        """
        Format the interaction for guardrail validation.
        
        Returns:
            list: Question and answer formatted for guardrail validation
        """
        return [
            {
                "text": {
                    "text": self.question,
                    "qualifiers": ["query"]
                }
            },
            {
                "text": {
                    "text": self.answer,
                    "qualifiers": ["guard_content"]
                }
            }
        ]


class Conversation:
    """
    A class representing a conversation composed of multiple interactions.
    
    Manages a list of Interaction objects that represent the back-and-forth 
    exchanges in a conversation.
    
    Attributes:
        messages (List[Interaction]): List of Interaction objects in the conversation
    """

    def __init__(self) -> None:
        """Initialize an empty Conversation with no messages."""
        self.messages: List[Interaction] = []

    def add_interaction(self, interaction: Interaction):
        """
        Add a new interaction to the conversation.
        
        Args:
            interaction (Interaction): The Interaction object to add
        """
        self.messages.append(interaction)
