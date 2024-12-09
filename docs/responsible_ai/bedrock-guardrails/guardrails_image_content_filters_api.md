## Amazon Bedrock Guardrails Image Content Filters - Examples using the Python SDK

----------------------------
### Overview

Amazon Bedrock Guardrails evaluates user inputs and FM responses based on use case specific policies, and provides an additional layer of safeguards regardless of the underlying FM. Guardrails can be applied across all large language models (LLMs) on Amazon Bedrock, including fine-tuned models. Customers can create multiple guardrails, each configured with a different combination of controls, and use these guardrails across different applications and use cases. 

Amazon Bedrock Guardrails can block inappropriate or harmful images by enabling image as a modality while configuring content filters within a guardrail. 

Currently in preview, the detection and blocking of harmful images is supported for Hate, Insults, Sexual, and Violence categories within content filters, and for images without any text in them. In addition to text, users can select the image modality for the above categories within content filters while creating a guardrail, and set the respective filtering strength to NONE, LOW, MEDIUM, or HIGH. These thresholds will be common to both text and image content for these categories, if both text and image are selected. Guardrails will evaluate images sent as an input by users, or generated as output from the model responses. 

The four supported categories for detection of harmful image content are described below. 
Hate - Describes contents that discriminate, criticize, insult, denounce, or dehumanize a person or group on the basis of an identity (such as race, ethnicity, gender, religion, sexual orientation, ability, and national origin). It also includes graphic and real-life visual content displaying symbols of hate groups, hateful symbols, and imagery associated with various organizations promoting discrimination, racism, and intolerance.

Insults - Describes content that includes demeaning, humiliating, mocking, insulting, or belittling language. This type of language is also labeled as bullying. It also encompasses various forms of rude, disrespectful or offensive hand gestures intended to express contempt, anger, or disapproval.

Sexual - Describes content that indicates sexual interest, activity, or arousal using direct or indirect references to body parts, physical traits, or sex. It also includes images displaying private parts and sexual activity involving intercourse. This category also encompasses cartoons, anime, drawings, sketches, and other illustrated content with sexual themes.

Violence - Describes content that includes glorification of or threats to inflict physical pain, hurt, or injury toward a person, group or thing.

Please refer to the public documentation for more details on supported regions and Bedrock Foundation Models supported with Guardrail Image Content Filters.

**Limitations** : 
1. The support to detect and block inappropriate and harmful images in content filters is currently in preview and not recommended for production workloads.
2. This capability is supported for only images and not supported for images with embedded video content.
3. This capability is only supported for Hate, Insults, Sexual, and Violence categories within content filters and not for any other categories including misconduct and prompt attacks.
4. Users can upload images with sizes up to a maximum of 4 MB, with a maximum of 20 images for a single request.
5. Only PNG and JPEG formats are supported for image content.



### Start by installing the dependencies to ensure we have a recent version


```python
%pip install --upgrade --force-reinstall boto3

import boto3
import botocore
import json
import base64
import os
import random
import string

from datetime import datetime
print(boto3.__version__)
```

### Let's define the region and model to use. We will also setup our boto3 client


```python
region = 'us-west-2' #Please update the region based on your region use.
print('Using region: ', region)

client = boto3.client(service_name = 'bedrock', region_name=region)
```

##### Lets create a utility function to handle datetime objects during JSON serialization


```python
def datetime_handler(obj):
    """Handler for datetime objects during JSON serialization"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
```

#### Creating a Guardrail with content filters for images

While creating a new guardrail or updating an existing guardrail, users will now see an option to select image (in preview) in addition to the existing text option. The image option is available for Hate, Insults, Sexual, or Violence categories. (Note: By default, the text option is enabled, and the image option needs to be explicitly enabled. Users can choose both text and image or either one of them depending on the use case.
(NOTE: This will not be enabled by default for existing Guardrails)

### Filter classification and blocking levels
Filtering is done based on the confidence classification of user inputs and FM responses. All user inputs and model responses are classified across four strength levels - None, Low, Medium, and High. The filter strength determines the sensitivity of filtering harmful content. As the filter strength is increased, the likelihood of filtering harmful content increases and the probability of seeing harmful content in your application decreases. When both image and text options are selected, the same filter strength is applied to both modalities for a particular category.


Lets create a new guardrail called **image-content-filters** that will detect and block harmful images for for Hate, Insults, Sexual, or Violence categories. We will set the filter strength for input and output as HIGH for Sexual, Violence, Hate and Insults. For Misconduct we will start with MEDIUM as the filter strength. We will also enable the Text based filters for these categories along with enabling the prompt attach filter.


```python
try:
    create_guardrail_response = client.create_guardrail(
        name='image-content-filters',
        description='Detect and block harmful images.',
        contentPolicyConfig={
            'filtersConfig': [
                {
                    'type': 'SEXUAL',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'VIOLENCE',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'HATE',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'INSULTS',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'MISCONDUCT',
                    'inputStrength': 'MEDIUM',
                    'outputStrength': 'MEDIUM',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                },
                {
                    'type': 'PROMPT_ATTACK',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'NONE',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                }
            ]
        },
        blockedInputMessaging='Sorry, the model cannot answer this question. Please review the trace for more details.',
        blockedOutputsMessaging='Sorry, the model cannot answer this question. Please review the trace for more details.',
    )

    print("Successfully created guardrail with details:")
    print(json.dumps(create_guardrail_response, indent=2, default=datetime_handler))
except botocore.exceptions.ClientError as err:
    print("Failed while calling CreateGuardrail API with RequestId = " + err.response['ResponseMetadata']['RequestId'])
    raise err
```

#### Getting a Guardrail, creating a version and listing all the versions and Drafts

##### Lets review the DRAFT version of our guardrail


```python
#This will provide all the data about the DRAFT version we have
get_response = client.get_guardrail(
    guardrailIdentifier=create_guardrail_response['guardrailId'],
    guardrailVersion='DRAFT'
)

get_response['createdAt'] = get_response['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
get_response['updatedAt'] = get_response['updatedAt'].strftime('%Y-%m-%d %H:%M:%S')
print(json.dumps(get_response, indent=2, default=datetime_handler))

```

##### Lets create a new version for our Guardrail


```python
version_response = client.create_guardrail_version(
    guardrailIdentifier=create_guardrail_response['guardrailId'],
    description='Version of Guardrail'
)

print(json.dumps(version_response, indent=2))
```

##### Lets list all versions of our guardrail
- To list the DRAFT version of all your guardrails, don’t specify the guardrailIdentifier field. 
- To list all versions of a guardrail, specify the ARN of the guardrail in the guardrailIdentifier field.


```python
list_guardrails_response = client.list_guardrails(
    guardrailIdentifier=create_guardrail_response['guardrailArn'],
    maxResults=5)

print(json.dumps(list_guardrails_response, indent=2, default=datetime_handler))
```

#### Updating a Guardrail 

Let's update the Guardrail but this time modify one of our content filters. We will update the filter strength for Misconduct to HIGH


```python
# Updating the Guardrail by providing another adjusting our Content Filter strength 

try:
    update_guardrail_response = client.update_guardrail(
        guardrailIdentifier=create_guardrail_response['guardrailArn'],
        name='image-content-filters',
        description='Detect and block harmful images.',
        contentPolicyConfig={
            'filtersConfig': [
                {
                    'type': 'SEXUAL',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'VIOLENCE',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'HATE',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'INSULTS',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT', 'IMAGE'],
                    'outputModalities': ['TEXT', 'IMAGE']
                },
                {
                    'type': 'MISCONDUCT',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'HIGH',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                },
                {
                    'type': 'PROMPT_ATTACK',
                    'inputStrength': 'HIGH',
                    'outputStrength': 'NONE',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                }
            ]
        },     
        blockedInputMessaging='Sorry, the model cannot answer this question. Please review the trace for more details.',
        blockedOutputsMessaging='Sorry, the model cannot answer this question. Please review the trace for more details.',
    )
    print("Successfully updated the guardrail with details:")
    print(json.dumps(update_guardrail_response, indent=2, default=datetime_handler))
except botocore.exceptions.ClientError as err:
    print("Failed while calling UpdateGuardrail API with RequestId = " + err.response['ResponseMetadata']['RequestId'])
    raise err




```

##### Lets review all our updates.


```python

get_response = client.get_guardrail(
    guardrailIdentifier=create_guardrail_response['guardrailId'],
    guardrailVersion='DRAFT'
)
print(json.dumps(get_response, indent=2, default=datetime_handler))
```

##### Lets create a new version from our updates.


```python
version_response = client.create_guardrail_version(
    guardrailIdentifier=create_guardrail_response['guardrailId'],
    description='Version of Guardrail that has a HIGH MisConduct Filter'
)

print(json.dumps(version_response, indent=2, default=datetime_handler))
```

##### Lets list all versions of our guardrail.


```python
list_guardrails_response = client.list_guardrails(
    guardrailIdentifier=create_guardrail_response['guardrailArn'],
    maxResults=5)

print(json.dumps(list_guardrails_response, indent=2, default=datetime_handler))
```

### Testing our Guardrail

##### Lets test our guardrail using the above sample image and call Bedrock using the converse API.

##### In the below example we will send the sample image as part of a message and request the model to describe the image. We will use the Converse operation and the Anthropic Claude 3.5 Sonnet model.


```python
import botocore
from typing import Dict, Any

#import the run-time client
bedrock_runtime = boto3.client(service_name = 'bedrock-runtime', region_name=region)

def process_image_with_bedrock(
    image_path: str,
    model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
    input_text: str = "Hi, can you describe this image to me?"
) -> Dict[str, Any]:
    """
    Process an image using Amazon Bedrock with error handling and optimized structure.
    
    Args:
        image_path (str): Path to the image file
        model_id (str): Bedrock model ID
        input_text (str): Text prompt for the image
        
    Returns:
        Dict[str, Any]: Processing results including response and metrics
    """
    try:
        # Use context manager for automatic file closing
        with open(image_path, "rb") as f:
            content_image = f.read()    

        # Structured message creation
        message = {
            "role": "user",
            "content": [
                {"text": input_text},                
                {
                    "image": {
                        "format": "jpeg",
                        "source": {"bytes": content_image}
                    }
                }            
            ]
        }

        guardrailIdentifier = create_guardrail_response['guardrailId']
        guardrail_config = {
            "guardrailIdentifier": guardrailIdentifier,
            "guardrailVersion": "2",
            "trace": "enabled"
        }

        # Make API call
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=[message],
            guardrailConfig=guardrail_config
        )

        # Extract response data
        output_message = response['output']['message']
        token_usage = response['usage']

        # Print formatted results
        print_response_details(output_message, token_usage, response['stopReason'], model_id)

        return response

    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        raise
    except botocore.exceptions.ClientError as err:
        print(f"A client error occurred: {err.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise

def print_response_details(output_message: Dict, token_usage: Dict, stop_reason: str, model_id: str) -> None:
    """Print formatted response details."""
    print(f"Role: {output_message['role']}")
    
    for content in output_message['content']:
        print(f"Text: {content['text']}")

    print(f"Input tokens:  {token_usage['inputTokens']}")
    print(f"Output tokens: {token_usage['outputTokens']}")
    print(f"Total tokens: {token_usage['totalTokens']}")
    print(f"Stop reason: {stop_reason}")
    print(f"Finished generating text with model {model_id}")

# Usage
if __name__ == "__main__":
    image_path = 'images/test-image1.jpg'
    process_image_with_bedrock(image_path)

```

## Using ApplyGuardrail API to test the Guardrail 
The `ApplyGuardrail` API allows customers to assess any text and image using their pre-configured Bedrock Guardrails, without invoking the foundation models.

##### Lets test the guardrail using the **ApplyGuardrail** API. We will use the same image for our test.


```python
guardrailIdentifier = create_guardrail_response['guardrailId']

import boto3
import botocore
import json

guardrailVersion ="2"
content_source = "INPUT"
image_path = "images/test-image1.jpg"
region = "us-west-2"

with open(image_path, 'rb') as image:
    image_bytes = image.read()

content = [
    {
        "text": {
            "text": "Hi, can you describe this image to me?"
        }
    },
    {
        "image": {
            "format": "jpeg",
            "source": {
                "bytes": image_bytes
            }
        }
    }
]

bedrock_runtime = boto3.client(service_name = 'bedrock-runtime', region_name=region)
try:
    print("Making a call to ApplyGuardrail API now")
    response = bedrock_runtime.apply_guardrail(
        guardrailIdentifier=guardrailIdentifier,
        guardrailVersion=guardrailVersion,
        source=content_source,
        content=content
    )
    print("Received response from ApplyGuardrail API:")
    action = response.get("action", "")
    assessments = response.get("assessments", [])
    print("action:", action)
    print("assessments:", json.dumps(assessments, indent=2))

except botocore.exceptions.ClientError as err:
    print("Failed while calling ApplyGuardrail API with RequestId = " + err.response['ResponseMetadata']['RequestId'])
    raise err
```

### Guardrails with Image Generation
##### Let's test our Guardrail with an Image generation use case. We will generate an image using the "Stability" model on Bedrock using the InvokeModel API and the guardrail.


```python
guardrailIdentifier = create_guardrail_response['guardrailId']
guardrailVersion ="2"

model_id = 'stability.sd3-large-v1:0'
output_images_folder = 'images/output'

body = json.dumps(
    {
        "prompt": "A Gun", #  for image generation ("A gun" should get blocked by violence)
        "output_format": "jpeg"
    }
)

bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
try:
    print("Making a call to InvokeModel API for model: {}".format(model_id))
    response = bedrock_runtime.invoke_model(
        body=body,
        modelId=model_id,
        trace='ENABLED',
        guardrailIdentifier=guardrailIdentifier,
        guardrailVersion=guardrailVersion
    )
    response_body = json.loads(response.get('body').read())
    print("Received response from InvokeModel API (Request Id: {})".format(response['ResponseMetadata']['RequestId']))
    if 'images' in response_body and len(response_body['images']) > 0:
        os.makedirs(output_images_folder, exist_ok=True)
        images = response_body["images"]
        for image in images:
            image_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            image_file = os.path.join(output_images_folder, "generated-image-{}.jpg".format(image_id))
            print("Saving generated image {} at {}".format(image_id, image_file))
            with open(image_file, 'wb') as image_file_descriptor:
                image_file_descriptor.write(base64.b64decode(image.encode('utf-8')))
    else:
        print("No images generated from model")
    guardrail_trace = response_body['amazon-bedrock-trace']['guardrail']
    guardrail_trace['modelOutput'] = ['<REDACTED>']
    print(guardrail_trace['outputs'])
    print("\nGuardrail Trace: {}".format(json.dumps(guardrail_trace, indent=2)))
except botocore.exceptions.ClientError as err:
    print("Failed while calling InvokeModel API with RequestId = {}".format(err.response['ResponseMetadata']['RequestId']))
    raise err

```
