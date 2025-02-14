import boto3
import json
import os
from scripts.utils import get_s3_file_content
from scripts import s3_bucket_name, s3_config_file
from scripts.upload_to_s3 import upload_file_to_s3


ROOT_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_PATH, "config")
CONFIG_JSON = os.path.join(CONFIG_PATH, "config.json")
config_ = json.loads(get_s3_file_content(s3_bucket_name, s3_config_file))

def create_inference_profile(
        bedrock_client, inference_profile_name, model_id, description, tags
):
    try:
        # Construct the model source ARN
        region = bedrock_client.meta.region_name
        model_arn = f"arn:aws:bedrock:{region}::foundation-model/{model_id}"

        response = bedrock_client.create_inference_profile(
            inferenceProfileName=inference_profile_name,
            modelSource={"copyFrom": model_arn},
            description=description,
            tags=tags
        )

        print(f"Inference Profile '{inference_profile_name}' created successfully.")
        return response['inferenceProfileArn']
    except Exception as e:
        print(f"Error creating Inference Profile '{inference_profile_name}': {e}")


def main():
    # Load configuration
    config_file = get_s3_file_content(s3_bucket_name, s3_config_file)
    config = json.loads(config_file)

    bedrock_client = boto3.client('bedrock', region_name=config['aws_region'])
    model_id = config['model_id']
    profiles = config['profiles']
    profiles_id = []
    for profile in profiles:
        tags = profile['tags']
        # Convert list of dicts to required format
        formatted_tags = [{'key': t['key'], 'value': t['value']} for t in tags]

        ip_arn = create_inference_profile(
            bedrock_client,
            inference_profile_name=profile['name'],
            model_id=model_id,
            description=profile['description'],
            tags=formatted_tags
        )
        profiles_id.append({profile['name']: ip_arn.split('/')[-1]})

    config['profile_ids'] = profiles_id
    with open(CONFIG_JSON, "w") as outfile:
        json.dump(config, outfile)
    upload_file_to_s3(CONFIG_JSON, s3_bucket_name, "config")

if __name__ == '__main__':
    main()