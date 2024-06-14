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
# EXPERIMENT_ID = "<your-experiment-id>" # this can be your project name
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
# SESSION_ID = "<your-session-id>"
# ENABLE_TRACE, END_SESSION = True, False