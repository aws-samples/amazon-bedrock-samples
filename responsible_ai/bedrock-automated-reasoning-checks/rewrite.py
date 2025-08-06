from pathlib import Path
from enum import IntEnum
from finding_utils import extract_reasoning_findings 

# Define enums for clarity and consistency - Using IntEnum for proper comparison
class FindingType(IntEnum):
    INVALID = 1
    SATISFIABLE = 2
    IMPOSSIBLE = 3
    TRANSLATION_AMBIGUOUS = 4
    NO_TRANSLATIONS = 5
    VALID = 6
    TOO_COMPLEX = 7
    
    @classmethod
    def from_key(cls, key):
        mapping = {
            "invalid": cls.INVALID,
            "satisfiable": cls.SATISFIABLE, 
            "impossible": cls.IMPOSSIBLE,
            "translationAmbiguous": cls.TRANSLATION_AMBIGUOUS,  
            "noTranslations": cls.NO_TRANSLATIONS,              
            "valid": cls.VALID,
            "tooComplex": cls.TOO_COMPLEX                       
        }
        return mapping.get(key)
    
    @property
    def key(self):
        mapping = {
            FindingType.INVALID: "invalid",
            FindingType.SATISFIABLE: "satisfiable",
            FindingType.IMPOSSIBLE: "impossible",
            FindingType.TRANSLATION_AMBIGUOUS: "translationAmbiguous",  
            FindingType.NO_TRANSLATIONS: "noTranslations",              
            FindingType.VALID: "valid",
            FindingType.TOO_COMPLEX: "tooComplex"                       
        }
        return mapping.get(self)

# Template manager to handle loading and formatting templates
class TemplateManager:
    def __init__(self, template_dir="response_rewriting_prompts"):
        self.template_dir = Path(template_dir)
        self.template_files = {
            FindingType.IMPOSSIBLE: self.template_dir / "impossible.md",
            FindingType.INVALID: self.template_dir / "invalid.md",
            FindingType.SATISFIABLE: self.template_dir / "satisfiable.md",
            FindingType.TRANSLATION_AMBIGUOUS: self.template_dir / "ambiguity.md",
            FindingType.NO_TRANSLATIONS: self.template_dir / "no-translation.md",
        }
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from files"""
        for finding_type, file_path in self.template_files.items():
            if file_path.exists():
                with open(file_path, 'r') as f:
                    self.templates[finding_type] = f.read()
    
    def get_template(self, finding_type):
        """Get template for a specific finding type"""
        return self.templates.get(finding_type)

# Class to process findings and extract relevant information
class FindingProcessor:
    def __init__(self, policy_definition=None):
        self.policy_definition = policy_definition
        self.rule_details = self._build_rule_details()
    
    def _build_rule_details(self):
        """Build a lookup dictionary for rule details"""
        rule_details = {}
        if self.policy_definition and 'rules' in self.policy_definition:
            for rule in self.policy_definition['rules']:
                rule_details[rule['id']] = {
                    'expression': rule.get('expression', 'No expression available'),
                    'alternateExpression': rule.get('alternateExpression', 'No alternate expression available')
                }
        return rule_details
    
    def categorize_findings(self, findings):
        """Categorize findings by type"""
        findings_by_type = {}
        for finding in findings:
            for key in finding.keys():
                # Only consider keys that represent finding types 
                if key in ["invalid", "satisfiable", "impossible", "valid", 
                        "translationAmbiguous", "noTranslations", "tooComplex"]:
                    finding_type = FindingType.from_key(key)
                    if finding_type:
                        if finding_type not in findings_by_type:
                            findings_by_type[finding_type] = []
                        findings_by_type[finding_type].append(finding)
        
        # Debug information - uncomment if needed
        # print(f"Findings by type: {[(k.key, len(v)) for k, v in findings_by_type.items()]}")
        return findings_by_type
    
    def get_highest_priority_type(self, findings_by_type):
        """Find the highest priority finding type"""
        if not findings_by_type:
            return None
            
        # If VALID or TOO_COMPLEX are present, prioritize them
        if FindingType.VALID in findings_by_type:
            return FindingType.VALID
        if FindingType.TOO_COMPLEX in findings_by_type:
            return FindingType.TOO_COMPLEX
            
        # Otherwise, use the original priority logic
        return min(findings_by_type.keys())
    
    def process_contradicting_rules(self, relevant_findings, finding_type):
        """Extract all contradicting rules from findings"""
        contradicting_rules = set()
        for finding in relevant_findings:
            data = finding[finding_type.key]
            if "contradictingRules" in data:
                for rule in data["contradictingRules"]:
                    rule_id = rule.get('identifier')
                    if rule_id in self.rule_details:
                        contradicting_rules.add(
                            f"Rule ID: {rule_id}\n"
                            f"Natural Language: {self.rule_details[rule_id]['alternateExpression']}"
                        )
        return "\n\n".join(contradicting_rules)
    
    def process_ambiguous_translations(self, relevant_findings):
        """Extract premises, claims and scenarios from ambiguous translations"""
        all_translations_data = []
        all_scenarios = []
        
        for finding in relevant_findings:
            data = finding[FindingType.TRANSLATION_AMBIGUOUS.key]
            
            # Process options and translations
            if "options" in data and data["options"]:
                for option_idx, option in enumerate(data["options"]):
                    if "translations" in option and option["translations"]:
                        for trans_idx, translation in enumerate(option["translations"]):
                            translation_info = []
                            translation_info.append(f"Option {option_idx+1}, Translation {trans_idx+1}:")
                            
                            # Process premises
                            if "premises" in translation and translation["premises"]:
                                translation_info.append("Premises:")
                                for premise in translation["premises"]:
                                    translation_info.append(f"- {premise['naturalLanguage']}")
                            
                            # Process claims
                            if "claims" in translation and translation["claims"]:
                                translation_info.append("\nClaims:")
                                for claim in translation["claims"]:
                                    translation_info.append(f"- {claim['naturalLanguage']}")
                            
                            all_translations_data.append("\n".join(translation_info))
            
            # Process difference scenarios
            if "differenceScenarios" in data and data["differenceScenarios"]:
                for scenario_idx, scenario in enumerate(data["differenceScenarios"]):
                    if "statements" in scenario and scenario["statements"]:
                        scenario_text = []
                        scenario_text.append(f"Scenario {scenario_idx+1}:")
                        for stmt in scenario["statements"]:
                            if 'naturalLanguage' in stmt and stmt['naturalLanguage']:
                                scenario_text.append(f"- {stmt['naturalLanguage']}")
                        
                        if len(scenario_text) > 1:  # If we have statements
                            all_scenarios.append("\n".join(scenario_text))
        
        return {
            "disagreeing_translations": "\n\n".join(all_translations_data),
            "disagreement_text": "\n\n".join(all_scenarios)
        }
    
    def process_no_translations(self, relevant_findings):
        """Handle no translations finding - create fallback approach"""
        # Since noTranslations is an empty object, we need a fallback approach
        return {
            "feedback_text": "The response should be more precise and only contain clearly defined statements.",
            "untranslated_text": "Vague or ambiguous statements that cannot be translated to logical form."
        }
    
    def process_satisfiable(self, relevant_findings):
        """Extract true/false scenarios from satisfiable findings"""
        all_scenarios = []
        for finding in relevant_findings:
            data = finding[FindingType.SATISFIABLE.key]
            all_scenarios.extend(self._extract_scenarios(data))
        
        return {"true_false_scenarios_text": "\n\n".join(all_scenarios)}
    
    def _extract_scenarios(self, data):
        """Helper to extract scenarios from finding data"""
        scenarios = []
        if "claimsTrueScenario" in data and "claimsFalseScenario" in data:
            true_stmts = data["claimsTrueScenario"].get("statements", [])
            false_stmts = data["claimsFalseScenario"].get("statements", [])
            
            if true_stmts and false_stmts:
                scenario_group = []
                scenario_group.append("Scenario True:")
                for stmt in true_stmts[:3]:  # Limit to keep prompt concise
                    scenario_group.append(f"- {stmt['naturalLanguage']}")
                
                scenario_group.append("\nScenario False:")
                for stmt in false_stmts[:3]:  # Limit to keep prompt concise
                    scenario_group.append(f"- {stmt['naturalLanguage']}")
                
                scenarios.append("\n".join(scenario_group))
        return scenarios

# Main Rewriter class
class ResponseRewriter:
    def __init__(self, policy_definition=None, template_dir="response_rewriting_prompts", domain="Mortgage"):
        self.domain = domain
        self.template_manager = TemplateManager(template_dir)
        self.finding_processor = FindingProcessor(policy_definition)
    
    def prepare_rewrite_prompt(self, user_query, llm_response, ar_findings):
        """
        Prepare a rewrite prompt based on the AR findings and appropriate template,
        prioritizing findings when multiple are present.
        """
        # If no findings, return None
        if not ar_findings or "findings" not in ar_findings:
            return None, None, []
            
        findings = ar_findings["findings"]
        if not findings:
            return None, None, []
        
        # Categorize and prioritize findings
        findings_by_type = self.finding_processor.categorize_findings(findings)
        highest_priority_type = self.finding_processor.get_highest_priority_type(findings_by_type)
        
        # If no recognizable findings or valid/too_complex, return without rewriting
        if not highest_priority_type or highest_priority_type in [FindingType.VALID, FindingType.TOO_COMPLEX]:
            return None, highest_priority_type, findings_by_type.get(highest_priority_type, [])
        
        # Get all findings of the highest priority type
        relevant_findings = findings_by_type[highest_priority_type]
        
        # Get the appropriate template
        template = self.template_manager.get_template(highest_priority_type)
        if not template:
            return None, highest_priority_type, relevant_findings
        
        # Process findings based on type and format template
        template_vars = {
            "domain": self.domain,
            "question": user_query,
            "original_answer": llm_response
        }
        
        if highest_priority_type in [FindingType.IMPOSSIBLE, FindingType.INVALID]:
            template_vars["corrections_text"] = self.finding_processor.process_contradicting_rules(
                relevant_findings, highest_priority_type
            )
        
        elif highest_priority_type == FindingType.TRANSLATION_AMBIGUOUS:
            template_vars.update(self.finding_processor.process_ambiguous_translations(relevant_findings))
        
        elif highest_priority_type == FindingType.NO_TRANSLATIONS:
            template_vars.update(self.finding_processor.process_no_translations(relevant_findings))
        
        elif highest_priority_type == FindingType.SATISFIABLE:
            template_vars.update(self.finding_processor.process_satisfiable(relevant_findings))
        
        # Format the template
        formatted_prompt = template.format(**template_vars)
        
        return formatted_prompt, highest_priority_type, relevant_findings
    
    def rewrite_response(self, user_query, llm_response, ar_findings, model_id, bedrock_runtime_client):
        """Rewrite response based on AR findings using templates"""
        result = {
            "original_response": llm_response,
            "rewritten": False,
            "finding_type": None,
            "findings_count": 0,
            "rewritten_response": None
        }
        
        # Prepare the rewrite prompt with prioritized findings
        rewrite_prompt, finding_type, used_findings = self.prepare_rewrite_prompt(
            user_query, llm_response, ar_findings
        )
        
        result["finding_type"] = finding_type.key if finding_type else None
        result["findings_count"] = len(used_findings) if used_findings else 0
        
        # If no rewrite needed or no prompt could be prepared
        if not rewrite_prompt:
            if finding_type in [FindingType.VALID, FindingType.TOO_COMPLEX]:
                result["message"] = f"No rewrite needed. Finding type: {finding_type.key if finding_type else None}"
            else:
                result["message"] = "Failed to prepare rewrite prompt"
            return result
        
        # Call foundation model using converse API
        try:
            # Use converse API for all models
            converse_response = bedrock_runtime_client.converse(
                modelId=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": rewrite_prompt}]
                    }
                ]
            )
            
            # Extract content from converse response format
            result["rewritten_response"] = converse_response['output']['message']['content'][0]['text']
            result["rewritten"] = True
            result["message"] = f"Successfully rewrote response based on {finding_type.key} finding ({result['findings_count']} findings)"
            
            return result
        except Exception as e:
            result["message"] = f"Error rewriting response: {str(e)}"
            return result

def summarize_results(user_query, llm_response, policy_definition, guardrail_id, guardrail_version, 
                     bedrock_runtime_client, model_id="anthropic.claude-3-sonnet-20240229-v1:0", domain=None):
    """
    Process a response with guardrails and return a simplified summary with key information.
    
    Args:
        user_query (str): User's original question
        llm_response (str): Original LLM response
        policy_definition (dict): Policy definition
        guardrail_id (str): Guardrail ID
        guardrail_version (str): Guardrail version
        bedrock_runtime_client: Bedrock runtime client
        model_id (str): Model ID for rewriting
        domain (str, optional): Domain for the policy
        
    Returns:
        dict: Dictionary with query, original response, rewritten response, and findings
    """
    # Prompt user for domain if not provided
    if domain is None:
        domain_prompt = """
Enter the domain of your policy (Examples: Insurance, Healthcare, HR, Finance, Mortgage, Banking): 
> """
        domain = input(domain_prompt)
        
        # If domain is empty, set a default value
        if not domain.strip():
            domain = "General"
            print(f"Using default domain: {domain}")
    
    # Step 1: Create content to validate
    content_to_validate = [
        {"text": {"text": user_query, "qualifiers": ["query"]}},
        {"text": {"text": llm_response, "qualifiers": ["guard_content"]}}
    ]
    
    # Step 2: Apply guardrail to check the response
    apply_guardrail_response = bedrock_runtime_client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=guardrail_version, 
        source="OUTPUT",
        content=content_to_validate
    )
    
    # Step 3: Extract the automatedReasoningPolicy part
    ar_findings = None
    if 'assessments' in apply_guardrail_response and apply_guardrail_response['assessments']:
        for assessment in apply_guardrail_response['assessments']:
            if 'automatedReasoningPolicy' in assessment:
                ar_findings = assessment['automatedReasoningPolicy']
                break
    
    # Step 4: Generate formatted findings
    formatted_findings = extract_reasoning_findings(
        apply_guardrail_response, 
        policy_definition
    )
    
    # Step 5: If needed, rewrite the response
    rewritten_response = None
    if ar_findings:
        rewriter = ResponseRewriter(policy_definition=policy_definition, domain=domain)
        result = rewriter.rewrite_response(
            user_query=user_query,
            llm_response=llm_response,
            ar_findings=ar_findings,
            model_id=model_id,
            bedrock_runtime_client=bedrock_runtime_client
        )
        
        if result.get('rewritten'):
            rewritten_response = result.get('rewritten_response')
    
    # Step 6: Return simplified results
    return {
        "query": user_query,
        "original_response": llm_response,
        "rewritten_response": rewritten_response,
        "findings": formatted_findings,
        "domain": domain  # Include domain in the results
    }