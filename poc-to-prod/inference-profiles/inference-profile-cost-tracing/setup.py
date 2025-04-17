import os
import json
import uuid
from scripts import utils
from scripts import create_iam_role, create_interence_profiles, setup_cloudwatch_sns, deploy_lambda, setup_api_gateway, upload_to_s3


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

uuid_tag = str(uuid.uuid4())
#IF YOU ARE RUNNING THIS ON A WINDOWS MACHINE ADDRESS THE FOLLOWING COMMENTS (LINE 35 & LINE 39). IF YOU ARE ON A MAC PLEASE IGNORE THIS.
s3_bucket_name = f'inference-cost-tracing-{uuid_tag}' #HARDCODE YOUR OWN PRE-CREATED S3 BUCKET NAME INTO THIS LINE
s3_config_file = 'config/config.json'
s3_models_file = 'config/models.json'

upload_to_s3.create_bucket(s3_bucket_name) #IF YOU HAVE ENTERED YOUR OWN PRE-CREATED BUCKET NAME INTO LINE 35, COMMENT OUT THIS LINE

CONFIG_JSON = os.path.join(CONFIG_PATH, "config.json")
MODELS_JSON = os.path.join(CONFIG_PATH, "models.json")

with open(CONFIG_JSON) as configfile:
    config_json = json.load(configfile)

config_json['s3_bucket_name'] = s3_bucket_name

with open(CONFIG_JSON, "w") as outfile:
    json.dump(config_json, outfile)

upload_to_s3.upload_file_to_s3(CONFIG_JSON, s3_bucket_name, 'config')
upload_to_s3.upload_file_to_s3(MODELS_JSON, s3_bucket_name, 'config')

print("######################################"
      "###########CREATE IAM ROLES###########"
      "######################################")
create_iam_role.main(s3_bucket_name)
print("######################################"
      "#######CREATE INFERENCE PROFILES######"
      "######################################")
create_interence_profiles.main(s3_bucket_name)
print("######################################"
      "####SET UP DASHBOARD AND SNS ALERTS###"
      "######################################")
setup_cloudwatch_sns.main(s3_bucket_name)
print("######################################"
      "########DEPLOY LAMBDA FUNCTION########"
      "######################################")
deploy_lambda.main(s3_bucket_name)
print("######################################"
      "#############GENERATE API#############"
      "######################################")
setup_api_gateway.main(s3_bucket_name)

