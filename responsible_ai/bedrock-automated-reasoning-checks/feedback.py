"""
A module for processing and formatting validation feedback for natural language interactions.

This module provides functionality to handle validation findings and generate structured
feedback messages. It includes the InteractionFeedback class which processes findings 
containing validation results, rules, and suggestions.

The module supports:
- Validating findings and determining overall validity
- Extracting invalid rules and their descriptions
- Formatting suggestions for corrections
- Generating formatted feedback messages for APIs

The feedback messages follow a standardized format using XML tags to denote different
types of feedback (<feedback>) and suggestions (<assumption>).
"""
import typing

CORRECTION_MESSAGE = (
    "Rewrite your answer using the feedback  below. "
    "The feedback includes the policy rules your answer broke inside "
    "<feedback> tags.\n\n"
    "The text inside the <correction> tag specifically reference factual "
    "statements you should change. \n\n"
    "For answers that are correct but incomplete, I also included an example "
    "of the conditions you should specify inside the <assumption> tag.\n\n"
    "The values inside the correction and assumption tags look like variables "
    "in code, make sure you change this to natural language. "
    "It is very important that your rewritten answer does not mention "
    "the fact that you received feedback! "
    "Do not quote the feedback, corrections, or assumptions verbatim in your answer."
)

class InteractionFeedback:
    """
    A class that stores and processes feedback about the accuracy of a natural language statement.

    This class takes findings from a validation process and provides methods to check validity
    and generate feedback messages.

    Attributes:
        raw_findings: List of validation findings containing results and rules
    """
    def __init__(self, findings) -> None:
        """
        Initialize InteractionFeedback with validation findings.

        Args:
            findings: List of validation findings containing results and rules
        """
        self.raw_findings = findings

    def is_invalid(self) -> bool:
        """
        Check if any findings indicate an invalid result.

        Returns:
            bool: True if any finding has an "INVALID" result, False otherwise
        """
        for f in self.raw_findings:
            if f["result"] == "INVALID":
                return True

        return False

    def validation_result(self) -> str:
        """
        Get the overall validation result.

        Returns:
            str: "VALID" if all findings are valid, "INVALID" otherwise
        """
        if self.is_invalid():
            return "INVALID"

        return "VALID"

    def invalid_rules(self) -> typing.List:
        """
        Get descriptions of all invalid rules from the findings.

        Iterates through the raw findings and extracts rule descriptions for any findings
        that are marked as invalid and have associated rules.

        Returns:
            list: A list of rule description strings for invalid findings. Empty list if no
                invalid rules are found.
        """
        rules = []
        for f in self.raw_findings:
            if f["result"] == "INVALID" and f["rules"] is not None:
                for r in f["rules"]:
                    rules.append(r["description"])

        return rules

    def suggestions(self) -> typing.List:
        """
        Get formatted suggestions from invalid findings.

        Iterates through raw findings and extracts suggestions for any findings that are
        marked as invalid and have associated suggestions. Each suggestion contains a type,
        key (variable name), and value.

        Returns:
            list: A list of formatted suggestion strings in XML tags. Each suggestion indicates
                what value a variable should have. Returns empty list if no suggestions found.
        """
        suggestions = []
        for f in self.raw_findings:
            if "suggestions" in f:
                true_scenario = ""
                corrections = ""
                # gather all assumptions to generate a valid scenario string
                for suggestion in f["suggestions"]:
                    suggestion_type = suggestion["type"].lower()
                    if suggestion_type == "assumption":
                        if true_scenario != "":
                            true_scenario += " and "
                        true_scenario += (
                            f"The variable {suggestion['key']} should have a value of {suggestion['value']}"
                        )
                    if suggestion_type == "correction":
                        if corrections != "":
                            corrections += " and "
                        corrections += (
                            f"Change the value for the variable {suggestion['key']} to {suggestion['value']}"
                        )
        
        if true_scenario != "":    
            suggestions.append(f"<assumption>{true_scenario}</assumption")
        if corrections != "":
            suggestions.append(f"<correction>{corrections}</correction>")
        return suggestions

    def to_feedback_message(self) -> str:
        """
        Generate a formatted feedback message from invalid findings.

        Returns:
            str: A string containing formatted feedback messages from invalid findings,
                 or None if there are no invalid findings
        """
        feedback = ""
        for r in self.invalid_rules():
            feedback += f"<feedback>{r}</feedback>\n"
        for s in self.suggestions():
            feedback += f"{s}\n"

        return None if feedback == "" else feedback

    def get_bedrock_feedback(self):
        """
        Create a formatted feedback message for Bedrock API.

        Returns:
            dict: A dictionary containing the feedback message formatted for Bedrock,
                 or None if there is no feedback to send
        """
        feedback_str = self.to_feedback_message()
        if not feedback_str:
            return None

        return {
            "role": "user", "content": [{"text": f"{CORRECTION_MESSAGE}\n\n {feedback_str}"}]
        }
