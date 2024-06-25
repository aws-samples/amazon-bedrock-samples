import base64
import json
import os
from random import randint
from typing import List

import boto3
import requests
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection


os.chdir("/tmp")
region = os.environ["region_info"]
bedrock_client = boto3.client("bedrock-runtime")
s3_client = boto3.client("s3")
bucket_name = os.environ["s3_bucket"]
host = os.environ["aoss_host"]
index_name = os.environ["index_name"]
embeddingSize = int(os.environ["embeddingSize"])

# similarity threshold - to retrieve the matching images from OpenSearch index
RETRIEVE_THRESHOLD = 0.6

def get_named_parameter(event, name):
    try:
        return next(item for item in event["parameters"] if item["name"] == name)[
            "value"
        ]
    except:
        return None


def get_weather(event):
    """
    Retrieves current weather data from Open-Meteo API for the given location.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        dict: A dictionary containing the current weather data.
    """
    location_name = get_named_parameter(event, "location_name")

    latitude, longitude = get_location_coordinates(location_name)
    if not latitude or not longitude:
        raise Exception(f"Error: Could not find location {location_name}")

    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": True,
        "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m",
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
    else:
        response_code = 400
        results = {
            "body": "There is no weather information for this location. Use default value.",
            "response_code": response_code,
        }
        return results

    payload = {
        "taskType": "WEATHER",
        "weatherParams": {
            "location_name": location_name,  # Required
        },
    }
    weather_data = data

    if weather_data:
        current_weather = weather_data["current_weather"]
        temperature = current_weather["temperature"]
        weathercode = current_weather["weathercode"]
        weather_code_dict = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Drizzle: Light intensity",
            53: "Drizzle: Moderate intensity",
            55: "Drizzle: Dense intensity",
            56: "Freezing Drizzle: Light intensity",
            57: "Freezing Drizzle: Dense intensity",
            61: "Rain: Slight intensity",
            63: "Rain: Moderate intensity",
            65: "Rain: Heavy intensity",
            66: "Freezing Rain: Light intensity",
            67: "Freezing Rain: Heavy intensity",
            71: "Snow fall: Slight intensity",
            73: "Snow fall: Moderate intensity",
            75: "Snow fall: Heavy intensity",
            77: "Snow grains",
            80: "Rain showers: Slight intensity",
            81: "Rain showers: Moderate intensity",
            82: "Rain showers: Violent intensity",
            85: "Snow showers: Slight intensity",
            86: "Snow showers: Heavy intensity",
            95: "Thunderstorm: Slight or moderate",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        response_code = 200
        results = {
            "body": f"Temperature is {temperature} in Fahrenheit. The weather description is {weather_code_dict[weathercode]}",
            "response_code": response_code,
        }
        return results
    else:
        response_code = 400
        results = {
            "body": "There is no weather information for this location. Use default value.",
            "response_code": response_code,
        }
        return results


def get_location_coordinates(location_name):
    """
    Calls the Open-Meteo Geocoding API to get the latitude and longitude
    of the given location name.

    Args:
        location_name (str): The name of the location to search for.

    Returns:
        tuple: A tuple containing the latitude and longitude of the location,
               or None if the location is not found.
    """
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={location_name}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            result = data["results"][0]
            latitude = result["latitude"]
            longitude = result["longitude"]
            return latitude, longitude
        else:
            return None, None

    return None, None


def find_similar_image_in_opensearch_index(
    image_path: str = "None", text: str = "None", k: int = 1
) -> List:
    # Create the client with SSL/TLS enabled, but hostname verification disabled.
    if host is None:
        return None
    credentials = boto3.session.Session().get_credentials()
    aws_auth = AWSV4SignerAuth(credentials, region, "aoss")
    opensearch_client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=aws_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
        timeout=3000,
    )
    if (image_path != "None") or (text != "None"):
        payload, embedding = get_titan_multimodal_embedding(
            image_path=image_path, text=text
        )
    query = {
        "size": 5,
        "query": {"knn": {"vector_field": {"vector": embedding["embedding"], "k": k}}},
    }
    # search for documents in the index with the given query
    response = opensearch_client.search(index=index_name, body=query)
    retrieved_images = []
    for hit in response["hits"]["hits"]:
        # only retrieve the image if it's matching more than a certain threshold. 
        if hit["_score"] > RETRIEVE_THRESHOLD:
            image = hit["_source"]["image_b64"]
            img = base64.b64decode(image)
            retrieved_images.append(img)
    return retrieved_images


def image_lookup(event, host):
    input_image = get_named_parameter(event, "input_image")
    input_query = get_named_parameter(event, "input_query")

    if not host:
        return {
            "body": "No database available for image look_up, try other actions.",
            "response_code": 404,
        }

    if (input_query != "None") or (input_image != "None"):
        similar_img_b64 = find_similar_image_in_opensearch_index(
            image_path=input_image, text=input_query, k=1
        )
    else:
        # If none of the two possible inputs is provided. Return 404
        return {
            "body": "No valid inputs provided. Ask user to provide and image or image description",
            "response_code": 404,
        }
    try:
        if similar_img_b64:
            with open("/tmp/" + "image.jpg", "wb") as f:
                f.write(similar_img_b64[0])

            rand_suffix = randint(0, 1000000)
            file_name = f"lookup_image_{rand_suffix}.jpg"
            output_key = "OutputImages/" + file_name
            output_s3_location = "s3://" + bucket_name + "/" + output_key
            s3_client.upload_file("/tmp/image.jpg", bucket_name, output_key)
            return {"body": output_s3_location, "response_code": 200}
        else:
            response = {"body": "", "response_code": 400}
    except Exception:
        response = {
            "body": "Something went wrong",
            "response_code": 400,
        }
    # If the response_code is 400 - return the original input image
    # if input_query and (input_query != "None"):
    #    response["body"] = input_query
    if input_image and (input_image != "None"):
        response["body"] = input_image

    return response


def inpaint(event):
    prompt_text = get_named_parameter(event, "text")
    prompt_mask = get_named_parameter(event, "mask")
    input_image = get_named_parameter(event, "image_location")

    try:
        encoded_image = load_image_from_s3(input_image)
        payload = {
            "taskType": "INPAINTING",
            "inPaintingParams": {
                "text": prompt_text,
                "negativeText": "bad quality, low resolution",  # Optional
                "image": encoded_image,  # Required
                "maskPrompt": prompt_mask,  # One of "maskImage" or "maskPrompt" is required
            },
        }
        # response_code = 400
        result = titan_image(payload)[0]
        # results ={"body":result,"response_code": f'mask prompt: {prompt_mask},input_image: {encoded_image},prompt_text: {prompt_text}'}
        if result:
            local_path = "/tmp/" + input_image.split("/")[-1]
            # result.save(local_path)
            with open(local_path, "wb") as f:
                f.write(result)
            output_key = "OutputImages/" + input_image.split("/")[-1]
            output_s3_location = "s3://" + bucket_name + "/" + output_key
            s3_client.upload_file(local_path, bucket_name, output_key)
    except Exception as e:
        response_code = 400
        results = {
            "body": f"Image cannot be inpainted, please try again: see error {e}",
            "response_code": response_code,
        }
        return results

    response_code = 200
    results = {"body": output_s3_location, "response_code": response_code}
    return results


def outpaint(event):
    prompt_text = get_named_parameter(event, "text")
    prompt_mask = get_named_parameter(event, "mask")
    input_image = get_named_parameter(event, "image_location")

    try:
        encoded_image = load_image_from_s3(input_image)
        payload = {
            "taskType": "OUTPAINTING",
            "outPaintingParams": {
                "text": prompt_text,  # Required
                "image": encoded_image,  # Required
                "maskPrompt": prompt_mask,  # One of "maskImage" or "maskPrompt" is required
                "outPaintingMode": "PRECISE",  # One of "PRECISE" or "DEFAULT"
            },
        }
        result = titan_image(payload)[0]

        if result:
            local_path = "/tmp/" + input_image.split("/")[-1]
            # result.save(local_path)
            with open(local_path, "wb") as f:
                f.write(result)
            output_key = "OutputImages/" + input_image.split("/")[-1]
            output_s3_location = "s3://" + bucket_name + "/" + output_key
            s3_client.upload_file(local_path, bucket_name, output_key)

    except Exception as e:
        response_code = 400
        results = {
            "body": f"Image cannot be outpainted, please try again: see error{e}",
            "response_code": response_code,
        }
        return results

    response_code = 200
    results = {"body": output_s3_location, "response_code": response_code}
    return results


def get_image_gen(event):
    # input_image = get_named_parameter(event, 'input_image')
    input_query = get_named_parameter(event, "input_query")
    weather = get_named_parameter(event, "weather")

    # Read image from file and encode it as base64 string.

    try:
        
        # Uncomment this to get the image file from s3 instead 
        # s3_client.download_file(bucket_name, input_image, f'/tmp/{input_image}')

        # with open(f'/tmp/{input_image}', "rb") as image_file:
        #     input_image = base64.b64encode(image_file.read()).decode('utf8')

        if weather == "None":
            prompt = f"{input_query}"
        else:
            prompt = f"{input_query}.Make the clothing suitable for wearing in {weather} weather conditions."

        body = json.dumps(
            {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": prompt},
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "height": 1024,
                    "width": 1024,
                    "cfgScale": 10.0,
                    "seed": 0,
                },
            }
        )

        accept = "application/json"
        content_type = "application/json"
        model_id = "amazon.titan-image-generator-v1"

        response = bedrock_client.invoke_model(
            body=body, modelId=model_id, accept=accept, contentType=content_type
        )
        response_body = json.loads(response.get("body").read())

        finish_reason = response_body.get("error")
        if finish_reason is not None:
            raise Exception(f"Image generation error. Error is {finish_reason}")

        base64_image = response_body.get("images")[0]
        base64_bytes = base64_image.encode("ascii")
        image_bytes = base64.b64decode(base64_bytes)

        with open("/tmp/" + "image.jpg", "wb") as f:
            f.write(image_bytes)

        rand_suffix = randint(0, 1000000)
        file_name = f"gen_image_{rand_suffix}.jpg"
        output_key = "OutputImages/" + file_name
        s3_client.upload_file("/tmp/image.jpg", bucket_name, output_key)
    except Exception as e:
        response_code = 400
        results = {
            "body": f"Image cannot be generated, please try again: see error {e}",
            "response_code": response_code,
        }
        return results

    response_code = 200
    output_s3_location = f"s3://{bucket_name}/{output_key}"
    results = {"body": output_s3_location, "response_code": response_code}

    return results


def load_image_from_s3(image_path: str):
    try:
        s3 = boto3.client("s3")
        _bucket_name, object_key = image_path.replace("s3://", "").split("/", 1)
        response = s3.get_object(Bucket=_bucket_name, Key=object_key)
        # Read the object's body
        image_content = response["Body"].read()
        # Encode the body in bytes & decode it into a string.
        image_encoded = base64.b64encode(image_content).decode("utf8")

    except Exception as e:
        print(f"Error downloading file from S3: {e}")
        return None

    return image_encoded


def get_titan_multimodal_embedding(
    image_path: str = "None",
    text: str = "None",
):
    """This function reads the image path, and gets the embeddings by calling Titan Multimodal Embeddings model Amazon Bedrock"""

    embedding_config = {
        # OutputEmbeddingLength has to be one of: [256, 384, 1024],
        "embeddingConfig": {"outputEmbeddingLength": embeddingSize}
    }

    payload_body = {}

    if image_path and image_path != "None":
        if image_path.startswith("s3"):
            payload_body["inputImage"] = load_image_from_s3(image_path)
        else:
            with open(image_path, "rb") as image_file:
                input_image = base64.b64encode(image_file.read()).decode("utf8")
            payload_body["inputImage"] = input_image
    if text and (text != "None"):
        payload_body["inputText"] = text

    if (image_path == "None") and (text == "None"):
        print("please provide either an image and/or a text description")

    response = bedrock_client.invoke_model(
        body=json.dumps({**payload_body, **embedding_config}),
        modelId="amazon.titan-embed-image-v1",
        accept="application/json",
        contentType="application/json",
    )
    vector = json.loads(response.get("body").read())
    return (payload_body, vector)


def titan_image(
    payload: dict,
    num_image: int = 1,
    cfg: float = 10.0,
    seed: int = None,
    modelId: str = "amazon.titan-image-generator-v1",
) -> list:
    #   ImageGenerationConfig Options:
    #   - numberOfImages: Number of images to be generated
    #   - quality: Quality of generated images, can be standard or premium
    #   - height: Height of output image(s)
    #   - width: Width of output image(s)
    #   - cfgScale: Scale for classifier-free guidance
    #   - seed: The seed to use for reproducibility
    seed = seed if seed is not None else randint(0, 214783647)

    params = {
        "imageGenerationConfig": {
            "numberOfImages": num_image,  # Range: 1 to 5
            "quality": "premium",  # Options: standard/premium
            "height": 1024,  # Supported height list above
            "width": 1024,  # Supported width list above
            "cfgScale": cfg,  # Range: 1.0 (exclusive) to 10.0
            "seed": seed,  # Range: 0 to 214783647
        }
    }
    body = json.dumps({**payload, **params})

    response = bedrock_client.invoke_model(
        body=body,
        modelId=modelId,
        accept="application/json",
        contentType="application/json",
    )

    response_body = json.loads(response.get("body").read())
    base64_image = response_body.get("images")[0]
    base64_bytes = base64_image.encode("ascii")
    image_bytes = base64.b64decode(base64_bytes)

    images = [
        # Image.open(io.BytesIO(base64.b64decode(base64_image)))
        # for base64_image in response_body.get("images")
        image_bytes
    ]
    return images


def lambda_handler(event, context):
    response_code = 200
    action_group = event["actionGroup"]
    api_path = event["apiPath"]

    if api_path == "/imageGeneration":
        result = get_image_gen(event)
        body = result["body"]
        response_code = result["response_code"]

    elif api_path == "/weather":
        result = get_weather(event)
        body = result["body"]
        response_code = result["response_code"]

    elif api_path == "/image_lookup":
        result = image_lookup(event, host)
        body = result["body"]
        response_code = result["response_code"]

    elif api_path == "/inpaint":
        result = inpaint(event)
        body = result["body"]
        response_code = result["response_code"]

    elif api_path == "/outpaint":
        result = outpaint(event)
        body = result["body"]
        response_code = result["response_code"]

    # This will collect the return content for a given path above
    response_body = {"application/json": {"body": str(body)}}
    action_response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": event["httpMethod"],
            "httpStatusCode": response_code,
            "responseBody": response_body,
        },
    }
    return action_response
