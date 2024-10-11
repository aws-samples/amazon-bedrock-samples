# Retrieval Augmented Generation with Amazon Bedrock - Workshop Setup

> *PLEASE NOTE: This notebook should work well with the **`Data Science 3.0`** kernel in SageMaker Studio*

---

In this notebook, we will set up the [`boto3` Python SDK](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) to work with [Amazon Bedrock](https://aws.amazon.com/bedrock/) Foundation Models as well as install extra dependencies needed for this workshop. Specifically, we will be using the following libraries throughout the workshop...

* [LangChain](https://python.langchain.com/docs/get_started/introduction) for large language model (LLM) utilities
* [FAISS](https://github.com/facebookresearch/faiss) for vector similarity searching
* [Streamlit](https://streamlit.io/) for user interface (UI) building

---
## Install External Dependencies

The code below will install the rest of the Python packages required for the workshop.


```python
%pip install --upgrade pip
%pip install --quiet -r ../requirements.txt
```

    Defaulting to user installation because normal site-packages is not writeable
    Requirement already satisfied: pip in /Users/sergncp/Library/Python/3.9/lib/python/site-packages (24.2)
    Note: you may need to restart the kernel to use updated packages.
    Note: you may need to restart the kernel to use updated packages.



```python
#!pip install boto3 --upgrade
#!pip install awscli --upgrade
```

---
## Create the `boto3` client connection to Amazon Bedrock

Interaction with the Bedrock API is done via the AWS SDK for Python: [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html).

As you are running this notebook from [Amazon Sagemaker Studio](https://aws.amazon.com/sagemaker/studio/) and your Sagemaker Studio [execution role](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html) has permissions to access Bedrock you can just run the cells below as-is in order to create a connection to Amazon Bedrock. This is also the case if you are running these notebooks from a computer whose default AWS credentials have access to Bedrock.


```python
import boto3
import os
from IPython.display import Markdown, display

region = os.environ.get("AWS_REGION")
bedrock_service = boto3.client(
    service_name='bedrock',
    region_name=region,
)
print(boto3.__version__)
```

    1.35.16


#### Validate the connection

We can check the client works by trying out the `list_foundation_models()` method, which will tell us all the models available for us to use 


```python
bedrock_service.list_foundation_models()
```




    {'ResponseMetadata': {'RequestId': '1eeb8bb1-1a68-45ae-9d6e-b8ebab32ee1d',
      'HTTPStatusCode': 200,
      'HTTPHeaders': {'date': 'Mon, 30 Sep 2024 21:21:58 GMT',
       'content-type': 'application/json',
       'content-length': '31450',
       'connection': 'keep-alive',
       'x-amzn-requestid': '1eeb8bb1-1a68-45ae-9d6e-b8ebab32ee1d'},
      'RetryAttempts': 0},
     'modelSummaries': [{'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-tg1-large',
       'modelId': 'amazon.titan-tg1-large',
       'modelName': 'Titan Text Large',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-g1-text-02',
       'modelId': 'amazon.titan-embed-g1-text-02',
       'modelName': 'Titan Text Embeddings v2',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-text-lite-v1:0:4k',
       'modelId': 'amazon.titan-text-lite-v1:0:4k',
       'modelName': 'Titan Text G1 - Lite',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': ['FINE_TUNING', 'CONTINUED_PRE_TRAINING'],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-text-lite-v1',
       'modelId': 'amazon.titan-text-lite-v1',
       'modelName': 'Titan Text G1 - Lite',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-text-express-v1:0:8k',
       'modelId': 'amazon.titan-text-express-v1:0:8k',
       'modelName': 'Titan Text G1 - Express',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': ['FINE_TUNING', 'CONTINUED_PRE_TRAINING'],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-text-express-v1',
       'modelId': 'amazon.titan-text-express-v1',
       'modelName': 'Titan Text G1 - Express',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v1:2:8k',
       'modelId': 'amazon.titan-embed-text-v1:2:8k',
       'modelName': 'Titan Embeddings G1 - Text',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v1',
       'modelId': 'amazon.titan-embed-text-v1',
       'modelName': 'Titan Embeddings G1 - Text',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v2:0:8k',
       'modelId': 'amazon.titan-embed-text-v2:0:8k',
       'modelName': 'Titan Text Embeddings V2',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': [],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v2:0',
       'modelId': 'amazon.titan-embed-text-v2:0',
       'modelName': 'Titan Text Embeddings V2',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-image-v1:0',
       'modelId': 'amazon.titan-embed-image-v1:0',
       'modelName': 'Titan Multimodal Embeddings G1',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['EMBEDDING'],
       'customizationsSupported': ['FINE_TUNING'],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-image-v1',
       'modelId': 'amazon.titan-embed-image-v1',
       'modelName': 'Titan Multimodal Embeddings G1',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['EMBEDDING'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-image-generator-v1:0',
       'modelId': 'amazon.titan-image-generator-v1:0',
       'modelName': 'Titan Image Generator G1',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': ['FINE_TUNING'],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-image-generator-v1',
       'modelId': 'amazon.titan-image-generator-v1',
       'modelName': 'Titan Image Generator G1',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-image-generator-v2:0',
       'modelId': 'amazon.titan-image-generator-v2:0',
       'modelName': 'Titan Image Generator G1 v2',
       'providerName': 'Amazon',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': ['FINE_TUNING'],
       'inferenceTypesSupported': ['PROVISIONED', 'ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/stability.stable-diffusion-xl-v1:0',
       'modelId': 'stability.stable-diffusion-xl-v1:0',
       'modelName': 'SDXL 1.0',
       'providerName': 'Stability AI',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/stability.stable-diffusion-xl-v1',
       'modelId': 'stability.stable-diffusion-xl-v1',
       'modelName': 'SDXL 1.0',
       'providerName': 'Stability AI',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/stability.sd3-large-v1:0',
       'modelId': 'stability.sd3-large-v1:0',
       'modelName': 'SD3 Large 1.0',
       'providerName': 'Stability AI',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/stability.stable-image-core-v1:0',
       'modelId': 'stability.stable-image-core-v1:0',
       'modelName': 'Stable Image Core 1.0',
       'providerName': 'Stability AI',
       'inputModalities': ['TEXT'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/stability.stable-image-ultra-v1:0',
       'modelId': 'stability.stable-image-ultra-v1:0',
       'modelName': 'Stable Image Ultra 1.0',
       'providerName': 'Stability AI',
       'inputModalities': ['TEXT'],
       'outputModalities': ['IMAGE'],
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/ai21.j2-grande-instruct',
       'modelId': 'ai21.j2-grande-instruct',
       'modelName': 'J2 Grande Instruct',
       'providerName': 'AI21 Labs',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/ai21.j2-jumbo-instruct',
       'modelId': 'ai21.j2-jumbo-instruct',
       'modelName': 'J2 Jumbo Instruct',
       'providerName': 'AI21 Labs',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-instant-v1:2:100k',
       'modelId': 'anthropic.claude-instant-v1:2:100k',
       'modelName': 'Claude Instant',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-instant-v1',
       'modelId': 'anthropic.claude-instant-v1',
       'modelName': 'Claude Instant',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2:0:18k',
       'modelId': 'anthropic.claude-v2:0:18k',
       'modelName': 'Claude',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2:0:100k',
       'modelId': 'anthropic.claude-v2:0:100k',
       'modelName': 'Claude',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2:1:18k',
       'modelId': 'anthropic.claude-v2:1:18k',
       'modelName': 'Claude',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2:1:200k',
       'modelId': 'anthropic.claude-v2:1:200k',
       'modelName': 'Claude',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2:1',
       'modelId': 'anthropic.claude-v2:1',
       'modelName': 'Claude',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-v2',
       'modelId': 'anthropic.claude-v2',
       'modelName': 'Claude',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0:28k',
       'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0:28k',
       'modelName': 'Claude 3 Sonnet',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0:200k',
       'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0:200k',
       'modelName': 'Claude 3 Sonnet',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0',
       'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0',
       'modelName': 'Claude 3 Sonnet',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0:48k',
       'modelId': 'anthropic.claude-3-haiku-20240307-v1:0:48k',
       'modelName': 'Claude 3 Haiku',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0:200k',
       'modelId': 'anthropic.claude-3-haiku-20240307-v1:0:200k',
       'modelName': 'Claude 3 Haiku',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0',
       'modelId': 'anthropic.claude-3-haiku-20240307-v1:0',
       'modelName': 'Claude 3 Haiku',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-opus-20240229-v1:0:12k',
       'modelId': 'anthropic.claude-3-opus-20240229-v1:0:12k',
       'modelName': 'Claude 3 Opus',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-opus-20240229-v1:0:28k',
       'modelId': 'anthropic.claude-3-opus-20240229-v1:0:28k',
       'modelName': 'Claude 3 Opus',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-opus-20240229-v1:0:200k',
       'modelId': 'anthropic.claude-3-opus-20240229-v1:0:200k',
       'modelName': 'Claude 3 Opus',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-opus-20240229-v1:0',
       'modelId': 'anthropic.claude-3-opus-20240229-v1:0',
       'modelName': 'Claude 3 Opus',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0:18k',
       'modelId': 'anthropic.claude-3-5-sonnet-20240620-v1:0:18k',
       'modelName': 'Claude 3.5 Sonnet',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0:51k',
       'modelId': 'anthropic.claude-3-5-sonnet-20240620-v1:0:51k',
       'modelName': 'Claude 3.5 Sonnet',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0:200k',
       'modelId': 'anthropic.claude-3-5-sonnet-20240620-v1:0:200k',
       'modelName': 'Claude 3.5 Sonnet',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0',
       'modelId': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
       'modelName': 'Claude 3.5 Sonnet',
       'providerName': 'Anthropic',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.command-text-v14:7:4k',
       'modelId': 'cohere.command-text-v14:7:4k',
       'modelName': 'Command',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': ['FINE_TUNING'],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.command-text-v14',
       'modelId': 'cohere.command-text-v14',
       'modelName': 'Command',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.command-r-v1:0',
       'modelId': 'cohere.command-r-v1:0',
       'modelName': 'Command R',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.command-r-plus-v1:0',
       'modelId': 'cohere.command-r-plus-v1:0',
       'modelName': 'Command R+',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.command-light-text-v14:7:4k',
       'modelId': 'cohere.command-light-text-v14:7:4k',
       'modelName': 'Command Light',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': ['FINE_TUNING'],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.command-light-text-v14',
       'modelId': 'cohere.command-light-text-v14',
       'modelName': 'Command Light',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.embed-english-v3:0:512',
       'modelId': 'cohere.embed-english-v3:0:512',
       'modelName': 'Embed English',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.embed-english-v3',
       'modelId': 'cohere.embed-english-v3',
       'modelName': 'Embed English',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.embed-multilingual-v3:0:512',
       'modelId': 'cohere.embed-multilingual-v3:0:512',
       'modelName': 'Embed Multilingual',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.embed-multilingual-v3',
       'modelId': 'cohere.embed-multilingual-v3',
       'modelName': 'Embed Multilingual',
       'providerName': 'Cohere',
       'inputModalities': ['TEXT'],
       'outputModalities': ['EMBEDDING'],
       'responseStreamingSupported': False,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-13b-chat-v1:0:4k',
       'modelId': 'meta.llama2-13b-chat-v1:0:4k',
       'modelName': 'Llama 2 Chat 13B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['PROVISIONED'],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-13b-chat-v1',
       'modelId': 'meta.llama2-13b-chat-v1',
       'modelName': 'Llama 2 Chat 13B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-70b-chat-v1:0:4k',
       'modelId': 'meta.llama2-70b-chat-v1:0:4k',
       'modelName': 'Llama 2 Chat 70B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': [],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-70b-chat-v1',
       'modelId': 'meta.llama2-70b-chat-v1',
       'modelName': 'Llama 2 Chat 70B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-13b-v1:0:4k',
       'modelId': 'meta.llama2-13b-v1:0:4k',
       'modelName': 'Llama 2 13B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': ['FINE_TUNING'],
       'inferenceTypesSupported': [],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-13b-v1',
       'modelId': 'meta.llama2-13b-v1',
       'modelName': 'Llama 2 13B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': [],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-70b-v1:0:4k',
       'modelId': 'meta.llama2-70b-v1:0:4k',
       'modelName': 'Llama 2 70B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': ['FINE_TUNING'],
       'inferenceTypesSupported': [],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama2-70b-v1',
       'modelId': 'meta.llama2-70b-v1',
       'modelName': 'Llama 2 70B',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': [],
       'modelLifecycle': {'status': 'LEGACY'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-8b-instruct-v1:0',
       'modelId': 'meta.llama3-8b-instruct-v1:0',
       'modelName': 'Llama 3 8B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-70b-instruct-v1:0',
       'modelId': 'meta.llama3-70b-instruct-v1:0',
       'modelName': 'Llama 3 70B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-1-8b-instruct-v1:0',
       'modelId': 'meta.llama3-1-8b-instruct-v1:0',
       'modelName': 'Llama 3.1 8B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-1-70b-instruct-v1:0',
       'modelId': 'meta.llama3-1-70b-instruct-v1:0',
       'modelName': 'Llama 3.1 70B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-1-405b-instruct-v1:0',
       'modelId': 'meta.llama3-1-405b-instruct-v1:0',
       'modelName': 'Llama 3.1 405B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-2-11b-instruct-v1:0',
       'modelId': 'meta.llama3-2-11b-instruct-v1:0',
       'modelName': 'Llama 3.2 11B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['INFERENCE_PROFILE'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-2-90b-instruct-v1:0',
       'modelId': 'meta.llama3-2-90b-instruct-v1:0',
       'modelName': 'Llama 3.2 90B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT', 'IMAGE'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['INFERENCE_PROFILE'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-2-1b-instruct-v1:0',
       'modelId': 'meta.llama3-2-1b-instruct-v1:0',
       'modelName': 'Llama 3.2 1B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['INFERENCE_PROFILE'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-2-3b-instruct-v1:0',
       'modelId': 'meta.llama3-2-3b-instruct-v1:0',
       'modelName': 'Llama 3.2 3B Instruct',
       'providerName': 'Meta',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['INFERENCE_PROFILE'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/mistral.mistral-7b-instruct-v0:2',
       'modelId': 'mistral.mistral-7b-instruct-v0:2',
       'modelName': 'Mistral 7B Instruct',
       'providerName': 'Mistral AI',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/mistral.mixtral-8x7b-instruct-v0:1',
       'modelId': 'mistral.mixtral-8x7b-instruct-v0:1',
       'modelName': 'Mixtral 8x7B Instruct',
       'providerName': 'Mistral AI',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/mistral.mistral-large-2402-v1:0',
       'modelId': 'mistral.mistral-large-2402-v1:0',
       'modelName': 'Mistral Large (2402)',
       'providerName': 'Mistral AI',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}},
      {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/mistral.mistral-large-2407-v1:0',
       'modelId': 'mistral.mistral-large-2407-v1:0',
       'modelName': 'Mistral Large (2407)',
       'providerName': 'Mistral AI',
       'inputModalities': ['TEXT'],
       'outputModalities': ['TEXT'],
       'responseStreamingSupported': True,
       'customizationsSupported': [],
       'inferenceTypesSupported': ['ON_DEMAND'],
       'modelLifecycle': {'status': 'ACTIVE'}}]}



---

## `InvokeModel` body and output

The `invoke_model()` method of the Amazon Bedrock client (`InvokeModel` API) will be the primary method we use for most of our Text Generation and Processing tasks - whichever model we're using.

Although the method is shared, the format of input and output varies depending on the foundation model used - as described below:

### Anthropic Claude

#### Input

```json
{
    "prompt": "\n\nHuman:<prompt>\n\Assistant:",
    "max_tokens_to_sample": 300,
    "temperature": 0.5,
    "top_k": 250,
    "top_p": 1,
    "stop_sequences": ["\n\nHuman:"]
}
```

#### Output

```json
{
    "completion": "<output>",
    "stop_reason": "stop_sequence"
}
```

---

## Common inference parameter definitions

### Randomness and Diversity

Foundation models support the following parameters to control randomness and diversity in the 
response.

**Temperature** – Large language models use probability to construct the words in a sequence. For any 
given next word, there is a probability distribution of options for the next word in the sequence. When 
you set the temperature closer to zero, the model tends to select the higher-probability words. When 
you set the temperature further away from zero, the model may select a lower-probability word.

In technical terms, the temperature modulates the probability density function for the next tokens, 
implementing the temperature sampling technique. This parameter can deepen or flatten the density 
function curve. A lower value results in a steeper curve with more deterministic responses, and a higher 
value results in a flatter curve with more random responses.

**Top K** – Temperature defines the probability distribution of potential words, and Top K defines the cut 
off where the model no longer selects the words. For example, if K=50, the model selects from 50 of the 
most probable words that could be next in a given sequence. This reduces the probability that an unusual 
word gets selected next in a sequence.
In technical terms, Top K is the number of the highest-probability vocabulary tokens to keep for Top-
K-filtering - This limits the distribution of probable tokens, so the model chooses one of the highest-
probability tokens.

**Top P** – Top P defines a cut off based on the sum of probabilities of the potential choices. If you set Top 
P below 1.0, the model considers the most probable options and ignores less probable ones. Top P is 
similar to Top K, but instead of capping the number of choices, it caps choices based on the sum of their 
probabilities.
For the example prompt "I hear the hoof beats of ," you may want the model to provide "horses," 
"zebras" or "unicorns" as the next word. If you set the temperature to its maximum, without capping 
Top K or Top P, you increase the probability of getting unusual results such as "unicorns." If you set the 
temperature to 0, you increase the probability of "horses." If you set a high temperature and set Top K or 
Top P to the maximum, you increase the probability of "horses" or "zebras," and decrease the probability 
of "unicorns."

### Length

The following parameters control the length of the generated response.

**Response length** – Configures the minimum and maximum number of tokens to use in the generated 
response.

**Length penalty** – Length penalty optimizes the model to be more concise in its output by penalizing 
longer responses. Length penalty differs from response length as the response length is a hard cut off for 
the minimum or maximum response length.

In technical terms, the length penalty penalizes the model exponentially for lengthy responses. 0.0 
means no penalty. Set a value less than 0.0 for the model to generate longer sequences, or set a value 
greater than 0.0 for the model to produce shorter sequences.

### Repetitions

The following parameters help control repetition in the generated response.

**Repetition penalty (presence penalty)** – Prevents repetitions of the same words (tokens) in responses. 
1.0 means no penalty. Greater than 1.0 decreases repetition.

---

## Try out the text generation model

With some theory out of the way, let's see the models in action! Run the cells below to see how to generate text with the Anthropic Claude Haiku model. 

### Client side `boto3` bedrock-runtime connection


```python
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=region,
)
```


```python
claude3 = 'claude3'
llama2 = 'llama2'
llama3='llama3'
mistral='mistral'
titan='titan'
models_dict = {
    claude3: 'anthropic.claude-3-haiku-20240307-v1:0',  # Updated to Claude Haiku model ID
    llama3: 'meta.llama3-8b-instruct-v1:0',
    mistral: 'mistral.mistral-7b-instruct-v0:2',
    titan: 'amazon.titan-tg1-large'
}
max_tokens_val = 100
temperature_val = 0.1
dict_add_params = {
    llama3: {"max_gen_len":max_tokens_val, "temperature":temperature_val} , 
    claude3: {"top_k": 200,  "temperature": temperature_val, "max_tokens": max_tokens_val},
    mistral: {"max_tokens":max_tokens_val, "temperature": temperature_val} , 
    titan:  {"topK": 200,  "maxTokenCount": max_tokens_val}
}
```

### Anthropic Claude Haiku


```python
import json

PROMPT_DATA = '''Human: Write me a blog about making strong business decisions as a leader.

Assistant:
'''
```


```python
messages_API_body = {
    "anthropic_version": "bedrock-2023-05-31", 
    "max_tokens": 100, #int(500/0.75),
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": PROMPT_DATA
                }
            ]
        }
    ]
}
```

### Ask claude to generate this article


```python
import json
from IPython.display import clear_output, display, display_markdown, Markdown

body = json.dumps(messages_API_body)
accept = "application/json"
contentType = "application/json"

# Updated model ID to Claude Haiku
modelId = "anthropic.claude-3-haiku-20240307-v1:0"

# Invoke the model with the request.
response = bedrock_runtime.invoke_model(
    modelId=modelId, body=body
)

# Extract and print the response text in real-time. Claude Haiku
model_response = json.loads(response["body"].read())

# Extract and print the response text.
response_text = model_response["content"][0]["text"]
display(Markdown(response_text))
```


Here is a draft blog post about making strong business decisions as a leader:

Title: 5 Tips for Making Tough Business Decisions as a Leader

As a business leader, you are constantly faced with important decisions that can significantly impact the trajectory of your company. Whether it's deciding on a new product strategy, choosing between candidates for a key role, or determining how to allocate limited resources, the choices you make will reverberate throughout your organization. 

Making tough calls is


## Generate streaming output

For large language models, it can take noticeable time to generate long output sequences. Rather than waiting for the entire response to be available, latency-sensitive applications may like to **stream** the response to users.

Run the code below to see how you can achieve this with Bedrock's `invoke_model_with_response_stream()` method - returning the response body in separate chunks.

### Each model has its unique input and output properties

**Claude models**

```
for event in streaming_response["body"]:
    chunk = json.loads(event["chunk"]["bytes"])
    if chunk["type"] == "content_block_delta":
        print(chunk["delta"].get("text", ""), end="")
        #display(Markdown(chunk["delta"].get("text", "")))
```

**Llama3**
```
for event in streaming_response["body"]:
    chunk = json.loads(event["chunk"]["bytes"])
    if "generation" in chunk:
        #print(chunk["generation"], end="")
        display(Markdown(chunk["generation"]))
```


```python
import json
from IPython.display import clear_output, display, display_markdown, Markdown

body = json.dumps(messages_API_body)
accept = "application/json"
contentType = "application/json"

# Updated model ID to Claude Haiku
modelId = "anthropic.claude-3-haiku-20240307-v1:0"

# Invoke the model with the request using streaming response
streaming_response = bedrock_runtime.invoke_model_with_response_stream(
    modelId=modelId, body=body
)

# Extract and print the response text in real-time
for event in streaming_response["body"]:
    chunk = json.loads(event["chunk"]["bytes"])
    
    if chunk["type"] == "content_block_delta":
        # Print the streamed response text incrementally
        print(chunk["delta"].get("text", ""), end="")
        # display(Markdown(chunk["delta"].get("text", "")))
```

    Here is a draft blog post about making strong business decisions as a leader:
    
    Title: 5 Tips for Making Tough Business Decisions as a Leader
    
    As a business leader, you are often faced with difficult decisions that can have a major impact on your company's success. Whether it's deciding on a new strategy, allocating resources, or addressing a crisis, the choices you make as a leader will largely determine the trajectory of your organization. 
    
    Making strong, well-informed business

### To solve this problem Bedrock has now created a `Converse API`

but the model decodng params are different


```
messages_API_body = {
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "Provide general steps to debug a BSOD on a Windows laptop."
                }
            ]
        }
    ],
    "system": [{"text" : "You are a tech support expert who helps resolve technical issues. Signal 'SUCCESS' if you can resolve the issue, otherwise 'FAILURE'"}],
    "inferenceConfig": {
        "stopSequences": [ "SUCCESS", "FAILURE" ]
    },
    "additionalModelRequestFields": {
        "top_k": 200,
        "max_tokens": 100
    },
    "additionalModelResponseFieldPaths": [
        "/stop_sequence"
    ]
}
```


```python
import boto3
import os
from IPython.display import Markdown, display
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

region = os.environ.get("AWS_REGION")
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=region,
)

# Model identifiers
claude3 = 'claude3'
llama2 = 'llama2'
llama3 = 'llama3'
mistral = 'mistral'
titan = 'titan'

# Updated model dictionary with correct model IDs
models_dict = {
    claude3: 'anthropic.claude-3-haiku-20240307-v1:0',  # Updated to Claude Haiku model ID
    llama2: 'meta.llama2-13b-chat-v1',
    llama3: 'meta.llama3-8b-instruct-v1:0',
    mistral: 'mistral.mistral-7b-instruct-v0:2',
    titan: 'amazon.titan-text-premier-v1:0'
}

max_tokens_val = 100
temperature_val = 0.1

# Additional parameters for different models
dict_add_params = {
    llama3: {},  # Adjust additional params if needed
    claude3: {"top_k": 200},
    mistral: {},
    titan: {"topK": 200},
}

# Base inference configuration
inference_config = {
    "temperature": temperature_val,
    "maxTokens": max_tokens_val,
    "topP": 0.9
}

def generate_conversation(bedrock_client, model_id, system_text, input_text):
    """
    Sends a message to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        system_text (JSON): The system prompt.
        input_text (str): The input message.

    Returns:
        response (JSON): The conversation that the model generated.
    """

    logger.info("Generating message with model %s", model_id)

    # Message to send
    message = {
        "role": "user",
        "content": [{"text": input_text}]
    }
    messages = [message]
    system_prompts = [{"text": system_text}]

    if model_id in [models_dict.get(mistral), models_dict.get(titan)]:
        system_prompts = []  # system prompts not supported for these models

    # Send the message
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=get_additional_model_fields(model_id)
    )

    return response

def get_additional_model_fields(model_id):
    """
    Retrieves additional model fields based on the model_id.
    """
    return dict_add_params.get(model_id, {})

def get_converse_output(response_obj):
    """
    Parses the output from the conversation.
    """
    ret_messages = []
    output_message = response_obj['output']['message']
    role_out = output_message['role']

    for content in output_message['content']:
        ret_messages.append(content['text'])
        
    return ret_messages, role_out

# Example response metadata extraction
response_metadata = {
    'ResponseMetadata': {
        'RequestId': 'bf55ac64-9df7-4e34-b423-39af447235d7',
        'HTTPStatusCode': 200,
        'HTTPHeaders': {
            'date': 'Mon, 09 Sep 2024 15:42:38 GMT',
            'content-type': 'application/json',
            'content-length': '29744',
            'connection': 'keep-alive',
            'x-amzn-requestid': 'bf55ac64-9df7-4e34-b423-39af447235d7'
        },
        'RetryAttempts': 0
    },
    'modelSummaries': [
        # Summaries for different models
        {'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0',
         'modelId': 'anthropic.claude-3-haiku-20240307-v1:0',
         'modelName': 'Claude 3 Haiku',
         'providerName': 'Anthropic',
         'inputModalities': ['TEXT'],
         'outputModalities': ['TEXT'],
         'responseStreamingSupported': True,
         'customizationsSupported': [],
         'inferenceTypesSupported': ['ON_DEMAND'],
         'modelLifecycle': {'status': 'ACTIVE'}}
    ]
}
```


```python
import logging
import boto3
from botocore.exceptions import ClientError
from IPython.display import Markdown, display

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Choose Claude Haiku model for conversation
modelId = models_dict.get('claude3')  # Updated to Claude Haiku (claude3)

# System and input texts
system_text = "You are an economist with access to lots of data."
input_text = "Write an article about impact of high inflation to GDP of a country."

# Generate a conversation
try:
    response = generate_conversation(bedrock_runtime, modelId, system_text, input_text)
    output_message = response['output']['message']

    # Output the role of the assistant
    print(f"Role: {output_message['role']}")

    # Output each text block from the assistant
    for content in output_message['content']:
        print(f"Text: {content['text']}")

    # Token usage information
    token_usage = response['usage']
    print(f"Input tokens:  {token_usage['inputTokens']}")
    print(f"Output tokens:  {token_usage['outputTokens']}")
    print(f"Total tokens:  {token_usage['totalTokens']}")

    # Stop reason for the response
    print(f"Stop reason: {response['stopReason']}")

    print(f"Finished generating text with model {modelId}.")

    # Display the first part of the generated output as Markdown
    display(Markdown(get_converse_output(response)[0][0]))

except ClientError as e:
    logger.error(f"An error occurred: {e}")
except KeyError as e:
    logger.error(f"Key error: {e} - possibly missing key in response.")
except Exception as e:
    logger.error(f"Unexpected error: {e}")

```

    INFO: Generating message with model anthropic.claude-3-haiku-20240307-v1:0


    Role: assistant
    Text: Here is a draft article on the impact of high inflation on a country's GDP:
    
    The Impact of High Inflation on GDP
    
    Persistently high inflation can have significant negative consequences for a country's economic growth and overall GDP. As prices rise rapidly across the economy, the purchasing power of consumers and businesses erodes, leading to a slowdown in economic activity.
    
    One of the primary ways high inflation impacts GDP is through its effect on consumer spending. When prices are rising quickly, consumers have
    Input tokens:  32
    Output tokens:  100
    Total tokens:  132
    Stop reason: max_tokens
    Finished generating text with model anthropic.claude-3-haiku-20240307-v1:0.



Here is a draft article on the impact of high inflation on a country's GDP:

The Impact of High Inflation on GDP

Persistently high inflation can have significant negative consequences for a country's economic growth and overall GDP. As prices rise rapidly across the economy, the purchasing power of consumers and businesses erodes, leading to a slowdown in economic activity.

One of the primary ways high inflation impacts GDP is through its effect on consumer spending. When prices are rising quickly, consumers have


## Generate embeddings

Use text embeddings to convert text into meaningful vector representations. You input a body of text 
and the output is a (1 x n) vector. You can use embedding vectors for a wide variety of applications. 
Bedrock currently offers Titan Embeddings for text embedding that supports text similarity (finding the 
semantic similarity between bodies of text) and text retrieval (such as search).

At the time of writing you can use `amazon.titan-embed-text-v1` as embedding model via the API. The input text size is 8192 tokens and the output vector length is 1536.

To use a text embeddings model, use the InvokeModel API operation or the Python SDK.
Use InvokeModel to retrieve the vector representation of the input text from the specified model.



#### Input

```json
{
    "inputText": "<text>"
}
```

#### Output

```json
{
    "embedding": []
}
```


Let's see how to generate embeddings of some text:


```python
prompt_data = "Amazon Bedrock supports foundation models from industry-leading providers such as \
AI21 Labs, Anthropic, Stability AI, and Amazon. Choose the model that is best suited to achieving \
your unique goals."
```


```python
body = json.dumps({"inputText": prompt_data})
modelId = "amazon.titan-embed-text-v1"
accept = "application/json"
contentType = "application/json"
response = bedrock_runtime.invoke_model(
body=body, modelId=modelId, accept=accept, contentType=contentType
)
response_body = json.loads(response.get("body").read())
embedding = response_body.get("embedding")
print(f"The embedding vector has {len(embedding)} values\n{embedding[0:3]+['...']+embedding[-3:]}")
```

    The embedding vector has 1536 values
    [0.166015625, 0.236328125, 0.703125, '...', 0.26953125, -0.609375, -0.55078125]


#### Now let us run a eval on our models

## Next steps

In this notebook we have successfully set up our Bedrock compatible environment and showed some basic examples of invoking Amazon Bedrock models using the AWS Python SDK. You're now ready to move on to the next notebook to start building our retrieval augmented generation (RAG) application!
