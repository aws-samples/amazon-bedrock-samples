import json
import logging
import os

import boto3

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Initialize clients
region = os.environ["AWS_REGION"]
cfn_client = boto3.client("cloudformation", region_name=region)
bedrock_client = boto3.client("bedrock-agent-runtime", region_name=region)
bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=region)
stack_name = os.getenv("CFN_STACK_NAME")


def create_user_friendly_message(assessments, source_type):
    """Create a user-friendly message based on guardrail assessment results."""
    intervention_reason = assessments.get(
        "intervention_reason", "Content Policy Violation"
    )
    details = assessments.get("details", {})

    message = f"Your {'input' if source_type == 'INPUT' else 'output'} was blocked due to a {intervention_reason}.\n\n"

    # Add specific details based on violation type
    if "blocked_topics" in details:
        message += f"Blocked topics: {', '.join(details['blocked_topics'])}\n"

    if "blocked_content" in details:
        content_types = [item.get("type", "") for item in details["blocked_content"]]
        message += f"Content filters triggered: {', '.join(content_types)}\n"

    if "blocked_words" in details:
        message += "Blocked words or phrases detected\n"

    if "sensitive_information" in details:
        pii_types = [
            item.get("type", "")
            for item in details["sensitive_information"]
            if "type" in item
        ]
        if pii_types:
            message += f"Sensitive information detected: {', '.join(pii_types)}\n"

    if "grounding_issues" in details:
        grounding_types = [item.get("type", "") for item in details["grounding_issues"]]
        message += f"Grounding issues: {', '.join(grounding_types)}\n"

    return message


def extract_guardrail_assessments(assessments):
    """Extract relevant information from guardrail assessments."""
    if not assessments:
        return {}

    result = {"intervention_reason": "", "details": {}}
    policy_checkers = {
        "topicPolicy": _check_topic_policy,
        "contentPolicy": _check_content_policy,
        "wordPolicy": _check_word_policy,
        "sensitiveInformationPolicy": _check_sensitive_info_policy,
        "contextualGroundingPolicy": _check_contextual_grounding_policy,
    }

    for assessment in assessments:
        for policy_type, checker_func in policy_checkers.items():
            if policy_type in assessment:
                checker_func(assessment[policy_type], result)

    # If no specific reason found but there was an intervention
    if not result["intervention_reason"] and assessments:
        result["intervention_reason"] = "Guardrail Policy Violation"
        result["details"]["raw_assessment"] = assessments

    return result


def _check_topic_policy(policy, result):
    """Check topic policy violations."""
    if "topics" in policy:
        blocked_topics = [
            topic.get("name", "")
            for topic in policy["topics"]
            if topic.get("action") == "BLOCKED"
        ]
        if blocked_topics:
            result["intervention_reason"] = "Topic Policy Violation"
            result["details"]["blocked_topics"] = blocked_topics


def _check_content_policy(policy, result):
    """Check content policy violations."""
    if "filters" in policy:
        blocked_content = [
            {"type": item.get("type", ""), "confidence": item.get("confidence", "")}
            for item in policy["filters"]
            if item.get("action") == "BLOCKED"
        ]
        if blocked_content:
            result["intervention_reason"] = "Content Policy Violation"
            result["details"]["blocked_content"] = blocked_content


def _check_word_policy(policy, result):
    """Check word policy violations."""
    blocked_words = []

    if "customWords" in policy:
        blocked_words.extend(
            [
                word.get("match", "")
                for word in policy["customWords"]
                if word.get("action") == "BLOCKED"
            ]
        )

    if "managedWordLists" in policy:
        blocked_words.extend(
            [
                {"match": word.get("match", ""), "type": word.get("type", "")}
                for word in policy["managedWordLists"]
                if word.get("action") == "BLOCKED"
            ]
        )

    if blocked_words:
        result["intervention_reason"] = "Word Policy Violation"
        result["details"]["blocked_words"] = blocked_words


def _check_sensitive_info_policy(policy, result):
    """Check sensitive information policy violations."""
    sensitive_info = []

    if "piiEntities" in policy:
        sensitive_info.extend(
            [
                {
                    "type": entity.get("type", ""),
                    "action": entity.get("action", ""),
                    "match": entity.get("match", ""),
                }
                for entity in policy["piiEntities"]
                if entity.get("action") in ["BLOCKED", "ANONYMIZED"]
            ]
        )

    if "regexes" in policy:
        sensitive_info.extend(
            [
                {
                    "name": regex.get("name", ""),
                    "action": regex.get("action", ""),
                    "match": regex.get("match", ""),
                }
                for regex in policy["regexes"]
                if regex.get("action") in ["BLOCKED", "ANONYMIZED"]
            ]
        )

    if sensitive_info:
        result["intervention_reason"] = "Sensitive Information Policy Violation"
        result["details"]["sensitive_information"] = sensitive_info


def _check_contextual_grounding_policy(policy, result):
    """Check contextual grounding policy violations."""
    if "filters" in policy:
        grounding_issues = [
            {
                "type": item.get("type", ""),
                "score": item.get("score"),
                "threshold": item.get("threshold"),
            }
            for item in policy["filters"]
            if item.get("action") == "BLOCKED"
        ]
        if grounding_issues:
            result["intervention_reason"] = "Contextual Grounding Policy Violation"
            result["details"]["grounding_issues"] = grounding_issues


def apply_guardrail(text, guardrail_id, source):
    """Apply guardrail to text and return assessment if intervention occurs."""
    response = bedrock_runtime_client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion="DRAFT",
        source=source,
        content=[{"text": {"text": text}}],
    )

    action = response.get("action", "NONE")
    logger.info(f"{source} Guardrail action: {action}")

    if action != "NONE":
        assessments = response.get("assessments", [])
        # logger.debug(f"{source} Guardrail assessments: {assessments}")
        extracted = extract_guardrail_assessments(assessments)
        message = create_user_friendly_message(extracted, source)

        return {
            "intervened": True,
            "message": message,
            "action": action,
            "assessments": extracted,
        }

    return {"intervened": False}


def get_stack_output(output_key):
    """Get a specific output value from CloudFormation stack."""
    response = cfn_client.describe_stacks(StackName=stack_name)

    if "Stacks" in response and len(response["Stacks"]) > 0:
        if "Outputs" in response["Stacks"][0]:
            for output in response["Stacks"][0]["Outputs"]:
                if output["OutputKey"] == output_key:
                    return output["OutputValue"]
    return None


def handler(event, context):
    try:
        # Parse and validate input
        body = (
            json.loads(event["body"])
            if isinstance(event["body"], str)
            else event["body"]
        )
        required_fields = ["prompt", "modelID", "temperature", "top_p"]

        if not all(field in body for field in required_fields):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields"}),
            }

        # Get guardrail and KB IDs from CloudFormation outputs
        input_guardrail_id = get_stack_output("InputGuardrailsID")
        output_guardrail_id = get_stack_output("OutputGuardrailsID")
        kb_id = get_stack_output("BedrockKBId")

        # Apply input guardrail
        input_guardrail_result = apply_guardrail(body["prompt"], input_guardrail_id, "INPUT")
        if input_guardrail_result["intervened"]:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "response": input_guardrail_result["message"],
                        "guardrail_action": input_guardrail_result["action"],
                    }
                ),
            }

        # Prepare inference configuration
        inference_config = {
            "textInferenceConfig": {
                "maxTokens": int(body["max_tokens"]),
                "temperature": float(body["temperature"]),
                "topP": float(body["top_p"]),
            }
        }

        # Call retrieve and generate
        response = bedrock_client.retrieve_and_generate(
            input={"text": body["prompt"]},
            retrieveAndGenerateConfiguration={
                "knowledgeBaseConfiguration": {
                    "generationConfiguration": {
                        "inferenceConfig": inference_config,
                    },
                    "knowledgeBaseId": kb_id,
                    "modelArn": body["modelID"],
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "numberOfResults": 10,
                        }
                    },
                },
                "type": "KNOWLEDGE_BASE",
            },
        )

        rng_response = response["output"]["text"]

        # Apply output guardrail
        output_guardrail_result = apply_guardrail(rng_response, output_guardrail_id, "OUTPUT")
        # logger.debug(f"Output Guardrail result: {output_guardrail_result}")
        user_message = (
            output_guardrail_result["message"]
            if output_guardrail_result["intervened"]
            else rng_response
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "response": user_message,
                    "guardrail_action": output_guardrail_result.get("action", "NONE"),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
