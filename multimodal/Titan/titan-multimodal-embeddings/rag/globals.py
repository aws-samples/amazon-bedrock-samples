import os

# global constants
LISTINGS_FILE: str = os.path.join("listings", "metadata", "listings_0.json")
LANGUAGE_TO_FILTER: str = "en_US"
IMAGE_ID_TO_FNAME_MAPPING_FILE: str = "images.csv"
ABO_S3_BUCKET: str = "amazon-berkeley-objects"
ABO_S3_PREFIX:str = "images/original"
ABO_S3_BUCKET_PREFIX: str = f"s3://{ABO_S3_BUCKET}/{ABO_S3_PREFIX}"
IMAGE_DATASET_FNAME: str = f"aob_{LANGUAGE_TO_FILTER}.csv"
DATA_DIR: str = "data"
IMAGES_DIR: str = os.path.join(DATA_DIR, "images", LANGUAGE_TO_FILTER)
B64_ENCODED_IMAGES_DIR: str = os.path.join(DATA_DIR, "b64_images", LANGUAGE_TO_FILTER)
VECTOR_DB_DIR: str = os.path.join(DATA_DIR, "vectordb", LANGUAGE_TO_FILTER)
SUCCESSFULLY_EMBEDDED_DIR: str = os.path.join(DATA_DIR, "successfully_embedded", LANGUAGE_TO_FILTER)
IMAGE_DATA_W_SUCCESSFUL_EMBEDDINGS_FPATH: str = os.path.join(SUCCESSFULLY_EMBEDDED_DIR, "data.csv")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(B64_ENCODED_IMAGES_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_DIR, exist_ok=True)
os.makedirs(SUCCESSFULLY_EMBEDDED_DIR, exist_ok=True)
FMC_URL: str = "https://bedrock-runtime.us-east-1.amazonaws.com"
FMC_MODEL_ID: str = "amazon.titan-embed-image-v1"
CLAUDE_V2_MODEL_ID: str  = "anthropic.claude-v2"
ACCEPT_ENCODING: str = "application/json"
CONTENT_ENCODING: str = "application/json"
VECTORDB_INDEX_FILE: str = f"aob_{LANGUAGE_TO_FILTER}_index"
VECTOR_DB_INDEX_FPATH: str = os.path.join(VECTOR_DB_DIR, VECTORDB_INDEX_FILE)
K: int = 4
N: int = 10000
MAX_IMAGE_HEIGHT: int = 2048
MAX_IMAGE_WIDTH: int = 2048
