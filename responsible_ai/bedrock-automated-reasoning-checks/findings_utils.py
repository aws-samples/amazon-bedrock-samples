def extract_reasoning_findings(guardrail_response, policy_definition=None):
    """
    Extract and format the automated reasoning findings from an AWS Bedrock Guardrails response.
    
    Args:
        guardrail_response (dict): The response from the apply_guardrail API call
        policy_definition (dict, optional): The policy definition containing rule details
        
    Returns:
        str: Formatted string containing the automated reasoning findings
    """
    # Check if there are any assessments in the response
    if "assessments" not in guardrail_response or not guardrail_response["assessments"]:
        return "No assessments found in the response."

    # Create a lookup dictionary for rule details if policy definition is provided
    rule_details = {}
    if policy_definition and 'rules' in policy_definition:
        for rule in policy_definition['rules']:
            rule_id = rule['id']
            rule_details[rule_id] = {
                'expression': rule.get('expression', 'No expression available'),
                'alternateExpression': rule.get('alternateExpression', 'No alternate expression available')
            }
    
    output = []
    output.append("# Automated Reasoning Policy Findings\n")
    
    # Find the assessment with automatedReasoningPolicy
    for assessment in guardrail_response["assessments"]:
        if "automatedReasoningPolicy" in assessment:
            findings = assessment["automatedReasoningPolicy"]["findings"]
            
            for i, finding in enumerate(findings):
                output.append(f"## Finding {i+1}")
                
                # Determine finding type and extract data
                for finding_type, data in finding.items():
                    output.append(f"**Finding Type:** {finding_type.capitalize()}\n")
                    
                    # Special handling for empty finding types
                    if finding_type == "tooComplex":
                        output.append("The reasoning is too complex for the system to analyze.\n")
                        continue
                        
                    if finding_type == "noTranslations":
                        output.append("The text couldn't be translated into logical form for analysis.\n")
                        continue
                    
                    # Special handling for translationAmbiguous
                    if finding_type == "translationAmbiguous":
                        if "options" in data and data["options"]:
                            output.append("### Translation Options:")
                            for j, option in enumerate(data["options"]):
                                output.append(f"#### Option {j+1}:")
                                
                                # Process translations within each option
                                if "translations" in option and option["translations"]:
                                    for k, translation in enumerate(option["translations"]):
                                        if k > 0:
                                            output.append(f"##### Translation {k+1}:")
                                            
                                        # Extract premises
                                        if "premises" in translation and translation["premises"]:
                                            output.append("##### Premises:")
                                            for l, premise in enumerate(translation["premises"]):
                                                output.append(f"- {premise['naturalLanguage']} (Logic -> {premise['logic']})")
                                            output.append("")
                                        
                                        # Extract claims
                                        if "claims" in translation and translation["claims"]:
                                            output.append("##### Claims:")
                                            for l, claim in enumerate(translation["claims"]):
                                                output.append(f"- {claim['naturalLanguage']} (Logic -> {claim['logic']})")
                                            output.append("")
                                            
                                        # Extract untranslated premises
                                        if "untranslatedPremises" in translation and translation["untranslatedPremises"]:
                                            output.append("##### Untranslated Premises:")
                                            for l, premise in enumerate(translation["untranslatedPremises"]):
                                                output.append(f"- {premise.get('text', 'No text available')}")
                                            output.append("")
                                            
                                        # Extract untranslated claims
                                        if "untranslatedClaims" in translation and translation["untranslatedClaims"]:
                                            output.append("##### Untranslated Claims:")
                                            for l, claim in enumerate(translation["untranslatedClaims"]):
                                                output.append(f"- {claim.get('text', 'No text available')}")
                                            output.append("")
                                            
                                        # Extract confidence score
                                        if "confidence" in translation:
                                            output.append(f"**Confidence Score:** {translation['confidence']}\n")
                                else:
                                    output.append("No translations provided in this option.\n")
                        
                        # Handle difference scenarios
                        if "differenceScenarios" in data and data["differenceScenarios"]:
                            output.append("### Difference Scenarios:")
                            for j, scenario in enumerate(data["differenceScenarios"]):
                                output.append(f"#### Scenario {j+1}:")
                                if "statements" in scenario and scenario["statements"]:
                                    for stmt in scenario["statements"]:
                                        output.append(f"- {stmt.get('naturalLanguage', 'N/A')} (Logic -> {stmt.get('logic', 'N/A')})")
                                else:
                                    output.append("No statements in this scenario.")
                                output.append("")
                        continue
                    
                    # Handle translation section for other finding types
                    if "translation" in data:
                        translation = data["translation"]
                        output.append("### Translation:")
                        
                        # Extract premises
                        if "premises" in translation and translation["premises"]:
                            output.append("#### Premises:")
                            for j, premise in enumerate(translation["premises"]):
                                output.append(f"- {premise['naturalLanguage']} (Logic -> {premise['logic']})")
                            output.append("")
                        
                        # Extract claims
                        if "claims" in translation and translation["claims"]:
                            output.append("#### Claims:")
                            for j, claim in enumerate(translation["claims"]):
                                output.append(f"- {claim['naturalLanguage']} (Logic -> {claim['logic']})")
                            output.append("")
                        
                        # Extract untranslated premises
                        if "untranslatedPremises" in translation and translation["untranslatedPremises"]:
                            output.append("#### Untranslated Premises:")
                            for j, premise in enumerate(translation["untranslatedPremises"]):
                                output.append(f"- {premise.get('text', 'No text available')}")
                            output.append("")
                        
                        # Extract untranslated claims
                        if "untranslatedClaims" in translation and translation["untranslatedClaims"]:
                            output.append("#### Untranslated Claims:")
                            for j, claim in enumerate(translation["untranslatedClaims"]):
                                output.append(f"- {claim.get('text', 'No text available')}")
                            output.append("")
                        
                        # Extract confidence score
                        if "confidence" in translation:
                            output.append(f"**Confidence Score:** {translation['confidence']}\n")
                    
                    # Extract contradicting rules with details
                    if "contradictingRules" in data and data["contradictingRules"]:
                        output.append("### Contradicting Rules:")
                        for j, rule in enumerate(data["contradictingRules"]):
                            rule_id = rule.get('identifier')
                            output.append(f"{j+1}. Identifier: {rule_id}")
                            
                            # Add rule details if available
                            if rule_id in rule_details:
                                output.append(f"   - Formal Expression: `{rule_details[rule_id]['expression']}`")
                                output.append(f"   - Natural Language: \"{rule_details[rule_id]['alternateExpression']}\"")
                        output.append("")
                    
                    # Extract supporting rules with details
                    if "supportingRules" in data and data["supportingRules"]:
                        output.append("### Supporting Rules:")
                        for j, rule in enumerate(data["supportingRules"]):
                            rule_id = rule.get('identifier')
                            output.append(f"{j+1}. Identifier: {rule_id}")
                            
                            # Add rule details if available
                            if rule_id in rule_details:
                                output.append(f"   - Formal Expression: `{rule_details[rule_id]['expression']}`")
                                output.append(f"   - Natural Language: \"{rule_details[rule_id]['alternateExpression']}\"")
                        output.append("")
                    
                    # Handle scenarios for valid/satisfiable findings
                    if "claimsTrueScenario" in data:
                        output.append("### Claims True Scenario:")
                        statements = data["claimsTrueScenario"].get("statements", [])
                        # Limit to show first 5 statements to keep output concise
                        for stmt in statements[:5]:
                            output.append(f"- {stmt['naturalLanguage']} (Logic -> {stmt['logic']})")
                        if len(statements) > 5:
                            output.append(f"- ... and {len(statements) - 5} more statements")
                        output.append("")
                            
                    if "claimsFalseScenario" in data:
                        output.append("### Claims False Scenario:")
                        statements = data["claimsFalseScenario"].get("statements", [])
                        # Limit to show first 5 statements to keep output concise
                        for stmt in statements[:5]:
                            output.append(f"- {stmt['naturalLanguage']} (Logic -> {stmt['logic']})")
                        if len(statements) > 5:
                            output.append(f"- ... and {len(statements) - 5} more statements")
                        output.append("")
                    
                    # Handle logic warnings
                    if "logicWarning" in data:
                        warning = data["logicWarning"]
                        output.append(f"### Logic Warning: {warning.get('type', 'Unknown')}")
                        
                        # Extract premises from warning
                        if "premises" in warning and warning["premises"]:
                            output.append("#### Warning Premises:")
                            for j, premise in enumerate(warning["premises"]):
                                output.append(f"- {premise['naturalLanguage']} (Logic -> {premise['logic']})")
                            output.append("")
                        
                        # Extract claims from warning
                        if "claims" in warning and warning["claims"]:
                            output.append("#### Warning Claims:")
                            for j, claim in enumerate(warning["claims"]):
                                output.append(f"- {claim['naturalLanguage']} (Logic -> {claim['logic']})")
                            output.append("")
                
                output.append("---\n")
    
    return "\n".join(output)