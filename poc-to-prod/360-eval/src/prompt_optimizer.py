import boto3

# Set values here
TARGET_MODEL_ID = "meta.llama3-3-70b-instruct-v1:0"

PROMPT = """You will be provided with meeting notes, and your task is to summarize the meeting as follows: 
-Overall summary of discussion 
-Action items (what needs to be done and who is doing it) 
-If applicable, a list of topics that need to be discussed more fully in the next meeting."""

def get_input(prompt):
    return {
        "textPrompt": {
            "text": prompt
        }
    }

def handle_response_stream(response):
    try:
        event_stream = response['optimizedPrompt']
        for event in event_stream:
            if 'optimizedPromptEvent' in event:
                print("========================== OPTIMIZED PROMPT ======================\n")
                optimized_prompt = event['optimizedPromptEvent']
                print(optimized_prompt['optimizedPrompt']['textPrompt']['text'])
            else:
                print("========================= ANALYZE PROMPT =======================\n")
                analyze_prompt = event['analyzePromptEvent']
                print(analyze_prompt)
    except Exception as e:
        raise e


if __name__ == '__main__':
    client = boto3.client('bedrock-agent-runtime', region_name='us-west-2')
    try:
        response = client.optimize_prompt(
            input=get_input(PROMPT),
            targetModelId=TARGET_MODEL_ID
        )
        print("Request ID:", response.get("ResponseMetadata").get("RequestId"))
        print("========================== INPUT PROMPT ======================\n")
        print(PROMPT)
        handle_response_stream(response)
    except Exception as e:
        raise e