import streamlit as st
from threading import Thread
import boto3
import json
import pandas as pd
from botocore.config import Config

print('Boto3 version:', boto3.__version__)

### Streamlit setup
st.set_page_config(layout="wide")
my_config = Config(read_timeout=600,
                   retries={
                       'max_attempts': 10,
                       'mode': 'standard'
                   })

### Constants
REGION = 'us-east-1'
MODEL_IDS = [
    "amazon.titan-text-premier-v1:0",
    "amazon.titan-text-express-v1",
    "amazon.titan-text-lite-v1",
    "ai21.j2-ultra-v1",
    "ai21.j2-mid-v1",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "cohere.command-r-plus-v1:0",
    "cohere.command-r-v1:0",
    "meta.llama3-70b-instruct-v1:0",
    "meta.llama3-8b-instruct-v1:0",
    "mistral.mistral-large-2402-v1:0",
    "mistral.mixtral-8x7b-instruct-v0:1",
    "mistral.mistral-7b-instruct-v0:2",
    "mistral.mistral-small-2402-v1:0"
]
messages = []

### Function for invoking Bedrock Converse
def invoke_bedrock_model(client, id, prompt, max_tokens=2000, temperature=0, top_p=0.9):
    response = ""
    messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
    ]
    try:
        response = client.converse(
            modelId=id,
            messages=messages,
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": max_tokens,
                "topP": top_p
            }
            # additionalModelRequestFields={
            # }
        )
    except Exception as e:
        print(e)
        result = "Model invocation error"
    try:
        result = {
            'Request': {
                'modelId': id,
                'messages': messages,
                'inferenceConfig': {
                    'temperature': temperature,
                    'maxTokens': max_tokens,
                    'topP': top_p
                },
            },
            'Response': {
                'output': response['output'],
                'stopReason': response['stopReason'],
                'usage': response['usage'],
                'metrics': response['metrics']
            }
        }
    except Exception as e:
        print(e)
        result = "Output parsing error"
    return result

### Class for theading calls
class ModelThread(Thread):
    def __init__(self, model_id, prompt):
        Thread.__init__(self)
        self.model_id = model_id
        self.model_response = None
        self.prompt = prompt
        self.client = boto3.client("bedrock-runtime", region_name=REGION, config=my_config)

    def run(self):
        response = invoke_bedrock_model(self.client, self.model_id, self.prompt)
        self.model_response = response
        print(f'{self.model_id} DONE')

### Function for invoking models in parallel
def invokeModelsInParallel(prompt):
    threads = [ModelThread(model_id=m, prompt=prompt) for m in MODEL_IDS]
    for thread in threads:
        thread.start()
    model_responses = {}
    for thread in threads:
        thread.join()
        model_responses[thread.model_id] = thread.model_response
    return model_responses

col1, col2 = st.columns([1, 9])
with col1:
    st.image('./images/bedrock.png', width=60)
with col2:
    st.write("#### Converse API for Amazon Bedrock - Model Choice Demo")

tabs = st.tabs(["Model Responses", "Message Details"])

with tabs[0]:
    st.markdown = "Write your prompt..."
    prompt = st.text_input("Input Prompt")

    if st.button('Go') or prompt != '':
        with st.spinner('Generating...'):
            model_responses = invokeModelsInParallel(prompt)
            with tabs[1]:
                for model_id, response in model_responses.items():
                    with st.expander(model_id):
                        st.json(response)
            table = [[key, value['Response']['output']['message']['content'][0]['text']] for key, value in model_responses.items()]
            df = pd.DataFrame(table, columns=['Model', 'ModelResponse'])
            df.index += 1
            st.table(df)

