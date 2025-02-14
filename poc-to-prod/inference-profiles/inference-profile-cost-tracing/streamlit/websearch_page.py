import streamlit as st
import boto3 
import json
import os
import requests

def main():
    # Check if user is authenticated
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.error("Please login first")
        st.stop()
    
    st.title("Welcome to Websearch Bot")
    st.caption("Logged in as: "+st.session_state.user_name)

    # Text input box
    user_input = st.text_input("Enter your text:")

    # New textbox for extra tags
    extra_tags = st.text_area("Enter additional tags (one per line, format: key:value):")

    # Submit button
    if st.button("Submit"):
        if user_input:
            # Parse extra tags
            additional_tags = parse_extra_tags(extra_tags)
            # Action that happens after button press
            st.success(invoke_api(user_input, additional_tags))
        else:
            st.warning("Please enter some text")

def parse_extra_tags(extra_tags):
    tags = []
    for line in extra_tags.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            tags.append({"key": key.strip(), "value": value.strip()})
    return tags

def invoke_api(user_input, additional_tags):
    #Change this URL to your own API Gateway URL
    url = "https://gidpxqz1o3.execute-api.us-west-2.amazonaws.com/Prod"
    
    # Combine default tags with additional tags
    default_tags = [
        {"key": "CreatedBy", "value": "Dev-Account"},
        {"key": "ApplicationID", "value": "Web-Search-Bot"},
        {"key": "TenantID", "value": "Customer-1"},
        {"key": "CustomerAccountID", "value": "111111111"},
        {"key": "ModelProvider", "value": "Anthropic"},
        {"key": "ModelName", "value": "Claude-3-haiku-v1"},
        {"key": "Environment", "value": "Dev"}
    ]
    all_tags = default_tags + additional_tags

    payload = {
        "headers": {
            "region": "us-west-2",
            "tags": all_tags
        },
        "body": [
            {
                "role": "user",
                "content": [
                    {
                        "text": "You are a bot that returns answers. Answer the following question and return links to sources: "+user_input
                    }
                ]
            }
        ]
    }
    response = requests.post(url, json=payload)

    # Parse the JSON response
    response_data = response.json()

    # The response_data is already a dictionary, so we don't need to parse it again
    body_content = json.loads(response_data['body'])

    # Extract the text from the message content
    text_content = body_content['message']['content'][0]['text']

    return text_content

if __name__ == "__main__":
    main()
