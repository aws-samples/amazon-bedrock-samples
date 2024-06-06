import streamlit as st
import boto3
from datetime import datetime
import pandas as pd
import json
from pyathena import connect

### Pre-requisite: This demo requires the setup of the example Athena database and table with synthetic data.
### Run the script 'creer_demo_setup.py' to create the database and table.

### Constants
region = 'us-west-2'
MODEL_IDS = [
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "cohere.command-r-plus-v1:0",
    "cohere.command-r-v1:0",
    "mistral.mistral-large-2402-v1:0",
]
bucket = 'bucket' ### REPLACE WITH YOUR AMAZON S3 BUCKET

### Initialize boto3 client
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=region,
)

### Defining tool for reading Amazon Athena catalog
class ToolsList:
    def query_athena(self, query):
        print(f"{datetime.now().strftime('%H:%M:%S')} - Got tool query: {query}\n")
        try:
            cursor = connect(s3_staging_dir=f"s3://{bucket}/athena/",
                                region_name="us-west-2").cursor()
            cursor.execute(query)
            df = pd.DataFrame(cursor.fetchall()).to_string(index=False)
            print(f"{datetime.now().strftime('%H:%M:%S')} - Tool result: {df}\n")
        except Exception as e:
            print(f'{datetime.now().strftime('%H:%M:%S')} - Error: {e}')
            st.exception(e)
            raise
        return df

### Invocation with Bedrock Converse
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

### Orchestration workflow, allows multiple tools (parallel fc)
def converse(modelId, prompt, system='', toolConfig=None):
    ### First invocation
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    st.session_state.history.append(messages)
    flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Invoking model...")
    output = converse_with_tools(modelId, messages, system, toolConfig)
    messages.append(output['output']['message'])
    flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Got output from model...")
    ### Check if function calling
    while True:
        function_calling = next((c['toolUse'] for c in output['output']['message']['content'] if 'toolUse' in c), None)
        if function_calling:
            flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Calling tool...")
            tool_name = function_calling['name']
            tool_args = function_calling['input'] or {}
            ### Calling the tool
            tool_response = getattr(ToolsList(), tool_name)(**tool_args)
            flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Got tool response...")
            ### Add tool result to messages
            tool_result_message = {
                "role": "user",
                "content": [{
                    'toolResult': {
                        'toolUseId': function_calling['toolUseId'],
                        'content': [{"text": tool_response}]
                    }
                }]
            }
            messages.append(tool_result_message)
            flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Calling model with result...")
            ### Second invocation with tool result
            output = converse_with_tools(modelId, messages, system, toolConfig)
            messages.append(output['output']['message'])
            flow.markdown(f"{datetime.now().strftime('%H:%M:%S')} - Function calling - Got model response.")
        else:
            break
    print(f"{datetime.now().strftime('%H:%M:%S')} - Messages history: {json.dumps(messages, indent=2, ensure_ascii=False)}\n")
    return messages, output

### Defining tool schema
toolConfig = {
    'tools': [{
        'toolSpec': {
            'name': 'query_athena',
            'description': 'Query the Acme Bank Athena catalog.',
            'inputSchema': {
                'json': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string', 'description': 'SQL query to run against the Athena catalog'}
                    },
                    'required': ['query']
                }
            }
        }
    }],
}

# Streamlit UI
st.markdown("### Converse API for Amazon Bedrock - Function Calling - Athena SQL Query Demo")
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
    modelId = st.sidebar.selectbox("Model ID", MODEL_IDS, index=0)
    st.sidebar.divider()
    flow = st.sidebar.container(border=True)
    flow.markdown(f"**Flow status:**")
    st.sidebar.divider()
    st.sidebar.image('./images/AWS_logo_RGB.png', width=40)
    with st.expander("Examples", expanded=False):
        st.markdown("""
                    * What were the transactions for Tom Hanks?
                    * What is the balance for Meryl Streep?
                    * How many users have had transactions higher than USD 700?
                    """)

    prompt = st.text_input("Enter your question about the Acme Bank data", "")

    if st.button("Submit"):
        system_prompt = [{"text": f"""You're provided with a tool that can query the Acme Bank Amazon Athena catalog using Hive QL DDL syntax. \
                          The database is called 'acme_bank'.
                          Use this tool to answer the user's question about the bank data.
                          Think step by step and, if required, use the tool to find out the schema of the table first.
                          Provide a detailed but user-friendly response in markdown format."""}]
        with st.spinner("In progress..."):
            messages, output = converse(modelId, prompt, system_prompt, toolConfig)

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

        with tabs[1]:
            st.markdown("**Request Messages**")
            st.json(st.session_state.history)