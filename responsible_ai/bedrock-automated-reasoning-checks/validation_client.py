"""
Module for interacting with Amazon Bedrock and Bedrock Guardrails.

This module provides classes for managing conversations with Amazon Bedrock models and validating 
responses using Bedrock Guardrails. It includes functionality for asking questions, validating 
answers, and rewriting responses based on validation feedback.

Classes:
    InteractionFeedback: Processes and stores feedback about the accuracy of model responses
    ValidatingConversationalClient: Main client for interacting with Bedrock and managing 
    conversations

Constants:
    CLAUDE_HAIKU_MODEL_ID: ID of the Claude Haiku model
    MAX_TOKENS: Maximum number of tokens for model responses
    TEMPERATURE: Temperature parameter for model inference
    SYSTEM_MESSAGE: System prompt for the model
    CORRECTION_MESSAGE: Template for correction feedback messages

The module enables:
- Conversational interactions with Bedrock models
- Response validation using Bedrock Guardrails
- Feedback-based answer correction
- Conversation history tracking
"""

from conversation import Conversation, Interaction
from feedback import InteractionFeedback


CLAUDE_HAIKU_MODEL_ID = ""
MAX_TOKENS = 1024
TEMPERATURE = 0.1
SYSTEM_MESSAGE = (
    "You are a highly informed assistant answering user questions about "
    "their motor vehicle insurance policy. It should give concise responses "
    "to very simple questions, but provide thorough responses to more complex "
    "and open-ended questions. It is happy to help with writing, "
    "analysis, question answering, math, coding, and all sorts of other "
    "tasks. It uses markdown for coding. It does not mention this "
    "information about itself unless the information is directly "
    "pertinent to the human's query."
)


class ValidatingConversationalClient:
    """
    A client class that handles interactions with Amazon Bedrock and Bedrock Guardrails.
    
    This class manages conversations with Bedrock models and validates responses using
    Bedrock Guardrails. It maintains conversation history and provides methods to ask
    questions, validate responses, and rewrite answers based on validation feedback.

    Attributes:
        client: The Bedrock client instance for making API calls
        guardrail_id: ID of the Bedrock Guardrail to use for validation
        guardrail_version: Version of the Bedrock Guardrail
        model: ID of the Bedrock model to use (defaults to CLAUDE_HAIKU_MODEL_ID)
        conversation: Conversation instance to track interaction history
    """
    def __init__(self, bedrock_client, guardrail_id, guardrail_version, model = None) -> None:
        """
        Initialize the ValidatingConversationalClient.

        Args:
            bedrock_client: Bedrock client instance for API calls
            guardrail_id: ID of the Bedrock Guardrail to use
            guardrail_version: Version of the Bedrock Guardrail
            model: Optional model ID (defaults to CLAUDE_HAIKU_MODEL_ID)
        """
        self.client = bedrock_client
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.model = CLAUDE_HAIKU_MODEL_ID if not model else model

        self.conversation = Conversation()

    def converse(self, messages):
        """
        Send messages to Bedrock model and get response.

        Args:
            messages: List of messages to send to the model

        Returns:
            str: The model's response text
        """
        response = self.client.converse(
            modelId=self.model,
            messages=messages,
            inferenceConfig={
                "maxTokens": MAX_TOKENS, 
                "temperature": TEMPERATURE, 
                "topP": 0.9
            },
            system=[{ "text": SYSTEM_MESSAGE }],
        )
        return response["output"]["message"]["content"][0]["text"]

    def add_qa(self, question: str, answer: str) -> None:
        """
        Add a question-answer pair to the conversation history.

        Args:
            question: The question text
            answer: The answer text
        """
        interaction = Interaction(question, answer)
        self.conversation.add_interaction(interaction)
        return interaction

    def ask_question(self, question: str) -> Interaction:
        """
        Ask a question and get response from the model.

        Creates a new interaction with the question, gets an answer from the model,
        and adds it to the conversation history.

        Args:
            question: The question text to ask

        Returns:
            Interaction: The interaction containing the question and answer
        """
        interaction = Interaction(question)

        answer = self.converse([interaction.get_bedrock_question()])
        interaction.set_answer(answer)
        self.conversation.add_interaction(interaction)
        return interaction

    def validate_interaction(self, interaction: Interaction) -> InteractionFeedback:
        """
        Validate an interaction using Bedrock Guardrails.

        Sends the interaction to Bedrock Guardrails for validation and returns
        feedback on the interaction.

        Args:
            interaction: The interaction to validate

        Returns:
            InteractionFeedback: Feedback from the guardrails validation
        """
        # call apply guardrails and generate feedback
        guardrails_output = self.client.apply_guardrail(
            guardrailIdentifier=self.guardrail_id,
            guardrailVersion=self.guardrail_version,
            source="OUTPUT",
            content=interaction.to_guardrail_input(),
        )
        ar_checks_assessment = None
        for assessment in guardrails_output["assessments"]:
            if "automatedReasoningPolicy" in assessment:
                ar_checks_assessment = assessment["automatedReasoningPolicy"]["findings"]

        if ar_checks_assessment is None:
            raise ValueError("Could not find Automated Reasoning checks assessment")

        return InteractionFeedback(ar_checks_assessment)

    def rewrite_answer(self,
                       interaction: Interaction,
                       feedback: InteractionFeedback) -> Interaction:
        """
        Rewrite an answer based on validation feedback.

        Takes an interaction and feedback, generates a new answer addressing the
        feedback, and updates the interaction with the rewritten answer.

        Args:
            interaction: The interaction containing the original answer
            feedback: Feedback from guardrails validation

        Returns:
            Interaction: The interaction with the rewritten answer

        Raises:
            Exception: If trying to rewrite a valid answer with no feedback
        """
        feedback_message = feedback.get_bedrock_feedback()
        if not feedback_message:
            raise RuntimeError("Cannot rewrite a valid answer")

        conversation = [
            interaction.get_bedrock_question(),
            interaction.get_bedrock_answer(),
            feedback_message
        ]
        rewritten_answer = self.converse(conversation)
        interaction.set_rewritten_answer(rewritten_answer)
        return interaction

    def get_conversation(self) -> Conversation:
        """
        Get the current conversation history.

        Returns:
            Conversation: The conversation containing all interactions
        """
        return self.conversation