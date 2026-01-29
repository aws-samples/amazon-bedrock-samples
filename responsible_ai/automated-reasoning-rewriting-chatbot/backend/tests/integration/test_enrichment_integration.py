"""
Integration test to verify rule enrichment works end-to-end.
"""
from backend.services.policy_service import PolicyService
from backend.models.thread import Finding


def test_enrichment_integration():
    """Test that enrichment works with realistic data."""
    
    # Simulate a policy definition
    policy_definition = {
        "rules": [
            {
                "id": "rule-123",
                "expression": "(=> (employee x) (has_badge x))",
                "alternateExpression": "All employees must have a badge",
                "description": "Security policy requiring badges"
            },
            {
                "id": "rule-456",
                "expression": "(=> (visitor x) (has_escort x))",
                "alternateExpression": "All visitors must have an escort",
                "description": "Security policy for visitors"
            }
        ]
    }
    
    # Create finding service
    policy_service = PolicyService(policy_definition)
    
    # Simulate a finding from validation service (VALID with supporting rules)
    finding = Finding(
        validation_output="VALID",
        details={
            "premises": [
                {"logic": "employee(john)", "natural_language": "John is an employee"}
            ],
            "claims": [
                {"logic": "has_badge(john)", "natural_language": "John has a badge"}
            ],
            "supporting_rules": [
                {
                    "identifier": "rule-123",
                    "policy_version_arn": "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy:1"
                }
            ]
        }
    )
    
    # Enrich the finding
    enriched_findings = policy_service.enrich_findings([finding])
    
    # Verify enrichment worked
    assert len(enriched_findings) == 1
    enriched = enriched_findings[0]
    
    print("\n=== Original Finding ===")
    print(f"Supporting rules: {finding.details['supporting_rules']}")
    
    print("\n=== Enriched Finding ===")
    print(f"Supporting rules: {enriched.details['supporting_rules']}")
    
    # Check that enrichment added the fields
    enriched_rule = enriched.details['supporting_rules'][0]
    assert enriched_rule['identifier'] == 'rule-123'
    assert enriched_rule['expression'] == '(=> (employee x) (has_badge x))'
    assert enriched_rule['alternateExpression'] == 'All employees must have a badge'
    assert enriched_rule['description'] == 'Security policy requiring badges'
    
    print("\n✓ Enrichment working correctly!")
    print(f"  - Rule ID: {enriched_rule['identifier']}")
    print(f"  - Alternate Expression: {enriched_rule['alternateExpression']}")
    print(f"  - Expression: {enriched_rule['expression']}")
    
    # Test with INVALID finding (contradicting rules)
    invalid_finding = Finding(
        validation_output="INVALID",
        details={
            "contradicting_rules": [
                {
                    "identifier": "rule-456",
                    "policy_version_arn": "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy:1"
                }
            ]
        }
    )
    
    enriched_invalid = policy_service.enrich_findings([invalid_finding])
    enriched_rule_2 = enriched_invalid[0].details['contradicting_rules'][0]
    
    assert enriched_rule_2['alternateExpression'] == 'All visitors must have an escort'
    print(f"\n✓ Contradicting rules also enriched correctly!")
    print(f"  - Rule ID: {enriched_rule_2['identifier']}")
    print(f"  - Alternate Expression: {enriched_rule_2['alternateExpression']}")


if __name__ == "__main__":
    test_enrichment_integration()
