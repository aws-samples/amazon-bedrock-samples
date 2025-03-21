import lib as lib
import streamlit as st
from lib import get_inference_profiles
from loguru import logger

ASSISTANT_AVATAR = "https://api.dicebear.com/9.x/bottts/svg?seed=Christian"
USER_AVATAR = "https://api.dicebear.com/9.x/notionists/svg?seed=Kingston"

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


# Initialize session state for login status
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login_page():

    with st.form("login_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            if user_id and password:
                response = lib.authenticate_user(user_id, password)
                if response['success']:
                    st.success("Login successful!")
                    st.session_state.logged_in = True
                    st.session_state.username = user_id
                    st.session_state.userrole = ', '.join(response["data"]["cognito:groups"])
                    st.session_state.messages = []
                    st.rerun()  # Rerun the app to show the home page
                else:
                    st.error(response['error_message'])
            else:
                st.error("Please enter both User ID and Password")

def home_page():

    # Display welcome message
    welcome_container = st.container()
    with welcome_container:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.markdown("👋 Hello! I'm here to help. What would you like to discuss?")
            st.markdown(""" You can ask me questions like below:""")
            st.markdown(
                    """ - List all patients with _Obesity_ as Symptom and the recommended medications
- Which patients are currently taking Furosemide and Atorvastatin medications
- Generate a list of all patient names and a summary of their symptoms
- List all patients under _Institution Flores Group Medical Center_
""")

    with st.sidebar:
        st.write("### User Profile")
        st.write(f"Login: {st.session_state.get('username', 'Error')}")
        st.write(f"Role: {st.session_state.get('userrole', 'Error')}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        st.write("### Inference Options")
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

        temperature = st.sidebar.slider(
            "Temperature:",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.01
        )
        top_p = st.sidebar.slider(
            "Top P:",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.01
        )

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

    prompt = st.chat_input("Type your message here...")
    if prompt:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with st.chat_message("user", avatar=USER_AVATAR):
            st.write(prompt)

        # Process the request
        with st.spinner("Processing your request..."):
            response, guardrail_action = lib.query_KB(
                prompt, st.session_state.model_id, temperature, top_p
            )
        # Display assistant response if available
        if response:
            guardrail_intervened = guardrail_action in [
                "INTERVENED",
                "GUARDRAIL_INTERVENED",
            ]
            # Store the message with guardrail intervention status
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                    "guardrail_intervened": guardrail_intervened,
                }
            )
            # Display assistant message
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                if guardrail_intervened:
                    st.markdown("🛡️ **Guardrail Intervened** 🛡️")
                st.markdown(response)
        else:
            st.error("Failed to get a response from the API.")

        st.rerun()

def main():
    if st.session_state.logged_in:
        home_page()
    else:
        login_page()

if __name__ == "__main__":
    main()
