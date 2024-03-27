import boto3
import json
import os
from nemoguardrails import LLMRails, RailsConfig

dirname = os.path.dirname(__file__)

config = RailsConfig.from_path(dirname + "/config")

rails = LLMRails(config)

response = rails.generate(messages=[{
    "role": "user",
    "content": "Hello world!"
}])

print(response)

