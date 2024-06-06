import streamlit as st
import boto3
import json
from datetime import datetime
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import io

### Constants
region = 'us-east-1'
MODEL_IDS = [
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "cohere.command-r-plus-v1:0",
    "cohere.command-r-v1:0",
    "mistral.mistral-large-2402-v1:0",
]

### Initialize the Boto3 client for Bedrock
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=region,
)

### Classes
### Example tool for getting weather in city & state as text
class ToolsList:
    def get_weather(self, city, state):
        result = f'Weather in {city, state} is 70F and clear skies.'
        return result
    
### Example tool for getting weather in city & state as both text and image
class ToolsList2:
    def get_weather(self, city, state):
        result = f'Weather in {city, state} is 70F and clear skies.'
        with open('./images/weather.jpg', "rb") as image_file:
            binary_data = image_file.read()
        return result, binary_data

### Example toolset for weather in city & state and running web search
class ToolsList3:
    def get_weather(self, city, state):
        result = f'Weather in {city, state} is 70F and clear skies.'
        return result

    def web_search(self, query):
        results = []
        response_list = []
        results.extend([r for r in search(query, 3, 'en')])
        for j in results:
            response = requests.get(j)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                response_list.append(soup.get_text().strip())
        response_text = ",".join(str(i) for i in response_list)
        return response_text

### Invocation to Bedrock Converse
def converse_with_tools(modelId, messages, system='', toolConfig=None):
    response = bedrock.converse(
        modelId=modelId,
        system=system,
        messages=messages,
        toolConfig=toolConfig
    )
    return response

### Streamlit setup
st.set_page_config(layout="wide")
if "history" not in st.session_state:
    st.session_state.history = []
if "image_result" not in st.session_state:
    st.session_state.image_result = 0

### Orchestration workflow for text response from tool
def converse(tool_class, modelId, prompt, system='', toolConfig=None):
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    st.session_state.history.append(messages)
    flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Invoking model...")
    output = converse_with_tools(modelId, messages, system, toolConfig)
    messages.append(output['output']['message'])
    flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Got output from model...")
    function_calling = [c['toolUse'] for c in output['output']['message']['content'] if 'toolUse' in c]
    if function_calling:
        tool_result_message = {
            "role": "user",
            "content": []
        }
        for function in function_calling:
            flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Calling tool...")
            tool_name = function['name']
            tool_args = function['input'] or {}
            tool_response = getattr(tool_class, tool_name)(**tool_args)
            flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Got tool response...")
            tool_result_message['content'].append({
                'toolResult': {
                    'toolUseId': function['toolUseId'],
                    'content': [{"text": tool_response}]
                }
            })
        messages.append(tool_result_message)
        flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Calling model with result...")
        output = converse_with_tools(modelId, messages, system, toolConfig)
        messages.append(output['output']['message'])
        flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Got final answer.")
    return messages, output

### Orchestration workflow for text & image response from tool
def converse_image(modelId, prompt, system='', toolConfig=None):
    ### First invocation
    st.session_state.image_result = 1
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    st.session_state.history.append(messages)
    flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Invoking model...")
    output = converse_with_tools(modelId, messages, system, toolConfig)
    messages.append(output['output']['message'])
    flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Got output from model...")
    function_calling = next((c['toolUse'] for c in output['output']['message']['content'] if 'toolUse' in c), None)
    ### Check if function calling
    if function_calling:
        flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Calling tool...")
        tool_name = function_calling['name']
        tool_args = function_calling['input'] or {}
        ### Calling the tool
        tool_response, tool_response_image = getattr(ToolsList2(), tool_name)(**tool_args)
        flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Got tool response...")
        ### Add tool result
        tool_result_message = {
            "role": "user",
            "content": [{
                'toolResult': {
                    'toolUseId': function_calling['toolUseId'],
                    'content': [
                        {"text": tool_response},
                        {"image": {"format": "jpeg", "source": {"bytes": tool_response_image}}}
                    ]
                }
            }]
        }
        messages.append(tool_result_message)
        flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Calling model with result...")
        ### Second invocation with tool result
        output = converse_with_tools(modelId, messages, system, toolConfig)
        messages.append(output['output']['message'])
        flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Got final answer.")
    return messages, output

### Basic tool schema definition
toolConfig_basic = {
    'tools': [{
        'toolSpec': {
            'name': 'get_weather',
            'description': 'Get weather of a location.',
            'inputSchema': {
                'json': {
                    'type': 'object',
                    'properties': {
                        'city': {'type': 'string', 'description': 'City of the location'},
                        'state': {'type': 'string', 'description': 'State of the location'}
                    },
                    'required': ['city', 'state']
                }
            }
        }
    }],
    #'toolChoice': {'auto': {}}
}

### Multi-tool schema definition
toolConfig_multi = {
    'tools': [
        {
            'toolSpec': {
                'name': 'get_weather',
                'description': 'Get weather of a location.',
                'inputSchema': {
                    'json': {
                        'type': 'object',
                        'properties': {
                            'city': {'type': 'string', 'description': 'City of the location'},
                            'state': {'type': 'string', 'description': 'State of the location'}
                        },
                        'required': ['city', 'state']
                    }
                }
            }
        },
        {
            'toolSpec': {
                'name': 'web_search',
                'description': 'Search a term in the public Internet.',
                'inputSchema': {
                    'json': {
                        'type': 'object',
                        'properties': {
                            'query': {'type': 'string', 'description': 'Term to search in the Internet'}
                        },
                        'required': ['query']
                    }
                }
            }
        }
    ],
    #'toolChoice': {'auto': {}}
}

# Streamlit UI
st.markdown("### Converse API for Amazon Bedrock - Function-Calling (tool use) Demo")
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
tabs = st.tabs(["Conversation", "Message Details"])

with tabs[0]:
    st.sidebar.image('./images/bedrock.png', width=60)
    st.sidebar.divider()
    example = st.sidebar.selectbox(
        "Choose an example",
        ["Basic Function Calling", "Function Calling with Image", "Multi-Tool Choice"]
    )
    modelId = st.sidebar.selectbox("Model ID", MODEL_IDS, index=0)
    st.sidebar.divider()
    flow = st.sidebar.container(border=True)
    flow.markdown(f"**Flow status:**")
    st.sidebar.divider()
    st.sidebar.image('./images/AWS_logo_RGB.png', width=40)
    
    prompt = st.text_input("Enter your prompt", "")

    if st.button("Submit"):
        if example == "Basic Function Calling":
            system_prompt = [{"text": "You're provided with a tool that can get the weather information for a specific location 'get_weather'; \
                              only use the tool if required. \
                              Don't make reference to the tools in your final answer."}]
            with st.spinner("In progress..."):
                messages, output = converse(ToolsList(), modelId, prompt, system_prompt, toolConfig_basic)
        elif example == "Function Calling with Image":
            system_prompt = [{"text": "You're provided with a tool that can get the weather information for a specific location called 'get_weather'; \
                              only use this tool if required. \
                              Don't make reference to the tools in your final answer."}]
            with st.spinner("In progress..."):
                messages, output = converse_image(modelId, prompt, system_prompt, toolConfig_basic)
                image = 1
        elif example == "Multi-Tool Choice":
            system_prompt = [{"text": "You're provided with a tool that can get the weather information for a specific location 'get_weather', \
                              and another tool to perform a web search for up-to-date information 'web_search'; \
                              use those tools if required. Don't mention the tools in your final answer."}]
            with st.spinner("In progress..."):
                messages, output = converse(ToolsList3(), modelId, prompt, system_prompt, toolConfig_multi)

        st.divider()
        st.markdown("**Conversation**")
        for message in messages:
            role = message['role']
            content_items = message['content']
            for item in content_items:
                if 'text' in item:
                    st.markdown(f"**{role.capitalize()}:** {item['text']}")
                elif 'toolResult' in item:
                    with st.expander(f"**Tool Result**", expanded=True):
                        st.markdown(f"{item['toolResult']['content'][0]['text']}")
                        if st.session_state.image_result == 1:
                            st.image('./weather.jpg', width=400, caption="Weather Image")

        with tabs[1]:
            st.markdown("**Request Messages**")
            st.json(st.session_state.history)
