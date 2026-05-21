def get_policy_definition(bedrock_client, policy_arn):
    """
    Get the policy definition.
    
    Args:
        bedrock_policy_client: Bedrock client for policy operations
        policy_arn (str): ARN of the policy.
        
    Returns:
        dict: Policy definition.
    """
    try:
        response = bedrock_client.export_automated_reasoning_policy_version(
            policyArn=policy_arn
        )
        
        return response.get('policyDefinition', {})
    except Exception as e:
        print(f"Error getting policy definition: {str(e)}")
        raise