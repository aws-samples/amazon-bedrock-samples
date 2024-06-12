import io
import json
import boto3
import base64
from PIL import Image
from dependencies.config import embeddingSize

# Define output vector size – 1,024 (default), 384, 256
assert embeddingSize in [1024, 384, 256]

EMBEDDING_CONFIG = {
    "embeddingConfig": {
        "outputEmbeddingLength": embeddingSize
    }
}


class OpensearchIngestion:

    def __init__(self, client, session=None):
        self.client = client
        self.session = session if session else boto3.Session()
        self.region = self.session.region_name

    def put_bulk_in_opensearch(self, docs):
        print(f"Putting {len(docs)} documents in OpenSearch")
        success, failed = self.client.bulk(docs)
        return success, failed

    def check_index_exists(self, index_name):
        return self.client.indices.exists(index=index_name)

    def create_index(self, index_name):
        if not self.check_index_exists(index_name):
            settings = {
                "settings": {
                    "index.knn": True,
                }
            }
            response = self.client.indices.create(index=index_name, body=settings)
            return bool(response['acknowledged'])
        return False

    def create_index_mapping(self, index_name):
        response = self.client.indices.put_mapping(
            index=index_name,
            body={
                "properties": {
                    "vector_field": {
                        "type": "knn_vector",
                        "dimension": embeddingSize,
                        "method": {
                            "name": "hnsw",
                            "engine": "nmslib",
                        }
                    },
                    "image_b64": {"type": "text"},
                }
            }
        )
        return bool(response['acknowledged'])

    def get_bedrock_client(self):
        return self.session.client("bedrock-runtime", region_name=self.region)

    def create_titan_multimodal_embeddings(
            self,
            image_path: str = "None",
            text: str = "None",
    ):
        """Creates the titan embeddings from the provided image and/or text."""
        payload_body = {}

        if image_path and image_path != "None":
            payload_body["inputImage"] = self.get_encoded_image(image_path)
        if text and (text != "None"):
            payload_body["inputText"] = text
        if (image_path == "None") and (text == "None"):
            raise "please provide either an image and/or a text description"

        bedrock_client = self.get_bedrock_client()

        response = bedrock_client.invoke_model(
            body=json.dumps({**payload_body, **EMBEDDING_CONFIG}),
            modelId="amazon.titan-embed-image-v1",
            accept="application/json",
            contentType="application/json",
        )
        vector = json.loads(response['body'].read())
        return (payload_body, vector)

    def get_encoded_image(self, image_path: str):
        max_height, max_width = 1024, 1024  # Conservative Limit. Can increase to 2048
        # Open the image and compress it if greater than the defined max size.
        with Image.open(image_path) as image:
            if (image.size[0] * image.size[1]) > (max_height * max_width):
                image.thumbnail((max_height, max_width))
                resized_img = image.copy()
            else:
                resized_img = image
            img_byte_array = io.BytesIO()
            resized_img.save(img_byte_array, format=image.format)
            img_bytes = img_byte_array.getvalue()

        # Encode the image to base64
        image_encoded = base64.b64encode(img_bytes).decode('utf8')
        return image_encoded