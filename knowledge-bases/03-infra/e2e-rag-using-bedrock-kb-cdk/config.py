'''
Copyright (c) 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
This source code is subject to the terms found in the AWS Enterprise Customer Agreement.
NOTE: If deploying to production, set this to true.
 - If this is set to true, all properties from the Prod_Props class will be used
 - If this is set to false, all the properties from the Dev_Props class will be used
'''


EMBEDDING_MODEL_IDs = ["amazon.titan-embed-text-v1"]
CHUNKING_STRATEGYIES = ["FIXED_SIZE","NONE"]

class EnvSettings:
    # General params
    ACCOUNT_ID =  "ACCOUNT_ID"
    ACCOUNT_REGION = "ACCOUNT_REGION"
    RAG_PROJ_NAME = "e2e-rag"

class KbConfig:
    KB_ROLE_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-role"
    EMBEDDING_MODEL_ID = EMBEDDING_MODEL_IDs[0]
    CHUNKING_STRATEGY = CHUNKING_STRATEGYIES[0]
    MAX_TOKENS = 512 # change this value accordingly if you choose "FIXED_SIZE" chunk strategy
    OVERLAP_PERCENTAGE = 20 

class DsConfig:
    S3_BUCKET_NAME = f"ocktank-chatbot-hr-data" # S3 bucket where your data is stored

class OpenSearchServerlessConfig:
    COLLECTION_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-collection"
    INDEX_NAME = f"{EnvSettings.RAG_PROJ_NAME}-kb-index"