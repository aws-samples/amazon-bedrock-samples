"""
Validation Service for interacting with Amazon Bedrock Guardrails.
"""
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
import boto3

from backend.models.thread import Finding
from backend.services.retry_handler import retry_api_call

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result from validating a response with Bedrock Guardrails.
    
    Attributes:
        output: The validation output status (VALID, INVALID, TOO_COMPLEX, etc.)
        findings: List of Finding objects with validation details
    """
    output: str
    findings: List[Finding]


class ValidationService:
    """
    Service for validating LLM responses using Amazon Bedrock Guardrails.
    
    This class handles:
    - Validation via the ApplyGuardrail API
    - Parsing validation results into structured findings
    - Sorting findings by priority
    - Retry logic with exponential backoff for transient failures
    """
    
    # Priority order for sorting findings
    FINDING_PRIORITY = {
        "TOO_COMPLEX": 0,           # Highest priority - cannot process
        "TRANSLATION_AMBIGUOUS": 1,  # Ambiguous input needs clarification
        "IMPOSSIBLE": 2,             # Contradictory premises/rules
        "INVALID": 3,                # Claims contradict rules
        "SATISFIABLE": 4,            # Claims could be true or false
        "NO_TRANSLATIONS": 99,       # No logical content found
        "VALID": 6                   # Lowest priority - everything is valid
    }
    
    def __init__(self, guardrail_id: str, guardrail_version: str = "DRAFT", region_name: str = "us-west-2"):
        """
        Initialize the validation service.
        
        Args:
            guardrail_id: The Bedrock Guardrail ID to use
            guardrail_version: The guardrail version (default: DRAFT)
            region_name: AWS region name (default: us-west-2)
        """
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.region_name = region_name
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name
        )
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds for exponential backoff
    
    def validate(self, prompt: str, response: str) -> ValidationResult:
        """
        Validate a response using Bedrock Guardrails.
        
        Implements retry logic with exponential backoff for transient failures.
        
        Args:
            prompt: The original user prompt
            response: The LLM-generated response to validate
            
        Returns:
            ValidationResult containing the output status and findings
            
        Raises:
            Exception: If the validation request fails after all retries
        """
        def apply_guardrail():
            api_response = self.client.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                outputScope="INTERVENTIONS",
                source="OUTPUT",
                content=[
                    {
                        "text": {
                            "text": f"{prompt}",
                            "qualifiers": ["query"]
                        }
                    },
                    {
                        "text": {
                            "text": f"{response}",
                            "qualifiers": ["guard_content"]
                        }
                    }
                ]
            )
            return self._parse_validation_result(api_response)
        
        return retry_api_call(
            apply_guardrail,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            operation_name="validate response"
        )
    
    def _parse_validation_result(self, api_response: Dict[str, Any]) -> ValidationResult:
        """
        Parse the ApplyGuardrail API response into a ValidationResult.
        
        Args:
            api_response: The response from the ApplyGuardrail API
            
        Returns:
            ValidationResult with parsed output and findings
        """
        # Extract the action from the response
        action = api_response.get("action", "NONE")
        
        # Extract assessments
        assessments = api_response.get("assessments", [])
        findings = []
        
        # Process each assessment
        for assessment in assessments:
            # Extract automated reasoning policy assessment if present
            ar_policy = assessment.get("automatedReasoningPolicy", {})
            if ar_policy:
                # Extract findings from the automated reasoning policy
                ar_findings = ar_policy.get("findings", [])
                
                for ar_finding in ar_findings:
                    # Each finding is a tagged union - determine which type it is
                    finding_type, finding_data = self._extract_finding_type(ar_finding)
                    
                    if finding_type:
                        # Extract relevant details based on finding type
                        details = self._extract_finding_details(finding_type, finding_data)
                        
                        findings.append(Finding(
                            validation_output=finding_type,
                            details=details
                        ))
        
        # Determine overall output status
        if not findings:
            # No findings means VALID
            output = "VALID"
        else:
            # Sort findings by priority and use the highest priority as overall status
            sorted_findings = self._sort_findings(findings)
            output = sorted_findings[0].validation_output
        
        # Sort findings before returning
        sorted_findings = self._sort_findings(findings)
        
        return ValidationResult(
            output=output,
            findings=sorted_findings
        )
    
    def _extract_finding_type(self, finding: Dict[str, Any]) -> tuple:
        """
        Extract the finding type from a tagged union structure.
        
        Args:
            finding: The finding dictionary from the API response
            
        Returns:
            Tuple of (finding_type, finding_data)
        """
        # Check each possible finding type
        if "valid" in finding:
            return ("VALID", finding["valid"])
        elif "invalid" in finding:
            return ("INVALID", finding["invalid"])
        elif "satisfiable" in finding:
            return ("SATISFIABLE", finding["satisfiable"])
        elif "impossible" in finding:
            return ("IMPOSSIBLE", finding["impossible"])
        elif "translationAmbiguous" in finding:
            return ("TRANSLATION_AMBIGUOUS", finding["translationAmbiguous"])
        elif "tooComplex" in finding:
            return ("TOO_COMPLEX", finding["tooComplex"])
        elif "noTranslations" in finding:
            return ("NO_TRANSLATIONS", finding["noTranslations"])
        
        return (None, None)
    
    def _extract_finding_details(self, finding_type: str, finding_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant details from a finding based on its type.
        
        Args:
            finding_type: The type of finding (VALID, INVALID, etc.)
            finding_data: The finding data dictionary
            
        Returns:
            Dictionary with extracted details
        """
        details = {}
        
        # Extract translation if present (common to most finding types)
        translation = finding_data.get("translation", {})
        if translation:
            # Extract premises with both logic and natural language
            premises = translation.get("premises", [])
            if premises:
                details["premises"] = [
                    {
                        "logic": p.get("logic", ""),
                        "natural_language": p.get("naturalLanguage", "")
                    }
                    for p in premises
                ]
            
            # Extract claims with both logic and natural language
            claims = translation.get("claims", [])
            if claims:
                details["claims"] = [
                    {
                        "logic": c.get("logic", ""),
                        "natural_language": c.get("naturalLanguage", "")
                    }
                    for c in claims
                ]
            
            # Extract untranslated premises and claims
            untranslated_premises = translation.get("untranslatedPremises", [])
            if untranslated_premises:
                details["untranslated_premises"] = [p.get("text", "") for p in untranslated_premises]
            
            untranslated_claims = translation.get("untranslatedClaims", [])
            if untranslated_claims:
                details["untranslated_claims"] = [c.get("text", "") for c in untranslated_claims]
            
            # Extract confidence score
            confidence = translation.get("confidence")
            if confidence is not None:
                details["confidence"] = confidence
        
        # Extract scenarios for SATISFIABLE findings
        if finding_type == "SATISFIABLE":
            if "claimsTrueScenario" in finding_data:
                details["claims_true_scenario"] = self._extract_detailed_scenario(finding_data["claimsTrueScenario"])
            if "claimsFalseScenario" in finding_data:
                details["claims_false_scenario"] = self._extract_detailed_scenario(finding_data["claimsFalseScenario"])
            # Extract logic warning if present
            if "logicWarning" in finding_data:
                details["logic_warning"] = self._extract_logic_warning(finding_data["logicWarning"])
        
        # Extract contradicting rules for INVALID/IMPOSSIBLE
        if finding_type in ["INVALID", "IMPOSSIBLE"]:
            contradicting_rules = finding_data.get("contradictingRules", [])
            if contradicting_rules:
                details["contradicting_rules"] = [
                    {
                        "identifier": rule.get("identifier", ""),
                        "policy_version_arn": rule.get("policyVersionArn", "")
                    }
                    for rule in contradicting_rules
                ]
            # Extract logic warning if present
            if "logicWarning" in finding_data:
                details["logic_warning"] = self._extract_logic_warning(finding_data["logicWarning"])
        
        # Extract supporting rules and scenario for VALID
        if finding_type == "VALID":
            supporting_rules = finding_data.get("supportingRules", [])
            if supporting_rules:
                details["supporting_rules"] = [
                    {
                        "identifier": rule.get("identifier", ""),
                        "policy_version_arn": rule.get("policyVersionArn", ""),
                        "id": rule.get("identifier", "")  # Add id field for consistency
                    }
                    for rule in supporting_rules
                ]
            # Extract claims true scenario
            if "claimsTrueScenario" in finding_data:
                details["claims_true_scenario"] = self._extract_detailed_scenario(finding_data["claimsTrueScenario"])
            # Extract logic warning if present
            if "logicWarning" in finding_data:
                details["logic_warning"] = self._extract_logic_warning(finding_data["logicWarning"])
        
        # Extract translation options for TRANSLATION_AMBIGUOUS
        if finding_type == "TRANSLATION_AMBIGUOUS":
            options = finding_data.get("options", [])
            if options:
                details["translation_options"] = []
                for option in options:
                    option_details = {
                        "translations": []
                    }
                    # Extract translations for this option
                    for trans in option.get("translations", []):
                        translation_detail = {}
                        if trans.get("premises"):
                            translation_detail["premises"] = [
                                {
                                    "logic": p.get("logic", ""),
                                    "natural_language": p.get("naturalLanguage", "")
                                }
                                for p in trans.get("premises", [])
                            ]
                        if trans.get("claims"):
                            translation_detail["claims"] = [
                                {
                                    "logic": c.get("logic", ""),
                                    "natural_language": c.get("naturalLanguage", "")
                                }
                                for c in trans.get("claims", [])
                            ]
                        option_details["translations"].append(translation_detail)
                    details["translation_options"].append(option_details)
                
                # Extract difference scenarios
                difference_scenarios = finding_data.get("differenceScenarios", [])
                if difference_scenarios:
                    details["difference_scenarios"] = [
                        self._extract_detailed_scenario(scenario)
                        for scenario in difference_scenarios
                    ]
        
        return details
    
    def _extract_detailed_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract detailed scenario information including both logic and natural language.
        
        Args:
            scenario: The scenario dictionary
            
        Returns:
            Dictionary with scenario details
        """
        statements = scenario.get("statements", [])
        return {
            "statements": [
                {
                    "logic": s.get("logic", ""),
                    "natural_language": s.get("naturalLanguage", "")
                }
                for s in statements
            ]
        }
    
    def _extract_logic_warning(self, warning: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract logic warning information.
        
        Args:
            warning: The logic warning dictionary
            
        Returns:
            Dictionary with warning details
        """
        warning_details = {
            "type": warning.get("type", "")
        }
        
        # Extract premises if present
        premises = warning.get("premises", [])
        if premises:
            warning_details["premises"] = [
                {
                    "logic": p.get("logic", ""),
                    "natural_language": p.get("naturalLanguage", "")
                }
                for p in premises
            ]
        
        # Extract claims if present
        claims = warning.get("claims", [])
        if claims:
            warning_details["claims"] = [
                {
                    "logic": c.get("logic", ""),
                    "natural_language": c.get("naturalLanguage", "")
                }
                for c in claims
            ]
        
        return warning_details
    
    def _sort_findings(self, findings: List[Finding]) -> List[Finding]:
        """
        Sort findings by priority order.
        
        Priority order: TRANSLATION_AMBIGUOUS, IMPOSSIBLE, INVALID, SATISFIABLE
        
        Args:
            findings: List of Finding objects to sort
            
        Returns:
            Sorted list of Finding objects
        """
        def get_priority(finding: Finding) -> int:
            # Get priority from the mapping, default to high number for unknown types
            return self.FINDING_PRIORITY.get(finding.validation_output, 999)
        
        return sorted(findings, key=get_priority)
    

