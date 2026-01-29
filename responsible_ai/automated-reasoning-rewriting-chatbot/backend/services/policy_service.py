"""
Policy Service for managing policy-related operations.

This service consolidates policy-related functionality from:
- finding_processor.py (sorting, selection, question allowance)
- finding_enricher.py (enrichment with rule content)
- policy_context_formatter.py (policy context formatting)
"""
import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional, Set, Tuple, Dict
from dataclasses import dataclass
from backend.models.thread import Finding

logger = logging.getLogger(__name__)


@dataclass
class ARPolicy:
    """
    Represents an Automated Reasoning Policy.
    
    Attributes:
        arn: The ARN of the policy
        name: Human-readable name of the policy
        description: Optional description of the policy
    """
    arn: str
    name: str
    description: Optional[str] = None


class PolicyService:
    """
    Unified service for all policy-related operations.
    
    This class handles:
    - Sorting findings by priority order
    - Selecting the next unprocessed finding
    - Determining if follow-up questions are allowed for a finding type
    - Enriching findings with rule content from policy definitions
    - Formatting policy context for LLM prompts
    """
    
    # Priority order for sorting findings (lower number = higher priority)
    FINDING_PRIORITY = {
        "TRANSLATION_AMBIGUOUS": 1,  # Highest priority - ambiguous input needs clarification
        "IMPOSSIBLE": 2,             # Contradictory premises/rules
        "INVALID": 3,                # Claims contradict rules
        "SATISFIABLE": 4,            # Claims could be true or false
        "NO_TRANSLATIONS": 99,       # Low priority - no logical content found
        "VALID": 100                 # Lowest priority - everything is valid
    }
    
    # Finding types that allow follow-up questions
    QUESTION_ALLOWED_TYPES = {"TRANSLATION_AMBIGUOUS", "SATISFIABLE"}
    
    def __init__(
        self,
        policy_definition: Optional[Dict] = None,
        region_name: str = "us-west-2"
    ):
        """
        Initialize the policy service.
        
        Args:
            policy_definition: The policy definition containing rules and variables
            region_name: AWS region for Bedrock client
        """
        self.policy_definition = policy_definition
        self.region_name = region_name
        self.bedrock_client = boto3.client(
            service_name="bedrock",
            region_name=region_name
        )
        self._rule_map = self._build_rule_map() if policy_definition else {}
    
    # === Policy Retrieval (from config_manager.py) ===
    
    def get_available_policies(self) -> List[ARPolicy]:
        """
        Get list of available AR policies from Bedrock.
        
        Uses the list_automated_reasoning_policies API to retrieve policies
        available in the configured AWS region.
        
        Returns:
            List of ARPolicy objects
            
        Raises:
            Exception: If the API call fails
        """
        try:
            response = self.bedrock_client.list_automated_reasoning_policies()
            policy_summaries = response.get("automatedReasoningPolicySummaries", [])
            
            # Convert to ARPolicy objects
            policies = []
            for policy_summary in policy_summaries:
                policy = ARPolicy(
                    arn=policy_summary.get("policyArn"),
                    name=policy_summary.get("name", policy_summary.get("policyArn")),
                    description=policy_summary.get("description")
                )
                policies.append(policy)
            
            logger.info(f"Retrieved {len(policies)} available AR policies")
            return policies
            
        except ClientError as e:
            raise Exception(f"Failed to retrieve available AR policies: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to retrieve available AR policies: {str(e)}")
    
    def get_policy_definition(self, policy_arn: str) -> Dict:
        """
        Get the policy definition from AWS Bedrock build workflow assets.
        
        This method:
        1. Lists build workflows for the policy
        2. Finds the latest successful build
        3. Fetches the policy definition asset from that build
        
        Args:
            policy_arn: The ARN of the AR policy
            
        Returns:
            Dictionary containing the policy definition with rules
            
        Raises:
            Exception: If the API call fails or no successful build is found
        """
        try:
            # Step 1: List build workflows for the policy
            logger.info(f"Listing build workflows for policy: {policy_arn}")
            list_response = self.bedrock_client.list_automated_reasoning_policy_build_workflows(
                policyArn=policy_arn,
                maxResults=10  # Get the 10 most recent builds
            )
            
            logger.info(f"List response keys: {list(list_response.keys())}")
            logger.info(f"Full list response: {list_response}")
            
            workflows = list_response.get("automatedReasoningPolicyBuildWorkflowSummaries", [])
            if not workflows:
                raise Exception(f"No build workflows found for policy: {policy_arn}")
            
            logger.info(f"Found {len(workflows)} build workflows")
            for i, wf in enumerate(workflows):
                logger.info(f"Workflow {i}: status={wf.get('status')}, buildId={wf.get('buildWorkflowId')}")
            
            # Step 2: Find the latest successful build
            successful_build = None
            for workflow in workflows:
                status = workflow.get("status")
                logger.info(f"Checking workflow with status: {status}")
                if status == "COMPLETED":
                    successful_build = workflow
                    break
            
            if not successful_build:
                raise Exception(f"No successful build workflow found for policy: {policy_arn}")
            
            # Try both possible field names for build ID
            build_id = successful_build.get("buildWorkflowId") or successful_build.get("buildId")
            if not build_id:
                raise Exception(f"Could not extract build ID from workflow: {successful_build}")
            
            logger.info(f"Found successful build: {build_id}")
            
            # Step 3: Get the policy definition asset from the build
            logger.info(f"Fetching policy definition asset from build: {build_id}")
            asset_response = self.bedrock_client.get_automated_reasoning_policy_build_workflow_result_assets(
                policyArn=policy_arn,
                buildWorkflowId=build_id,
                assetType="POLICY_DEFINITION"
            )
            logger.info(asset_response)
            # The policy definition is returned as a string, parse it as JSON
            policy_definition = asset_response.get("buildWorkflowAssets", {}).get("policyDefinition", "{}")
            
            logger.info(f"Retrieved policy definition for {policy_arn}")
            logger.info(f"Policy definition structure: {list(policy_definition.keys())}")
            if "rules" in policy_definition:
                logger.info(f"Found {len(policy_definition['rules'])} rules in policy definition")
            
            return policy_definition
            
        except ClientError as e:
            raise Exception(f"Failed to retrieve policy definition: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse policy definition: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to retrieve policy definition: {str(e)}")
    
    def get_mock_policy_definition(self) -> Dict:
        """
        Get a mock policy definition for testing.
        
        Returns:
            Mock policy definition with sample rules
        """
        return {
            "version": "1.0",
            "rules": [
                {
                    "id": "rule-1",
                    "expression": "(=> (employee x) (has_badge x))",
                    "alternateExpression": "All employees must have a badge",
                    "description": "Security policy requiring employee badges"
                },
                {
                    "id": "rule-2",
                    "expression": "(=> (visitor x) (has_escort x))",
                    "alternateExpression": "All visitors must have an escort",
                    "description": "Security policy for visitor escorts"
                },
                {
                    "id": "rule-3",
                    "expression": "(=> (contractor x) (has_clearance x))",
                    "alternateExpression": "All contractors must have security clearance",
                    "description": "Security policy for contractor clearance"
                }
            ]
        }
    
    # === Finding Processing (from finding_processor.py) ===
    
    def sort_findings(self, findings: List[Finding]) -> List[Finding]:
        """
        Sort findings by priority order.
        
        Priority order: TRANSLATION_AMBIGUOUS, IMPOSSIBLE, INVALID, SATISFIABLE
        
        Args:
            findings: List of Finding objects to sort
            
        Returns:
            Sorted list of Finding objects (highest priority first)
        """
        def get_priority(finding: Finding) -> int:
            # Get priority from the mapping, default to high number for unknown types
            return self.FINDING_PRIORITY.get(finding.validation_output, 999)
        
        return sorted(findings, key=get_priority)
    
    def get_next_finding(
        self,
        findings: List[Finding],
        processed_finding_indices: Set[int]
    ) -> Optional[Tuple[int, Finding]]:
        """
        Get the next unprocessed finding by priority.
        
        This method:
        1. Sorts findings by priority
        2. Filters out already processed findings by index
        3. Returns the highest priority unprocessed finding
        
        Args:
            findings: List of Finding objects
            processed_finding_indices: Set of indices that have been processed
            
        Returns:
            Tuple of (index, finding) or None if all findings are processed
        """
        # Sort findings by priority
        sorted_findings = self.sort_findings(findings)
        
        # Find the first unprocessed finding
        for i, finding in enumerate(sorted_findings):
            if i not in processed_finding_indices:
                return (i, finding)
        
        # All findings have been processed
        return None
    
    def should_allow_questions(self, finding_type: str) -> bool:
        """
        Determine if follow-up questions are allowed for this finding type.
        
        Follow-up questions are only allowed for TRANSLATION_AMBIGUOUS and SATISFIABLE
        finding types, as these are cases where clarification can help the LLM
        provide a better response.
        
        Args:
            finding_type: The validation output type of the finding
            
        Returns:
            True for TRANSLATION_AMBIGUOUS and SATISFIABLE, False otherwise
        """
        return finding_type in self.QUESTION_ALLOWED_TYPES
    
    # === Finding Enrichment (from finding_enricher.py) ===
    
    def enrich_findings(self, findings: List[Finding]) -> List[Finding]:
        """
        Enrich findings by replacing rule IDs with rule content.
        
        Args:
            findings: List of Finding objects to enrich
            
        Returns:
            List of enriched Finding objects
        """
        if not self._rule_map:
            logger.info("No rule map available, returning findings unchanged")
            return findings 
        
        logger.info(f"Enriching {len(findings)} findings with {len(self._rule_map)} rules available")
        enriched_findings = []
        
        for finding in findings:
            enriched_finding = self._enrich_finding(finding)
            enriched_findings.append(enriched_finding)
        
        logger.info(f"Enrichment complete, returning {len(enriched_findings)} findings")
        return enriched_findings
    
    def _enrich_finding(self, finding: Finding) -> Finding:
        """
        Enrich a single finding with rule content.
        
        Args:
            finding: The Finding object to enrich
            
        Returns:
            Enriched Finding object
        """
        # Create a copy of the finding details
        enriched_details = finding.details.copy()
        
        # Enrich supporting rules
        if "supporting_rules" in enriched_details and enriched_details["supporting_rules"]:
            enriched_details["supporting_rules"] = self._enrich_rules(
                enriched_details["supporting_rules"]
            )
        
        # Enrich contradicting rules
        if "contradicting_rules" in enriched_details and enriched_details["contradicting_rules"]:
            enriched_details["contradicting_rules"] = self._enrich_rules(
                enriched_details["contradicting_rules"]
            )
        
        # Create a new Finding with enriched details
        return Finding(
            validation_output=finding.validation_output,
            details=enriched_details
        )
    
    def _enrich_rules(self, rules: List[Dict]) -> List[Dict]:
        """
        Enrich a list of rules with content from the policy definition.
        
        Args:
            rules: List of rule dictionaries with identifiers
            
        Returns:
            List of enriched rule dictionaries
        """
        enriched_rules = []
        
        for rule in rules:
            identifier = rule.get("identifier")
            
            if identifier and identifier in self._rule_map:
                # Get the full rule from the policy definition
                full_rule = self._rule_map[identifier]
                
                # Create enriched rule with AWS format fields
                enriched_rule = {
                    "identifier": identifier,
                    "expression": full_rule.get("expression", ""),
                    "alternateExpression": full_rule.get("alternateExpression", ""),
                }
                
                # Preserve additional fields if present
                if "description" in full_rule:
                    enriched_rule["description"] = full_rule["description"]
                if "policy_version_arn" in rule:
                    enriched_rule["policy_version_arn"] = rule["policy_version_arn"]
                    
                logger.debug(f"Enriched rule {identifier} with expression: {enriched_rule}")
                enriched_rules.append(enriched_rule)
            else:
                # Keep the original rule if we can't find it in the map
                logger.debug(f"Rule {identifier} not found in rule map, keeping original")
                enriched_rules.append(rule)
        
        return enriched_rules
    
    def _build_rule_map(self) -> Dict[str, Dict]:
        """
        Build a map of rule identifiers to rule content.
        
        Returns:
            Dictionary mapping rule identifiers to rule objects
        """
        rule_map = {}
        
        if not self.policy_definition:
            return rule_map
        
        # Extract rules from the policy definition
        # The structure may vary, but typically rules are in a "rules" array
        logger.info(self.policy_definition)
        rules = self.policy_definition.get("rules", [])
        
        for rule in rules:
            # AWS policies use "id" field
            identifier = rule.get("id")
            if identifier:
                rule_map[identifier] = rule
        
        logger.info(f"Built rule map with {len(rule_map)} rules")
        return rule_map
    
    def update_policy_definition(self, policy_definition: Dict):
        """
        Update the policy definition and rebuild the rule map.
        
        Args:
            policy_definition: The new policy definition
        """
        self.policy_definition = policy_definition
        self._rule_map = self._build_rule_map()
        logger.info("Policy definition updated and rule map rebuilt")
    
    # === Policy Context Formatting (from policy_context_formatter.py) ===
    
    def format_policy_context(self) -> str:
        """
        Format the policy context as a string for prompt inclusion.
        
        Returns:
            Formatted policy context string with rules and variables sections,
            or empty string if no policy or both rules and variables are empty.
        """
        if not self.policy_definition:
            return ""
        
        rules = self._extract_rules()
        variables = self._extract_variables()
        
        # If both are empty, return empty string
        if not rules and not variables:
            return ""
        
        sections = []
        sections.append("## Policy Context")
        
        # Add rules section if rules exist
        if rules:
            sections.append("\n### Rules")
            for rule in rules:
                sections.append(f"- {rule['identifier']}: {rule['natural_language']}")
        
        # Add variables section if variables exist
        if variables:
            sections.append("\n### Variables")
            for variable in variables:
                sections.append(f"- {variable['name']}: {variable['description']}")
        
        return "\n".join(sections)
    
    def _extract_rules(self) -> List[Dict[str, str]]:
        """
        Extract rules from policy definition.
        
        Returns:
            List of dicts with 'identifier' and 'natural_language' keys.
            Skips rules that are missing required fields.
        """
        if not self.policy_definition:
            return []
        
        rules_data = self.policy_definition.get("rules", [])
        if not rules_data:
            return []
        
        extracted_rules = []
        for rule in rules_data:
            # Skip rules missing required fields
            if not isinstance(rule, dict):
                logger.warning(f"Skipping non-dict rule: {rule}")
                continue
            
            # AWS policy definitions use 'id' and 'alternateExpression'
            identifier = rule.get("id")
            natural_language = rule.get("alternateExpression")
            
            if identifier and natural_language:
                extracted_rules.append({
                    "identifier": identifier,
                    "natural_language": natural_language
                })
            else:
                logger.warning(f"Skipping rule with missing fields: {rule}")
        
        return extracted_rules
    
    def _extract_variables(self) -> List[Dict[str, str]]:
        """
        Extract variables from policy definition.
        
        Returns:
            List of dicts with 'name' and 'description' keys.
            Skips variables that are missing required fields.
        """
        if not self.policy_definition:
            return []
        
        variables_data = self.policy_definition.get("variables", [])
        if not variables_data:
            return []
        
        extracted_variables = []
        for variable in variables_data:
            # Skip variables missing required fields
            if not isinstance(variable, dict):
                logger.warning(f"Skipping non-dict variable: {variable}")
                continue
            
            name = variable.get("name")
            description = variable.get("description")
            
            if name and description:
                extracted_variables.append({
                    "name": name,
                    "description": description
                })
            else:
                logger.warning(f"Skipping variable with missing fields: {variable}")
        
        return extracted_variables
