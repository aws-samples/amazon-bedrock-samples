import json
import logging
import os

import boto3

# get logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

region = os.environ["AWS_REGION"]
cfn_client = boto3.client("cloudformation", region_name=region)
bedrock_client = boto3.client("bedrock-agent-runtime", region_name=region)
stack_name = os.getenv("CFN_STACK_NAME")


def handler(event, context):
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
        body = (
            json.loads(event["body"])
            if isinstance(event["body"], str)
            else event["body"]
        )

        # account_id = event["requestContext"]["accountId"]

        # logger.info(f"Region: {region}; Account ID: {account_id}; Model ID: {model_id}")

        # Validate required fields
        if not all(
            key in body for key in ["prompt", "modelID", "temperature", "top_p"]
        ):
            # logger.debug(f"Missing required fields: {body}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields"}),
            }
        # logger.info(f"Received body: {body}")  # Debug log

        response = cfn_client.describe_stacks(StackName=stack_name)

        outputs = {}
        if "Stacks" in response and len(response["Stacks"]) > 0:
            if "Outputs" in response["Stacks"][0]:
                for output in response["Stacks"][0]["Outputs"]:
                    outputs[output["OutputKey"]] = output["OutputValue"]

        guardrailID = outputs["GuardrailsId"]
        # model_arn = f"arn:aws:bedrock:{region}::foundation-model/{body['modelID']}"
        # model_arn = (
        #     f"arn:aws:bedrock:{region}:{account_id}:inference-profile/us.{model_id}"
        # )
        # logger.info(f"Inference Profile ARN: {model_arn}")

        # Extract parameters with type conversion
        inference_config = {
            "textInferenceConfig": {
                "maxTokens": int(body["max_tokens"]),
                "temperature": float(body["temperature"]),
                "topP": float(body["top_p"]),
            }
        }
        logger.debug(f"Received inference_config: {inference_config}")

        # Retrieve modelID from the body
        model_id = body["modelID"]

        response = bedrock_client.retrieve_and_generate(
            input={"text": body["prompt"]},
            retrieveAndGenerateConfiguration={
                "knowledgeBaseConfiguration": {
                    "generationConfiguration": {
                        "guardrailConfiguration": {
                            "guardrailId": guardrailID,
                            "guardrailVersion": "DRAFT",
                        },
                        "inferenceConfig": inference_config,
                    },
                    "knowledgeBaseId": outputs["BedrockKBId"],
                    "modelArn": model_id,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "numberOfResults": 10,
                        }
                    },
                },
                "type": "KNOWLEDGE_BASE",
            },
        )
        return {"statusCode": 200, "body": response["output"]["text"]}

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
