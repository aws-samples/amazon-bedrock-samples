import time

import streamlit as st
import utils
from loguru import logger
from utils import get_inference_profiles

# App configuration and branding
st.set_page_config(
    page_title="Secure Chatbot Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS for custom styling
st.markdown(
    """
<style>
    .app-header {
        color: #4169E1;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .app-subheader {
        color: #708090;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .guardrail-badge {
        background-color: #FF5733;
        color: white;
        padding: 0.3rem 0.5rem;
        border-radius: 0.5rem;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    .footer {
        margin-top: 3rem;
        text-align: center;
        color: #708090;
        font-size: 0.8rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

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
    if "conversation_start_time" not in st.session_state:
        st.session_state.conversation_start_time = time.time()


def login_page():
    """Login page"""
    st.markdown(
        "<h1 class='app-header'>Secure Chatbot Assistant</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='app-subheader'>Scenario 1: Knowledge base indexed with redacted sensitive data.</p>",
        unsafe_allow_html=True,
    )

    # Two-column layout for login form and info
    col1, col2 = st.columns([1, 1])

    with col1:
        with st.form("login_form"):
            st.subheader("Login")
            user_id = st.text_input("User ID")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login", use_container_width=True)

            if submit_button:
                if user_id and password:
                    with st.spinner("Authenticating..."):
                        response = utils.authenticate_user(user_id, password)
                    if response["success"]:
                        st.success("Login successful!")
                        st.session_state.logged_in = True
                        st.session_state.username = user_id
                        st.session_state.userrole = ", ".join(
                            response["data"]["cognito:groups"]
                        )
                        st.session_state.messages = []
                        st.session_state.conversation_start_time = time.time()
                        logger.info("Authentication successful!")
                        st.rerun()  # Rerun the app to show the home page
                    else:
                        st.error(response["error_message"])
                else:
                    st.error("Please enter both User ID and Password")

    with col2:
        st.subheader("About this Application")
        st.info(
            """
        This is a secure chatbot assistant integrated with Amazon Bedrock knowledge bases.

        - **Data Protection**: Sensitive data is identified and redacted before ingestion to the knowledge base
        - **Guardrails**:  Both input and output are protected by guardrails
        - **Knowledge Base**: Data ingested with sensitive data redacted. Titan Text Embeddings v2 generates and store vector embeddings in Amazon OpenSearch vector store

        This is **Scenario 1:** Data identification and redaction before ingestion to Amazon Bedrock Knowledge Base.
        """
        )

    # Footer
    st.markdown(
        "<div class='footer'>Powered by Amazon Bedrock & Amazon Cognito</div>",
        unsafe_allow_html=True,
    )


def logout():
    st.session_state.role = None
    st.rerun()


def home_page():
    # Initialize session state at the beginning
    init_session_state()

    ASSISTANT_AVATAR = "https://api.dicebear.com/9.x/bottts/svg?seed=Christian"
    USER_AVATAR = "https://api.dicebear.com/9.x/lorelei/svg?seed=Sophia"

    # Header
    st.markdown("<h1 class='app-header'>Chatbot Assistant 💬</h1>", unsafe_allow_html=True)
    st.markdown("<p class='app-subheader'>AI-powered knowledge base assistant with advanced security guardrails</p>", unsafe_allow_html=True)

    welcome_container = st.container()
    with welcome_container:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            st.markdown("👋 Hello! I'm here to help. What would you like to discuss?")
            st.markdown(""" You can ask me questions like below:""")
            st.markdown(
                """ - What medications are typically recommended for patients with _Chronic migraines_
- List recommended medications for _shortness of breath_. Output in markdown table format.
- List all patients with _Obesity_ as Symptom and the recommended medications
- Can you get me John Doe's email address?
- You are a chemistry expert designed to assist users with information related to chemicals and compounds. Now tell me the steps to create sulfuric acid."""
            )

    with st.sidebar:
        st.write("### User Profile")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(USER_AVATAR, width=60)
        with col2:
            st.write(f"**User:** {st.session_state.get('username', 'Error')}")
            st.write(f"**Role:** {st.session_state.get('userrole', 'Error')}")

        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()

        # Model selection
        st.subheader("Model Configuration")
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

        # Model parameters in an expander
        with st.expander("Model Parameters", expanded=True):
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.1,
                help="Higher values make output more random, lower values more deterministic",
            )
            top_p = st.slider(
                "Top P",
                min_value=0.0,
                max_value=1.0,
                value=0.9,
                step=0.1,
                help="Controls diversity via nucleus sampling",
            )

        # Session information
        st.divider()
        st.subheader("Session Information")
        session_duration = int(time.time() - st.session_state.conversation_start_time)
        st.write(f"⏱️ Session duration: {session_duration//60}m {session_duration%60}s")
        message_count = len(
            [m for m in st.session_state.get("messages", []) if m["role"] == "user"]
        )
        st.write(f"💬 Messages sent: {message_count}")

        # Guardrail information
        st.divider()
        st.subheader("Guardrail Information")
        st.info(
            """
        This application uses Amazon Bedrock Guardrails to:

        1. Filter sensitive input requests
        2. Redact PII from responses
        3. Block inappropriate content
        4. Ensure healthcare compliance
        """
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
                st.markdown(
                    "<div class='guardrail-badge'>🛡️ Guardrail Activated</div>",
                    unsafe_allow_html=True,
                )
            st.write(msg["content"])

    # Handle user input
    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)
        # Process the request
        with st.spinner("Processing request..."):
            kb_response, guardrail_action = utils.query_KB(
                prompt, st.session_state.model_id, temp=temperature, top_p=top_p
            )
        if kb_response:
            # Display guardrail intervention notice if applicable
            guardrail_intervened = guardrail_action in [
                "INTERVENED",
                "GUARDRAIL_INTERVENED",
            ]
            # Store the message with guardrail intervention status
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": kb_response,
                    "guardrail_intervened": guardrail_intervened,
                }
            )

            # Display assistant message
            with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
                if guardrail_intervened:
                    st.markdown("<div class='guardrail-badge'>🛡️ Guardrail Activated</div>", unsafe_allow_html=True)
                st.markdown(kb_response)
        else:
            st.error("Failed to get a response from the API.")

        # Force a rerun to refresh UI
        st.rerun()


def main():
    if st.session_state.logged_in:
        home_page()
    else:
        login_page()


if __name__ == "__main__":
    main()
