# Amazon Bedrock Guardrails - Selective Content Evaluation Guide

## Overview

Amazon Bedrock Guardrails provides flexible content evaluation that works with any LLM—whether hosted on Amazon Bedrock or external providers. The `ApplyGuardrail` API enables you to evaluate content independently of model invocation, making it ideal for architectures that use multiple model providers.

This guide explains how to implement selective content evaluation using `ApplyGuardrail`, focusing on the Split Prompt Pattern for protecting dynamic content while keeping trusted static content unguarded.

---

## Understanding the Original Request

The original JSON attempted to use XML-style tags within content passed to `ApplyGuardrail`:

```json
{
    "messages": [
        {"content": "text text text text", "role": "system"},
        {"content": "<amazon-bedrock-guardrails-guardContent>High-Risk Early-Stage or Advanced Triple-Negative Breast Cancer (TNBC)</amazon-bedrock-guardrails-guardContent>", "role": "user"}
    ]
}
```

**Why this doesn't work**: The XML tag format (`<amazon-bedrock-guardrails-guardContent>`) is designed for the `InvokeModel` API where guardrails are applied during model invocation. The `ApplyGuardrail` API uses a different approach—it evaluates all content blocks you provide, giving you explicit control over what gets evaluated by choosing what to include in the request.

---

## ApplyGuardrail API - Recommended for Multi-Provider Architectures

The `ApplyGuardrail` API is the preferred choice when:
- You use models from multiple providers (Bedrock + external LLMs)
- You want to validate content before incurring LLM invocation costs
- You need decoupled guardrail evaluation in your application flow

### How ApplyGuardrail Works

`ApplyGuardrail` evaluates **all content blocks** you provide in the request. This design gives you explicit control—you decide what to evaluate by choosing what to include:

```python
# Only the content you include gets evaluated
response = bedrock_runtime.apply_guardrail(
    guardrailIdentifier="your-guardrail-id",
    guardrailVersion="DRAFT",
    source="INPUT",
    content=[
        {"text": {"text": "This content will be evaluated"}}
        # Content NOT included here is NOT evaluated
    ]
)
```

### Qualifiers for Contextual Grounding

The `qualifiers` field (`grounding_source`, `query`, `guard_content`) is specifically designed for **contextual grounding checks** to detect hallucinations in model responses:

```python
# Contextual grounding check example
response = bedrock_runtime.apply_guardrail(
    guardrailIdentifier="your-guardrail-id",
    guardrailVersion="DRAFT",
    source="OUTPUT",
    content=[
        {"text": {"text": "Reference source text", "qualifiers": ["grounding_source"]}},
        {"text": {"text": "User question", "qualifiers": ["query"]}},
        {"text": {"text": "Model response to check", "qualifiers": ["guard_content"]}}
    ]
)
```

---

## Split Prompt Pattern - Selective Evaluation Workaround

For selective content filter evaluation with `ApplyGuardrail`, use the **Split Prompt Pattern**: separate your prompt into trusted (static) and untrusted (dynamic) components, then only send the dynamic content to the guardrail.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Application                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────┐    ┌─────────────────────────────┐   │
│   │  STATIC CONTENT     │    │  DYNAMIC CONTENT            │   │
│   │  (Trusted)          │    │  (Untrusted - needs guard)  │   │
│   │                     │    │                             │   │
│   │  • System role      │    │  • Developer instructions   │   │
│   │  • Base persona     │    │  • User-provided context    │   │
│   │  • Fixed guidelines │    │  • External data            │   │
│   └─────────────────────┘    └──────────────┬──────────────┘   │
│            │                                 │                   │
│            │                                 ▼                   │
│            │                    ┌────────────────────────┐      │
│            │                    │   ApplyGuardrail API   │      │
│            │                    │   (Validate dynamic    │      │
│            │                    │    content only)       │      │
│            │                    └───────────┬────────────┘      │
│            │                                │                   │
│            │                    ┌───────────┴────────────┐      │
│            │                    │                        │      │
│            │               PASSED                   BLOCKED     │
│            │                    │                        │      │
│            ▼                    ▼                        ▼      │
│   ┌─────────────────────────────────────┐    ┌──────────────┐  │
│   │  Combine static + dynamic content   │    │ Return error │  │
│   │  Invoke LLM (Bedrock or external)   │    │ Skip LLM     │  │
│   └─────────────────────────────────────┘    └──────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Benefits

1. **Cost optimization**: Only evaluate content that needs protection
2. **Performance**: Reduce guardrail processing time by excluding trusted content
3. **Flexibility**: Works with any LLM provider (Bedrock, OpenAI, Anthropic direct, etc.)
4. **Control**: Fail fast—block harmful content before incurring LLM costs

---

## Complete Code Example

The following example demonstrates the Split Prompt Pattern with `ApplyGuardrail` and the OpenAI Responses API on Bedrock Mantle (GPT OSS 20B):

```python
"""
Split Prompt Pattern: Selective guardrail evaluation for multi-provider LLM architectures.
Validates dynamic content with ApplyGuardrail before invoking the LLM.
"""

import boto3
import httpx
from openai import OpenAI
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class BedrockMantleSigV4Auth(httpx.Auth):
    """SigV4 authentication for Bedrock Mantle OpenAI-compatible endpoints."""
    
    def __init__(self, region: str, credentials):
        self.service = "bedrock-mantle"
        self.region = region
        self.credentials = credentials

    def auth_flow(self, request: httpx.Request):
        headers_to_sign = {'host': request.url.host, 'x-amz-date': None}
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers_to_sign
        )
        SigV4Auth(self.credentials, self.service, self.region).add_auth(aws_request)
        for key, value in aws_request.headers.items():
            request.headers[key] = value
        yield request


def validate_content(runtime_client, guardrail_id: str, content: str) -> dict:
    """Validate content using ApplyGuardrail API."""
    response = runtime_client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion="DRAFT",
        source="INPUT",
        content=[{"text": {"text": content}}]
    )
    return {
        "passed": response["action"] == "NONE",
        "action": response["action"],
        "reason": response.get("actionReason")
    }


def create_openai_client(region: str) -> OpenAI:
    """Create OpenAI client for Bedrock Mantle with SigV4 auth."""
    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()
    return OpenAI(
        api_key="dummy",
        base_url=f"https://bedrock-mantle.{region}.api.aws/v1",
        http_client=httpx.Client(auth=BedrockMantleSigV4Auth(region, credentials))
    )


def guarded_llm_call(
    runtime_client,
    openai_client: OpenAI,
    guardrail_id: str,
    static_role: str,
    dynamic_instructions: str,
    user_query: str
) -> dict:
    """
    Execute LLM call with guardrail protection on dynamic content only.
    
    Args:
        runtime_client: Bedrock Runtime client for ApplyGuardrail
        openai_client: OpenAI client configured for Bedrock Mantle
        guardrail_id: Guardrail identifier
        static_role: Trusted static system role (NOT evaluated)
        dynamic_instructions: Untrusted dynamic content (EVALUATED by guardrail)
        user_query: User's question
    
    Returns:
        dict with success status and response or error details
    """
    
    # Step 1: Validate ONLY the dynamic content with guardrail
    validation = validate_content(runtime_client, guardrail_id, dynamic_instructions)
    
    if not validation["passed"]:
        return {
            "success": False,
            "stage": "guardrail_validation",
            "reason": f"Dynamic content blocked: {validation['reason']}"
        }
    
    # Step 2: Content passed - combine and invoke LLM
    full_system_prompt = f"{static_role}\n\n{dynamic_instructions}"
    
    response = openai_client.responses.create(
        model="openai.gpt-oss-20b",
        input=[
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_query}
        ]
    )
    
    # Extract response text
    output_text = None
    for item in getattr(response, "output", []):
        if getattr(item, "type", None) == "message":
            for content in getattr(item, "content", []) or []:
                if text := getattr(content, "text", None):
                    output_text = text
                    break
    
    return {
        "success": True,
        "stage": "llm_response",
        "output": output_text
    }


# Example usage
if __name__ == "__main__":
    region = "us-east-1"
    guardrail_id = "your-guardrail-id"
    
    runtime_client = boto3.client("bedrock-runtime", region_name=region)
    openai_client = create_openai_client(region)
    
    # Static role - trusted, NOT sent to guardrail
    static_role = "You're a medical research expert specializing in oncology."
    
    # Dynamic instructions - untrusted, VALIDATED by guardrail
    dynamic_instructions = """
    When answering questions about cancer treatments:
    - Cite recent clinical trials when available
    - Explain mechanisms of action clearly
    - Note any FDA approval status
    """
    
    result = guarded_llm_call(
        runtime_client=runtime_client,
        openai_client=openai_client,
        guardrail_id=guardrail_id,
        static_role=static_role,
        dynamic_instructions=dynamic_instructions,
        user_query="What are the latest treatments for triple-negative breast cancer?"
    )
    
    if result["success"]:
        print(f"Response: {result['output']}")
    else:
        print(f"Blocked: {result['reason']}")
```

---

## Alternative APIs for Bedrock-Only Architectures

If you're using only Amazon Bedrock models, you can use built-in selective evaluation:

### Converse API with `guardContent`

```python
response = bedrock_runtime.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{
        "role": "user",
        "content": [
            {"text": "Context - not evaluated"},
            {"guardContent": {"text": {"text": "Query - evaluated by guardrails"}}}
        ]
    }],
    guardrailConfig={
        "guardrailIdentifier": "your-guardrail-id",
        "guardrailVersion": "DRAFT"
    }
)
```

### InvokeModel API with XML Tags

```python
import secrets

tag_suffix = secrets.token_hex(6)  # Unique per request for security
prompt = f"""Context here
<amazon-bedrock-guardrails-guardContent_{tag_suffix}>Content to evaluate</amazon-bedrock-guardrails-guardContent_{tag_suffix}>"""

response = bedrock_runtime.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps({"messages": [{"role": "user", "content": prompt}]}),
    guardrailIdentifier="your-guardrail-id",
    guardrailVersion="DRAFT",
    trace="ENABLED"
)
# Include in request headers: "amazon-bedrock-guardrailConfig": {"tagSuffix": tag_suffix}
```

---

## Summary

| Scenario | Recommended Approach |
|----------|---------------------|
| Multi-provider LLMs (Bedrock + external) | `ApplyGuardrail` with Split Prompt Pattern |
| Pre-validation before LLM costs | `ApplyGuardrail` with Split Prompt Pattern |
| Hallucination detection | `ApplyGuardrail` with `qualifiers` |
| Bedrock-only chat applications | Converse API with `guardContent` |
| Bedrock-only direct invocation | InvokeModel API with XML tags |

The Split Prompt Pattern with `ApplyGuardrail` provides maximum flexibility for multi-provider architectures—you control exactly what content is validated, when validation occurs, and how to handle blocked content before incurring LLM invocation costs.
