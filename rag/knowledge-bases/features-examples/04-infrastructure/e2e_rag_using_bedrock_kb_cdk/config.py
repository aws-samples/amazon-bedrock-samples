'''
Copyright (c) 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
This source code is subject to the terms found in the AWS Enterprise Customer Agreement.
NOTE: If deploying to production, set this to true.
 - If this is set to true, all properties from the Prod_Props class will be used
 - If this is set to false, all the properties from the Dev_Props class will be used
'''

# Define variables

MODEL_ID_TO_INDEX_REQUEST_MAP = {
    "amazon.titan-embed-text-v1": {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                        "space_type": "l2",
                    },
                },
                "AMAZON_BEDROCK_METADATA": {"type": "text", "index": False},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text", "index": True},
            }
        },
    },
    "amazon.titan-embed-text-v2:0": {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                        "space_type": "l2",
                    },
                },
                "AMAZON_BEDROCK_METADATA": {"type": "text", "index": False},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text", "index": True},
            }
        },
    },
    "cohere.embed-english-v3": {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                        "space_type": "l2",
                    },
                },
                "AMAZON_BEDROCK_METADATA": {"type": "text", "index": False},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text", "index": True},
            }
        },
    },
}

EMBEDDING_MODEL_IDs = ["amazon.titan-embed-text-v1", "amazon.titan-embed-text-v2:0", "cohere.embed-english-v3"]
CHUNKING_STRATEGIES = {0:"Default chunking",1:"Fixed-size chunking", 2:"No chunking"}

class EnvSettings:
    # General params
    ACCOUNT_ID =  "XXXXXXXXXXXX" # TODO: Change this to your account
    ACCOUNT_REGION = "us-east-1" # TODO: Change this to your region
    RAG_PROJ_NAME = "kb-cdk" # TODO: Change this to any name of your choice, but keep it short to avoid naming conflicts 

class KbConfig:
    KB_ROLE_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-role"
    EMBEDDING_MODEL_ID = EMBEDDING_MODEL_IDs[1]
    CHUNKING_STRATEGY = CHUNKING_STRATEGIES[1] # TODO: Choose the Chunking option 0,1,2
    MAX_TOKENS = 512 # TODO: Change this value accordingly if you choose "FIXED_SIZE" chunk strategy
    OVERLAP_PERCENTAGE = 20 # TODO: Change this value accordingly
    VECTOR_STORE_TYPE = "OSS" # TODO: Change this value to either "OSS" or "Aurora" based on your vector store preference. 
    MULTI_MODAL= True # TODO: Change this value to True if you need multi-modal RAG,
    PARSING_STRATEGY = "BEDROCK_FOUNDATION_MODEL" # TODO: Change this value to 'BEDROCK_FOUNDATION_MODEL' for FM parser, or  BEDROCK_DATA_AUTOMATION for BDA Parser
    
class DsConfig:
    S3_BUCKET_NAME = "<<s3-bucket-name>>" # TODO: Change this to the S3 bucket where your data is stored
    MM_STORAGE_S3 = "<<mm-storage-s3-bucket-name>>" # TODO: Change this to the S3 bucket as your multimodal storage destination


class OpenSearchServerlessConfig:
    COLLECTION_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-collection"
    INDEX_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-index"
    INDEX_MAPPING = MODEL_ID_TO_INDEX_REQUEST_MAP[KbConfig.EMBEDDING_MODEL_ID]