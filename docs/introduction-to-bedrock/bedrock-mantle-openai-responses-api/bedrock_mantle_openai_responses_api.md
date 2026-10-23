---
tags:
    - API-Usage-Example
---

!!! tip inline end "[Open in GitHub](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/introduction-to-bedrock/bedrock-mantle-openai-responses-api/bedrock_mantle_openai_responses_api.ipynb){:target=\"_blank\"}"

<h1>Use the OpenAI Responses API with Amazon Bedrock</h1>

<h2>Overview</h2>

This notebook shows how to run an existing OpenAI Python SDK workflow against Amazon Bedrock by changing the endpoint and API key. It provides a complete path from client setup to model discovery, non-streaming and streaming inference, stateful multi-turn conversation, background processing, and cleanup.

By the end of the notebook, you will be able to:

- connect the OpenAI Python SDK to the Amazon Bedrock `bedrock-mantle` endpoint;
- discover models available to your Amazon Bedrock project;
- choose explicitly between retained and non-retained response state;
- continue a conversation with `previous_response_id`;
- stream response text incrementally; and
- submit and poll a background response.

<h2>Context or Details about feature/use case</h2>

Amazon Bedrock exposes OpenAI-compatible APIs through the regional `bedrock-mantle` endpoint. Existing applications that use the OpenAI SDK can move their inference traffic to Amazon Bedrock while retaining the familiar SDK interface. The two required configuration changes are:

1. Set the base URL to `https://bedrock-mantle.<region>.api.aws/v1`.
2. Authenticate with an Amazon Bedrock API key.

The Responses API supports streaming, background processing, and stateful multi-turn interactions. Stateful responses are scoped to an Amazon Bedrock Project. When response storage is enabled, subsequent calls can reference an earlier response instead of resending the entire conversation.

This notebook uses `openai.gpt-oss-120b` as the default model because it is used in the Amazon Bedrock Responses API documentation. Set `BEDROCK_MODEL_ID` before running the notebook to use another model that supports the Responses API in your Region.

Useful references:

- [Amazon Bedrock endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html)
- [Inference using the Responses API](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)
- [API compatibility by model](https://docs.aws.amazon.com/bedrock/latest/userguide/models-api-compatibility.html)
- [Amazon Bedrock Projects](https://docs.aws.amazon.com/bedrock/latest/userguide/projects.html)

<h2>Prerequisites</h2>

Before running the notebook, you need:

- an AWS account with access to Amazon Bedrock;
- a Region where the `bedrock-mantle` endpoint and your selected model are available;
- an Amazon Bedrock API key generated in the same Region; and
- Python 3.10 or later.

For exploration, you can follow the [30-day API key quickstart](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-keys.html). For production workloads, prefer a [short-term Amazon Bedrock API key](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-reference.html) and least-privilege IAM permissions.

This notebook invokes a billable foundation model. Review [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) and stop after each example if you do not want to run the remaining calls.

<h2>Setup</h2>

Install the OpenAI Python SDK used by this example. Restart the kernel if the notebook environment asks you to do so.


```python
%pip install --quiet --upgrade -r requirements.txt
```

Import dependencies and define configuration. The API key is read from `OPENAI_API_KEY` when available; otherwise, the notebook requests it without displaying it. Do not paste a key directly into a notebook cell.


```python
import getpass
import os
import time

import openai
from openai import OpenAI


AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
BEDROCK_BASE_URL = f"https://bedrock-mantle.{AWS_REGION}.api.aws/v1"
REQUESTED_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "openai.gpt-oss-120b")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    api_key = getpass.getpass("Amazon Bedrock API key: ")

if not api_key:
    raise ValueError("An Amazon Bedrock API key is required.")

print(f"Region: {AWS_REGION}")
print(f"Endpoint: {BEDROCK_BASE_URL}")
print(f"Requested model: {REQUESTED_MODEL_ID}")
```

<h2>Your code with comments starts here</h2>

<h3>Create a Bedrock-backed OpenAI client</h3>

Pass the Amazon Bedrock base URL explicitly. This prevents an inherited `OPENAI_BASE_URL` value from accidentally routing the Bedrock API key to a different service.

The SDK retries transient connection errors and HTTP 429 responses. Keep the timeout finite so a notebook cell cannot wait forever.


```python
client = OpenAI(
    api_key=api_key,
    base_url=BEDROCK_BASE_URL,
    max_retries=3,
    timeout=60.0,
)

if "bedrock-mantle" not in str(client.base_url):
    raise RuntimeError("The OpenAI client is not configured for Amazon Bedrock.")

print("OpenAI client configured for Amazon Bedrock.")
```

<h3>Discover compatible models</h3>

The Models API returns models exposed to the current Amazon Bedrock Project. Validate the configured model rather than silently selecting another one, because API compatibility and regional availability vary by model.


```python
available_model_ids = sorted(model.id for model in client.models.list().data)

print(f"Discovered {len(available_model_ids)} model(s):")
for model_id in available_model_ids:
    print(f"- {model_id}")

if REQUESTED_MODEL_ID not in available_model_ids:
    raise ValueError(
        f"{REQUESTED_MODEL_ID!r} is not available from {BEDROCK_BASE_URL}. "
        "Set BEDROCK_MODEL_ID to a listed model that supports the Responses API."
    )

MODEL_ID = REQUESTED_MODEL_ID
```

<h3>Send a privacy-conscious, non-retained request</h3>

Amazon Bedrock follows the OpenAI Responses API default of `store=True`. This example sets `store=False` explicitly, which means Amazon Bedrock does not retain the request or response for later retrieval. Use this mode when your application manages conversation state itself or when retention is not appropriate.


```python
private_response = client.responses.create(
    model=MODEL_ID,
    input="In two sentences, explain what the Amazon Bedrock Mantle endpoint provides.",
    max_output_tokens=200,
    store=False,
)

print(private_response.output_text)
```

<h3>Create a stateful multi-turn conversation</h3>

To continue a conversation by response ID, both calls must use stored state. Stored responses are encrypted, scoped to the current Project, and retained in the source Region for up to 30 days.


```python
first_response = client.responses.create(
    model=MODEL_ID,
    input="Remember this deployment code: BLUE-742. Reply only with 'stored'.",
    max_output_tokens=50,
    store=True,
)
print(first_response.output_text)

follow_up_response = client.responses.create(
    model=MODEL_ID,
    previous_response_id=first_response.id,
    input="What deployment code did I give you? Reply with only the code.",
    max_output_tokens=50,
    store=True,
)
print(follow_up_response.output_text)
```

<h3>Retrieve stored response state</h3>

Stored responses can be retrieved by ID from the same Amazon Bedrock Project during their retention window.


```python
retrieved_response = client.responses.retrieve(follow_up_response.id)

print(f"Response ID: {retrieved_response.id}")
print(f"Status: {retrieved_response.status}")
print(f"Text: {retrieved_response.output_text}")
```

<h3>Stream response text</h3>

Streaming returns typed events as output becomes available. Process only `response.output_text.delta` events when the application needs the generated text.


```python
stream = client.responses.create(
    model=MODEL_ID,
    input="Give three concise reasons to use streaming inference.",
    max_output_tokens=200,
    store=False,
    stream=True,
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
print()
```

<h3>Run a response in the background</h3>

Background mode is useful for work that may outlive an interactive request. Submit the response, poll it with a bounded deadline, and handle every terminal status explicitly.


```python
background_response = client.responses.create(
    model=MODEL_ID,
    input="Create a five-point checklist for migrating an OpenAI SDK application to Amazon Bedrock.",
    max_output_tokens=300,
    store=True,
    background=True,
)

terminal_statuses = {"completed", "failed", "cancelled", "incomplete"}
deadline = time.monotonic() + 120

while background_response.status not in terminal_statuses:
    if time.monotonic() >= deadline:
        raise TimeoutError(
            f"Response {background_response.id} did not finish within 120 seconds."
        )
    time.sleep(2)
    background_response = client.responses.retrieve(background_response.id)
    print(f"Status: {background_response.status}")

if background_response.status != "completed":
    raise RuntimeError(
        f"Background response ended with status {background_response.status!r}."
    )

print(background_response.output_text)
```

<h3>Handle common API errors</h3>

The SDK exposes specific exception classes so applications can distinguish authentication failures, unsupported parameters, throttling, and network failures. Production applications should log request identifiers but must never log API keys or sensitive prompt content.


```python
def create_private_response(prompt: str) -> str:
    """Create a non-retained response with actionable error messages."""
    try:
        response = client.responses.create(
            model=MODEL_ID,
            input=prompt,
            max_output_tokens=200,
            store=False,
        )
        return response.output_text
    except openai.AuthenticationError as error:
        raise RuntimeError(
            "Authentication failed. Verify the Bedrock API key and its Region."
        ) from error
    except openai.RateLimitError as error:
        raise RuntimeError(
            "The request was throttled after SDK retries. Review Bedrock Mantle token quotas."
        ) from error
    except openai.BadRequestError as error:
        raise RuntimeError(
            "Bedrock rejected the request. Verify model and Responses API compatibility."
        ) from error
    except openai.APIConnectionError as error:
        raise RuntimeError(
            "Could not reach the Bedrock Mantle endpoint. Verify Region and network access."
        ) from error


print(create_private_response("Reply with exactly: Bedrock connection verified"))
```

<h2>Other Considerations or Advanced section or Best Practices</h2>

- **Retention:** `store=True` is the Responses API default. Amazon Bedrock retains the input and output for up to 30 days in the source Region. Set `store=False` on every request when retention is not required.
- **Project isolation:** Stored responses belong to an Amazon Bedrock Project and cannot be retrieved or continued from a different Project. Use Projects to separate applications, environments, access policies, and cost attribution.
- **Credentials:** Prefer short-term API keys for production. Never commit keys to notebooks, environment files, source control, or cell outputs.
- **Endpoint validation:** Pass `base_url` explicitly and verify that it contains `bedrock-mantle` before sending a request.
- **Model compatibility:** Not every Bedrock model supports the Responses API or every Responses capability. Consult the compatibility table before selecting a model.
- **Quotas:** Mantle inference has token quotas separate from the `bedrock-runtime` endpoint. Use exponential backoff and request quota increases before production traffic ramps up.
- **Network controls:** For private workloads, evaluate AWS PrivateLink and VPC endpoints to avoid routing inference traffic through a public internet gateway.
- **Observability:** Log latency, model ID, response status, token usage, Project, and request identifiers. Redact secrets and sensitive prompt or response content.

<h2>Next Steps</h2>

After completing this notebook:

1. Create separate Amazon Bedrock Projects for development, staging, and production.
2. Add approved tools and structured application-level validation around model output.
3. Compare the Responses API with Chat Completions, Converse, and InvokeModel for your workload.
4. Add application metrics, distributed tracing, cost allocation tags, and quota alarms.
5. Replace exploratory long-term keys with short-term credentials and least-privilege policies.

<h2>Cleanup</h2>

This notebook does not provision AWS infrastructure. Close the HTTP client and remove the in-memory key reference when you finish.

Stored responses created by this notebook remain scoped to the current Project until their retention period expires. If you created an exploratory API key specifically for this notebook, deactivate or delete it in the Amazon Bedrock console.


```python
client.close()
api_key = None

print("Client closed. Revoke any exploratory API key that is no longer needed.")
```
