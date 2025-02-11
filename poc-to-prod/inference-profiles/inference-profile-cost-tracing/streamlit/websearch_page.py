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

    #ADD TEXTBOX FOR EXTRA TAGS 
    
    # Submit button
    if st.button("Submit"):
        if user_input:
            # Action that happens after button press
            st.success(invoke_api(user_input))
        else:
            st.warning("Please enter some text")

def invoke_api(user_input):
    #Look for inference profile ID from config setup file, this will be done in the Lambda Function

    url = "https://gidpxqz1o3.execute-api.us-west-2.amazonaws.com/Prod"
    payload = {
        "headers": {
            "region": "us-west-2",
            "tags": {
            "CreatedBy": "Dev-Account",
            "ApplicationID": "Web-Search-Bot",
            "TenantID": st.session_state.user_name,
            "CustomerAccountID": "123987456",
            "ModelProvider": "Anthropic"
            }
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

    # Parse the body string as JSON
    body = json.loads(response.json()['body'])

    # Navigate through the nested structure
    text = body['message']['content'][0]['text']

    return text
    
if __name__ == "__main__":
    main()
