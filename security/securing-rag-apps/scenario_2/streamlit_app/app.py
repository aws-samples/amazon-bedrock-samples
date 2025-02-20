import streamlit as st
import lib as lib
from lib import get_bedrock_model_ids

ASSISTANT_AVATAR = "https://api.dicebear.com/9.x/bottts/svg?seed=Christian"
USER_AVATAR = "https://api.dicebear.com/9.x/notionists/svg?seed=Kingston"

# Initialize session state for login status
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def login_page():
    with st.form("login_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            if user_id and password:
                response = lib.authenticate_user(user_id, password)
                if response["success"]:
                    st.success("Login successful!")
                    st.session_state.logged_in = True
                    st.session_state.username = user_id
                    st.session_state.userrole = ", ".join(
                        response["data"]["cognito:groups"]
                    )
                    st.session_state.messages = []
                    st.rerun()  # Rerun the app to show the home page
                else:
                    st.error(response["error_message"])
            else:
                st.error("Please enter both User ID and Password")


def home_page():
    with st.sidebar:
        st.write("### User Profile")
        st.write(f"Login: {st.session_state.get('username', 'Error')}")
        st.write(f"Role: {st.session_state.get('userrole', 'Error')}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        st.write("### Inference Options")
        # model_id = st.sidebar.selectbox("Model ID: ",['anthropic.claude-3-haiku-20240307-v1:0','anthropic.claude-3-sonnet-20240229-v1:0','us.anthropic.claude-3-opus-20240229-v1:0','us.anthropic.claude-3-5-sonnet-20241022-v2:0','us.meta.llama3-2-11b-instruct-v1:0'])
        claude_models = get_bedrock_model_ids(provider="Anthropic")
        model_id = st.selectbox(
            "Select Text generation model",
            options=claude_models,
            help="Model used for text generation in chat",
        )
        temperature = st.sidebar.slider(
            "Temperature:", min_value=0.0, max_value=1.0, value=0.0, step=0.01
        )
        top_p = st.sidebar.slider(
            "Top P:", min_value=0.0, max_value=1.0, value=1.0, step=0.01
        )

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        avatar = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
        with st.chat_message(msg["role"], avatar=avatar):
            st.write(msg["content"])

    # Display welcome message
    if not st.session_state.messages:
        welcome_container = st.container()
        with welcome_container:
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                st.markdown(
                    "👋 Hello! I'm here to help. What would you like to discuss?"
                )
                st.markdown(""" You can ask me questions like below:""")
                st.markdown(
                    """ - List all patients with _Obesity_ as Symptom and the recommended medications
- List all patients under _Institution Flores Group Medical Center_
- Which patients are currently taking Furosemide and Atorvastatin medications
- Generate a list of all patient names and a summary of their symptoms"""
                )

    prompt = st.chat_input("Type your message here...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.write(prompt)
        response = lib.query_KB(prompt, model_id, temperature, top_p)
        if response:
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            st.error("Failed to get a response from the API.")


def main():
    if st.session_state.logged_in:
        home_page()
    else:
        login_page()


if __name__ == "__main__":
    main()
