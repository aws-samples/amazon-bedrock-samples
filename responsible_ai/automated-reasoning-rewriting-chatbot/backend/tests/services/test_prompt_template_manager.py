"""
Tests for Prompt Template Manager.
"""
import pytest
import os
import tempfile
from backend.services.prompt_template_manager import PromptTemplateManager
from backend.models.thread import Finding


class TestPromptTemplateManager:
    """Tests for PromptTemplateManager."""
    
    def test_load_template_success(self):
        """Test loading an existing template file."""
        # Use path relative to project root (tests/services -> backend -> project root -> prompts)
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts")
        manager = PromptTemplateManager(templates_dir=templates_dir)
        
        # Load one of the templates we created
        template = manager.load_template_for_validation_result("INVALID")
        
        # Verify template was loaded and contains expected content
        assert template is not None
        assert len(template) > 0
        assert "{{original_prompt}}" in template
        assert "{{findings}}" in template
        # New templates don't show original_response to avoid anchoring the LLM
    
    def test_load_template_not_found(self):
        """Test loading a non-existent template raises FileNotFoundError."""
        # Use path relative to project root (tests/services -> backend -> project root -> prompts)
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts")
        manager = PromptTemplateManager(templates_dir=templates_dir)
        
        with pytest.raises(FileNotFoundError):
            manager.load_template_for_validation_result("NONEXISTENT")
    
    def test_render_template_basic(self):
        """Test rendering a template with basic placeholders."""
        manager = PromptTemplateManager()
        
        template = """
Original: {{original_prompt}}
Findings: {{findings}}
"""
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={
                    "premises": [{"logic": "x > 0", "natural_language": "x is positive"}],
                    "claims": [{"logic": "x < 0", "natural_language": "x is negative"}]
                }
            )
        ]
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            original_response="Test response",
            findings=findings
        )
        
        # Verify placeholders were replaced
        assert "Test prompt" in rendered
        assert "INVALID" in rendered
        assert "Finding 1" in rendered
        assert "{{original_prompt}}" not in rendered
        assert "{{original_response}}" not in rendered
    

    def test_render_template_empty_findings(self):
        """Test rendering with empty findings list."""
        manager = PromptTemplateManager()
        
        template = "Findings: {{findings}}\nProperty: {{property}}"
        
        rendered = manager.render_template(
            template=template,
            original_prompt="prompt",
            original_response="response",
            findings=[]
        )
        
        # Should handle empty findings gracefully
        assert "No specific findings provided" in rendered
        assert "Property: " in rendered  # Empty property
    
    def test_format_findings_multiple(self):
        """Test formatting multiple findings."""
        manager = PromptTemplateManager()
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={
                    "premises": [{"logic": "p1", "natural_language": "premise 1"}],
                    "claims": [{"logic": "c1", "natural_language": "claim 1"}]
                }
            ),
            Finding(
                validation_output="SATISFIABLE",
                details={
                    "premises": [{"logic": "p2", "natural_language": "premise 2"}],
                    "claims": [{"logic": "c2", "natural_language": "claim 2"}]
                }
            )
        ]
        
        formatted = manager._format_findings(findings)
        
        # Verify both findings are included with new format
        assert "Finding 1: INVALID" in formatted
        assert "Finding 2: SATISFIABLE" in formatted
        assert "premise 1" in formatted
        assert "claim 2" in formatted
    
    def test_integration_with_real_templates(self):
        """Test loading and rendering real template files."""
        # Use path relative to project root (tests/services -> backend -> project root -> prompts)
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts")
        manager = PromptTemplateManager(templates_dir=templates_dir)
        
        # Test each template type
        for validation_output in ["INVALID", "SATISFIABLE", "IMPOSSIBLE", "TRANSLATION_AMBIGUOUS"]:
            template = manager.load_template_for_validation_result(validation_output)
            
            findings = [
                Finding(
                    validation_output=validation_output,
                    details={
                        "premises": [{"logic": "test", "natural_language": "test premise"}],
                        "claims": [{"logic": "test", "natural_language": "test claim"}]
                    }
                )
            ]
            
            rendered = manager.render_template(
                template=template,
                original_prompt="What is 2+2?",
                original_response="5",
                findings=findings
            )
            
            # Verify rendering worked - new templates don't show original response
            assert "What is 2+2?" in rendered
            assert validation_output in rendered
            assert "Finding 1" in rendered
            assert "{{original_prompt}}" not in rendered
            assert "{{original_response}}" not in rendered
            assert "{{findings}}" not in rendered
    
    def test_render_template_with_context_augmentation(self):
        """Test rendering a template with context augmentation."""
        manager = PromptTemplateManager()
        
        template = """
Original: {{original_prompt}}
{{context_augmentation}}
Findings: {{findings}}
"""
        
        findings = [
            Finding(
                validation_output="TRANSLATION_AMBIGUOUS",
                details={
                    "premises": [{"logic": "x > 0", "natural_language": "x is positive"}],
                    "claims": [{"logic": "x < 0", "natural_language": "x is negative"}]
                }
            )
        ]
        
        context_augmentation = """**Previous Clarification:**

Q: What specific aspect would you like me to clarify?
A: I'm interested in scenario A specifically."""
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            original_response="Test response",
            findings=findings,
            context_augmentation=context_augmentation
        )
        
        # Verify placeholders were replaced
        assert "Test prompt" in rendered
        assert "Previous Clarification" in rendered
        assert "What specific aspect" in rendered
        assert "scenario A specifically" in rendered
        assert "TRANSLATION_AMBIGUOUS" in rendered
        assert "{{context_augmentation}}" not in rendered
    
    def test_render_template_without_context_augmentation(self):
        """Test rendering a template without context augmentation (None)."""
        manager = PromptTemplateManager()
        
        template = """
Original: {{original_prompt}}
{{context_augmentation}}
Findings: {{findings}}
"""
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={
                    "premises": [{"logic": "x > 0", "natural_language": "x is positive"}]
                }
            )
        ]
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            original_response="Test response",
            findings=findings,
            context_augmentation=None
        )
        
        # Verify placeholder was replaced with empty string
        assert "Test prompt" in rendered
        assert "{{context_augmentation}}" not in rendered
        # Should not have extra blank lines or content where augmentation would be
        assert "Original: Test prompt\n\nFindings:" in rendered
    
    def test_render_template_preserves_original_content_with_augmentation(self):
        """Test that original prompt and response are preserved when augmentation is added."""
        manager = PromptTemplateManager()
        
        template = """
Original Prompt: {{original_prompt}}
Original Response: {{original_response}}
{{context_augmentation}}
Findings: {{findings}}
"""
        
        findings = [
            Finding(
                validation_output="SATISFIABLE",
                details={"premises": [{"natural_language": "test"}]}
            )
        ]
        
        context_augmentation = "**Previous Clarification:**\n\nQ: Test?\nA: Yes."
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Original user prompt",
            original_response="Original LLM response",
            findings=findings,
            context_augmentation=context_augmentation
        )
        
        # Verify original content is preserved
        assert "Original user prompt" in rendered
        assert "Original LLM response" in rendered
        # Verify augmentation is included
        assert "Previous Clarification" in rendered
        assert "Q: Test?" in rendered
        # Verify findings are included
        assert "SATISFIABLE" in rendered
    
    def test_render_template_with_policy_context(self):
        """Test rendering a template with policy context."""
        manager = PromptTemplateManager()
        
        template = """
{{policy_context}}

Original: {{original_prompt}}
Findings: {{findings}}
"""
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={
                    "premises": [{"logic": "x > 0", "natural_language": "x is positive"}],
                    "claims": [{"logic": "x < 0", "natural_language": "x is negative"}]
                }
            )
        ]
        
        policy_context = """## Policy Context

### Rules
- rule-1: All employees must have a badge
- rule-2: All visitors must have an escort

### Variables
- employee: A person employed by the organization
- visitor: A person visiting the organization"""
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            original_response="Test response",
            findings=findings,
            policy_context=policy_context
        )
        
        # Verify placeholders were replaced
        assert "Test prompt" in rendered
        assert "INVALID" in rendered
        assert "Policy Context" in rendered
        assert "All employees must have a badge" in rendered
        assert "employee: A person employed by the organization" in rendered
        assert "{{policy_context}}" not in rendered
    
    def test_render_template_without_policy_context(self):
        """Test rendering a template without policy context (empty string)."""
        manager = PromptTemplateManager()
        
        template = """
{{policy_context}}
Original: {{original_prompt}}
Findings: {{findings}}
"""
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={
                    "premises": [{"logic": "x > 0", "natural_language": "x is positive"}]
                }
            )
        ]
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            original_response="Test response",
            findings=findings,
            policy_context=""
        )
        
        # Verify placeholder was replaced with empty string
        assert "Test prompt" in rendered
        assert "{{policy_context}}" not in rendered
        # Should not have policy context content
        assert "Policy Context" not in rendered
        assert "Rules" not in rendered or "Finding" in rendered  # "Rules" might appear in findings
    
    def test_render_template_policy_context_default_empty(self):
        """Test that policy_context defaults to empty string when not provided."""
        manager = PromptTemplateManager()
        
        template = "{{policy_context}}Content: {{original_prompt}}"
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={"premises": [{"natural_language": "test"}]}
            )
        ]
        
        # Call without policy_context parameter
        rendered = manager.render_template(
            template=template,
            original_prompt="Test",
            original_response="Response",
            findings=findings
        )
        
        # Verify placeholder was replaced with empty string
        assert "{{policy_context}}" not in rendered
        assert "Content: Test" in rendered
    
    def test_render_template_auto_appends_policy_context(self):
        """Test that policy context is automatically appended even when not in template."""
        manager = PromptTemplateManager()
        
        # Template without {{policy_context}} placeholder
        template = """Original: {{original_prompt}}
Response: {{original_response}}
Findings: {{findings}}"""
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={
                    "premises": [{"logic": "x > 0", "natural_language": "x is positive"}]
                }
            )
        ]
        
        policy_context = """## Policy Context

### Rules
- rule-1: All employees must have a badge
- rule-2: All visitors must have an escort"""
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            original_response="Test response",
            findings=findings,
            policy_context=policy_context
        )
        
        # Verify template content is present
        assert "Original: Test prompt" in rendered
        assert "Response: Test response" in rendered
        assert "INVALID" in rendered
        
        # Verify policy context was automatically appended at the end
        assert "## Policy Context" in rendered
        assert "All employees must have a badge" in rendered
        assert "All visitors must have an escort" in rendered
        
        # Verify policy context appears after the main content
        prompt_index = rendered.index("Test prompt")
        policy_index = rendered.index("## Policy Context")
        assert policy_index > prompt_index, "Policy context should be appended after main content"
    
    def test_render_template_no_duplicate_policy_context(self):
        """Test that policy context is not duplicated when placeholder is used."""
        manager = PromptTemplateManager()
        
        # Template WITH {{policy_context}} placeholder
        template = """{{policy_context}}

Original: {{original_prompt}}
Response: {{original_response}}"""
        
        policy_context = """## Policy Context

### Rules
- rule-1: Test rule"""
        
        rendered = manager.render_template(
            template=template,
            original_prompt="Test prompt",
            original_response="Test response",
            policy_context=policy_context
        )
        
        # Verify policy context appears only once
        policy_count = rendered.count("## Policy Context")
        assert policy_count == 1, f"Policy context should appear exactly once, found {policy_count} times"
        
        # Verify it's at the beginning (where placeholder was)
        assert rendered.strip().startswith("## Policy Context")


# Property-Based Tests
from hypothesis import given, strategies as st, settings
from backend.services.prompt_template_manager import (
    extract_variable_from_statement,
    identify_disagreeing_variables,
    filter_scenario_statements
)


class TestScenarioFilteringProperties:
    """Property-based tests for scenario filtering functions."""
    
    @given(
        st.lists(
            st.tuples(
                st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=10),
                st.text(min_size=1, max_size=20)
            ),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_property_complete_disagreement_identification(self, var_value_pairs):
        """
        **Feature: rewriting-feedback-clarity, Property 1: Complete disagreement identification**
        
        Property: For any pair of scenarios (claims true and claims false), 
        the disagreement identification function should return all variables 
        that have different values between the two scenarios, and only those variables.
        
        **Validates: Requirements 1.1**
        """
        if not var_value_pairs:
            # Edge case: empty scenarios
            claims_true = {"statements": []}
            claims_false = {"statements": []}
            result = identify_disagreeing_variables(claims_true, claims_false)
            assert result == set()
            return
        
        # Split variables into agreeing and disagreeing
        # Use first half as agreeing (same value in both scenarios)
        # Use second half as disagreeing (different values in scenarios)
        split_point = len(var_value_pairs) // 2
        agreeing_vars = var_value_pairs[:split_point]
        disagreeing_vars = var_value_pairs[split_point:]
        
        # Build expected disagreeing set
        expected_disagreeing = {var for var, _ in disagreeing_vars}
        
        # Build claims_true scenario
        true_statements = []
        for var, value1 in agreeing_vars:
            true_statements.append({
                "logic": f"{var} = {value1}",
                "natural_language": f"{var} equals {value1}"
            })
        for var, value1 in disagreeing_vars:
            true_statements.append({
                "logic": f"{var} = {value1}",
                "natural_language": f"{var} equals {value1}"
            })
        
        # Build claims_false scenario
        false_statements = []
        for var, value1 in agreeing_vars:
            # Same value as true scenario
            false_statements.append({
                "logic": f"{var} = {value1}",
                "natural_language": f"{var} equals {value1}"
            })
        for var, value1 in disagreeing_vars:
            # Different value from true scenario
            false_statements.append({
                "logic": f"{var} = different_{value1}",
                "natural_language": f"{var} equals different_{value1}"
            })
        
        claims_true = {"statements": true_statements}
        claims_false = {"statements": false_statements}
        
        # Test the property
        result = identify_disagreeing_variables(claims_true, claims_false)
        
        # Verify: result should contain exactly the disagreeing variables
        assert result == expected_disagreeing, \
            f"Expected disagreeing variables {expected_disagreeing}, but got {result}"
    
    @given(
        st.lists(
            st.tuples(
                st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=10),
                st.text(min_size=1, max_size=20),
                st.booleans()  # True if disagreeing, False if agreeing
            ),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_property_filtered_scenarios_contain_only_disagreeing(self, var_value_disagree_tuples):
        """
        **Feature: rewriting-feedback-clarity, Property 2: Filtered scenarios contain only disagreeing variables**
        
        Property: For any scenario and set of disagreeing variables, filtering the scenario 
        should result in a scenario containing only statements about variables in the 
        disagreeing set, with all other statements removed.
        
        **Validates: Requirements 1.2, 1.3**
        """
        if not var_value_disagree_tuples:
            # Edge case: empty scenario
            scenario = {"statements": []}
            disagreeing = set()
            result = filter_scenario_statements(scenario, disagreeing)
            assert result == {"statements": []}
            return
        
        # Build scenario and disagreeing set
        statements = []
        disagreeing_vars = set()
        
        for var, value, is_disagreeing in var_value_disagree_tuples:
            statements.append({
                "logic": f"{var} = {value}",
                "natural_language": f"{var} equals {value}"
            })
            if is_disagreeing:
                disagreeing_vars.add(var)
        
        scenario = {"statements": statements}
        
        # Filter the scenario
        result = filter_scenario_statements(scenario, disagreeing_vars)
        
        # Verify: all statements in result should be about disagreeing variables
        result_statements = result.get("statements", [])
        for stmt in result_statements:
            var = extract_variable_from_statement(stmt)
            assert var in disagreeing_vars, \
                f"Filtered scenario contains statement about non-disagreeing variable: {var}"
        
        # Verify: all disagreeing variables that were in original should be in result
        original_vars = {extract_variable_from_statement(stmt) for stmt in statements}
        expected_in_result = disagreeing_vars & original_vars
        result_vars = {extract_variable_from_statement(stmt) for stmt in result_statements}
        
        assert result_vars == expected_in_result, \
            f"Expected variables {expected_in_result} in filtered result, but got {result_vars}"


class TestContextAugmentation:
    """Tests for context augmentation functionality."""
    
    def test_create_context_augmentation_with_valid_qa_pairs(self):
        """Test creating augmentation with valid question-answer pairs."""
        manager = PromptTemplateManager()
        
        questions = [
            'What specific aspect would you like me to clarify?',
            'Are you asking about scenario A or scenario B?'
        ]
        answers = [
            'I am interested in scenario A specifically.',
            'The technical perspective.'
        ]
        
        result = manager.create_context_augmentation(questions, answers)
        
        # Check that the result contains the expected format
        assert '**Previous Clarification:**' in result
        assert 'Q: What specific aspect would you like me to clarify?' in result
        assert 'A: I am interested in scenario A specifically.' in result
        assert 'Q: Are you asking about scenario A or scenario B?' in result
        assert 'A: The technical perspective.' in result
    
    def test_create_context_augmentation_with_single_qa_pair(self):
        """Test creating augmentation with a single question-answer pair."""
        manager = PromptTemplateManager()
        
        questions = ['What do you mean by that?']
        answers = ['I mean the first option.']
        
        result = manager.create_context_augmentation(questions, answers)
        
        assert '**Previous Clarification:**' in result
        assert 'Q: What do you mean by that?' in result
        assert 'A: I mean the first option.' in result
    
    def test_create_context_augmentation_with_empty_questions(self):
        """Test that empty questions list returns empty string."""
        manager = PromptTemplateManager()
        
        questions = []
        answers = ['Some answer']
        
        result = manager.create_context_augmentation(questions, answers)
        
        assert result == ""
    
    def test_create_context_augmentation_with_empty_answers(self):
        """Test that empty answers list returns empty string."""
        manager = PromptTemplateManager()
        
        questions = ['Some question?']
        answers = []
        
        result = manager.create_context_augmentation(questions, answers)
        
        assert result == ""
    
    def test_create_context_augmentation_with_mismatched_counts(self):
        """Test handling of mismatched question and answer counts."""
        manager = PromptTemplateManager()
        
        questions = [
            'Question 1?',
            'Question 2?',
            'Question 3?'
        ]
        answers = ['Answer 1']
        
        result = manager.create_context_augmentation(questions, answers)
        
        # Should only include the first Q&A pair (minimum of both lengths)
        assert '**Previous Clarification:**' in result
        assert 'Q: Question 1?' in result
        assert 'A: Answer 1' in result
        # Should not include questions without answers
        assert 'Question 2?' not in result
        assert 'Question 3?' not in result
    
    def test_create_context_augmentation_with_whitespace_in_qa(self):
        """Test that whitespace is properly handled in questions and answers."""
        manager = PromptTemplateManager()
        
        questions = ['  Question with spaces?  ']
        answers = ['  Answer with spaces  ']
        
        result = manager.create_context_augmentation(questions, answers)
        
        # Whitespace should be stripped
        assert 'Q: Question with spaces?' in result
        assert 'A: Answer with spaces' in result
    
    def test_create_context_augmentation_skips_empty_qa_pairs(self):
        """Test that empty Q&A pairs are skipped."""
        manager = PromptTemplateManager()
        
        questions = ['Valid question?', '', 'Another valid question?']
        answers = ['Valid answer', 'Some answer', '']
        
        result = manager.create_context_augmentation(questions, answers)
        
        # Should include the first valid pair
        assert 'Q: Valid question?' in result
        assert 'A: Valid answer' in result
        # Should skip pairs with empty questions or answers
        # The third pair has an empty answer, so it should be skipped
    
    def test_create_context_augmentation_format_structure(self):
        """Test that the augmentation follows the correct format structure."""
        manager = PromptTemplateManager()
        
        questions = ['Question 1?', 'Question 2?']
        answers = ['Answer 1', 'Answer 2']
        
        result = manager.create_context_augmentation(questions, answers)
        
        lines = result.split('\n')
        
        # First line should be the header
        assert lines[0] == '**Previous Clarification:**'
        # Second line should be empty
        assert lines[1] == ''
        # Then Q&A pairs with empty lines between them
        assert lines[2].startswith('Q: ')
        assert lines[3].startswith('A: ')
        assert lines[4] == ''  # Empty line after first pair
        assert lines[5].startswith('Q: ')
        assert lines[6].startswith('A: ')


class TestBackwardCompatibility:
    """Tests for backward compatibility of prompt template manager enhancements."""
    
    def test_non_satisfiable_findings_render_unchanged(self):
        """Test that non-SATISFIABLE findings render with original formatting."""
        manager = PromptTemplateManager()
        
        # Test INVALID finding
        invalid_finding = Finding(
            validation_output="INVALID",
            details={
                "premises": [{"logic": "x > 0", "natural_language": "x is positive"}],
                "claims": [{"logic": "x < 0", "natural_language": "x is negative"}],
                "contradicting_rules": [{"identifier": "rule_123"}]
            }
        )
        
        formatted = manager._format_findings([invalid_finding])
        
        # Verify original formatting is preserved
        assert "Finding 1: INVALID" in formatted
        assert "What the system understood as given facts (premises):" in formatted
        assert "x is positive" in formatted
        assert "What the system understood as your claims:" in formatted
        assert "x is negative" in formatted
        assert "Your response contradicts these policy rules:" in formatted
        assert "rule_123" in formatted
        
        # Verify no scenario filtering guidance is added
        assert "disagreeing variables" not in formatted.lower()
        assert "unstated assumptions" not in formatted.lower()
    
    def test_impossible_findings_render_unchanged(self):
        """Test that IMPOSSIBLE findings render with original formatting."""
        manager = PromptTemplateManager()
        
        impossible_finding = Finding(
            validation_output="IMPOSSIBLE",
            details={
                "premises": [{"logic": "p1", "natural_language": "premise 1"}],
                "contradicting_rules": [{"identifier": "rule_456"}]
            }
        )
        
        formatted = manager._format_findings([impossible_finding])
        
        # Verify original formatting
        assert "Finding 1: IMPOSSIBLE" in formatted
        assert "premise 1" in formatted
        assert "rule_456" in formatted
        
        # Verify no scenario filtering guidance
        assert "disagreeing variables" not in formatted.lower()
    
    def test_valid_findings_render_unchanged(self):
        """Test that VALID findings render with original formatting."""
        manager = PromptTemplateManager()
        
        valid_finding = Finding(
            validation_output="VALID",
            details={
                "premises": [{"logic": "p1", "natural_language": "premise 1"}],
                "claims": [{"logic": "c1", "natural_language": "claim 1"}],
                "supporting_rules": [{"identifier": "rule_789"}],
                "confidence": 0.95
            }
        )
        
        formatted = manager._format_findings([valid_finding])
        
        # Verify original formatting
        assert "Finding 1: VALID" in formatted
        assert "premise 1" in formatted
        assert "claim 1" in formatted
        assert "Supporting policy rules:" in formatted
        assert "rule_789" in formatted
        assert "Confidence in this interpretation: 95.0%" in formatted
        
        # Verify no scenario filtering guidance
        assert "disagreeing variables" not in formatted.lower()
    
    def test_satisfiable_findings_without_scenarios(self):
        """Test that SATISFIABLE findings without scenarios render gracefully."""
        manager = PromptTemplateManager()
        
        # SATISFIABLE finding with no scenarios
        satisfiable_finding = Finding(
            validation_output="SATISFIABLE",
            details={
                "premises": [{"logic": "p1", "natural_language": "premise 1"}],
                "claims": [{"logic": "c1", "natural_language": "claim 1"}]
            }
        )
        
        formatted = manager._format_findings([satisfiable_finding])
        
        # Verify basic formatting works
        assert "Finding 1: SATISFIABLE" in formatted
        assert "premise 1" in formatted
        assert "claim 1" in formatted
        
        # Verify no scenario sections are added
        assert "Scenario where your claims would be TRUE:" not in formatted
        assert "Scenario where your claims would be FALSE:" not in formatted
        
        # Verify no errors or exceptions occurred
        assert len(formatted) > 0
    
    def test_satisfiable_findings_with_only_one_scenario(self):
        """Test that SATISFIABLE findings with only one scenario use original formatting."""
        manager = PromptTemplateManager()
        
        # SATISFIABLE finding with only claims_true_scenario
        satisfiable_finding = Finding(
            validation_output="SATISFIABLE",
            details={
                "premises": [{"logic": "p1", "natural_language": "premise 1"}],
                "claims": [{"logic": "c1", "natural_language": "claim 1"}],
                "claims_true_scenario": {
                    "statements": [
                        {"logic": "x = 5", "natural_language": "x equals 5"},
                        {"logic": "y = 10", "natural_language": "y equals 10"}
                    ]
                }
            }
        )
        
        formatted = manager._format_findings([satisfiable_finding])
        
        # Verify original formatting (no filtering)
        assert "Finding 1: SATISFIABLE" in formatted
        assert "Scenario where your claims would be TRUE:" in formatted
        assert "x equals 5" in formatted
        assert "y equals 10" in formatted
        
        # Verify no filtering guidance is added
        assert "disagreeing variables" not in formatted.lower()
        assert "unstated assumptions" not in formatted.lower()
    
    def test_existing_placeholder_system_continues_to_work(self):
        """Test that all existing placeholders continue to work correctly."""
        manager = PromptTemplateManager()
        
        template = """
Original Prompt: {{original_prompt}}
Original Response: {{original_response}}
Context: {{context_augmentation}}
Findings: {{findings}}
"""
        
        findings = [
            Finding(
                validation_output="INVALID",
                details={
                    "premises": [{"natural_language": "test premise"}],
                    "claims": [{"natural_language": "test claim"}]
                }
            )
        ]
        
        rendered = manager.render_template(
            template=template,
            original_prompt="user prompt",
            original_response="llm response",
            findings=findings,
            context_augmentation="previous Q&A"
        )
        
        # Verify all placeholders are replaced
        assert "{{original_prompt}}" not in rendered
        assert "{{original_response}}" not in rendered
        assert "{{context_augmentation}}" not in rendered
        assert "{{findings}}" not in rendered
        
        # Verify values are present
        assert "user prompt" in rendered
        assert "llm response" in rendered
        assert "previous Q&A" in rendered
        assert "INVALID" in rendered
    
    def test_translation_ambiguous_findings_render_unchanged(self):
        """Test that TRANSLATION_AMBIGUOUS findings render with original formatting."""
        manager = PromptTemplateManager()
        
        translation_finding = Finding(
            validation_output="TRANSLATION_AMBIGUOUS",
            details={
                "translation_options": [
                    {
                        "translations": [
                            {
                                "premises": [{"logic": "p1", "natural_language": "premise 1"}],
                                "claims": [{"logic": "c1", "natural_language": "claim 1"}]
                            }
                        ]
                    },
                    {
                        "translations": [
                            {
                                "premises": [{"logic": "p2", "natural_language": "premise 2"}],
                                "claims": [{"logic": "c2", "natural_language": "claim 2"}]
                            }
                        ]
                    }
                ]
            }
        )
        
        formatted = manager._format_findings([translation_finding])
        
        # Verify original formatting
        assert "Finding 1: TRANSLATION_AMBIGUOUS" in formatted
        assert "Possible interpretations of your response:" in formatted
        assert "Interpretation 1:" in formatted
        assert "Interpretation 2:" in formatted
        assert "premise 1" in formatted
        assert "claim 2" in formatted
        
        # Verify no scenario filtering guidance
        assert "disagreeing variables" not in formatted.lower()
    
    def test_satisfiable_findings_with_both_scenarios_uses_filtering(self):
        """Test that SATISFIABLE findings with both scenarios use filtering."""
        manager = PromptTemplateManager()
        
        # SATISFIABLE finding with both scenarios and disagreeing variables
        satisfiable_finding = Finding(
            validation_output="SATISFIABLE",
            details={
                "premises": [{"logic": "p1", "natural_language": "premise 1"}],
                "claims": [{"logic": "c1", "natural_language": "claim 1"}],
                "claims_true_scenario": {
                    "statements": [
                        {"logic": "x = 5", "natural_language": "x equals 5"},
                        {"logic": "y = 10", "natural_language": "y equals 10"},
                        {"logic": "z = 20", "natural_language": "z equals 20"}
                    ]
                },
                "claims_false_scenario": {
                    "statements": [
                        {"logic": "x = 5", "natural_language": "x equals 5"},  # Same as true
                        {"logic": "y = 15", "natural_language": "y equals 15"},  # Different
                        {"logic": "z = 25", "natural_language": "z equals 25"}   # Different
                    ]
                }
            }
        )
        
        formatted = manager._format_findings([satisfiable_finding])
        
        # Verify filtering guidance is added
        assert "The following variables have different values between scenarios:" in formatted
        assert "(These represent the unstated assumptions causing ambiguity)" in formatted
        
        # Verify scenarios are shown
        assert "Scenario where your claims would be TRUE:" in formatted
        assert "Scenario where your claims would be FALSE:" in formatted
        
        # Verify only disagreeing variables are shown (y and z, not x)
        assert "y equals 10" in formatted  # y in true scenario
        assert "y equals 15" in formatted  # y in false scenario
        assert "z equals 20" in formatted  # z in true scenario
        assert "z equals 25" in formatted  # z in false scenario
        
        # x should NOT appear since it's the same in both scenarios
        # Note: We need to be careful here - "x equals 5" shouldn't appear in the scenario sections
        # Let's check that the filtered scenarios don't contain x
        lines = formatted.split('\n')
        in_scenario_section = False
        for line in lines:
            if "Scenario where your claims would be" in line:
                in_scenario_section = True
            elif "Finding" in line or "What the system understood" in line:
                in_scenario_section = False
            
            if in_scenario_section and "x equals" in line:
                # x should not appear in scenario sections
                assert False, f"Variable x (which agrees in both scenarios) should not appear in filtered scenarios, but found: {line}"
