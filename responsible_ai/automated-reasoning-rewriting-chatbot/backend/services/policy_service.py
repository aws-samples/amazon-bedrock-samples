"""
Policy Service for managing policy-related operations.

This service consolidates policy-related functionality from:
- finding_processor.py (sorting, selection, question allowance)
- finding_enricher.py (enrichment with rule content)
- policy_context_formatter.py (policy context formatting)
- source document retrieval (RAG content for LLM prompts)
"""
import base64
import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional, Set, Tuple, Dict
from dataclasses import dataclass, field
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


@dataclass
class SourceDocument:
    """
    Represents a source document retrieved from a policy build workflow.
    
    Attributes:
        name: The document filename
        content_type: MIME type (pdf or txt)
        text_content: Extracted text content (decoded from base64 for txt documents)
        description: Optional description of the document
        document_hash: SHA-256 hash for integrity verification
    """
    name: str
    content_type: str
    text_content: str
    description: Optional[str] = None
    document_hash: Optional[str] = None


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
        region_name: str = "us-west-2",
        source_documents: Optional[List['SourceDocument']] = None
    ):
        """
        Initialize the policy service.
        
        Args:
            policy_definition: The policy definition containing rules and variables
            region_name: AWS region for Bedrock client
            source_documents: Optional list of source documents for RAG context
        """
        self.policy_definition = policy_definition
        self.region_name = region_name
        self.source_documents = source_documents or []
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
    
    def _find_latest_successful_build(self, policy_arn: str) -> Tuple[str, str]:
        """
        Find the latest successful build workflow for a policy.
        
        Args:
            policy_arn: The ARN of the AR policy
            
        Returns:
            Tuple of (build_workflow_id, policy_arn)
            
        Raises:
            Exception: If no successful build is found
        """
        list_response = self.bedrock_client.list_automated_reasoning_policy_build_workflows(
            policyArn=policy_arn,
            maxResults=10
        )
        
        workflows = list_response.get("automatedReasoningPolicyBuildWorkflowSummaries", [])
        if not workflows:
            raise Exception(f"No build workflows found for policy: {policy_arn}")
        
        for workflow in workflows:
            if workflow.get("status") == "COMPLETED":
                build_id = workflow.get("buildWorkflowId") or workflow.get("buildId")
                if build_id:
                    return build_id
        
        raise Exception(f"No successful build workflow found for policy: {policy_arn}")
    
    def get_source_documents(self, policy_arn: str) -> List['SourceDocument']:
        """
        Retrieve source documents from a policy's build workflow assets.
        
        This method:
        1. Finds the latest successful build workflow
        2. Fetches the asset manifest to discover source document IDs
        3. Fetches each source document by its asset ID
        4. Decodes text documents from base64
        
        Args:
            policy_arn: The ARN of the AR policy
            
        Returns:
            List of SourceDocument objects
            
        Raises:
            Exception: If the API calls fail
        """
        try:
            build_id = self._find_latest_successful_build(policy_arn)
            logger.info(f"Fetching source documents from build: {build_id}")
            
            # Step 1: Fetch the asset manifest
            manifest_response = self.bedrock_client.get_automated_reasoning_policy_build_workflow_result_assets(
                policyArn=policy_arn,
                buildWorkflowId=build_id,
                assetType="ASSET_MANIFEST"
            )
            
            manifest = manifest_response.get("buildWorkflowAssets", {}).get("assetManifest", {})
            entries = manifest.get("entries", [])
            
            # Filter for SOURCE_DOCUMENT entries
            source_doc_entries = [
                entry for entry in entries
                if entry.get("assetType") == "SOURCE_DOCUMENT"
            ]
            
            if not source_doc_entries:
                logger.info(f"No source documents found in build {build_id}")
                return []
            
            logger.info(f"Found {len(source_doc_entries)} source document(s) in manifest")
            
            # Step 2: Fetch each source document
            documents = []
            for entry in source_doc_entries:
                asset_id = entry.get("assetId")
                asset_name = entry.get("assetName", "unknown")
                
                if not asset_id:
                    logger.warning(f"Source document entry missing assetId: {entry}")
                    continue
                
                try:
                    doc_response = self.bedrock_client.get_automated_reasoning_policy_build_workflow_result_assets(
                        policyArn=policy_arn,
                        buildWorkflowId=build_id,
                        assetType="SOURCE_DOCUMENT",
                        assetId=asset_id
                    )
                    
                    doc_data = doc_response.get("buildWorkflowAssets", {}).get("document", {})
                    
                    content_type = doc_data.get("documentContentType", "txt")
                    doc_name = doc_data.get("documentName", asset_name)
                    doc_description = doc_data.get("documentDescription")
                    doc_hash = doc_data.get("documentHash")
                    raw_content = doc_data.get("document", "")
                    
                    # Decode base64 content
                    if isinstance(raw_content, bytes):
                        decoded_bytes = raw_content
                    else:
                        decoded_bytes = base64.b64decode(raw_content) if raw_content else b""
                    
                    # Extract text content
                    if content_type == "txt":
                        text_content = decoded_bytes.decode("utf-8", errors="replace")
                    elif content_type == "pdf":
                        # For PDFs, attempt basic text extraction
                        # Fall back to noting it's a PDF if extraction isn't possible
                        text_content = self._extract_pdf_text(decoded_bytes, doc_name)
                    else:
                        text_content = decoded_bytes.decode("utf-8", errors="replace")
                    
                    documents.append(SourceDocument(
                        name=doc_name,
                        content_type=content_type,
                        text_content=text_content,
                        description=doc_description,
                        document_hash=doc_hash
                    ))
                    
                    logger.info(f"Retrieved source document: {doc_name} ({content_type}, {len(text_content)} chars)")
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch source document {asset_id}: {e}")
                    continue
            
            logger.info(f"Successfully retrieved {len(documents)} source document(s)")
            return documents
            
        except ClientError as e:
            raise Exception(f"Failed to retrieve source documents: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to retrieve source documents: {str(e)}")
    
    def _extract_pdf_text(self, pdf_bytes: bytes, doc_name: str) -> str:
        """
        Attempt to extract text from PDF bytes.
        
        Falls back to a placeholder message if PDF parsing libraries
        are not available.
        
        Args:
            pdf_bytes: Raw PDF content
            doc_name: Document name for logging
            
        Returns:
            Extracted text or placeholder message
        """
        try:
            import PyPDF2
            import io
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            if pages:
                return "\n\n".join(pages)
            else:
                return f"[PDF document '{doc_name}' - text extraction yielded no content]"
        except ImportError:
            logger.warning("PyPDF2 not available for PDF text extraction")
            return f"[PDF document '{doc_name}' - install PyPDF2 for text extraction]"
        except Exception as e:
            logger.warning(f"Failed to extract text from PDF '{doc_name}': {e}")
            return f"[PDF document '{doc_name}' - text extraction failed: {e}]"
    
    def get_mock_source_documents(self) -> List['SourceDocument']:
        """
        Get mock source documents for testing.
        
        Returns:
            List of mock SourceDocument objects
        """
        return [
            SourceDocument(
                name="security_policy.txt",
                content_type="txt",
                text_content=(
                    "Company Security Policy\n\n"
                    "1. All employees must have a valid badge to enter the building.\n"
                    "2. All visitors must be accompanied by an escort at all times.\n"
                    "3. All contractors must have security clearance before accessing restricted areas.\n"
                    "4. Badge access is revoked immediately upon termination.\n"
                    "5. Visitors must sign in at the front desk and receive a temporary badge.\n"
                ),
                description="Main security policy document"
            )
        ]
    
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
    
    def update_source_documents(self, source_documents: List['SourceDocument']):
        """
        Update the source documents used for RAG context.
        
        Args:
            source_documents: List of SourceDocument objects
        """
        self.source_documents = source_documents
        logger.info(f"Source documents updated: {len(source_documents)} document(s)")
    
    # === Policy Context Formatting (from policy_context_formatter.py) ===
    
    def format_policy_context(self) -> str:
        """
        Format the policy context as a string for prompt inclusion.
        
        Uses source documents as RAG content when available. Falls back to
        the formal logic policy definition (rules and variables) if no
        source documents are loaded.
        
        Returns:
            Formatted policy context string, or empty string if nothing available.
        """
        # Prefer source documents as RAG content
        if self.source_documents:
            return self._format_source_document_context()
        
        # Fall back to formal logic rules/variables
        return self._format_rules_context()
    
    def _format_source_document_context(self) -> str:
        """
        Format source documents as RAG context for LLM prompts.
        
        Returns:
            Formatted string with source document content
        """
        sections = []
        sections.append("## Reference Documents")
        sections.append("")
        sections.append(
            "The following source documents define the policy. "
            "Use them as your primary reference when answering questions."
        )
        
        for doc in self.source_documents:
            sections.append(f"\n### {doc.name}")
            if doc.description:
                sections.append(f"*{doc.description}*")
            sections.append("")
            sections.append(doc.text_content)
        
        return "\n".join(sections)
    
    def _format_rules_context(self) -> str:
        """
        Format the formal logic policy definition (rules and variables) as context.
        
        This is the legacy format used when source documents are not available.
        
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
