---
tags:
    - API-Usage-Example
---
<!-- <h2> How to work with Converse API in Amazon Bedrock - Getting Started. </h2> -->

!!! tip inline end "[Open in github](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/introduction-to-bedrock/converse_api/01_converse_api.ipynb){:target="_blank"}"

<h2> Overview </h2>

In this notebook, we'll explore the basics of the Converse API in Amazon Bedrock. The Converse or ConverseStream API is a unified structured text API action that allows you simplifying the invocations to Bedrock LLMs, using a universal syntax and message structured prompts for any of the supported model providers.

To use the Converse API, you call the `Converse` or `ConverseStream` operations to send messages to a model. To call Converse, you require permission for the `bedrock:InvokeModel` operation. To call ConverseStream, you require permission for the `bedrock:InvokeModelWithResponseStream` operation.

<h2> Prerequisites </h2>

Before you can use Amazon Bedrock, you must carry out the following steps:

- Sign up for an AWS account (if you don't already have one) and IAM Role with the necessary permissions for Amazon Bedrock, see [AWS Account and IAM Role](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html#new-to-aws){:target="_blank"}.
- Request access to the foundation models (FM) that you want to use, see [Request access to FMs](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html#getting-started-model-access){:target="_blank"}. 
    
    We have used below Foundation Models in our examples in this Notebook in `us-west-2` (Oregon) region.
    
| Provider Name | Foundation Model Name | Model Id |
| ------- | ------------- | ------------- |
| Amazon | Titan Text G1 - Express  | amazon.titan-text-express-v1 |
| Amazon | Titan Text G1 - Lite | amazon.titan-text-lite-v1 |
| Anthropic | Claude 3.5 Sonnet  | anthropic.claude-3-5-sonnet-20240620-v1:0 |
| Anthropic | Claude 3 Haiku  | anthropic.claude-3-haiku-20240307-v1:0 |
| Cohere | Command R+ | cohere.command-r-plus-v1:0 |
| Cohere | Command R | cohere.command-r-v1:0 |
| Meta | Llama 3.1 70B Instruct | meta.llama3-1-70b-instruct-v1:0 |
| Meta | Llama 3.1 8B Instruct | meta.llama3-1-8b-instruct-v1:0 |
| Mistral AI | Mistral Large 2 (24.07) | mistral.mistral-large-2407-v1:0 |
| Mistral AI | Mixtral 8X7B Instruct | mistral.mixtral-8x7b-instruct-v0:1 |


<h2> Setup </h2>

!!! info
    This notebook should work well with the Data Science 3.0 kernel (Python 3.10 runtime) in SageMaker Studio

Run the cells in this section to install the packages needed by this notebook.


```python
!pip install --upgrade --force-reinstall boto3

import boto3
import sys
from botocore.exceptions import ClientError
print('Running boto3 version:', boto3.__version__)
```

Let's define the region and models to use. We can also setup our boto3 client.


```python
region = 'us-west-2'
print('Using region: ', region)

bedrock = boto3.client(
    service_name = 'bedrock-runtime',
    region_name = region,
    )

MODEL_IDS = [
    "amazon.titan-text-express-v1",
    "amazon.titan-text-lite-v1",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "cohere.command-r-plus-v1:0",
    "cohere.command-r-v1:0",
    "meta.llama3-1-70b-instruct-v1:0",
    "meta.llama3-1-8b-instruct-v1:0",
    "mistral.mistral-large-2407-v1:0",
    "mistral.mixtral-8x7b-instruct-v0:1"
    ]

```

<h2>Notebook/Code with comments</h2>

We're now ready to setup our Converse API action in Bedrock. Note that we use the same syntax for any model, including the messages-formatted prompts, and the inference parameters. Also note that we read the output in the same way independently of the model used.

Optionally, we could define additional model specific request fields that are not common across all providers. For more information on this check the Bedrock Converse API documentation.


<h3> Converse for one-shot invocations </h3>


```python
def invoke_bedrock_model(client, id, prompt, max_tokens=2000, temperature=0, top_p=0.9):
    response = ""
    try:
        response = client.converse(
            modelId=id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": max_tokens,
                "topP": top_p
            }
            #additionalModelRequestFields={
            #}
        )
    except Exception as e:
        print(e)
        result = "Model invocation error"
    try:
        result = response['output']['message']['content'][0]['text'] \
        + '\n--- Latency: ' + str(response['metrics']['latencyMs']) \
        + 'ms - Input tokens:' + str(response['usage']['inputTokens']) \
        + ' - Output tokens:' + str(response['usage']['outputTokens']) + ' ---\n'
        return result
    except Exception as e:
        print(e)
        result = "Output parsing error"
    return result
```

Finally, we can test our invocation.

In this example, we run the same prompt across all the text models supported in Bedrock by the time of writing this example.


```python
prompt = ("What is the capital of Italy?")
print(f'Prompt: {prompt}\n')

for i in MODEL_IDS:
    response = invoke_bedrock_model(bedrock, i, prompt)
    print(f'Model: {i}\n{response}')
```

<h3> ConverseStream for streaming invocations </h3>

We can also use the Converse API for streaming invocations. In this case we rely on the ConverseStream action.


```python
def invoke_bedrock_model_stream(client, id, prompt, max_tokens=2000, temperature=0, top_p=0.9):
    response = ""
    response = client.converse_stream(
        modelId=id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        inferenceConfig={
            "temperature": temperature,
            "maxTokens": max_tokens,
            "topP": top_p
        }
    )
    # Extract and print the response text in real-time.
    for event in response['stream']:
        if 'contentBlockDelta' in event:
            chunk = event['contentBlockDelta']
            sys.stdout.write(chunk['delta']['text'])
            sys.stdout.flush()
    return
```


```python
prompt = ("What is the capital of Italy?")
print(f'Prompt: {prompt}\n')

for i in MODEL_IDS:
    print(f'\n\nModel: {i}')
    invoke_bedrock_model_stream(bedrock, i, prompt)
```

<h3> Conversation with Text using Converse API and model specific parameters </h3>

In this example we will call the Converse operation with the Anthropic Claude 3.5 Sonnet model. We will send the input text, inference parameters, and additional parameters that are unique to the model. We will start a conversation by asking the model to create a list of songs, then continues the conversation by asking that the songs are by artists from the United Kingdom.


```python
def generate_conversation(bedrock_client,
                          model_id,
                          system_prompts,
                          messages):
    """
    Sends messages to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        system_prompts (JSON) : The system prompts for the model to use.
        messages (JSON) : The messages to send to the model.

    Returns:
        response (JSON): The conversation that the model generated.

    """

    print(f'Generating message with model {model_id}')

    # Inference parameters to use.
    temperature = 0.5
    top_k = 200

    # Base inference parameters to use which are common across all FMs.
    inference_config = {"temperature": temperature}

    # Additional inference parameters to use for Anthropic Claude Models.
    additional_model_fields = {"top_k": top_k}

    # Send the message.
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields
    )

    # Log token usage.
    token_usage = response['usage']
    print(f"Input tokens: {token_usage['inputTokens']}")
    print(f"Output tokens: {token_usage['outputTokens']}")
    print(f"Total tokens: {token_usage['totalTokens']}")
    print(f"Stop reason: {response['stopReason']}")

    return response
```


```python
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Setup the system prompts and messages to send to the model.
system_prompts = [{"text": "You are an app that creates playlists for a radio station that plays rock and pop music."
                    "Only return song names and the artist."}]
message_1 = {
    "role": "user",
    "content": [{"text": "Create a list of 3 pop songs."}]
}
message_2 = {
    "role": "user",
    "content": [{"text": "Make sure the songs are by artists from the United Kingdom."}]
}
messages = []

try:

    bedrock_client = boto3.client(service_name='bedrock-runtime')

    # Start the conversation with the 1st message.
    messages.append(message_1)
    response = generate_conversation(
        bedrock_client, model_id, system_prompts, messages)

    # Add the response message to the conversation.
    output_message = response['output']['message']
    messages.append(output_message)

    # Continue the conversation with the 2nd message.
    messages.append(message_2)
    response = generate_conversation(
        bedrock_client, model_id, system_prompts, messages)

    output_message = response['output']['message']
    messages.append(output_message)

    # Show the complete conversation.
    for message in messages:
        print(f"Role: {message['role']}")
        for content in message['content']:
            print(f"Text: {content['text']}")
        print()

except ClientError as err:
    message = err.response['Error']['Message']
    print(f"A client error occured: {message}")

else:
    print(
        f"Finished generating text with model {model_id}.")
```

<h3> Conversation with Image using Converse API </h3>

In this example we will send an image as part of a message and requests that the model describe the image. The example uses Converse operation and the Anthropic Claude 3.5 Sonnet model.

Sample image used in this example.

![Sample Image](assets/sample_image.jpg)


```python
def image_conversation(bedrock_client,
                          model_id,
                          input_text,
                          input_image):
    """
    Sends a message to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        input text : The input message.
        input_image : The input image.

    Returns:
        response (JSON): The conversation that the model generated.

    """

    print(f"Generating message with model {model_id}")

    # Message to send.

    with open(input_image, "rb") as f:
        image = f.read()

    message = {
        "role": "user",
        "content": [
            {
                "text": input_text
            },
            {
                    "image": {
                        "format": 'jpeg',
                        "source": {
                            "bytes": image
                        }
                    }
            }
        ]
    }

    messages = [message]

    # Send the message.
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages
    )

    return response
```


```python
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
input_text = "What's in this image?"
input_image = "assets/sample_image.jpg"

try:

    bedrock_client = boto3.client(service_name="bedrock-runtime")

    response = image_conversation(
        bedrock_client, model_id, input_text, input_image)

    output_message = response['output']['message']

    print(f"Role: {output_message['role']}")

    for content in output_message['content']:
        print(f"Text: {content['text']}")

    token_usage = response['usage']
    print(f"Input tokens:  {token_usage['inputTokens']}")
    print(f"Output tokens:  {token_usage['outputTokens']}")
    print(f"Total tokens:  {token_usage['totalTokens']}")
    print(f"Stop reason: {response['stopReason']}")

except ClientError as err:
    message = err.response['Error']['Message']
    logger.error("A client error occurred: %s", message)
    print(f"A client error occured: {message}")

else:
    print(
        f"Finished generating text with model {model_id}.")
```

<h3>Conversation with Document using Converse API</h3>


In this example, we will send a document as part of a message and requests that the model describe the contents of the document. The example uses Converse operation and the Meta Llama 3.1 8B Instruct Model.


```python
def document_conversation(bedrock_client,
                     model_id,
                     input_text,
                     input_document):
    """
    Sends a message to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        input text : The input message.
        input_document : The input document.

    Returns:
        response (JSON): The conversation that the model generated.

    """

    print(f"Generating message with model {model_id}")

    # Message to send.
    
    with open(input_document, "rb") as f:
        doc_bytes = f.read()

    message = {
        "role": "user",
        "content": [
            {
                "text": input_text
            },
            {
                "document": {
                    "name": "MyDocument",
                    "format": "pdf",
                    "source": {
                        "bytes": doc_bytes
                    }
                }
            }
        ]
    }

    messages = [message]

    # Send the message.
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages
    )

    return response
```


```python
model_id = "meta.llama3-1-8b-instruct-v1:0" 
input_text = "What's in this document?"
input_document = 'assets/2022-Shareholder-Letter.pdf'

try:

    bedrock_client = boto3.client(service_name="bedrock-runtime")

    response = document_conversation(
        bedrock_client, model_id, input_text, input_document)

    output_message = response['output']['message']

    print(f"Role: {output_message['role']}")

    for content in output_message['content']:
        print(f"Text: {content['text']}")

    token_usage = response['usage']
    print(f"Input tokens:  {token_usage['inputTokens']}")
    print(f"Output tokens:  {token_usage['outputTokens']}")
    print(f"Total tokens:  {token_usage['totalTokens']}")
    print(f"Stop reason: {response['stopReason']}")

except ClientError as err:
    message = err.response['Error']['Message']
    print(f"A client error occured: {message}")

else:
    print(
        f"Finished generating text with model {model_id}.")
```

<h2>Next steps</h2>

Now that we have seen the Converse API allow us to easily run the invocations with the same syntax across all the models, you can learn

- How to do [function calling with the Converse API](../../agents/function-calling/function_calling_with_converse/function_calling_with_converse.md)
- How to work with [Converse API and Amazon Bedrock Guardrails](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/responsible_ai/){:target="_blank"}


<h2>Clean up</h2>

This notebook does not require any cleanup or additional deletion of resources.
