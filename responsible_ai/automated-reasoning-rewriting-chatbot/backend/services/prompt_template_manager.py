"""
Prompt Template Manager for generating rewriting prompts.
"""
import os
import logging
import re
from typing import List, Dict, Any, Set

from backend.models.thread import Finding

logger = logging.getLogger(__name__)


def extract_variable_from_statement(statement: Dict[str, Any]) -> str:
    """
    Extract the variable name from a scenario statement.
    
    This function parses the logic field of a statement to identify the variable name.
    It handles various logic formats:
    - S-expressions: "(= homeworkType WRITTEN_RESPONSE)" -> "homeworkType"
    - Predicates: "(not hasFullName)" -> "hasFullName"
    - Simple assignments: "x = 5" -> "x"
    - Predicates: "isType(solution, mathematical)" -> "solution"
    - Comparisons: "count > 0" -> "count"
    
    Args:
        statement: A statement dictionary with logic and natural_language fields
        
    Returns:
        The variable name extracted from the logic statement.
        Returns empty string if logic field is missing or empty.
        Falls back to entire logic string if parsing fails.
    """
    if not statement:
        return ""
    
    logic = statement.get("logic", "")
    if not logic:
        return ""
    
    # Remove whitespace and newlines for easier parsing
    logic_clean = logic.strip().replace('\n', ' ').replace('  ', ' ')
    
    # Try to extract variable from different patterns
    
    # Pattern 1: S-expression equality - (= variable value) or (= variable\n   value)
    # Example: "(= homeworkType WRITTEN_RESPONSE)" -> "homeworkType"
    sexp_eq_match = re.match(r'^\(\s*=\s+(\w+)', logic_clean)
    if sexp_eq_match:
        return sexp_eq_match.group(1)
    
    # Pattern 2: S-expression predicate - (not variable) or (predicate variable)
    # Example: "(not hasFullName)" -> "hasFullName"
    sexp_pred_match = re.match(r'^\(\s*\w+\s+(\w+)', logic_clean)
    if sexp_pred_match:
        return sexp_pred_match.group(1)
    
    # Pattern 3: Predicate format - predicate(variable, ...)
    # Example: isType(solution, mathematical)
    predicate_match = re.match(r'^\w+\((\w+)', logic_clean)
    if predicate_match:
        return predicate_match.group(1)
    
    # Pattern 4: Assignment or comparison - variable = value or variable > value
    # Example: x = 5, count > 0
    operator_match = re.match(r'^(\w+)\s*[=<>!]', logic_clean)
    if operator_match:
        return operator_match.group(1)
    
    # Pattern 5: Just a word at the start
    word_match = re.match(r'^(\w+)', logic_clean)
    if word_match:
        return word_match.group(1)
    
    # Fallback: return the entire logic string
    return logic_clean


def identify_disagreeing_variables(
    claims_true_scenario: Dict[str, Any],
    claims_false_scenario: Dict[str, Any]
) -> Set[str]:
    """
    Identify variables that have different values between two scenarios.
    
    This function compares the statements in both scenarios and identifies
    which variables have different values, representing the unstated assumptions
    causing ambiguity.
    
    Args:
        claims_true_scenario: Scenario where claims would be true
        claims_false_scenario: Scenario where claims would be false
        
    Returns:
        Set of variable names (from logic statements) that disagree between scenarios.
        Returns empty set if scenarios are identical or if either scenario is empty/invalid.
    """
    if not claims_true_scenario or not claims_false_scenario:
        return set()
    
    true_statements = claims_true_scenario.get("statements", [])
    false_statements = claims_false_scenario.get("statements", [])
    
    if not true_statements or not false_statements:
        return set()
    
    # Build a mapping of variable -> logic value for each scenario
    true_vars = {}
    for stmt in true_statements:
        var = extract_variable_from_statement(stmt)
        if var:
            true_vars[var] = stmt.get("logic", "")
    
    false_vars = {}
    for stmt in false_statements:
        var = extract_variable_from_statement(stmt)
        if var:
            false_vars[var] = stmt.get("logic", "")
    
    # Find variables that exist in both scenarios but have different logic values
    disagreeing = set()
    for var in true_vars:
        if var in false_vars and true_vars[var] != false_vars[var]:
            disagreeing.add(var)
    
    return disagreeing


def filter_scenario_statements(
    scenario: Dict[str, Any],
    disagreeing_variables: Set[str]
) -> Dict[str, Any]:
    """
    Filter a scenario to include only statements about disagreeing variables.
    
    This function creates a new scenario dictionary containing only the statements
    whose variables are in the disagreeing_variables set. The structure and content
    of matching statements are preserved exactly.
    
    Args:
        scenario: The scenario dictionary with statements
        disagreeing_variables: Set of variable names to keep
        
    Returns:
        Filtered scenario dictionary with only relevant statements.
        Returns scenario with empty statements list if no matches or if input is invalid.
    """
    if not scenario:
        return {"statements": []}
    
    if not disagreeing_variables:
        return {"statements": []}
    
    statements = scenario.get("statements", [])
    if not statements:
        return {"statements": []}
    
    # Filter statements to only those whose variable is in disagreeing_variables
    filtered_statements = []
    for stmt in statements:
        var = extract_variable_from_statement(stmt)
        if var in disagreeing_variables:
            # Preserve the entire statement structure
            filtered_statements.append(stmt)
    
    return {"statements": filtered_statements}


class PromptTemplateManager:
    """
    Manages prompt templates for rewriting LLM responses based on validation findings.
    
    This class handles:
    - Loading markdown template files based on validation output
    - Rendering templates with placeholder replacement
    - Formatting findings for inclusion in prompts
    - Creating context augmentation from Q&A exchanges
    """
    
    def __init__(self, templates_dir: str = None):
        """
        Initialize the prompt template manager.
        
        Args:
            templates_dir: Directory containing template markdown files 
                          (default: prompts directory relative to project root)
        """
        if templates_dir is None:
            # Default to prompts directory relative to project root
            # This file is in backend/services/, so go up two levels to project root
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            templates_dir = os.path.join(project_root, "prompts")
        self.templates_dir = templates_dir
    
    def create_context_augmentation(
        self,
        questions: List[str],
        answers: List[str]
    ) -> str:
        """
        Create a context augmentation from question-answer pairs.
        
        Formats the Q&A exchange as a structured dialogue with the
        "Previous Clarification" label and Q:/A: format.
        
        Args:
            questions: List of questions asked by the LLM
            answers: List of answers provided by the user
            
        Returns:
            Formatted context augmentation string
            Returns empty string if data is invalid or missing
        """
        # Handle empty or missing data gracefully
        if not questions:
            logger.warning("No questions provided for context augmentation")
            return ""
        
        if not answers:
            logger.warning("No answers provided for context augmentation")
            return ""
        
        # Validate that question and answer counts match
        if len(questions) != len(answers):
            logger.warning(
                f"Question count ({len(questions)}) does not match "
                f"answer count ({len(answers)}). Creating partial augmentation."
            )
            # Use the minimum length to avoid index errors
            pair_count = min(len(questions), len(answers))
        else:
            pair_count = len(questions)
        
        try:
            # Build the augmentation string
            lines = ["**Previous Clarification:**", ""]
            
            for i in range(pair_count):
                question = questions[i].strip()
                answer = answers[i].strip()
                
                # Skip empty Q&A pairs
                if not question or not answer:
                    logger.debug(f"Skipping empty Q&A pair at index {i}")
                    continue
                
                lines.append(f"Q: {question}")
                lines.append(f"A: {answer}")
                lines.append("")  # Empty line between pairs
            
            # Join all lines with newlines
            augmentation = "\n".join(lines)
            
            logger.info(f"Created context augmentation with {pair_count} Q&A pair(s)")
            
            return augmentation
            
        except Exception as e:
            logger.error(f"Error creating context augmentation: {str(e)}")
            return ""
    
    def create_all_clarifications_context(
        self,
        qa_exchanges: List
    ) -> str:
        """
        Create a context augmentation from multiple Q&A exchanges.
        
        Formats all Q&A exchanges as a structured dialogue with numbered
        clarification rounds.
        
        Args:
            qa_exchanges: List of QuestionAnswerExchange objects
            
        Returns:
            Formatted context augmentation string with all clarifications
            Returns empty string if no valid exchanges
        """
        if not qa_exchanges:
            return ""
        
        # Filter to only answered exchanges (not skipped)
        answered_exchanges = [
            qa for qa in qa_exchanges 
            if not qa.skipped and qa.answers
        ]
        
        if not answered_exchanges:
            return ""
        
        try:
            lines = ["**Previous Clarifications:**", ""]
            
            for exchange_num, qa_exchange in enumerate(answered_exchanges, 1):
                if len(answered_exchanges) > 1:
                    lines.append(f"Clarification Round {exchange_num}:")
                
                for i, (question, answer) in enumerate(zip(qa_exchange.questions, qa_exchange.answers)):
                    question = question.strip()
                    answer = answer.strip()
                    
                    if question and answer:
                        lines.append(f"Q: {question}")
                        lines.append(f"A: {answer}")
                        lines.append("")  # Empty line between pairs
                
                if len(answered_exchanges) > 1:
                    lines.append("")  # Extra line between rounds
            
            augmentation = "\n".join(lines)
            logger.info(f"Created context augmentation with {len(answered_exchanges)} clarification round(s)")
            
            return augmentation
            
        except Exception as e:
            logger.error(f"Error creating all clarifications context: {str(e)}")
            return ""
    
    def load_template_for_validation_result(self, validation_output: str) -> str:
        """
        Load a template file based on the validation output type.
        
        Args:
            validation_output: The validation output type (e.g., INVALID, SATISFIABLE)
            
        Returns:
            The template content as a string
            
        Raises:
            FileNotFoundError: If the template file doesn't exist
        """
        # Convert validation output to lowercase for filename
        template_name = validation_output.lower()
        return self.load_template_by_name(template_name)
    
    def load_template_by_name(self, template_name: str) -> str:
        """
        Load a template file by its name.
        
        Args:
            template_name: The template name (e.g., 'initial_response', 'clarification_regeneration')
            
        Returns:
            The template content as a string
            
        Raises:
            FileNotFoundError: If the template file doesn't exist
        """
        filename = f"{template_name}.md"
        filepath = os.path.join(self.templates_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Template file not found: {filepath}")
            raise FileNotFoundError(f"Template file not found: {template_name}")
    
    def render_template(
        self,
        template: str,
        original_prompt: str = "",
        original_response: str = "",
        findings: List[Finding] = None,
        context_augmentation: str = "",
        policy_context: str = "",
        **kwargs
    ) -> str:
        """
        Render a template by replacing placeholders with actual values.
        
        This method supports both common named parameters and arbitrary keyword arguments
        for maximum flexibility. Policy context is automatically appended to the rendered
        template if provided, even when not explicitly used in the template.
        
        Common placeholders:
        - {{original_prompt}}: The user's original prompt
        - {{original_response}}: The LLM's response that failed validation
        - {{findings}}: Formatted list of validation findings (auto-generated from findings param)
        - {{context_augmentation}}: Previous Q&A clarification
        - {{policy_context}}: Formatted policy context with rules and variables
        - Any custom placeholder matching a kwarg key
        
        Args:
            template: The template string with placeholders
            original_prompt: The user's original prompt
            original_response: The LLM's response that failed validation
            findings: Optional list of Finding objects for auto-formatting
            context_augmentation: Previous Q&A clarification
            policy_context: Formatted policy context with rules and variables
            **kwargs: Additional keyword arguments where keys match placeholder names
            
        Returns:
            The rendered template with placeholders replaced, and policy context appended
            
        Example:
            # Simple rendering with named params
            render_template(template, original_prompt="Hello", policy_context="...")
            
            # Findings-based rendering
            render_template(template, findings=[...], original_prompt="...", original_response="...")
            
            # Custom placeholders
            render_template(template, user_prompt="Hello", custom_field="value")
        """
        # Build the replacement dictionary starting with named parameters
        replacements = {
            'original_prompt': original_prompt,
            'original_response': original_response,
            'context_augmentation': context_augmentation,
            'policy_context': policy_context,
        }
        
        # Merge in any additional kwargs first (they can override defaults)
        replacements.update(kwargs)
        
        # If findings parameter is provided (even if empty), auto-generate findings-related placeholders
        # Only process if findings is a list (not if it's already been formatted as a string)
        if findings is not None and isinstance(findings, list):
            # Format findings as a readable list (only if not already provided in kwargs)
            if 'findings' not in replacements:
                replacements['findings'] = self._format_findings(findings)
        elif findings is not None:
            # findings is provided but not a list (e.g., a pre-formatted string)
            # Add it to replacements if not already there
            if 'findings' not in replacements:
                replacements['findings'] = str(findings)
        
        # Replace all placeholders
        rendered = template
        for key, value in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value) if value is not None else "")
        
        # Always append policy context at the end if provided and not already in template
        # This ensures policy context is available even if template doesn't use {{policy_context}}
        if policy_context and policy_context.strip():
            # Check if policy_context placeholder was used in the template
            policy_placeholder_used = "{{policy_context}}" in template
            
            if not policy_placeholder_used:
                # Append policy context at the end with clear separation
                rendered = f"{rendered}\n\n{policy_context}"
                logger.debug("Policy context automatically appended to rendered template")
        
        return rendered
    
    def _format_findings(self, findings: List[Finding]) -> str:
        """
        Format findings as a readable text list with rich details.
        
        Args:
            findings: List of Finding objects
            
        Returns:
            Formatted string representation of findings
        """
        if not findings:
            return "No specific findings provided."
        
        formatted_lines = []
        for i, finding in enumerate(findings, 1):
            validation_output = finding.validation_output
            details = finding.details
            
            # Build finding description
            lines = [f"Finding {i}: {validation_output}"]
            
            # Add premises if available
            if details.get("premises"):
                lines.append("\nWhat the system understood as given facts (premises):")
                for j, premise in enumerate(details["premises"], 1):
                    premise_text = premise.get("natural_language") or premise.get("logic", "")
                    if premise_text:
                        lines.append(f"  {j}. {premise_text}")
            
            # Add claims if available
            if details.get("claims"):
                lines.append("\nWhat the system understood as your claims:")
                for j, claim in enumerate(details["claims"], 1):
                    claim_text = claim.get("natural_language") or claim.get("logic", "")
                    if claim_text:
                        lines.append(f"  {j}. {claim_text}")
            
            # Add confidence if available
            if details.get("confidence") is not None:
                confidence_pct = details["confidence"] * 100
                lines.append(f"\nConfidence in this interpretation: {confidence_pct:.1f}%")
            
            # Add supporting rules for VALID findings
            if details.get("supporting_rules"):
                lines.append("\nSupporting policy rules:")
                for rule in details["supporting_rules"]:
                    lines.append(f"  - Rule ID: {rule.get('identifier', 'unknown')}")
            
            # Add contradicting rules for INVALID/IMPOSSIBLE findings
            if details.get("contradicting_rules"):
                lines.append("\nYour response contradicts these policy rules:")
                for rule in details["contradicting_rules"]:
                    lines.append(f"  - Rule ID: {rule.get('identifier', 'unknown')}")
            
            # Add scenarios for SATISFIABLE findings
            # For SATISFIABLE findings with both scenarios, filter to show only disagreeing variables
            if validation_output == "SATISFIABLE" and details.get("claims_true_scenario") and details.get("claims_false_scenario"):
                # Identify disagreeing variables
                disagreeing_vars = identify_disagreeing_variables(
                    details["claims_true_scenario"],
                    details["claims_false_scenario"]
                )
                
                if disagreeing_vars:
                    # Filter scenarios to show only disagreeing variables
                    filtered_true = filter_scenario_statements(
                        details["claims_true_scenario"],
                        disagreeing_vars
                    )
                    filtered_false = filter_scenario_statements(
                        details["claims_false_scenario"],
                        disagreeing_vars
                    )
                    
                    # Add enhanced guidance about disagreeing variables
                    lines.append("\nThe following variables have different values between scenarios:")
                    lines.append("(These represent the unstated assumptions causing ambiguity)")
                    
                    lines.append("\nScenario where your claims would be TRUE:")
                    for stmt in filtered_true.get("statements", []):
                        stmt_text = stmt.get("natural_language") or stmt.get("logic", "")
                        if stmt_text:
                            lines.append(f"  - {stmt_text}")
                    
                    lines.append("\nScenario where your claims would be FALSE:")
                    for stmt in filtered_false.get("statements", []):
                        stmt_text = stmt.get("natural_language") or stmt.get("logic", "")
                        if stmt_text:
                            lines.append(f"  - {stmt_text}")
                else:
                    # No disagreeing variables found - fall back to showing full scenarios
                    lines.append("\nScenario where your claims would be TRUE:")
                    for stmt in details["claims_true_scenario"].get("statements", []):
                        stmt_text = stmt.get("natural_language") or stmt.get("logic", "")
                        if stmt_text:
                            lines.append(f"  - {stmt_text}")
                    
                    lines.append("\nScenario where your claims would be FALSE:")
                    for stmt in details["claims_false_scenario"].get("statements", []):
                        stmt_text = stmt.get("natural_language") or stmt.get("logic", "")
                        if stmt_text:
                            lines.append(f"  - {stmt_text}")
            else:
                # Non-SATISFIABLE or missing scenarios - use original formatting
                if details.get("claims_true_scenario"):
                    lines.append("\nScenario where your claims would be TRUE:")
                    for stmt in details["claims_true_scenario"].get("statements", []):
                        stmt_text = stmt.get("natural_language") or stmt.get("logic", "")
                        if stmt_text:
                            lines.append(f"  - {stmt_text}")
                
                if details.get("claims_false_scenario"):
                    lines.append("\nScenario where your claims would be FALSE:")
                    for stmt in details["claims_false_scenario"].get("statements", []):
                        stmt_text = stmt.get("natural_language") or stmt.get("logic", "")
                        if stmt_text:
                            lines.append(f"  - {stmt_text}")
            
            # Add translation options for TRANSLATION_AMBIGUOUS findings
            if details.get("translation_options"):
                lines.append("\nPossible interpretations of your response:")
                for j, option in enumerate(details["translation_options"], 1):
                    lines.append(f"\nInterpretation {j}:")
                    for trans in option.get("translations", []):
                        if trans.get("premises"):
                            lines.append("  Premises:")
                            for premise in trans["premises"]:
                                p_text = premise.get("natural_language") or premise.get("logic", "")
                                if p_text:
                                    lines.append(f"    - {p_text}")
                        if trans.get("claims"):
                            lines.append("  Claims:")
                            for claim in trans["claims"]:
                                c_text = claim.get("natural_language") or claim.get("logic", "")
                                if c_text:
                                    lines.append(f"    - {c_text}")
            
            # Add logic warnings if present
            if details.get("logic_warning"):
                warning = details["logic_warning"]
                lines.append(f"\n⚠️  Logic Warning: {warning.get('type', 'Unknown')}")
                if warning.get("premises"):
                    lines.append("  Affected premises:")
                    for premise in warning["premises"]:
                        p_text = premise.get("natural_language") or premise.get("logic", "")
                        if p_text:
                            lines.append(f"    - {p_text}")
            
            formatted_lines.append("\n".join(lines))
        
        return "\n\n".join(formatted_lines)
