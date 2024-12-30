# Interacting with Amazon Nova-Lite with images

## Context

Amazon Nova Lite is a very low-cost multimodal model that is lightning fast for processing image, video, and text inputs to generate text output. Amazon Nova Lite can handle real-time customer interactions, document analysis, and visual question-answering tasks with high accuracy. The model processes inputs up to 300K tokens in length and can analyze multiple images or up to 30 minutes of video in a single request. Amazon Nova Lite also supports text and multimodal fine-tuning and can be optimized to deliver the best quality and costs for your use case with techniques such as model distillation.

Please see [Amazon Nova User Guide](https://docs.aws.amazon.com/nova/latest/userguide/what-is-nova.html) for more details on Nova model variants & their capabilities.


In this notebook, we will provide an image **"animal.jpg"** to the Nova Lite model with model identifier **"us.amazon.nova-lite-v1:0"** together with a text query asking about what is in the image. To do this, we will package the image and text into the **MessagesAPI** format and utilize the **invoke_model** function from **bedrock-runtime** within our helper function defined below to generate a response from Nova Lite.


## Setup Dependencies

This notebook uses boto3 module



```python
%pip install --upgrade pip
%pip install boto3 --upgrade --quiet
%pip install botocore --upgrade --quiet

```

Restart the kernel to use installed dependencies



```python
# restart kernel
from IPython.core.display import HTML
HTML("<script>Jupyter.notebook.kernel.restart()</script>")
```

Import Packages

1. Import the necessary libraries for creating the **bedrock-runtime** needed to invoke foundation models, formatting our JSON bodies, and converting our images into base64 encoding



```python
import boto3
import json
import base64
from PIL import Image


bedrock_client = boto3.client('bedrock-runtime',region_name='us-west-2')

```

## Build Helper Functions

These helper functions read images, encode them to base64, prepare payload following Nova supported format and invoke the model



```python
MODEL_ID = 'us.amazon.nova-lite-v1:0'


def read_and_encode_image(image_path, message_prompt):
    """
    Reads an image from a local file path and encodes it to a data URL.
    """
    with open(image_path, 'rb') as image_file:
        image_bytes = image_file.read()
        
    base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
    # Determine the image format (supported formats: jpg, jpeg, png, gif, webp)
    image_format = Image.open(image_path).format.lower()

    message_content = {
                    "image": {
                        "format": image_format,
                        "source": {"bytes": image_bytes},
                    }
                }
    
    return message_content

```


```python
def send_images_to_model_using_converse(system_prompt: str, image_list: list):
    """
    Sends images and a prompt to the model and returns the response in plain text.
    """
    content_list = []
    for img in image_list:
        message_content = read_and_encode_image(img['image_path'], img['message_prompt'])
        content_list.append(message_content)
        content_list.append({'text': img['message_prompt']})
    

    system = [ { "text": system_prompt } ]
    # Define a "user" message including both the image and a text prompt.
    messages = [
        {
            "role": "user",
            "content": content_list,
        }
    ]
    
    # Configure the inference parameters.
    inf_params = {"maxTokens": 500, "temperature": 1.0}

    # payload = {
    #     "schemaVersion": "messages-v1",
    #     "messages": messages,
    #     "system": system_list,
    #     "inferenceConfig": inf_params,
    # } 
    
    response = bedrock_client.converse(
        modelId=MODEL_ID, 
        messages=messages,
        system=system)
    
    # Print Response
    output_message = response['output']['message']
    print("\n[Response Content Text]")
    for content in output_message['content']:
        print(f"{content['text']}")


    token_usage = response['usage']
    print("\t--- Token Usage ---")
    print(f"\tInput tokens:  {token_usage['inputTokens']}")
    print(f"\tOutput tokens:  {token_usage['outputTokens']}")
    print(f"\tTotal tokens:  {token_usage['totalTokens']}")
    print(f"\tStop reason: {response['stopReason']}")

    return output_message
    
```

## Usage Examples

### Describe Image

In this use case, we provide an image of penguins and ask model to describe it.


```python
image_path = './images/animal.jpg'
Image.open(image_path).show()
```


```python
system_prompt = 'You are an expert wildlife explorer. When the user provides you with an image, provide a hilarious response'
image_list = [
    {
        "image_path": image_path, 
        "message_prompt": "What is in this image?"
    }]
response = send_images_to_model_using_converse(system_prompt, image_list)
```

Now that we have seen how to incoporate multimodal capabilties of Nova-Lite on Amazon Bedrock, try asking a different question about the image like "How many animals are shown in the image", or "What kind of location was this image taken at?" In addition to asking different questions, you can trying inputting other images and experimenting with the results.

### Vehicle Damage Assessment

Insurance agents need to assess damage to the vehicle by assessing images taken at the time of issuing policy and during claim processing. Nova Lite's vision capabilities can be used to assess damages


```python
image_path1 = './images/car_image_before.png'
image_path2 = './images/car_image_after.png'
Image.open(image_path1).show()
Image.open(image_path2).show()
```


```python
system_prompt = '''You are a helpful ai assistant for an insurance agent. Insurance agent has received a claim for a vehicle damage. This claim includes two images. One of the image was taken before the incident and another was taken after the incident.
Analyse these images and answer below questions:
1. describe if there is any damage to the vehicle
2. should insurance agent accept or reject the claim'''

image_list = [
    {
        "image_path": image_path1, 
        "message_prompt": "This image was taken when policy was issued"
    },
    {
        "image_path": image_path2, 
        "message_prompt": "This image was taken when claim was filed"
    }]
response = send_images_to_model_using_converse(system_prompt, image_list)
```

### Structured Data Extraction

As an ecommerce catalog manager, one needs to prepare product description and metadata. Nova Lite has capabilities that can extract structured data from product images. This metadata, in JSON format, can be used for facilitate seamless integration with other apps.



```python
system_prompt = """
You are a product analyst your job is to analyze the images provided and output the information in the exact JSON structure specified below. Ensure that you populate each field accurately based on the visible details in the image. If any information is not available or cannot be determined, use 'Unknown' for string fields and an empty array [] for lists.

Use the format shown exactly, ensuring all fields and values align with the JSON schema requirements.

Use this JSON schema:

{
  "title": "string",
  "description": "string",
  "category": {
    "type": "string",
    "enum": ["Electronics", "Furniture", "Luggage", "Clothing", "Appliances", "Toys", "Books", "Tools", "Other"]
  },
  "metadata": {
    "color": {
      "type": "array",
      "items": { "type": "string" }
    },
    "shape": {
      "type": "string",
      "enum": ["Round", "Square", "Rectangular", "Irregular", "Other"]
    },
    "condition": {
      "type": "string",
      "enum": ["New", "Like New", "Good", "Fair", "Poor", "Unknown"]
    },
    "material": {
      "type": "array",
      "items": { "type": "string" }
    },
    "brand": { "type": "string" }
  },
  "image_quality": {
    "type": "string",
    "enum": ["High", "Medium", "Low"]
  },
  "background": "string",
  "additional_features": {
    "type": "array",
    "items": { "type": "string" }
  }
}
"""
image_path = "./images/luggage.jpg"
Image.open(image_path).show()
image_list = [
    {
        "image_path": image_path, 
        "message_prompt": "product picture"
    }]
response = send_images_to_model_using_converse(system_prompt, image_list)
```


```python
image_path = "./images/dresser.jpg"
Image.open(image_path).show()
image_list = [
    {
        "image_path": image_path, 
        "message_prompt": "product picture"
    }]
response = send_images_to_model_using_converse(system_prompt, image_list)
```

### Chart Analysis

In this example, we provide a bar charts of sales and operating income of an organization. We are expecting the model to analyse these charts and share it's report.


```python
system_prompt= """

Analyze the attached image of the chart or graph. Your tasks are to:

Identify the type of chart or graph (e.g., bar chart, line graph, pie chart, etc.).
Extract the key data points, including labels, values, and any relevant scales or units.
Identify and describe the main trends, patterns, or significant observations presented in the chart.
Generate a clear and concise paragraph summarizing the extracted data and insights. The summary should highlight the most important information and provide an overview that would help someone understand the chart without seeing it.
Ensure that your summary is well-structured, accurately reflects the data, and is written in a professional tone.
"""
image_path = "./images/amazon_chart.png"  # Replace with your local image path

Image.open(image_path).show()
image_list = [
    {
        "image_path": image_path,
        "message_prompt": "chart picture"
    }]
response = send_images_to_model_using_converse(system_prompt, image_list)
```
