"""
Tests for the Finding Service.

This test file consolidates tests from:
- test_finding_enricher.py (enrichment functionality)
- Policy context formatting tests (from integration tests)
- Finding processing tests (sorting, selection, question allowance)
"""
import pytest
from unittest.mock import patch, MagicMock
from backend.services.policy_service import PolicyService
from backend.models.thread import Finding


# ============================================================================
# Initialization Tests
# ============================================================================

@patch('backend.services.policy_service.boto3')
def test_policy_service_initializes_bedrock_client(mock_boto3):
    """Test that PolicyService initializes boto3 Bedrock client."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    service = PolicyService(region_name="us-east-1")
    
    # Verify boto3.client was called with correct parameters
    mock_boto3.client.assert_called_once_with(
        service_name="bedrock",
        region_name="us-east-1"
    )
    
    # Verify the client is stored as instance variable
    assert service.bedrock_client == mock_client
    assert service.region_name == "us-east-1"


@patch('backend.services.policy_service.boto3')
def test_policy_service_uses_default_region(mock_boto3):
    """Test that PolicyService uses default region when not specified."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    service = PolicyService()
    
    # Verify default region is used
    mock_boto3.client.assert_called_once_with(
        service_name="bedrock",
        region_name="us-west-2"
    )
    
    assert service.region_name == "us-west-2"


# ============================================================================
# Policy Retrieval Tests
# ============================================================================

@patch('backend.services.policy_service.boto3')
def test_get_available_policies_success(mock_boto3):
    """Test that get_available_policies returns list of ARPolicy objects."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock the API response
    mock_client.list_automated_reasoning_policies.return_value = {
        "automatedReasoningPolicySummaries": [
            {
                "policyArn": "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy-1",
                "name": "Test Policy 1",
                "description": "First test policy"
            },
            {
                "policyArn": "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy-2",
                "name": "Test Policy 2",
                "description": "Second test policy"
            }
        ]
    }
    
    service = PolicyService()
    policies = service.get_available_policies()
    
    # Verify the API was called
    mock_client.list_automated_reasoning_policies.assert_called_once()
    
    # Verify the returned policies
    assert len(policies) == 2
    assert policies[0].arn == "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy-1"
    assert policies[0].name == "Test Policy 1"
    assert policies[0].description == "First test policy"
    assert policies[1].arn == "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy-2"
    assert policies[1].name == "Test Policy 2"
    assert policies[1].description == "Second test policy"


@patch('backend.services.policy_service.boto3')
def test_get_available_policies_handles_missing_name(mock_boto3):
    """Test that get_available_policies uses ARN as name when name is missing."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock the API response with missing name
    mock_client.list_automated_reasoning_policies.return_value = {
        "automatedReasoningPolicySummaries": [
            {
                "policyArn": "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy",
                "description": "Test policy without name"
            }
        ]
    }
    
    service = PolicyService()
    policies = service.get_available_policies()
    
    # Verify the ARN is used as name
    assert len(policies) == 1
    assert policies[0].name == "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"


@patch('backend.services.policy_service.boto3')
def test_get_available_policies_handles_client_error(mock_boto3):
    """Test that get_available_policies raises exception on ClientError."""
    from botocore.exceptions import ClientError
    
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock a ClientError
    mock_client.list_automated_reasoning_policies.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "list_automated_reasoning_policies"
    )
    
    service = PolicyService()
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        service.get_available_policies()
    
    assert "Failed to retrieve available AR policies" in str(exc_info.value)


@patch('backend.services.policy_service.boto3')
def test_get_available_policies_handles_unexpected_error(mock_boto3):
    """Test that get_available_policies raises exception on unexpected error."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock an unexpected error
    mock_client.list_automated_reasoning_policies.side_effect = ValueError("Unexpected error")
    
    service = PolicyService()
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        service.get_available_policies()
    
    assert "Failed to retrieve available AR policies" in str(exc_info.value)


@patch('backend.services.policy_service.boto3')
def test_get_policy_definition_success(mock_boto3):
    """Test that get_policy_definition retrieves policy definition successfully."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock the list_automated_reasoning_policy_build_workflows response
    mock_client.list_automated_reasoning_policy_build_workflows.return_value = {
        "automatedReasoningPolicyBuildWorkflowSummaries": [
            {
                "buildWorkflowId": "build-123",
                "status": "COMPLETED"
            }
        ]
    }
    
    # Mock the get_automated_reasoning_policy_build_workflow_result_assets response
    mock_client.get_automated_reasoning_policy_build_workflow_result_assets.return_value = {
        "buildWorkflowAssets": {
            "policyDefinition": {
                "version": "1.0",
                "rules": [
                    {
                        "id": "rule-1",
                        "expression": "(=> (P x) (Q x))",
                        "alternateExpression": "Test rule"
                    }
                ]
            }
        }
    }
    
    service = PolicyService()
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    policy_definition = service.get_policy_definition(policy_arn)
    
    # Verify the API calls were made
    mock_client.list_automated_reasoning_policy_build_workflows.assert_called_once_with(
        policyArn=policy_arn,
        maxResults=10
    )
    mock_client.get_automated_reasoning_policy_build_workflow_result_assets.assert_called_once_with(
        policyArn=policy_arn,
        buildWorkflowId="build-123",
        assetType="POLICY_DEFINITION"
    )
    
    # Verify the returned policy definition
    assert policy_definition["version"] == "1.0"
    assert len(policy_definition["rules"]) == 1
    assert policy_definition["rules"][0]["id"] == "rule-1"


@patch('backend.services.policy_service.boto3')
def test_get_policy_definition_uses_buildId_field(mock_boto3):
    """Test that get_policy_definition handles buildId field name."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock response with buildId instead of buildWorkflowId
    mock_client.list_automated_reasoning_policy_build_workflows.return_value = {
        "automatedReasoningPolicyBuildWorkflowSummaries": [
            {
                "buildId": "build-456",
                "status": "COMPLETED"
            }
        ]
    }
    
    mock_client.get_automated_reasoning_policy_build_workflow_result_assets.return_value = {
        "buildWorkflowAssets": {
            "policyDefinition": {
                "version": "1.0",
                "rules": []
            }
        }
    }
    
    service = PolicyService()
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    policy_definition = service.get_policy_definition(policy_arn)
    
    # Verify the buildId was used
    mock_client.get_automated_reasoning_policy_build_workflow_result_assets.assert_called_once_with(
        policyArn=policy_arn,
        buildWorkflowId="build-456",
        assetType="POLICY_DEFINITION"
    )
    
    assert policy_definition["version"] == "1.0"


@patch('backend.services.policy_service.boto3')
def test_get_policy_definition_no_workflows(mock_boto3):
    """Test that get_policy_definition raises exception when no workflows found."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock empty workflows response
    mock_client.list_automated_reasoning_policy_build_workflows.return_value = {
        "automatedReasoningPolicyBuildWorkflowSummaries": []
    }
    
    service = PolicyService()
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        service.get_policy_definition(policy_arn)
    
    assert "No build workflows found" in str(exc_info.value)


@patch('backend.services.policy_service.boto3')
def test_get_policy_definition_no_successful_build(mock_boto3):
    """Test that get_policy_definition raises exception when no successful build found."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock workflows with no COMPLETED status
    mock_client.list_automated_reasoning_policy_build_workflows.return_value = {
        "automatedReasoningPolicyBuildWorkflowSummaries": [
            {
                "buildWorkflowId": "build-123",
                "status": "FAILED"
            },
            {
                "buildWorkflowId": "build-456",
                "status": "IN_PROGRESS"
            }
        ]
    }
    
    service = PolicyService()
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        service.get_policy_definition(policy_arn)
    
    assert "No successful build workflow found" in str(exc_info.value)


@patch('backend.services.policy_service.boto3')
def test_get_policy_definition_missing_build_id(mock_boto3):
    """Test that get_policy_definition raises exception when build ID is missing."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock workflow with no build ID field
    mock_client.list_automated_reasoning_policy_build_workflows.return_value = {
        "automatedReasoningPolicyBuildWorkflowSummaries": [
            {
                "status": "COMPLETED"
                # Missing both buildWorkflowId and buildId
            }
        ]
    }
    
    service = PolicyService()
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        service.get_policy_definition(policy_arn)
    
    assert "Could not extract build ID" in str(exc_info.value)


@patch('backend.services.policy_service.boto3')
def test_get_policy_definition_handles_client_error(mock_boto3):
    """Test that get_policy_definition raises exception on ClientError."""
    from botocore.exceptions import ClientError
    
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock a ClientError
    mock_client.list_automated_reasoning_policy_build_workflows.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFound", "Message": "Policy not found"}},
        "list_automated_reasoning_policy_build_workflows"
    )
    
    service = PolicyService()
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        service.get_policy_definition(policy_arn)
    
    assert "Failed to retrieve policy definition" in str(exc_info.value)


@patch('backend.services.policy_service.boto3')
def test_get_policy_definition_handles_unexpected_error(mock_boto3):
    """Test that get_policy_definition raises exception on unexpected error."""
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client
    
    # Mock an unexpected error
    mock_client.list_automated_reasoning_policy_build_workflows.side_effect = ValueError("Unexpected error")
    
    service = PolicyService()
    policy_arn = "arn:aws:bedrock:us-west-2:123456789012:policy/test-policy"
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        service.get_policy_definition(policy_arn)
    
    assert "Failed to retrieve policy definition" in str(exc_info.value)


def test_get_mock_policy_definition():
    """Test that get_mock_policy_definition returns a valid mock policy."""
    service = PolicyService()
    
    mock_policy = service.get_mock_policy_definition()
    
    # Verify the structure
    assert "version" in mock_policy
    assert mock_policy["version"] == "1.0"
    assert "rules" in mock_policy
    assert len(mock_policy["rules"]) == 3
    
    # Verify first rule
    rule1 = mock_policy["rules"][0]
    assert rule1["id"] == "rule-1"
    assert rule1["expression"] == "(=> (employee x) (has_badge x))"
    assert rule1["alternateExpression"] == "All employees must have a badge"
    assert rule1["description"] == "Security policy requiring employee badges"
    
    # Verify second rule
    rule2 = mock_policy["rules"][1]
    assert rule2["id"] == "rule-2"
    assert rule2["expression"] == "(=> (visitor x) (has_escort x))"
    assert rule2["alternateExpression"] == "All visitors must have an escort"
    assert rule2["description"] == "Security policy for visitor escorts"
    
    # Verify third rule
    rule3 = mock_policy["rules"][2]
    assert rule3["id"] == "rule-3"
    assert rule3["expression"] == "(=> (contractor x) (has_clearance x))"
    assert rule3["alternateExpression"] == "All contractors must have security clearance"
    assert rule3["description"] == "Security policy for contractor clearance"


# ============================================================================
# Finding Enrichment Tests (from test_finding_enricher.py)
# ============================================================================

def test_policy_service_with_no_policy():
    """Test that service works without a policy definition."""
    service = PolicyService(None)
    
    findings = [
        Finding(
            validation_output="INVALID",
            details={
                "supporting_rules": [{"identifier": "rule-1"}]
            }
        )
    ]
    
    enriched = service.enrich_findings(findings)
    
    # Should return findings unchanged
    assert len(enriched) == 1
    assert enriched[0].details["supporting_rules"][0]["identifier"] == "rule-1"


def test_policy_service_enriches_supporting_rules():
    """Test that service adds content to supporting rules."""
    policy_definition = {
        "rules": [
            {
                "id": "rule-1",
                "expression": "(=> (P x) (Q x))",
                "alternateExpression": "If P is true for x, then Q is true for x",
                "description": "Test rule 1"
            }
        ]
    }
    
    service = PolicyService(policy_definition)
    
    findings = [
        Finding(
            validation_output="VALID",
            details={
                "supporting_rules": [{"identifier": "rule-1"}]
            }
        )
    ]
    
    enriched = service.enrich_findings(findings)
    
    # Should have enriched the rule
    assert len(enriched) == 1
    rule = enriched[0].details["supporting_rules"][0]
    assert rule["identifier"] == "rule-1"
    assert rule["expression"] == "(=> (P x) (Q x))"
    assert rule["alternateExpression"] == "If P is true for x, then Q is true for x"
    assert rule["description"] == "Test rule 1"


def test_policy_service_enriches_contradicting_rules():
    """Test that service adds content to contradicting rules."""
    policy_definition = {
        "rules": [
            {
                "id": "rule-2",
                "expression": "(=> (R x) (S x))",
                "alternateExpression": "If R is true for x, then S is true for x"
            }
        ]
    }
    
    service = PolicyService(policy_definition)
    
    findings = [
        Finding(
            validation_output="INVALID",
            details={
                "contradicting_rules": [{"identifier": "rule-2"}]
            }
        )
    ]
    
    enriched = service.enrich_findings(findings)
    
    # Should have enriched the rule
    assert len(enriched) == 1
    rule = enriched[0].details["contradicting_rules"][0]
    assert rule["identifier"] == "rule-2"
    assert rule["expression"] == "(=> (R x) (S x))"
    assert rule["alternateExpression"] == "If R is true for x, then S is true for x"


def test_policy_service_handles_missing_rules():
    """Test that service handles rules not in the policy definition."""
    policy_definition = {
        "rules": [
            {
                "id": "rule-1",
                "expression": "(test)",
                "alternateExpression": "test content"
            }
        ]
    }
    
    service = PolicyService(policy_definition)
    
    findings = [
        Finding(
            validation_output="INVALID",
            details={
                "contradicting_rules": [
                    {"identifier": "rule-1"},
                    {"identifier": "rule-unknown"}
                ]
            }
        )
    ]
    
    enriched = service.enrich_findings(findings)
    
    # Should have enriched rule-1 but kept rule-unknown as-is
    assert len(enriched) == 1
    rules = enriched[0].details["contradicting_rules"]
    assert len(rules) == 2
    assert rules[0]["expression"] == "(test)"
    assert rules[1]["identifier"] == "rule-unknown"
    assert "content" not in rules[1]


def test_policy_service_update_policy():
    """Test that service can update its policy definition."""
    policy_definition_1 = {
        "rules": [
            {"id": "rule-1", "expression": "(test1)", "alternateExpression": "content 1"}
        ]
    }
    
    policy_definition_2 = {
        "rules": [
            {"id": "rule-2", "expression": "(test2)", "alternateExpression": "content 2"}
        ]
    }
    
    service = PolicyService(policy_definition_1)
    
    # Update policy
    service.update_policy_definition(policy_definition_2)
    
    findings = [
        Finding(
            validation_output="VALID",
            details={
                "supporting_rules": [{"identifier": "rule-2"}]
            }
        )
    ]
    
    enriched = service.enrich_findings(findings)
    
    # Should use the new policy
    rule = enriched[0].details["supporting_rules"][0]
    assert rule["expression"] == "(test2)"


# ============================================================================
# Policy Context Formatting Tests
# ============================================================================

def test_policy_context_formatting_with_rules_and_variables():
    """Test that policy context is formatted correctly with rules and variables."""
    policy_definition = {
        "rules": [
            {
                "id": "rule-1",
                "expression": "(=> (employee x) (has_badge x))",
                "alternateExpression": "All employees must have a badge"
            },
            {
                "id": "rule-2",
                "expression": "(=> (visitor x) (has_escort x))",
                "alternateExpression": "All visitors must have an escort"
            }
        ],
        "variables": [
            {
                "name": "employee",
                "description": "A person employed by the organization"
            },
            {
                "name": "visitor",
                "description": "A person visiting the organization"
            }
        ]
    }
    
    service = PolicyService(policy_definition)
    policy_context = service.format_policy_context()
    
    # Verify policy context is formatted correctly
    assert "## Policy Context" in policy_context
    assert "### Rules" in policy_context
    assert "rule-1: All employees must have a badge" in policy_context
    assert "rule-2: All visitors must have an escort" in policy_context
    assert "### Variables" in policy_context
    assert "employee: A person employed by the organization" in policy_context
    assert "visitor: A person visiting the organization" in policy_context


def test_policy_context_formatting_without_policy():
    """Test that policy context returns empty string when no policy is provided."""
    service = PolicyService(None)
    policy_context = service.format_policy_context()
    
    # Verify empty policy context
    assert policy_context == ""


def test_policy_context_formatting_with_only_rules():
    """Test that policy context works with only rules (no variables)."""
    policy_definition = {
        "rules": [
            {
                "id": "rule-1",
                "expression": "(test)",
                "alternateExpression": "Test rule"
            }
        ]
    }
    
    service = PolicyService(policy_definition)
    policy_context = service.format_policy_context()
    
    assert "## Policy Context" in policy_context
    assert "### Rules" in policy_context
    assert "rule-1: Test rule" in policy_context
    assert "### Variables" not in policy_context


def test_policy_context_formatting_with_only_variables():
    """Test that policy context works with only variables (no rules)."""
    policy_definition = {
        "variables": [
            {
                "name": "test_var",
                "description": "Test variable"
            }
        ]
    }
    
    service = PolicyService(policy_definition)
    policy_context = service.format_policy_context()
    
    assert "## Policy Context" in policy_context
    assert "### Variables" in policy_context
    assert "test_var: Test variable" in policy_context
    assert "### Rules" not in policy_context


# ============================================================================
# Finding Processing Tests (sorting, selection, question allowance)
# ============================================================================

def test_finding_sorting_by_priority():
    """Test that findings are sorted by priority order."""
    service = PolicyService()
    
    findings = [
        Finding(validation_output="VALID", details={}),
        Finding(validation_output="TRANSLATION_AMBIGUOUS", details={}),
        Finding(validation_output="IMPOSSIBLE", details={}),
        Finding(validation_output="SATISFIABLE", details={}),
        Finding(validation_output="INVALID", details={}),
    ]
    
    sorted_findings = service.sort_findings(findings)
    
    # Verify priority order
    assert sorted_findings[0].validation_output == "TRANSLATION_AMBIGUOUS"
    assert sorted_findings[1].validation_output == "IMPOSSIBLE"
    assert sorted_findings[2].validation_output == "INVALID"
    assert sorted_findings[3].validation_output == "SATISFIABLE"
    assert sorted_findings[4].validation_output == "VALID"


def test_finding_sorting_with_unknown_types():
    """Test that unknown finding types are sorted to the end."""
    service = PolicyService()
    
    findings = [
        Finding(validation_output="UNKNOWN_TYPE", details={}),
        Finding(validation_output="INVALID", details={}),
        Finding(validation_output="ANOTHER_UNKNOWN", details={}),
    ]
    
    sorted_findings = service.sort_findings(findings)
    
    # Known type should come first
    assert sorted_findings[0].validation_output == "INVALID"
    # Unknown types should be at the end
    assert sorted_findings[1].validation_output in ["UNKNOWN_TYPE", "ANOTHER_UNKNOWN"]
    assert sorted_findings[2].validation_output in ["UNKNOWN_TYPE", "ANOTHER_UNKNOWN"]


def test_get_next_finding():
    """Test getting the next unprocessed finding."""
    service = PolicyService()
    
    findings = [
        Finding(validation_output="INVALID", details={}),
        Finding(validation_output="TRANSLATION_AMBIGUOUS", details={}),
        Finding(validation_output="SATISFIABLE", details={}),
    ]
    
    processed_indices = set()
    
    # Get first finding
    result = service.get_next_finding(findings, processed_indices)
    assert result is not None
    index, finding = result
    assert finding.validation_output == "TRANSLATION_AMBIGUOUS"  # Highest priority
    
    # Mark as processed and get next
    processed_indices.add(index)
    result = service.get_next_finding(findings, processed_indices)
    assert result is not None
    index, finding = result
    assert finding.validation_output == "INVALID"  # Second highest priority
    
    # Mark as processed and get next
    processed_indices.add(index)
    result = service.get_next_finding(findings, processed_indices)
    assert result is not None
    index, finding = result
    assert finding.validation_output == "SATISFIABLE"  # Third highest priority
    
    # Mark as processed - should return None
    processed_indices.add(index)
    result = service.get_next_finding(findings, processed_indices)
    assert result is None


def test_should_allow_questions():
    """Test question allowance for different finding types."""
    service = PolicyService()
    
    # Should allow questions
    assert service.should_allow_questions("TRANSLATION_AMBIGUOUS") is True
    assert service.should_allow_questions("SATISFIABLE") is True
    
    # Should not allow questions
    assert service.should_allow_questions("IMPOSSIBLE") is False
    assert service.should_allow_questions("INVALID") is False
    assert service.should_allow_questions("VALID") is False
    assert service.should_allow_questions("NO_TRANSLATIONS") is False
    assert service.should_allow_questions("UNKNOWN_TYPE") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
