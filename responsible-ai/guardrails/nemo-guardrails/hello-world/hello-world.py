
# Make sure to install nemoguardrails and dependencies, see https://github.com/NVIDIA/NeMo-Guardrails/blob/develop/docs/getting_started/installation-guide.md 
from nemoguardrails import LLMRails, RailsConfig

from os.path import dirname, abspath

# NeMo expects a config folder with at least a config.yml to configure the model, instructions, rails and more
config = RailsConfig.from_path(dirname(dirname(abspath(__file__))) + "/no-rails-config")

# Initializing with the config 
rails = LLMRails(config)

# Generating a response - in this case calling the LLM without any rails 
response = rails.generate(messages=[{
    "role": "user",
    "content": "Hello World!"
}])

# The library comes with optional monitoring and explainability features, e.g. to check LLM calls and timing
info = rails.explain()

# Output all LLM calls in more detail - only 1 in this case 
info.print_llm_calls_summary()

# Output the prompts (or completions) generated for any of the LLM calls to check how instructions, rails, etc. have been used 
print(info.llm_calls[0].prompt)

# Output the response 
print(response['content'])

