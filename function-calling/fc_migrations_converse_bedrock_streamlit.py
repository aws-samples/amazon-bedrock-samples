import streamlit as st
import boto3
import json
from datetime import datetime
import pprint

### Constants  
region = 'us-west-2'
MODEL_IDS = [
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "cohere.command-r-plus-v1:0",
    "cohere.command-r-v1:0",
    "mistral.mistral-large-2402-v1:0",
]
### Setup boto3 client
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=region,
)

### Functions
### Function for translating OAI tool spec to Bedrock Converse
def oai_call_to_bedrock_call(oai_call: dict) -> dict:
    _functions = []
    for _function in oai_call['functions']: 
        _functions.append({
            "toolSpec": {
                "name": _function["name"],
                "description": _function["description"],
                "inputSchema": {
                    "json": _function["parameters"]
                }
            }
        })

    _messages = []
    for _message in oai_call['messages']:
        _messages.append({
            "role": _message["role"],
            "content": [ 
                {
                    "text": _message["content"]
                }                
            ]})
        
    return {
        "messages": _messages,
        "toolConfig": {
            "tools": _functions
        }
    }

### Function for invoking Bedrock Converse
def converse_with_tools(messages: dict, system: str="", toolConfig: dict={},
                        modelId = 'anthropic.claude-3-sonnet-20240229-v1:0'):
    system_prompt = [{"text": system}]

    response = bedrock.converse(
        modelId=modelId,
        system=system_prompt,
        messages=messages,
        toolConfig=toolConfig
    )
    return response

# Streamlit UI
st.set_page_config(layout="wide")
st.markdown("### Converse API for Amazon Bedrock - Function-Calling Migration Demo")
st.markdown(
    """
    <style>
        [data-testid=stSidebar] [data-testid=stImage]{
            text-align: center;
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True
)
st.sidebar.image('./images/bedrock.png', width=60)
st.sidebar.divider()
modelId = st.sidebar.selectbox("**Model ID (for testing the function):**", MODEL_IDS, index=0)
st.sidebar.divider()
st.sidebar.image('./images/AWS_logo_RGB.png', width=40)

tabs = st.tabs(["Conversion", "Output"])

st.markdown("**Enter your original message-structured prompt and function definition JSON:**")

with st.expander("Example", expanded=False):
    st.markdown("""{
  "model": "gpt-3.5-turbo-0613",
  "messages": [
    {
      "role": "user",
      "content": "Schedule a meeting with John Doe next Tuesday at 3 PM."
    }
  ],
  "functions": [
    {
      "name": "schedule_meeting",
      "description": "Please schedule a meeting.",
      "parameters": {
        "type": "object",
        "properties": {
          "attendee": {
            "type": "string",
            "description": "Attendee for the meeting"
          },
          "date": {
            "type": "string",
            "description": "Date of the meeting"
          },
          "time": {
            "type": "string",
            "description": "Time of the meeting"
          }
        }
      }
    }
  ]
}""")
openai_json = st.text_area("Original JSON", height=300)

### Convert on-click
if st.button("Convert"):
    try:
        openai_call = json.loads(openai_json)
    except:
        e = RuntimeError('Invalid JSON provided')
        st.exception(e)
    bedrock_call = oai_call_to_bedrock_call(openai_call)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Original Definition:**")
        st.json(openai_call)
    with col2:
        st.markdown("**Converted Bedrock Converse Definition:**")
        st.json(bedrock_call)
    st.divider()
    with st.container():
        st.markdown("**Prompt:**")
        st.json(openai_call['messages'])
        st.markdown("**Model Response:**")
        with st.spinner("In progress..."):
            output = converse_with_tools(bedrock_call['messages'], 
                                        system="you are a helpful assistant",
                                        modelId=modelId,
                                        toolConfig=bedrock_call['toolConfig'])
        st.json(output['output'])