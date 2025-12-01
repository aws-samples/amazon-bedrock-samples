import json
import boto3

def get_streamlit_url():
    try:
        # Read the JSON file
        with open('/opt/ml/metadata/resource-metadata.json', 'r') as file:
            data = json.load(file)
            domain_id = data['DomainId']
            space_name = data['SpaceName']
    except FileNotFoundError:
        print("Resource-metadata.json file not found -- running outside SageMaker Studio")
        domain_id = None
        space_name = None
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in resource-metadata.json")
    except KeyError as e:
        print(f"Error: Required key {e} not found in JSON")
    
    # Now you can use domain_id and space_name variables in your code
    print(f"Domain ID: {domain_id}")
    print(f"Space Name: {space_name}")
    
    if domain_id is not None:
        sagemaker_client = boto3.client('sagemaker')

        response = sagemaker_client.describe_space(
            DomainId=domain_id,
            SpaceName=space_name
        )
        
        streamlit_url = response['Url']+"/proxy/8501/"
    else:
        streamlit_url = "http://localhost:8501"
    return streamlit_url