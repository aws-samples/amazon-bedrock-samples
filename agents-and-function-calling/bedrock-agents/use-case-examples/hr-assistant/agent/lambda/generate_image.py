import base64
import json
import os
import uuid

import boto3

bedrock_client = boto3.client("bedrock-runtime")
s3 = boto3.client("s3")
s3_bucket = os.environ["S3_BUCKET_NAME"]


# Generate an image by calling Amazon Titan Image Generator V1
def generate_image(image_type, image_description) -> dict:
    body = json.dumps(
        {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": image_type + ": " + image_description},  # Required
            "imageGenerationConfig": {
                "numberOfImages": 1,  # Range: 1 to 5
                "quality": "standard",  # Options: standard or premium
                "height": 512,  # Supported height list in the docs
                "width": 512,  # Supported width list in the docs
            },
        }
    )

    response = bedrock_client.invoke_model(
        body=body,
        modelId="amazon.titan-image-generator-v1",
        accept="application/json",
        contentType="application/json",
    )

    # Process the image
    response_body = json.loads(response.get("body").read())
    base64_image_data = response_body["images"][0]

    image_data = base64.b64decode(base64_image_data)

    random_identifier = uuid.uuid4()

    object_key = "generated_images/image_{}".format(random_identifier)

    s3.put_object(
        Bucket=s3_bucket,
        Key=object_key,
        Body=image_data,
        ContentType="image/jpeg",  # This is adjustable!
    )

    return {"s3_location": "s3://{}/{}".format(s3_bucket, object_key)}
