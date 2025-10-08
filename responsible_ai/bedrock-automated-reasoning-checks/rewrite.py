from pathlib import Path
from enum import Enum
from findings_utils import extract_reasoning_findings 

class FindingType(Enum):
    TRANSLATION_AMBIGUOUS = 1
    INVALID = 2
    IMPOSSIBLE = 3
    SATISFIABLE = 4
    NO_TRANSLATIONS = 5
    VALID = 6
    TOO_COMPLEX = 7
    
    @classmethod
    def from_key(cls, key):
        mapping = {
            "translationAmbiguous": cls.TRANSLATION_AMBIGUOUS,
            "invalid": cls.INVALID,
            "impossible": cls.IMPOSSIBLE,
            "satisfiable": cls.SATISFIABLE, 
            "noTranslations": cls.NO_TRANSLATIONS,
            "valid": cls.VALID,
            "tooComplex": cls.TOO_COMPLEX                       
        }
        return mapping.get(key)
    
    @property
    def key(self):
        mapping = {
            FindingType.TRANSLATION_AMBIGUOUS: "translationAmbiguous",
            FindingType.INVALID: "invalid",
            FindingType.IMPOSSIBLE: "impossible",
            FindingType.SATISFIABLE: "satisfiable",
            FindingType.NO_TRANSLATIONS: "noTranslations",
            FindingType.VALID: "valid",
            FindingType.TOO_COMPLEX: "tooComplex"                       
        }
        return mapping.get(self)

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
        for finding_type, file_path in self.template_files.items():
            if file_path.exists():
                with open(file_path, 'r') as f:
                    self.templates[finding_type] = f.read()
    
    def get_template(self, finding_type):
        return self.templates.get(finding_type)

class FindingProcessor:
    def __init__(self, policy_definition=None):
        self.policy_definition = policy_definition
        self.rule_details = self._build_rule_details()
    
    def _build_rule_details(self):
        rule_details = {}
        if self.policy_definition and 'rules' in self.policy_definition:
            for rule in self.policy_definition['rules']:
                rule_details[rule['id']] = {
                    'expression': rule.get('expression', 'No expression available'),
                    'alternateExpression': rule.get('alternateExpression', 'No alternate expression available')
                }
        return rule_details
    
    def categorize_findings(self, findings):
        findings_by_type = {}
        for finding in findings:
            for key in finding.keys():
                if key in ["translationAmbiguous", "invalid", "impossible", "satisfiable", 
                          "noTranslations", "valid", "tooComplex"]:
                    finding_type = FindingType.from_key(key)
                    if finding_type:
                        if finding_type not in findings_by_type:
                            findings_by_type[finding_type] = []
                        findings_by_type[finding_type].append(finding)
        return findings_by_type
    
    def get_priority_types(self, findings_by_type):
        """Get finding types in priority order"""
        if not findings_by_type:
            return []
            
        # Skip if only VALID exists
        if len(findings_by_type) == 1 and FindingType.VALID in findings_by_type:
            return [FindingType.VALID]
            
        # Skip if only TOO_COMPLEX exists
        if len(findings_by_type) == 1 and FindingType.TOO_COMPLEX in findings_by_type:
            return [FindingType.TOO_COMPLEX]
            
        # Priority order
        priority_order = [
            FindingType.TRANSLATION_AMBIGUOUS,
            FindingType.INVALID,
            FindingType.IMPOSSIBLE,
            FindingType.SATISFIABLE,
            FindingType.NO_TRANSLATIONS
        ]
        
        # Return types that exist in findings in priority order
        return [t for t in priority_order if t in findings_by_type]
    
    def process_finding_data(self, finding_type, findings):
        template_vars = {}
        
        if finding_type in [FindingType.IMPOSSIBLE, FindingType.INVALID]:
            template_vars["corrections_text"] = self.process_contradicting_rules(findings, finding_type)
        
        elif finding_type == FindingType.TRANSLATION_AMBIGUOUS:
            template_vars.update(self.process_ambiguous_translations(findings))
        
        elif finding_type == FindingType.NO_TRANSLATIONS:
            template_vars.update({
                "feedback_text": "The response should be more precise and only contain clearly defined statements.",
                "untranslated_text": "Vague or ambiguous statements that cannot be translated to logical form."
            })
        
        elif finding_type == FindingType.SATISFIABLE:
            template_vars.update(self.process_satisfiable(findings))
        
        return template_vars
    
    def process_contradicting_rules(self, findings, finding_type):
        contradicting_rules = set()
        for finding in findings:
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
    
    def process_ambiguous_translations(self, findings):
        all_translations_data = []
        all_scenarios = []
        
        for finding in findings:
            data = finding[FindingType.TRANSLATION_AMBIGUOUS.key]
            
            if "options" in data and data["options"]:
                for option_idx, option in enumerate(data["options"]):
                    if "translations" in option and option["translations"]:
                        for trans_idx, translation in enumerate(option["translations"]):
                            translation_info = []
                            translation_info.append(f"Option {option_idx+1}, Translation {trans_idx+1}:")
                            
                            if "premises" in translation and translation["premises"]:
                                translation_info.append("Premises:")
                                for premise in translation["premises"]:
                                    translation_info.append(f"- {premise['naturalLanguage']}")
                            
                            if "claims" in translation and translation["claims"]:
                                translation_info.append("\nClaims:")
                                for claim in translation["claims"]:
                                    translation_info.append(f"- {claim['naturalLanguage']}")
                            
                            all_translations_data.append("\n".join(translation_info))
            
            if "differenceScenarios" in data and data["differenceScenarios"]:
                for scenario_idx, scenario in enumerate(data["differenceScenarios"]):
                    if "statements" in scenario and scenario["statements"]:
                        scenario_text = []
                        scenario_text.append(f"Scenario {scenario_idx+1}:")
                        for stmt in scenario["statements"]:
                            if 'naturalLanguage' in stmt and stmt['naturalLanguage']:
                                scenario_text.append(f"- {stmt['naturalLanguage']}")
                        
                        if len(scenario_text) > 1:
                            all_scenarios.append("\n".join(scenario_text))
        
        return {
            "disagreeing_translations": "\n\n".join(all_translations_data),
            "disagreement_text": "\n\n".join(all_scenarios)
        }
    
    def process_satisfiable(self, findings):
        all_scenarios = []
        for finding in findings:
            data = finding[FindingType.SATISFIABLE.key]
            
            if "claimsTrueScenario" in data and "claimsFalseScenario" in data:
                true_stmts = data["claimsTrueScenario"].get("statements", [])
                false_stmts = data["claimsFalseScenario"].get("statements", [])
                
                if true_stmts and false_stmts:
                    scenario_group = []
                    scenario_group.append("Scenario True:")
                    for stmt in true_stmts:  
                        scenario_group.append(f"- {stmt['naturalLanguage']}")
                    
                    scenario_group.append("\nScenario False:")
                    for stmt in false_stmts:  
                        scenario_group.append(f"- {stmt['naturalLanguage']}")
                    
                    all_scenarios.append("\n".join(scenario_group))
        
        return {"true_false_scenarios_text": "\n\n".join(all_scenarios)}

class ResponseRewriter:
    def __init__(self, policy_definition=None, template_dir="response_rewriting_prompts", domain="Mortgage"):
        self.domain = domain
        self.template_manager = TemplateManager(template_dir)
        self.finding_processor = FindingProcessor(policy_definition)
    
    def prepare_rewrite_prompt(self, user_query, llm_response, finding_type, relevant_findings):
        template = self.template_manager.get_template(finding_type)
        if not template:
            return None
        
        template_vars = {
            "domain": self.domain,
            "question": user_query,
            "original_answer": llm_response
        }
        
        template_vars.update(self.finding_processor.process_finding_data(finding_type, relevant_findings))
        return template.format(**template_vars)

    def rewrite_response(self, user_query, llm_response, ar_findings, model_id, bedrock_runtime_client):
        """Rewrite response handling multiple finding types"""
        result = {
            "original_response": llm_response,
            "rewritten": False,
            "finding_types": [],
            "findings_count": 0,
            "rewritten_response": None
        }
        
        if not ar_findings or "findings" not in ar_findings or not ar_findings["findings"]:
            return result
        
        findings_by_type = self.finding_processor.categorize_findings(ar_findings["findings"])
        priority_types = self.finding_processor.get_priority_types(findings_by_type)
        
        if not priority_types:
            return result
        
        # Special handling for TOO_COMPLEX as the only finding
        if priority_types == [FindingType.TOO_COMPLEX]:
            result["finding_types"] = [FindingType.TOO_COMPLEX.key]
            result["findings_count"] = len(findings_by_type.get(FindingType.TOO_COMPLEX, []))
            result["rewritten"] = True
            result["rewritten_response"] = "This question contains too much information to process accurately. Please break it down into simpler, more focused questions."
            result["message"] = "Replaced with generic TOO_COMPLEX message"
            return result
        
        # If VALID is the only finding, skip rewriting
        if priority_types == [FindingType.VALID]:
            result["finding_types"] = [priority_types[0].key]
            result["message"] = f"No rewrite needed. Finding type: {priority_types[0].key}"
            result["findings_count"] = len(findings_by_type.get(priority_types[0], []))
            return result
        
        # Process each finding type in priority order
        rewrites = []
        for finding_type in priority_types:
            relevant_findings = findings_by_type[finding_type]
            prompt = self.prepare_rewrite_prompt(user_query, llm_response, finding_type, relevant_findings)
            
            if prompt:
                try:
                    response = bedrock_runtime_client.converse(
                        modelId=model_id,
                        messages=[{"role": "user", "content": [{"text": prompt}]}]
                    )
                    
                    rewritten_text = response['output']['message']['content'][0]['text']
                    rewrites.append({
                        "finding_type": finding_type.key,
                        "rewritten_text": rewritten_text
                    })
                    result["finding_types"].append(finding_type.key)
                    result["findings_count"] += len(relevant_findings)
                except Exception as e:
                    continue
        
        # If we have rewrites, combine them
        if rewrites:
            if len(rewrites) == 1:
                result["rewritten_response"] = rewrites[0]["rewritten_text"]
                result["rewritten"] = True
                result["message"] = f"Successfully rewrote response for {rewrites[0]['finding_type']}"
            else:
                combine_prompt = f"""
Your task is to combine multiple corrected answers into a single coherent response.
Original Question: {user_query}
Original Answer: {llm_response}
The following are corrected versions addressing different issues:
"""
                for i, rewrite in enumerate(rewrites):
                    combine_prompt += f"Correction {i+1}: {rewrite['rewritten_text']}\n\n"
                
                combine_prompt += """
Create a single unified response that:
1. Directly answers the question without any meta-commentary
2. Combines all corrections without redundancy or overlap
3. Does NOT include phrases like "here's a comprehensive response" or "addressing both issues"
4. Does NOT add any new information beyond what's in the corrections
5. Maintains a natural, conversational tone
Your response should begin immediately with the answer.
"""
                
                try:
                    response = bedrock_runtime_client.converse(
                        modelId=model_id,
                        messages=[{"role": "user", "content": [{"text": combine_prompt}]}]
                    )
                    
                    result["rewritten_response"] = response['output']['message']['content'][0]['text']
                    result["rewritten"] = True
                    result["message"] = f"Successfully rewrote response for: {', '.join(result['finding_types'])}"
                except Exception as e:
                    result["message"] = f"Error combining rewrites: {str(e)}"
                
        return result

def summarize_results(user_query, llm_response, policy_definition, guardrail_id, guardrail_version, 
                     bedrock_runtime_client, model_id="anthropic.claude-3-sonnet-20240229-v1:0", domain=None):
    if domain is None:
        domain = input("Enter domain (e.g. Insurance, Healthcare): ") or "General"
    
    content_to_validate = [
        {"text": {"text": user_query, "qualifiers": ["query"]}},
        {"text": {"text": llm_response, "qualifiers": ["guard_content"]}}
    ]
    
    apply_guardrail_response = bedrock_runtime_client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=guardrail_version, 
        source="OUTPUT",
        content=content_to_validate
    )
    
    ar_findings = None
    if 'assessments' in apply_guardrail_response and apply_guardrail_response['assessments']:
        for assessment in apply_guardrail_response['assessments']:
            if 'automatedReasoningPolicy' in assessment:
                ar_findings = assessment['automatedReasoningPolicy']
                break
    
    formatted_findings = extract_reasoning_findings(apply_guardrail_response, policy_definition)
    
    rewriter = ResponseRewriter(policy_definition=policy_definition, domain=domain)
    result = rewriter.rewrite_response(
        user_query=user_query,
        llm_response=llm_response,
        ar_findings=ar_findings,
        model_id=model_id,
        bedrock_runtime_client=bedrock_runtime_client
    )
    
    return {
        "query": user_query,
        "original_response": llm_response,
        "rewritten_response": result.get("rewritten_response"),
        "findings": formatted_findings,
        "finding_types": result.get("finding_types", []),
        "domain": domain
    }