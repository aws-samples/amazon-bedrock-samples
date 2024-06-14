# # Configure the following values to be used in the example notebooks or, update these based on your implementation
# REGION = "us-east-1"
# FIREHOSE_NAME = "<your-firehose-name>"
# CRAWLER_NAME = "<your-crawler-name>"
# MODEL_ID = "<your-model-id>"
# MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/{MODEL_ID}"

# # Knowledge Base Configuration
# KB_ID = "<your-kb-id>"
# APPLICATION_NAME = '<your-application-name>'

# # Application Configuration
# EXPERIMENT_ID = "<your-experiment-id>"
# CUSTOM_TAG = {"application_stage":"production",
#               "cost-centre":"GenAI-Center",
#               "other-custom-tag":"tag-value"}

# # Retrieval and Generation Configuration
# GUARDRAIL_ID = "<your-guardrail-id>"
# GUARDRAIL_VERSION = "<your-guardrail-version>"
# MAX_TOKENS = 250
# TEMPERATURE = 0.01
# TOP_P = 0.01

# # Agent 
# AGENT_ID = "<your-agent-id>"
# AGENT_ALIAS_ID = "<your-agent-alias-id>"
# AGENT_CONFIG = {'model_name': 'Claude 3.0 Sonnet', 
#                 'temperature': TEMPERATURE}

# # Agent Session:
# ENABLE_TRACE, END_SESSION = True, False



# AWS Configuration
REGION = "us-east-1"
FIREHOSE_NAME = "kb-observability-767397817418-firehose-202406051123" # "kb-observability-767397817418-firehose"
CRAWLER_NAME = "GlueCrawler-kZsS9VCPLARq"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Knowledge Base Configuration
KB_ID = "ON3190TKPR"
APPLICATION_NAME = 'KB Chatbot for Octank Financial'

# Knowledge Base Evaluation Configuration
MODEL_ID_EVAL = "anthropic.claude-3-sonnet-20240229-v1:0"
MODEL_ID_GEN = "anthropic.claude-3-haiku-20240307-v1:0"
# MODEL_ID_GEN = "mistral.mistral-7b-instruct-v0:2"
# MODEL_ID_GEN = "cohere.command-r-v1:0"
MODEL_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/{MODEL_ID}"

# Application Configuration
EXPERIMENT_DESCRIPTION = "Observability Testing for KB"
CUSTOM_TAG = {"experiment_version": "v1", 
              "experiment_description": f"Generation Model {MODEL_ID_GEN}",
              "experiment_evaluation": f"RAG Eval Model {MODEL_ID_EVAL}"}

# Retrieval and Generation Configuration
GUARDRAIL_ID = "k4h1ufgm2m32"
GUARDRAIL_VERSION = "1"
MAX_TOKENS = 4000
TEMPERATURE = 0.01
TOP_P = 0.01