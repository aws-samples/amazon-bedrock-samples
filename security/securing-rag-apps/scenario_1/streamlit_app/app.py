import os

import streamlit as st
import utils
from loguru import logger
from utils import get_bedrock_model_ids

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_page():
    """Login page"""
    with st.form("login_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            if user_id and password:
                response = utils.authenticate_user(user_id, password)
                if response["success"]:
                    st.success("Login successful!")
                    st.session_state.logged_in = True
                    st.session_state.username = user_id
                    st.session_state.userrole = ", ".join(
                        response["data"]["cognito:groups"]
                    )
                    st.session_state.messages = []
                    logger.info("Authentication successful!")
                    st.rerun()  # Rerun the app to show the home page

                else:
                    st.error(response["error_message"])
            else:
                st.error("Please enter both User ID and Password")


def logout():
    st.session_state.role = None
    st.rerun()


def home_page():
    ASSISTANT_AVATAR = "https://api.dicebear.com/9.x/bottts/svg?seed=Christian"
    USER_AVATAR = "https://api.dicebear.com/9.x/notionists/svg?seed=Kingston"
    welcome_container = st.container()
    with welcome_container:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.markdown("👋 Hello! I'm here to help. What would you like to discuss?")
            st.markdown(""" You can ask me questions like below:""")
            st.markdown(
                """ - What medications were recommended for _Chronic migraines_
- Typically what are recommended medications for _shortness of breath_
- List all patients with _Obesity_ as Symptom and the recommended medications
- What is the home address of _Nikhil Jayashankar_
- List all patients under _Institution Flores Group Medical Center_"""
            )

    with st.sidebar:
        st.write("### User Profile")
        st.write(f"Login: {st.session_state.get('username', 'Error')}")
        st.write(f"Role: {st.session_state.get('userrole', 'Error')}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        llm_model_name = st.selectbox(
            "Select Text generation model",
            options=get_bedrock_model_ids(provider="Anthropic"),
            help="Model used for text generation in chat",
        )
        # st.header("Model Parameters")
        temperature = st.slider(
            "Temperature", min_value=0.0, max_value=1.0, value=0.1, step=0.01
        )
        top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.9, step=0.1)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        avatar = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
        with st.chat_message(msg["role"], avatar=avatar):
            st.write(msg["content"])

    # Handle user input
    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)
        with st.spinner("Processing request..."):
            kb_response = utils.query_KB(
                prompt, llm_model_name, temp=temperature, top_p=top_p
            )
        if kb_response:
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                st.write(kb_response)
            st.session_state.messages.append(
                {"role": "assistant", "content": kb_response}
            )
        else:
            st.error("Failed to get a response from the API.")


def main():
    if st.session_state.logged_in:
        home_page()
    else:
        login_page()


if __name__ == "__main__":
    main()
