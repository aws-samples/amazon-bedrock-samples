"""
Property-based tests for Validation Service.
"""
import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch

from backend.services.validation_service import ValidationService, ValidationResult
from backend.models.thread import Finding


class TestValidationServiceProperties:
    """Property-based tests for Validation Service."""
    
    @given(
        validation_output=st.sampled_from([
            "VALID", "INVALID", "SATISFIABLE", "IMPOSSIBLE", 
            "TRANSLATION_AMBIGUOUS", "TOO_COMPLEX", "NO_TRANSLATIONS"
        ]),
        property_text=st.text(min_size=1, max_size=100),
        explanation=st.text(min_size=1, max_size=200)
    )
    def test_property_12_validation_results_are_parsed(
        self, validation_output, property_text, explanation
    ):
        """
        Feature: ar-chatbot, Property 12: Validation results are parsed
        
        For any ApplyGuardrail API response, the system should correctly parse 
        the validation output and findings.
        
        Validates: Requirements 3.3
        """
        # Create service
        service = ValidationService(
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        
        # Create a mock API response using the correct structure
        # The finding is a tagged union with one key matching the validation_output
        finding_key = validation_output.lower().replace("_", "")  # Convert to camelCase-ish
        if validation_output == "TRANSLATION_AMBIGUOUS":
            finding_key = "translationAmbiguous"
        elif validation_output == "TOO_COMPLEX":
            finding_key = "tooComplex"
        elif validation_output == "NO_TRANSLATIONS":
            finding_key = "noTranslations"
        
        finding_data = {
            "translation": {
                "premises": [{"naturalLanguage": property_text}],
                "claims": [{"naturalLanguage": explanation}]
            }
        }
        
        mock_response = {
            "action": "GUARDRAIL_INTERVENED" if validation_output != "VALID" else "NONE",
            "assessments": [
                {
                    "automatedReasoningPolicy": {
                        "findings": [
                            {finding_key: finding_data}
                        ]
                    }
                }
            ] if validation_output != "VALID" else []
        }
        
        # Mock the boto3 client
        service.client.apply_guardrail = Mock(return_value=mock_response)
        
        # Call validate
        result = service.validate("test prompt", "test response")
        
        # Verify the result is a ValidationResult
        assert isinstance(result, ValidationResult)
        
        # Verify output is parsed correctly
        assert result.output is not None
        assert isinstance(result.output, str)
        
        # Verify findings are parsed correctly
        assert isinstance(result.findings, list)
        
        # If there were findings in the response, verify they were parsed
        if validation_output != "VALID":
            assert len(result.findings) > 0
            finding = result.findings[0]
            assert isinstance(finding, Finding)
            assert finding.validation_output == validation_output
            # Verify details were extracted
            assert isinstance(finding.details, dict)
    
    @given(
        # Generate a list of findings with different validation outputs
        findings_data=st.lists(
            st.sampled_from([
                "TRANSLATION_AMBIGUOUS",
                "IMPOSSIBLE", 
                "INVALID",
                "SATISFIABLE"
            ]),
            min_size=2,
            max_size=10
        )
    )
    def test_property_27_findings_are_sorted_by_priority(self, findings_data):
        """
        Feature: ar-chatbot, Property 27: Findings are sorted by priority
        
        For any rewriting prompt generation, findings should be sorted in this order:
        TRANSLATION_AMBIGUOUS, IMPOSSIBLE, INVALID, SATISFIABLE.
        
        Validates: Requirements 7.2
        """
        # Create service
        service = ValidationService(
            guardrail_id="test-guardrail-id",
            guardrail_version="DRAFT"
        )
        
        # Create findings from the generated data
        findings = [
            Finding(validation_output=output, details={"property": f"prop_{i}"})
            for i, output in enumerate(findings_data)
        ]
        
        # Sort the findings using the service's method
        sorted_findings = service._sort_findings(findings)
        
        # Define the expected priority order
        priority_order = [
            "TRANSLATION_AMBIGUOUS",
            "IMPOSSIBLE",
            "INVALID",
            "SATISFIABLE"
        ]
        
        # Verify that findings are sorted according to priority
        # For each pair of consecutive findings, verify the first has equal or higher priority
        for i in range(len(sorted_findings) - 1):
            current_output = sorted_findings[i].validation_output
            next_output = sorted_findings[i + 1].validation_output
            
            current_priority = priority_order.index(current_output)
            next_priority = priority_order.index(next_output)
            
            # Current finding should have equal or higher priority (lower index)
            assert current_priority <= next_priority, (
                f"Findings not sorted correctly: {current_output} (priority {current_priority}) "
                f"should come before or equal to {next_output} (priority {next_priority})"
            )
