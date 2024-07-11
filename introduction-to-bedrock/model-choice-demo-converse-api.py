from threading import Thread
import boto3 
import json 
import pandas as pd

print('Boto3 version:', boto3.__version__)

### Contants
REGION = 'us-east-1'
MODEL_IDS = [
{'id':"arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-text-premier-v1:0", 'name': 'Amazon Titan Premier'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-text-express-v1", 'name': 'Amazon Titan Express'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-text-lite-v1", 'name': 'Amazon Titan Lite'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/ai21.j2-ultra-v1", 'name': 'AI21 Jurassic Ultra'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/ai21.j2-mid-v1", 'name': 'AI21 Jurassic Mid'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0", 'name': 'Anthropic Claude 3 Sonnet'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0", 'name': 'Anthropic Claude 3 Haiku'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/cohere.command-r-plus-v1:0", 'name': 'Cohere Command R Plus'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/cohere.command-r-v1:0", 'name': 'Cohere Command R'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-70b-instruct-v1:0", 'name': 'Meta Llama3 70B Instruct'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-8b-instruct-v1:0", 'name': 'Meta Llama3 8B Instruct'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/mistral.mistral-large-2402-v1:0", 'name': 'Mistral Mistral Large'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/mistral.mixtral-8x7b-instruct-v0:1", 'name': 'Mistral Mixtral 8x7B'},
{'id':"arn:aws:bedrock:us-east-1::foundation-model/mistral.mistral-7b-instruct-v0:2", 'name': 'Mistral Mistral 7B'},
]

### Function for invoking Bedrock Converse
def invoke_bedrock_model(client, id, prompt, max_tokens=2000, temperature=0, top_p=0.9):
    response = ""
    try:
        response = client.converse(
            modelId=id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": max_tokens,
                "topP": top_p
            }
            #additionalModelRequestFields={
            #}
        )
    except Exception as e:
        print(e)
        result = "Model invocation error"
    try:
        result = response['output']['message']['content'][0]['text'] \
        + '   -   Latency: ' + str(response['metrics']['latencyMs']) \
        + 'ms Input tokens:' + str(response['usage']['inputTokens']) \
        + ' Output tokens:' + str(response['usage']['outputTokens'])
        return result
    except Exception as e:
        print(e)
        result = "Output parsing error"
    return result

### Function for threading
class ModelThread(Thread):
    def __init__(self, model_id, model_name, prompt):
        Thread.__init__(self)
        self.model_id = model_id
        self.model_name = model_name
        self.model_response = None
        self.prompt = prompt
        self.client = boto3.client("bedrock-runtime", region_name=REGION)
    def run(self):
        response = invoke_bedrock_model(self.client, self.model_id, self.prompt)
        self.model_response = response
        print(f'{self.model_name} DONE')

### Function for invoking models in parallel
def invokeModelsInParallel(prompt):
    threads = [ModelThread(m['id'], m['name'], prompt) for m in MODEL_IDS]
    for thread in threads:
        thread.start()
    model_responses = {}
    for thread in threads:
        thread.join()
        model_responses[thread.model_name] = thread.model_response
    return model_responses

### Example prompt and outputs
### CHANGE THIS PROMPT TO YOUR OWN ###
prompt = "What is the capital of Spain?"
model_responses = invokeModelsInParallel(prompt)        
table = [[key, value] for key, value in model_responses.items()]
df = pd.DataFrame(table, columns=['Model', 'ModelResponse']) 
df.index += 1
print(df.to_string())