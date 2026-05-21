import os
import json
from scripts import utils
from scripts import unsetup_s3,unsetup_api_gateway, unsetup_lambda, unsetup_inference_profiles
from scripts.utils import get_s3_file_content
from scripts import s3_config_file
import json


print("######################################"
      "###########SET UP INITIATED###########"
      "######################################"
      )
ROOT_PATH = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(ROOT_PATH, "config")

s3_config_file = 'config/config.json'
s3_models_file = 'config/models.json'

CONFIG_JSON = os.path.join(CONFIG_PATH, "config.json")
MODELS_JSON = os.path.join(CONFIG_PATH, "models.json")


with open(CONFIG_JSON) as configfile:
    config_json = json.load(configfile)

s3_bucket_name = config_json['s3_bucket_name'] 
# Load configuration
config = json.loads(get_s3_file_content(s3_bucket_name, s3_config_file))
region = config['aws_region']


print("######################################"
      "#############DELETE API#############"
      "######################################")
api_id = config['api_id']
unsetup_api_gateway.main(api_id, region, s3_bucket_name)

print("######################################"
      "#############DELETE LAMBDA#############"
      "######################################")
function_name = config['lambda_function_name']
unsetup_lambda.main(function_name, region)

print("######################################"
      "#######CREATE INFERENCE PROFILES######"
      "######################################")
profile_ids = config['profile_ids']
unsetup_inference_profiles.main(profile_ids, region)

print("######################################"
      "#######EMPTY S3 BUCKET######"
      "######################################")
unsetup_s3.main(s3_bucket_name, region)