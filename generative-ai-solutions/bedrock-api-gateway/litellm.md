# Call Bedrock with OpenAI Proxy (LiteLLM)

Call Bedrock with an openai-compatible proxy with [LiteLLM](https://github.com/BerriAI/litellm). 

# AWS Bedrock
Anthropic, Amazon Titan, A121 LLMs are Supported on Bedrock

LiteLLM requires `boto3` to be installed on your system for Bedrock requests
```shell
pip install boto3>=1.28.57
```

## Required Environment Variables
```python
os.environ["AWS_ACCESS_KEY_ID"] = ""  # Access key
os.environ["AWS_SECRET_ACCESS_KEY"] = "" # Secret access key
os.environ["AWS_REGION_NAME"] = "" # us-east-1, us-east-2, us-west-1, us-west-2
```

## OpenAI Proxy Usage 

Here's how to call Anthropic with the LiteLLM Proxy Server

### 1. Setup config.yaml

```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      aws_access_key_id: os.environ/CUSTOM_AWS_ACCESS_KEY_ID
      aws_secret_access_key: os.environ/CUSTOM_AWS_SECRET_ACCESS_KEY
      aws_region_name: os.environ/CUSTOM_AWS_REGION_NAME
```

All possible auth params: 

```
aws_access_key_id: Optional[str],
aws_secret_access_key: Optional[str],
aws_session_token: Optional[str],
aws_region_name: Optional[str],
aws_session_name: Optional[str],
aws_profile_name: Optional[str],
aws_role_name: Optional[str],
aws_web_identity_token: Optional[str],
```

### 2. Start the proxy 

```bash
litellm --config /path/to/config.yaml
```
### 3. Test it


#### Curl Request

```shell
curl --location 'http://0.0.0.0:4000/chat/completions' \
--header 'Content-Type: application/json' \
--data ' {
      "model": "bedrock-claude",
      "messages": [
        {
          "role": "user",
          "content": "what llm are you"
        }
      ]
    }
'
```

#### OpenAI Python SDK

```python
import openai
client = openai.OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)

# request sent to model set on litellm proxy, `litellm --model`
response = client.chat.completions.create(model="bedrock-claude", messages = [
    {
        "role": "user",
        "content": "this is a test request, write a short poem"
    }
])

print(response)

```

#### Langchain

```python
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import HumanMessage, SystemMessage

chat = ChatOpenAI(
    openai_api_base="http://0.0.0.0:4000", # set openai_api_base to the LiteLLM Proxy
    model = "bedrock-claude",
    temperature=0.1
)

messages = [
    SystemMessage(
        content="You are a helpful assistant that im using to make a test request to."
    ),
    HumanMessage(
        content="test from litellm. tell me why it's amazing in 1 sentence"
    ),
]
response = chat(messages)

print(response)
```


## Set temperature, top p, etc.

**Set on yaml**

```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      temperature: <your-temp>
      top_p: <your-top-p>
```

**Set on request**

```python

import openai
client = openai.OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)

# request sent to model set on litellm proxy, `litellm --model`
response = client.chat.completions.create(model="bedrock-claude", messages = [
    {
        "role": "user",
        "content": "this is a test request, write a short poem"
    }
],
temperature=0.7,
top_p=1
)

print(response)

```

## Pass provider-specific params 

If you pass a non-openai param to litellm, we'll assume it's provider-specific and send it as a kwarg in the request body. [See more](../completion/input.md#provider-specific-params)


**Set on yaml**

```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      top_k: 1 # 👈 PROVIDER-SPECIFIC PARAM
```

**Set on request**

```python

import openai
client = openai.OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)

# request sent to model set on litellm proxy, `litellm --model`
response = client.chat.completions.create(model="bedrock-claude", messages = [
    {
        "role": "user",
        "content": "this is a test request, write a short poem"
    }
],
temperature=0.7,
extra_body={
    top_k=1 # 👈 PROVIDER-SPECIFIC PARAM
}
)

print(response)

```

## Usage - Function Calling 

LiteLLM uses Bedrock's Converse API for making tool calls

```python
from openai import OpenAI

client = OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)


tools = [
  {
    "type": "function",
    "function": {
      "name": "get_current_weather",
      "description": "Get the current weather in a given location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA",
          },
          "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
      },
    }
  }
]
messages = [{"role": "user", "content": "What's the weather like in Boston today?"}]
completion = client.chat.completions.create(
  model="bedrock-claude",
  messages=messages,
  tools=tools,
  tool_choice="auto"
)

print(completion)

```


## Usage - Vision 

```python
from openai import OpenAI

client = OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)

response = client.chat.completions.create(
    model="bedrock-claude",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                },
            ],
        }
    ],
    max_tokens=300,
)

print(response.choices[0])

```


## Usage - Streaming
```python
from openai import OpenAI
client = OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)


completion = client.chat.completions.create(
  model="bedrock-claude",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  stream=True
)

for chunk in completion:
  print(chunk.choices[0].delta)

```

#### Example Streaming Output Chunk
```json
{
  "choices": [
    {
      "finish_reason": null,
      "index": 0,
      "delta": {
        "content": "ase can appeal the case to a higher federal court. If a higher federal court rules in a way that conflicts with a ruling from a lower federal court or conflicts with a ruling from a higher state court, the parties involved in the case can appeal the case to the Supreme Court. In order to appeal a case to the Sup"
      }
    }
  ],
  "created": null,
  "model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
  "usage": {
    "prompt_tokens": null,
    "completion_tokens": null,
    "total_tokens": null
  }
}
```

## Boto3 - Authentication

### Passing credentials as parameters - Completion()
Pass AWS credentials as parameters to litellm.completion

```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      aws_access_key_id:""
      aws_secret_access_key:""
      aws_region_name:""
```

### SSO Login (AWS Profile)
- Set `AWS_PROFILE` environment variable
- Make bedrock completion call

```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
```

or pass `aws_profile_name`:

```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      aws_profile_name="dev-profile",
```


### STS based Auth

- Set `aws_role_name` and `aws_session_name` in yaml

Make the bedrock completion call

```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      max_tokens: 10,
      temperature: 0.1,
      aws_role_name: "aws_role_name",
      aws_session_name: "my-test-session",
```


If you also need to dynamically set the aws user accessing the role, add the additional args in the yaml


```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      max_tokens: 10,
      temperature: 0.1,
      aws_region_name: aws_region_name,
      aws_access_key_id: aws_access_key_id,
      aws_secret_access_key: aws_secret_access_key,
      aws_role_name: aws_role_name,
      aws_session_name: "my-test-session",
```


## Provisioned throughput models
To use provisioned throughput Bedrock models pass 
- `model=bedrock/<base-model>`, example `model=bedrock/anthropic.claude-v2`. Set `model` to any of the [Supported AWS models](#supported-aws-bedrock-models)
- `model_id=provisioned-model-arn` 


```yaml
model_list:
  - model_name: bedrock-claude
    litellm_params:
      model: bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0
      model_id="provisioned-model-arn",
```


## Supported AWS Bedrock Models
Here's an example of using a bedrock model with LiteLLM. For a complete list, refer to the [model cost map](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json)

| Model Name                 | Command                                                          |
|----------------------------|------------------------------------------------------------------|
| Anthropic Claude-V3.5 Sonnet    | `completion(model='bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Anthropic Claude-V3  sonnet    | `completion(model='bedrock/anthropic.claude-3-sonnet-20240229-v1:0', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Anthropic Claude-V3 Haiku     | `completion(model='bedrock/anthropic.claude-3-haiku-20240307-v1:0', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Anthropic Claude-V3 Opus     | `completion(model='bedrock/anthropic.claude-3-opus-20240229-v1:0', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Anthropic Claude-V2.1      | `completion(model='bedrock/anthropic.claude-v2:1', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Anthropic Claude-V2        | `completion(model='bedrock/anthropic.claude-v2', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Anthropic Claude-Instant V1 | `completion(model='bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0', messages=messages)` | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Meta llama3-70b        | `completion(model='bedrock/meta.llama3-70b-instruct-v1:0', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Meta llama3-8b | `completion(model='bedrock/meta.llama3-8b-instruct-v1:0', messages=messages)` | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`           |
| Amazon Titan Lite          | `completion(model='bedrock/amazon.titan-text-lite-v1', messages=messages)` | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| Amazon Titan Express       | `completion(model='bedrock/amazon.titan-text-express-v1', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| Cohere Command             | `completion(model='bedrock/cohere.command-text-v14', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| AI21 J2-Mid                | `completion(model='bedrock/ai21.j2-mid-v1', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| AI21 J2-Ultra              | `completion(model='bedrock/ai21.j2-ultra-v1', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| AI21 Jamba-Instruct              | `completion(model='bedrock/ai21.jamba-instruct-v1:0', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| Meta Llama 2 Chat 13b      | `completion(model='bedrock/meta.llama2-13b-chat-v1', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| Meta Llama 2 Chat 70b      | `completion(model='bedrock/meta.llama2-70b-chat-v1', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| Mistral 7B Instruct        | `completion(model='bedrock/mistral.mistral-7b-instruct-v0:2', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |
| Mixtral 8x7B Instruct      | `completion(model='bedrock/mistral.mixtral-8x7b-instruct-v0:1', messages=messages)`   | `os.environ['AWS_ACCESS_KEY_ID']`, `os.environ['AWS_SECRET_ACCESS_KEY']`, `os.environ['AWS_REGION_NAME']` |

## Bedrock Embedding

### API keys
This can be set as env variables or passed as **params to litellm.embedding()**
```python
import os
os.environ["AWS_ACCESS_KEY_ID"] = ""        # Access key
os.environ["AWS_SECRET_ACCESS_KEY"] = ""    # Secret access key
os.environ["AWS_REGION_NAME"] = ""           # us-east-1, us-east-2, us-west-1, us-west-2
```

### Usage

1. Setup config.yaml 
```yaml
model_list:
  - model_name: bedrock-titan-embeddings
    litellm_params:
      model: bedrock/amazon.titan-embed-text-v1
```

2. Test it!
```python
from openai import OpenAI
client = OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)


client.embeddings.create(
  model="bedrock-titan-embeddings",
  input="The food was delicious and the waiter...",
)
```

## Supported AWS Bedrock Embedding Models

| Model Name           | Function Call                               |
|----------------------|---------------------------------------------|
| Titan Embeddings V2 | `embedding(model="bedrock/amazon.titan-embed-text-v2:0", input=input)` |
| Titan Embeddings - V1 | `embedding(model="bedrock/amazon.titan-embed-text-v1", input=input)` |
| Cohere Embeddings - English | `embedding(model="bedrock/cohere.embed-english-v3", input=input)` |
| Cohere Embeddings - Multilingual | `embedding(model="bedrock/cohere.embed-multilingual-v3", input=input)` |

## Image Generation
Use this for stable diffusion on bedrock


### Usage

1. Setup config.yaml
```yaml
model_list:
  - model_name: bedrock-stability
    litellm_params:
      model: bedrock/stability.stable-diffusion-xl-v0
```

2. Test it! 
```python
from openai import OpenAI
client = OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)


client.images.generate(
  model="bedrock-stability",
  prompt="A cute baby sea otter",
)
```

**Set optional params**
```python

from openai import OpenAI
client = OpenAI(
    api_key="anything",
    base_url="http://0.0.0.0:4000"
)


client.images.generate(
  model="bedrock-stability",
  prompt="A cute baby sea otter",
  size="128x512" ### OPENAI-COMPATIBLE ###
  extra_body={
    "seed": 30 ### PROVIDER-SPECIFIC ###
  }
)
```

## Supported AWS Bedrock Image Generation Models

| Model Name           | Function Call                               |
|----------------------|---------------------------------------------|
| Stable Diffusion - v0 | `embedding(model="bedrock/stability.stable-diffusion-xl-v0", prompt=prompt)` |
| Stable Diffusion - v0 | `embedding(model="bedrock/stability.stable-diffusion-xl-v1", prompt=prompt)` |