 Here is a draft README.md file:

# Using Bedrock with AWS Lambda

## Overview

The new Bedrock AI service from AWS provides powerful generative AI capabilities through API calls. However, the default Boto3 included in AWS Lambda has not yet been updated to support Bedrock. 

To use Bedrock in Lambda functions today, you need to create a Lambda layer with an updated Boto3 that contains the Bedrock service definitions. This README provides steps and code snippets to create a Boto3 layer and deploy Lambda functions that can call Bedrock.


## Prerequisites

- AWS account
- Configured AWS credentials on your local system 
- Python 3.7+
- Boto3 1.28.57 or later (for Bedrock service definitions)

## Errors Without Lambda Layer

If you try to call Bedrock from a Lambda function without using a layer, you will see errors like:

```python
Response
{
  "errorMessage": "2023-09-29T20:33:02.415Z 8c7bbc05-5757-40b4-9876-a269ecb350f2 Task timed out after 3.03 seconds"
}
...
raise UnknownServiceError(START RequestId: 8c7bbc05-5757-40b4-9876-a269ecb350f2 Version: $LATEST
...
```

This occurs because the default Boto3 in Lambda does not have the service endpoints defined for Bedrock.

## Steps to Create Layer

1. Package Boto3 1.28.57 or later into a .zip file
2. Use Lambda API to publish a layer version 
3. Specify the layer ARN when creating Lambda functions


[Here is a general video](https://www.youtube.com/watch?v=I13FPeC5LTw) showing the steps to create a lambda layer 

See `lambda_base.py` for layer creation code.

## Lambda Function Code

`lambda_function.py` shows sample code to call Bedrock from a Python Lambda function. 

The key points are:

- Import Boto3 and Bedrock clients

    ```python
    import boto3
    ```

- Specify the Bedrock endpoint URL

    ```python 
    bedrock = boto3.client(
        service_name='bedrock', 
        region_name=REGION,
        endpoint_url=f'https://bedrock.{REGION}.amazonaws.com'
    )
    ```

- Invoke Bedrock APIs like `list_foundation_models`

    ```python
    response = bedrock.list_foundation_models()
    ```
There are two clients for Amazon Bedrock. 

The `bedrock` client is for creating and managing Bedrock models. 

The `bedrock-runtime` client is for running inference on Bedrock models. 

## Equivalent AWS CLI Commands

To create the layer:

```bash
aws lambda publish-layer-version --layer-name bedrock-1-28-57 --content fileb://bedrock-1-28-57.zip --compatible-runtimes python3.8 python3.9 python3.10 python3.11 --compatible-architectures x86_64 arm64
``` 
**Note**: Get the layer arn from the output above and update the value below.

To create function:

```bash
aws lambda create-function --function-name my-function --zip-file fileb://lamdba_function.py.zip --role arn:aws:iam::123456789012:role/lambda-role --layers {{layer arn}} --handler lambda_function.lambda_handler --runtime python3.8 --archecture arm64
```

## Learn More 

- [Overview Video of Lambda and Lambda Layers](https://youtu.be/fDv_RKygOXU?si=7Auq2CwBX9rdpSr2) Until 15:20 in the video
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Bedrock service docs](https://docs.aws.amazon.com/bedrock/latest/APIReference/welcome.html)
- [Boto3 AWS SDK](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock.html)
- [Lambda layers](https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html)
