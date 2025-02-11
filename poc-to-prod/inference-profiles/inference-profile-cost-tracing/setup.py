import os
import json
from scripts import utils
from scripts import create_iam_role, create_interence_profiles, setup_cloudwatch_sns, deploy_lambda, setup_api_gateway

os.environ['AWS_PROFILE'] = 'cost-tracing'

def create_directory(directory_path):
    """
    Create a directory if it doesn't exist.

    :param directory_path: Path of the directory to be created
    """
    try:
        # Check if the directory already exists
        if not os.path.exists(directory_path):
            # Create the directory
            os.makedirs(directory_path)
            print(f"Directory created successfully: {directory_path}")
        else:
            print(f"Directory already exists: {directory_path}")
    except OSError as e:
        print(f"Error creating directory {directory_path}: {e}")

print("######################################"
      "###########SET UP INITIATED###########"
      "######################################"
      )
ROOT_PATH = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(ROOT_PATH, "config")
create_directory(CONFIG_PATH)

s3_bucket_name = 'inference-cost-tracing'
s3_config_file = 'config/config.json'
s3_models_file = 'config/models.json'

config_json = json.loads(utils.get_s3_file_content(s3_bucket_name, s3_config_file))
models_json = json.loads(utils.get_s3_file_content(s3_bucket_name, s3_models_file))

CONFIG_JSON = os.path.join(CONFIG_PATH, "config.json")
MODELS_JSON = os.path.join(CONFIG_PATH, "models.json")

with open(CONFIG_JSON, "w") as outfile:
    json.dump(config_json, outfile)

with open(MODELS_JSON, "w") as outfile:
    json.dump(models_json, outfile)


print("######################################"
      "###########CREATE IAM ROLES###########"
      "######################################")
create_iam_role.main()
print("######################################"
      "#######CREATE INFERENCE PROFILES######"
      "######################################")
create_interence_profiles.main()
print("######################################"
      "####SET UP DASHBOARD AND SNS ALERTS###"
      "######################################")
setup_cloudwatch_sns.main()
print("######################################"
      "########DEPLOY LAMBDA FUNCTION########"
      "######################################")
deploy_lambda.main()
print("######################################"
      "#############GENERATE API#############"
      "######################################")
setup_api_gateway.main()

