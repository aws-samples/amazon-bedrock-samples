import os
import boto3
from pathlib import Path
import pandas as pd
import numpy as np
import json
import base64

from pathlib import Path
from PIL import Image
import seaborn as sns
from PIL import Image
import matplotlib.pyplot as plt

from io import BytesIO
from typing import List, Union 
from sagemaker.s3 import S3Downloader as s3down

session = boto3.session.Session()
region = session.region_name

# Define bedrock client
bedrock_client = boto3.client(
    "bedrock-runtime", 
    region, 
    endpoint_url=f"https://bedrock-runtime.{region}.amazonaws.com"
)


# Bedrock models
# Select Amazon titan-embed-image-v1 as Embedding model for multimodal indexing
multimodal_embed_model = f'amazon.titan-embed-image-v1'

"""
Function to generate Embeddings from image or text
"""

def get_titan_multimodal_embedding(
    image_path:str=None,  # maximum 2048 x 2048 pixels
    description:str=None, # English only and max input tokens 128
    dimension:int=1024,   # 1,024 (default), 384, 256
    model_id:str=multimodal_embed_model
):
    payload_body = {}
    embedding_config = {
        "embeddingConfig": { 
             "outputEmbeddingLength": dimension
         }
    }
    # You can specify either text or image or both
    if image_path:
        if image_path.startswith('s3'):
            s3 = boto3.client('s3')
            bucket_name, key = image_path.replace("s3://", "").split("/", 1)
            obj = s3.get_object(Bucket=bucket_name, Key=key)
            # Read the object's body
            body = obj['Body'].read()
            # Encode the body in base64
            base64_image = base64.b64encode(body).decode('utf-8')
            payload_body["inputImage"] = base64_image
        else:   
            with open(image_path, "rb") as image_file:
                input_image = base64.b64encode(image_file.read()).decode('utf8')
            payload_body["inputImage"] = input_image
    if description:
        payload_body["inputText"] = description

    assert payload_body, "please provide either an image and/or a text description"
    # print("\n".join(payload_body.keys()))

    response = bedrock_client.invoke_model(
        body=json.dumps({**payload_body, **embedding_config}), 
        modelId=model_id,
        accept="application/json", 
        contentType="application/json"
    )

    return json.loads(response.get("body").read())



""" 
Function to plot heatmap from embeddings
"""

def plot_similarity_heatmap(embeddings_a, embeddings_b):
    inner_product = np.inner(embeddings_a, embeddings_b)
    sns.set(font_scale=1.1)
    graph = sns.heatmap(
        inner_product,
        vmin=np.min(inner_product),
        vmax=1,
        cmap="OrRd",
    )

""" 
Function to fetch the image based on image id from dataset
"""
def get_image_from_item_id( item_id = "0", dataset = None, return_image=True):
 
    item_idx = dataset.query(f"item_id == {item_id}").index[0]
    img_path = dataset.iloc[item_idx].image_path
    
    if return_image:
        img = Image.open(img_path)
        return img, dataset.iloc[item_idx].item_desc
    else:
        return img_path, dataset.iloc[item_idx].item_desc
    print(item_idx,img_path)


""" 
Function to fetch the image based on image id from S3 bucket
"""
    
def get_image_from_item_id_s3(item_id = "B0896LJNLH", dataset = None, image_path = None,  return_image=True):

    item_idx = dataset.query(f"item_id == '{item_id}'").index[0]
    img_loc =  dataset.iloc[item_idx].img_full_path
    
    if img_loc.startswith('s3'):
        # download and store images locally 
        local_data_root = f'./data/images'
        local_file_name = img_loc.split('/')[-1]
 
        s3down.download(img_loc, local_data_root)
 
    local_image_path = f"{local_data_root}/{local_file_name}"
    
    if return_image:
        img = Image.open(local_image_path)
        return img, dataset.iloc[item_idx].item_name_in_en_us
    else:
        return local_image_path, dataset.iloc[item_idx].item_name_in_en_us

""" 
Function to display the images.
"""
def display_images(
    images: [Image], 
    columns=2, width=20, height=8, max_images=15, 
    label_wrap_length=50, label_font_size=8):
 
    if not images:
        print("No images to display.")
        return 
 
    if len(images) > max_images:
        print(f"Showing {max_images} images of {len(images)}:")
        images=images[0:max_images]
 
    height = max(height, int(len(images)/columns) * height)
    plt.figure(figsize=(width, height))
    for i, image in enumerate(images):
 
        plt.subplot(int(len(images) / columns + 1), columns, i + 1)
        plt.imshow(image)
 
        if hasattr(image, 'name_and_score'):
            plt.title(image.name_and_score, fontsize=label_font_size); 
            

""" 
Function for semantic search capability using knn on input query prompt.
"""
def find_similar_items_from_query(query_prompt: str, k: int, num_results: int, index_name: str, image_root_path: str, dataset, open_search_client ) -> []:
    """
    Main semantic search capability using knn on input query prompt.
    Args:
        k: number of top-k similar vectors to retrieve from OpenSearch index
        num_results: number of the top-k similar vectors to retrieve
        index_name: index name in OpenSearch
    """
    query_emb = get_titan_multimodal_embedding(description=query_prompt, dimension=1024)["embedding"]

    body = {
        "size": num_results,
        "_source": {
            "exclude": ["image_vector"],
        },
        "query": {
            "knn": {
                "image_vector": {
                    "vector": query_emb,
                    "k": k,
                }
            }
        },
    }     

    res = open_search_client.search(index=index_name, body=body)
    images = []
    
    for hit in res["hits"]["hits"]:
        id_ = hit["_id"]
        item_id_ = hit["_source"]["item_id"]
        # image, item_name = get_image_from_item_id(item_id = id_, dataset = dataset )
        image, item_name = get_image_from_item_id_s3(item_id = item_id_, dataset = dataset,image_path = image_root_path)
        image.name_and_score = f'{hit["_score"]}:{item_name}'
        images.append(image)
        
    return images

""" 
Function for semantic search capability using knn on input image prompt.
"""
def find_similar_items_from_image(image_path: str, k: int, num_results: int, index_name: str, image_root_path: str, dataset, open_search_client  ) -> []:
    """
    Main semantic search capability using knn on input image prompt.
    Args:
        k: number of top-k similar vectors to retrieve from OpenSearch index
        num_results: number of the top-k similar vectors to retrieve
        index_name: index name in OpenSearch
    """
    query_emb = get_titan_multimodal_embedding(image_path=image_path, dimension=1024)["embedding"]

    body = {
        "size": num_results,
        "_source": {
            "exclude": ["image_vector"],
        },
        "query": {
            "knn": {
                "image_vector": {
                    "vector": query_emb,
                    "k": k,
                }
            }
        },
    }     

    res = open_search_client.search(index=index_name, body=body)
    images = []
    
    for hit in res["hits"]["hits"]:
        id_ = hit["_id"]
        item_id_ = hit["_source"]["item_id"]
        # image, item_name = get_image_from_item_id(item_id = id_, dataset = dataset )
        image, item_name = get_image_from_item_id_s3(item_id = item_id_, dataset = dataset,image_path = image_root_path)
        image.name_and_score = f'{hit["_score"]}:{item_name}'
        images.append(image)
        
    return images
