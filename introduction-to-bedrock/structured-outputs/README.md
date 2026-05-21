# Structured Outputs with Claude on Amazon Bedrock

🚀 **Build reliable AI applications with schema-compliant JSON responses**

This repository contains a comprehensive Jupyter notebook (`structured_outputs_notebook.ipynb`) that demonstrates how to leverage structured outputs on Amazon Bedrock. Through constrained decoding, you can receive schema-compliant JSON responses from Claude models without custom parsing or validation logic. Through practical examples and real-world use cases, you'll discover why structured outputs is a game-changer for production AI applications.

---

## 📊 Key Findings from Our Analysis

Our notebook demonstrates Claude's impressive schema compliance capabilities on Amazon Bedrock through practical examples and real-world testing.

### Why Structured Outputs Matters

Traditional JSON generation from language models requires elaborate error handling and retry logic, losing valuable time and increasing costs. Amazon Bedrock's structured outputs uses constrained decoding to:

- 📈 **Schema Compliance**: Constrain responses to match your exact JSON schema
- 📍 **Type Safety**: Enforce field types, required fields, and enum value constraints
- 🎯 **Zero Validation Overhead**: Eliminate JSON.parse() errors and schema validation code
- ⚡ **Production Reliability**: Deploy with confidence knowing outputs conform to your schema

---

## 🎯 Quick Start: Copy-Paste Ready Examples

### 1. Basic JSON Schema Output with Converse API

```python
import boto3
import json

bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Define your schema
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]}
    },
    "required": ["name", "email", "priority"],
    "additionalProperties": False  # CRITICAL: Must be False
}

response = bedrock_runtime.converse(
    modelId="us.anthropic.claude-opus-4-5-20251101-v1:0",
    messages=[{"role": "user", "content": [{"text": "Extract: John (john@example.com) needs urgent help"}]}],
    inferenceConfig={"maxTokens": 1024},
    outputConfig={
        "textFormat": {
            "type": "json_schema",
            "structure": {
                "jsonSchema": {
                    "schema": json.dumps(schema),
                    "name": "contact_extraction"
                }
            }
        }
    }
)

# Schema-compliant JSON response
result = json.loads(response["output"]["message"]["content"][0]["text"])
print(result)  # {"name": "John", "email": "john@example.com", "priority": "high"}
```

### 2. Strict Tool Use for Agentic Workflows

```python
response = bedrock_runtime.converse(
    modelId="us.anthropic.claude-opus-4-5-20251101-v1:0",
    messages=[{"role": "user", "content": [{"text": "Book a flight to Tokyo for 2 passengers"}]}],
    inferenceConfig={"maxTokens": 1024},
    toolConfig={
        "tools": [{
            "toolSpec": {
                "name": "book_flight",
                "description": "Book a flight",
                "strict": True,  # Enable strict validation
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string"},
                            "passengers": {"type": "integer"}
                        },
                        "required": ["destination", "passengers"],
                        "additionalProperties": False
                    }
                }
            }
        }]
    }
)

# Tool inputs conform to the schema
```

### 3. Using InvokeModel API - Critical Requirements

⚠️ **Important**: The InvokeModel API uses a different parameter structure. Without the correct format, you'll receive standard (non-validated) responses.

```python
# CRITICAL: Schema goes in output_config.format, not outputConfig!
request_body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": [{"type": "text", "text": "Analyze this..."}]}],
    "output_config": {
        "format": {
            "type": "json_schema",
            "schema": {  # Direct JSON object, not stringified
                "type": "object",
                "properties": {"sentiment": {"type": "string"}},
                "required": ["sentiment"],
                "additionalProperties": False
            }
        }
    }
}

response = bedrock_runtime.invoke_model(
    modelId="us.anthropic.claude-opus-4-5-20251101-v1:0",
    body=json.dumps(request_body)
)
```

---

## ⚠️ Critical Requirements

**Always set `additionalProperties: false`** on all object types in your schema. Without this, structured outputs will not work correctly.

❌ Don't use recursive schemas
❌ Don't use external `$ref` references
❌ Don't use numerical constraints (`minimum`, `maximum`)
❌ Don't use string length constraints (`minLength`, `maxLength`)

✅ Do use `enum` for constrained string values
✅ Do use descriptive property names and descriptions
✅ Do check `stopReason` in responses for edge cases
✅ Do plan for schema caching (24-hour cache improves performance)

---

## 🔍 What the Notebook Demonstrates

### JSON Schema Output Format

The notebook shows structured outputs accurately extracting:

- Lead information from customer emails with required field presence
- Invoice data with nested line items and calculated totals
- Sentiment analysis with constrained emotion categories
- Multi-entity extraction (people, organizations, dates, monetary values)

### Strict Tool Use

The notebook demonstrates validated tool parameters for:

- Flight booking with integer passenger counts
- Hotel reservations with constrained room types
- Weather queries with enum-validated temperature units
- Multi-tool workflows with consistent parameter types

### Real-World Performance Metrics

From our testing:

- Schema compliance across all test cases
- Zero JSON parsing errors with structured outputs enabled
- Consistent enum values matching defined constraints
- Proper type coercion (integers stay integers, not strings)

---

## 💡 Key Implementation Insights

### 1. API Selection Guide

| Feature | Converse API | InvokeModel API |
|---------|--------------|-----------------|
| Schema Location | `outputConfig.textFormat` | `output_config.format` |
| Schema Format | JSON string | JSON object |
| Tool Strict Flag | `toolSpec.strict` | `tools[].strict` |
| Best For | Multi-turn conversations | Single-turn, Claude-native |

### 2. Common Pitfalls to Avoid

❌ Don't forget `additionalProperties: false`
❌ Don't use unsupported schema features
❌ Don't ignore `stopReason` in responses

✅ Do validate schemas before deployment
✅ Do handle refusal and max_tokens edge cases
✅ Do leverage enum constraints for categorical data

### 3. Performance Optimization Tips

- **Schema Caching**: Compiled grammars are cached for 24 hours—reuse schemas across requests
- **First Request Latency**: Initial compilation may add latency; subsequent requests are fast
- **Schema Complexity**: Simpler schemas compile faster and are easier to maintain

---

## 📈 Business Impact

Based on the examples in our notebook, implementing structured outputs can deliver:

- **Development Time Savings**: Eliminate custom JSON validation and retry logic
- **Reduced Error Rates**: Zero schema violations means zero parsing failures
- **Cost Efficiency**: No wasted tokens on malformed responses requiring retries
- **Production Confidence**: Deploy AI applications knowing outputs are always valid

---

## 🛠️ Getting Started

### Prerequisites:

```bash
pip install boto3 --upgrade
```

### Amazon Bedrock Setup:

1. Ensure you have an AWS account with Amazon Bedrock access
2. Enable model access for Claude Sonnet 4.5, Claude Haiku 4.5, or Claude Opus 4.5
3. Configure AWS credentials (AWS CLI, environment variables, or IAM role)

### Run the Notebook:

1. Clone this repository
2. Open `structured_outputs_notebook.ipynb`
3. Update the `REGION` variable to your preferred AWS Region
4. Follow along with the examples

---

## 🎓 What You'll Learn

By exploring the notebook, you'll learn how to:

- Extract structured data from unstructured text without validation code
- Build reliable agentic workflows with validated tool parameters
- Handle nested objects and arrays in JSON schemas
- Use enum constraints for categorical classification
- Implement proper error handling for edge cases
- Choose between Converse API and InvokeModel API for your use case
- Optimize for schema caching and performance

---

## 🚀 Next Steps

After exploring this notebook, you can:

- Build zero-validation data extraction pipelines
- Create intelligent ticket classification systems with constrained categories
- Develop multi-step agentic workflows with reliable tool calls
- Design API integrations that trust model outputs
- Implement production-ready AI applications without retry logic

---

## 📚 Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Converse API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [InvokeModel API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html)
- [JSON Schema Specification](https://json-schema.org/)

---

Ready to build reliable AI applications with schema-compliant responses? Dive into the notebook and discover how structured outputs on Amazon Bedrock can transform your AI workflows! 🎯
