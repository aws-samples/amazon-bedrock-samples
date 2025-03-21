import os

import streamlit as st
import utils
from loguru import logger
from utils import get_inference_profiles

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# function to store widget state
def store_widget_state(key):
    """Store widget state to session state."""
    st.session_state[key] = st.session_state["_" + key]
    logger.debug(f"Selected {key}: {st.session_state[key]}")

def format_model_names(model_id):
    model_id = model_id.replace("US ", "")
    return model_id


def init_session_state():
    if "llm_model_name" not in st.session_state:
        st.session_state.llm_model_name = None
    if "model_id" not in st.session_state:
        st.session_state.model_id = None


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
    # Initialize session state at the beginning
    init_session_state()

    ASSISTANT_AVATAR = "https://api.dicebear.com/9.x/bottts/svg?seed=Christian"
    USER_AVATAR = "https://api.dicebear.com/9.x/notionists/svg?seed=Kingston"
    welcome_container = st.container()
    with welcome_container:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.markdown("👋 Hello! I'm here to help. What would you like to discuss?")
            st.markdown(""" You can ask me questions like below:""")
            st.markdown(
                """ - What medications were recommended for _Chronic migraines_
- Summarize retirement planning meeting notes
- Typically what are recommended medications for _shortness of breath_
- List all patients with _Obesity_ as Symptom and the recommended medications
- Can you get me John Doe's email address?
- You are a banking assistant designed to help users with their banking information. You are polite, kind and helpful. Now answer the following question: What is the account number for John Doe"""
            )

    with st.sidebar:
        st.write("### User Profile")
        st.write(f"Login: {st.session_state.get('username', 'Error')}")
        st.write(f"Role: {st.session_state.get('userrole', 'Error')}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        # Model selection
        inf_profiles = get_inference_profiles(provider="Anthropic")
        model_id = st.selectbox(
            "Select Model",
            options=list(inf_profiles.keys()),
            key="_llm_model_name",
            help="Select the model to be used for chat application.",
            on_change=store_widget_state,
            args=["llm_model_name"],
            format_func=format_model_names,
        )
        st.session_state.model_id = inf_profiles[model_id]
        # llm_model_name = st.selectbox(
        #     "Select Text generation model",
        #     options=get_bedrock_model_ids(provider="Anthropic"),
        #     help="Model used for text generation in chat",
        # )
        st.header("Model Parameters")
        temperature = st.slider(
            "Temperature", min_value=0.0, max_value=1.0, value=0.1, step=0.1
        )
        top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.9, step=0.1)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        avatar = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
        with st.chat_message(msg["role"], avatar=avatar):
            # Check if this message had a guardrail intervention
            if msg["role"] == "assistant" and msg.get("guardrail_intervened", False):
                st.markdown("🛡️ **Guardrail Intervened** 🛡️")
            st.write(msg["content"])

    # Handle user input
    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)
        with st.spinner("Processing request..."):
            kb_response, guardrail_action = utils.query_KB(
                prompt, st.session_state.model_id, temp=temperature, top_p=top_p
            )
        if kb_response:
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                # Display guardrail intervention notice if applicable
                guardrail_intervened = guardrail_action in [
                    "INTERVENED",
                    "GUARDRAIL_INTERVENED",
                ]
                if guardrail_intervened:
                    logger.debug("Guardrail Intervened")
                    st.markdown("🛡️ **Guardrail Intervened** 🛡️")
                st.markdown(kb_response)

            # Store the message with guardrail intervention status
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": kb_response,
                    "guardrail_intervened": guardrail_intervened,
                }
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
