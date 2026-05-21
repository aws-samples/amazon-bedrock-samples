import time
import random
import json
import requests
from scripts import s3_bucket_name, s3_config_file
from scripts.utils import get_s3_file_content

large_prompt = """
Uruguay is a small South American country situated on the Atlantic coast, known for its rolling hills, fertile land, and picturesque coastline; it is the second smallest country in South America. With its capital city being Montevideo, Uruguay is sparsely populated, with most residents concentrated in the southern half of the country. The official language is Spanish, reflecting its European colonial heritage, and the majority of the population is of European descent. Uruguay is recognized for its progressive social policies, including legalized same-sex marriage, and boasts a well-developed social security and healthcare system.
"""

price_file = 'config/models.json'
queries = [
    "What is the weather like in Punta del Este in July?",
    "Why is Uruguay so great at Soccer? Give me the entire history of Uruguayan Soccer",
    "Where can I get mate tea in Seattle",
    "Where is the widest river located? Rank the top 10 based on geography data, do not use historical rivers, only the current",
    "How many letters are in the acronym AAA?",
    "Who are the top most influential people in Uruguay?",
    "What is the second largest city in Uruguay? what is its history? who are some famous people from there? why is it named like that?",
    "What has more caffeine a traditional Mate drink or Coffee?",
    "What is Lunfardo and where does it come from? give me the history of all places of origin of the pople that created it",
    "How can I become better at coding",
    "Write the the first page of the Don Quixote book as if you were Miguel de Cerbantes",
    f"{large_prompt}\n.Write a poem using the information above",
]


# Replace with your actual API Gateway endpoint
api_gateway_endpoint = "https://your-api-id.execute-api.your-region.amazonaws.com/your-stage/invoke"

def lambda_handler(event, context):
    # This is where you'd implement your inference logic
    print(event)
    return {
        'statusCode': 200,
        'body': json.dumps({
            'inference': "This is a placeholder for the inference result.",
            'profile_used': event['headers']['inference-profile-id']
        }),
        'headers': {
            'Content-Type': 'application/json'
        }
    }

def test_api():
    config_json = json.loads(get_s3_file_content(s3_bucket_name, s3_config_file))
    for ip_dic in config_json['profile_ids']:
        ip = next(iter(ip_dic.values()))
        n_inf = random.randrange(9, 13)
        for q in queries[:n_inf]:
            print(q)
            sleep_time = random.randrange(3, 12)
            time.sleep(sleep_time)
            event = {
                "headers": {
                    "inference-profile-id": ip,
                    "content-type": "application/json",
                    "region": "us-west-2"
                },
                "body": [
                    {
                        "role": "user",
                        "content": [{"text": q}],
                    }
                ]
            }

            # Make the API call
            response = requests.post(api_gateway_endpoint, headers=event['headers'], json=event['body'])
            print(response.json())

if __name__ == "__main__":
    test_api()
