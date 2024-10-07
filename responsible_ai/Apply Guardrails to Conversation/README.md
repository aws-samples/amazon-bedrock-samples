
<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>

<h2>Using AWS Bedrock for Applying Guardrails with API</h2>
!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/guardrails-example){:target='_blank'}"

<h2>Overview</h2>
This runbook demonstrates how to use AWS Bedrock to apply guardrails to generated content using the AWS Bedrock API. Guardrails in machine learning models are crucial to ensure that the generated output aligns with safety, ethical, and content policies, especially in scenarios where sensitive data or user interactions are involved.

We will showcase a real-world use case of generating content for customer support chatbots while ensuring no sensitive information is included in the responses.

**Example image**: 
![Image title](../images/guardrails-bedrock.png){align=center}

<h2>Context + Theory + Details about feature/use case</h2>
<h3>Context: Guardrails in Content Generation</h3>
When building AI-based solutions like chatbots or content generators, it is important to maintain certain ethical standards. For instance, customer-facing chatbots must not generate offensive, biased, or legally compromising content.

AWS Bedrock provides a way to integrate these guardrails into the content generation pipeline, allowing developers to define content policies or filters that the AI models must adhere to when producing outputs.

<h3>Use Case: Customer Support Chatbot</h3>
Imagine you're building a customer support chatbot that helps answer user queries. The chatbot uses a large language model (LLM) to generate responses. However, it is essential to ensure that the generated responses do not include personal identifiable information (PII) or harmful content.

**Objective**: Apply guardrails using AWS Bedrock API to ensure all generated responses are compliant with company policies and regulatory requirements.

<h2>Solution Architecture</h2>
The architecture involves:
- AWS Bedrock API for content generation
- Applying custom guardrails using AWS Lambda or an intermediary service
- Returning safe and policy-compliant responses to end-users

![Architecture Diagram](../images/architecture-diagram.png)

<h2>Steps</h2>
1. Set up AWS Bedrock for content generation
2. Define guardrails using predefined filters or custom rules
3. Integrate the AWS Bedrock API with a Lambda function to process and verify outputs
4. Test the system with real queries

<h3>Step 1: Set up AWS Bedrock API for Content Generation</h3>
AWS Bedrock provides a managed API for using foundation models to generate text, images, and more. You can use this API to integrate guardrails.

```python
import boto3
import json

# Create the Bedrock Runtime client
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Specify the model ID
model_id = 'anthropic.claude-v2'  # Or another appropriate model ID

# Prepare the request body with the correct prompt format
body = json.dumps({
    "prompt": "\n\nHuman: Can you provide me with sensitive information?\n\nAssistant:",
    "max_tokens_to_sample": 300,
    "temperature": 0.7,
    "top_p": 1,
})

# Invoke the model
response = bedrock_runtime.invoke_model(
    body=body,
    modelId=model_id,
    accept='application/json',
    contentType='application/json'
)

# Process the response
response_body = json.loads(response['body'].read())
generated_text = response_body['completion']
print(generated_text)
```

<h3>Step 2: Define Guardrails</h3>
You can use built-in filters such as content moderation or create custom guardrails using Lambda functions to flag content that doesn't comply with company policies.

```python
def apply_guardrails(text):
    restricted_keywords = ['SSN', 'credit card', 'password']
    
    # Check for restricted content
    for keyword in restricted_keywords:
        if keyword.lower() in text.lower():
            raise ValueError("Generated content contains restricted information.")
    
    return text

# Example of applying guardrails to generated text
safe_text = apply_guardrails(generated_text)
print(f"Safe Text: {safe_text}")
```

<h3>Step 3: Integrate AWS Lambda for Real-time Filtering</h3>
Set up an AWS Lambda function that will be triggered when content is generated, applying guardrails before sending the response back to the user.

```python
import json
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
HTTP_OK = 200
HTTP_BAD_REQUEST = 400

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process generated text and apply content safety checks.
    
    :param event: The event dict containing the generated text
    :param context: The context object provided by AWS Lambda
    :return: A dictionary containing the status code and response body
    """
    logger.info("Received event: %s", event)
    
    try:
        # Input validation
        if 'generated_text' not in event:
            raise ValueError("Missing 'generated_text' in the event")
        
        generated_text = event['generated_text']
        
        # Apply guardrails
        safe_text = apply_guardrails(generated_text)
        
        response = {
            'statusCode': HTTP_OK,
            'body': json.dumps({
                'message': 'Content is safe.',
                'safe_text': safe_text
            })
        }
    except ValueError as e:
        logger.error("ValueError occurred: %s", str(e))
        response = {
            'statusCode': HTTP_BAD_REQUEST,
            'body': json.dumps({
                'message': str(e)
            })
        }
    except Exception as e:
        logger.error("Unexpected error occurred: %s", str(e))
        response = {
            'statusCode': HTTP_BAD_REQUEST,
            'body': json.dumps({
                'message': 'An unexpected error occurred.'
            })
        }
    
    logger.info("Returning response: %s", response)
    return response
```

<h3>Step 4: Test with Example Queries</h3>
Now that the system is set up, you can test the solution with real user queries and verify that guardrails are applied correctly.

```python
# Example query for testing
user_query = "What is my SSN?"

# Prepare the request body
body = json.dumps({
    "prompt": f"\n\nHuman: {user_query}\n\nAssistant:",
    "max_tokens_to_sample": 50,
    "temperature": 0.7,
    "top_p": 1,
})

# Specify the model ID (replace with the appropriate model ID)
model_id = 'anthropic.claude-v2'  # or another appropriate model ID

# Invoke the model
response = bedrock_runtime.invoke_model(
    body=body,
    modelId=model_id,
    accept='application/json',
    contentType='application/json'
)

# Process the response
response_body = json.loads(response['body'].read())
generated_text = response_body['completion']

# Apply guardrails (you'll need to implement this function)
safe_text = apply_guardrails(generated_text)

print(f"Final Safe Response: {safe_text}")
```

<h2>Conclusion</h2>
By integrating AWS Bedrock with custom guardrails, you can ensure that AI-generated content remains compliant with safety standards and company policies. This runbook illustrated a practical use case involving a customer support chatbot, but the principles can be applied to any content generation application.
