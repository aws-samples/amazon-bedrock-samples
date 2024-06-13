import streamlit as st
import boto3
import sys
import json
from botocore.config import Config 

### Streamlit setup
st.set_page_config(layout="wide")
my_config = Config(read_timeout=600,
                   retries = {
                        'max_attempts': 10,
                        'mode': 'standard'
                    })
st.sidebar.image('./images/bedrock.png', width=60)

### Models available for Amazon Bedrock Converse API
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

st.sidebar.divider()
selected_model_id = st.sidebar.selectbox("**Select Model ID**", MODEL_IDS, index=6)

# Initialize boto3 client
region = 'us-east-1'
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=region,
)

st.markdown("### Amazon Bedrock Converse API Example")

tabs = st.tabs(["Chat", "Details"])

# Initialize session state
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "details" not in st.session_state:
    st.session_state.details = []

# Function to invoke Bedrock Converse
def invoke_bedrock_model(client, model_id, messages, max_tokens=2000, temperature=0, top_p=0.9):
    response = client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={
            "temperature": temperature,
            "maxTokens": max_tokens,
            "topP": top_p
        }
    )
    return response

# Chat tab
with tabs[0]:
    conversation_placeholder = st.empty()
    user_input = st.text_input("You:")
    if user_input:
        st.session_state.conversation.append({"role": "user", "content": user_input})
        metrics = st.empty()

        # Prepare messages for the model
        messages = [
            {
                "role": msg["role"],
                "content": [{"text": msg["content"]}]
            } for msg in st.session_state.conversation
        ]
        
        response = invoke_bedrock_model(bedrock, selected_model_id, messages)
        
        result = response['output']['message']['content'][0]['text']
        latency = response['metrics']['latencyMs']
        input_tokens = response['usage']['inputTokens']
        output_tokens = response['usage']['outputTokens']
        
        st.session_state.conversation.append({"role": "assistant", "content": result})
        
        conversation_placeholder.markdown(f"You: {user_input}\n\nAssistant: {result}\n\n***Last message metrics: Latency {latency} ms, Input Tokens {input_tokens}, Output Tokens {output_tokens}***")

        # Store the details
        st.session_state.details.append({
            "request": {
                "modelId": selected_model_id,
                "messages": messages,
                "inferenceConfig": {
                    "temperature": 0,
                    "maxTokens": 2000,
                    "topP": 0.9
                }
            },
            "response": response
        })

    st.divider()
    st.markdown("**Conversation history**")

    for message in st.session_state.conversation:
        if message['role'] == 'user':
            st.markdown(f"**You:** {message['content']}")
        else:
            st.markdown(f"**Assistant:** {message['content']}")

# Details tab
with tabs[1]:
    st.header("Messages Details")
    
    if st.session_state.details:
        for detail in st.session_state.details:
            with st.expander("Request and Response JSON"):
                st.json({
                    "request": detail["request"],
                    "response": detail["response"]
                })
    else:
        st.write("No details available.")