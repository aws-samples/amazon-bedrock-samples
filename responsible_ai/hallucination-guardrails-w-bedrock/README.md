
<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
</style>

<h2>Using AWS Bedrock to Apply Hallucination Guardrails</h2>
!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/hallucination-guardrails){:target='_blank'}"

<h2>Overview</h2>
This runbook demonstrates how to use AWS Bedrock to apply guardrails to prevent hallucinations in AI-generated content. In generative AI models, hallucinations refer to outputs that are fabricated or false but presented as factual. This is a common issue in large language models (LLMs), where responses may appear convincing but include inaccurate or misleading information.

We will provide a real-world scenario where a legal assistant AI generates responses based on provided case data but must be restricted from generating false legal claims or statutes.

**Example image**: 
![Image title](../images/hallucination-guardrails.png){align=center}

<h2>Context + Theory + Details about feature/use case</h2>
<h3>Context: Hallucinations in Language Models</h3>
AI models often generate content based on patterns and probabilities, which can lead to the creation of statements or facts that are not grounded in real data, known as hallucinations. In critical areas such as legal, healthcare, and finance, these hallucinations can lead to severe consequences.

Guardrails can help mitigate this risk by verifying the factual accuracy of AI-generated content before it is presented to users.

<h3>Use Case: AI Legal Assistant</h3>
Imagine you are developing an AI-based legal assistant to help law firms by generating summaries of legal cases or providing answers to legal questions. While the model can generate insightful information, there is a risk that it could "hallucinate" nonexistent laws or precedents.

**Objective**: Use AWS Bedrock API to apply guardrails that prevent the generation of hallucinated or inaccurate legal information.

<h2>Solution Architecture</h2>
The solution architecture includes:
- AWS Bedrock API for generating content
- A verification layer that uses existing legal databases or knowledge bases to cross-reference the generated content
- AWS Lambda to apply these guardrails and prevent hallucinated content from reaching end users

![Architecture Diagram](../images/legal-assistant-architecture.png)

<h2>Steps</h2>
1. Set up AWS Bedrock API for content generation
2. Integrate a verification system for cross-referencing legal facts
3. Implement guardrails using AWS Lambda
4. Test the system with real-world legal queries

<h3>Step 1: Set up AWS Bedrock API for Content Generation</h3>
First, set up the AWS Bedrock API to generate legal content using a pre-trained language model. The content generation process will include legal summaries or responses based on input questions.

```python
import boto3

# Initialize AWS Bedrock client
import boto3
import json

# Create the Bedrock Runtime client
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Specify the model ID
model_id = 'anthropic.claude-v2'  # Or another appropriate model ID

# Prepare the request body with the correct prompt format
body = json.dumps({
    "prompt": "\n\nHuman:Summarize the case law regarding intellectual property?\n\nAssistant:",
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

<h3>Step 2: Cross-reference Generated Content</h3>
To prevent hallucinations, we will implement a cross-referencing system that checks the generated text against a database of actual legal statutes and case law.

```python
# Example of a simple legal verification function
# Example of a simple legal verification function
def verify_legal_content(text, legal_database):
    verified_facts = []
    for sentence in text.split('.'):
        # Check if the sentence exists in the legal database
        if sentence.strip() in legal_database:
            verified_facts.append(sentence)
        else:
            print(f"Warning: The following statement may be hallucinated: {sentence}")
    return verified_facts

# Sample legal database (for demonstration purposes)
legal_database = [
    "The case law regarding intellectual property is well-established in several jurisdictions.",
    "Intellectual property laws protect the rights of creators and inventors."
]

# Cross-reference generated content
verified_text = verify_legal_content(generated_text, legal_database)
print(f"Verified Text: {'. '.join(verified_text)}")
```

<h3>Step 3: Implement AWS Lambda to Apply Guardrails</h3>
AWS Lambda will be used to automatically verify content before delivering it to end users. The Lambda function will apply hallucination guardrails by calling the verification process and only allowing verified content to pass through.

```python
import json

def lambda_handler(event, context):
    # Parse the generated content
    generated_text = event['generated_text']
    
    # Legal database (in a real scenario, this could be a large external database)
    legal_database = [
        "The case law regarding intellectual property is well-established in several jurisdictions.",
        "Intellectual property laws protect the rights of creators and inventors."
    ]
    
    # Apply hallucination guardrails by verifying content
    verified_text = verify_legal_content(generated_text, legal_database)
    
    if verified_text:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Content verified and safe to deliver.',
                'verified_text': '. '.join(verified_text)
            })
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Generated content contains hallucinations and cannot be delivered.'
            })
        }
```

<h3>Step 4: Test with Example Queries</h3>
Test the system with legal queries to ensure the hallucination guardrails are functioning properly. This example shows how to generate legal content and apply the guardrails.

```python
# Example query for testing
user_query = "Summarize the case law regarding intellectual property."

# Prepare the request body
body = json.dumps({
    "prompt": f"\n\nHuman: {user_query}\n\nAssistant:",
    "max_tokens_to_sample": 150,
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

# Apply hallucination guardrails (using the cross-reference function)
verified_text = verify_legal_content(generated_text, legal_database)

if verified_text:
    print(f"Final Verified Response: {'. '.join(verified_text)}")
else:
    print("Content contains hallucinations and cannot be used.")
```

<h2>Conclusion</h2>
By integrating AWS Bedrock with hallucination guardrails, you can ensure that AI-generated legal content is factually accurate and reliable. This example illustrated a legal assistant use case, but the same principles can be applied across industries where factual accuracy is critical, such as healthcare, finance, and more.
