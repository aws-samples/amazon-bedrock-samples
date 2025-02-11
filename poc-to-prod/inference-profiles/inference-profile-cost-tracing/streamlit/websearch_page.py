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

    # Submit button
    if st.button("Submit"):
        if user_input:
            # Action that happens after button press
            st.success(invoke_api(user_input))
        else:
            st.warning("Please enter some text")

def invoke_api(user_input):
    #Look for inference profile ID from config file 

    #Get the absolute path of the directory containing the streamlit page
    current_dir = os.path.dirname(os.path.abspath(__file__))
    #Get path of config file in relation to streamlit page
    config_path = os.path.join(current_dir, "config.json")

    #dynamically create inference profile name for search:
    search_name = st.session_state.user_name+"-Websearch"
    
    with open(config_path, "r") as file:
        config = json.load(file)
        profile_id = next(item[search_name] for item in config["profile_ids"] if search_name in item)

    url = "https://5kdzf9q1yf.execute-api.us-west-2.amazonaws.com/Prod"
    payload = {
        "headers": {
            "inference-profile-id": profile_id,
            "region": "us-west-2"
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
