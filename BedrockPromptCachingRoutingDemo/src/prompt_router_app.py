import streamlit as st
import os
from bedrock_prompt_routing import PromptRouterManager, ChatSession
from file_processor import FileProcessor
import time

class BedrockChatUI:
    def __init__(self):
        self.setup_streamlit()
        self.init_session_state()
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.router_manager = PromptRouterManager(region=self.region)

    def setup_streamlit(self):
        st.set_page_config(
            page_title="Amazon Bedrock Prompt Router Demo",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        st.markdown("""
            <style>
                .stApp {
                    background-color: #0E1117;
                    color: white;
                }
                .stSidebar {
                    background-color: #1A1C24;
                    padding: 2rem 1rem;
                }
                .stTextInput, .stSelectbox, div[data-baseweb="select"] > div {
                    background-color: #262730;
                }
                .stButton > button {
                    background-color: #262730;
                    color: white;
                    border: 1px solid #4A4A4A;
                }
                .stTextArea > textarea {
                    background-color: #262730;
                    color: white;
                }
                .metric-container {
                    background-color: #262730;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin: 0.5rem 0;
                }
                div[data-testid="stMetricValue"] {
                    color: #00BFFF;
                    font-size: 1.8rem;
                }
                div[data-testid="stMetricLabel"] {
                    color: #E0E0E0;
                }
                .chat-message {
                    padding: 1rem;
                    margin: 0.5rem 0;
                    border-radius: 0.5rem;
                    background-color: #262730;
                }
                .user-message {
                    border-left: 4px solid #00BFFF;
                }
                .assistant-message {
                    border-left: 4px solid #00FF00;
                }
                .upload-section {
                    background-color: #262730;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin: 1rem 0;
                }
            </style>
        """, unsafe_allow_html=True)

    def init_session_state(self):
        if 'chat_session' not in st.session_state:
            st.session_state.chat_session = None
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'current_router' not in st.session_state:
            st.session_state.current_router = None

    def render_router_sidebar(self):
        with st.sidebar:
            st.title("🤖 Prompt Router Selection")
            routers = self.router_manager.get_prompt_routers()
            
            router_options = [(r['name'], r['arn'], r['provider']) for r in routers]
            selected_router = st.selectbox(
                "Select a Prompt-Router",
                options=router_options,
                format_func=lambda x: f"{x[0]} ({x[2]})",
                key="router_select"
            )

            if selected_router:
                if st.session_state.current_router != selected_router[1]:
                    st.session_state.current_router = selected_router[1]
                    st.session_state.chat_session = ChatSession(
                        model_id=selected_router[1],
                        region=self.region
                    )

                router_details = self.router_manager.get_router_details(selected_router[1])
                
                st.divider()
                st.subheader("📊 Prompt-Router Details")
                st.markdown(f"**Provider:** {selected_router[2]}")
                st.markdown(f"**Type:** {router_details.get('type', 'N/A')}")
                
                if router_details['supported_models']:
                    st.divider()
                    st.subheader("🔧 Available Models")
                    for model in router_details['supported_models']:
                        st.markdown(f"- `{model}`")

    def render_chat_area(self):
        chat_col, stats_col = st.columns([2, 1])

        with chat_col:
            st.title("💬 Amazon Bedrock Prompt Router Demo")
            
            with st.container():
                st.markdown("### 📎 File Upload")
                uploaded_file = st.file_uploader(
                    "Upload PDF, DOCX, or TXT file",
                    type=['pdf', 'docx', 'txt']
                )

                if uploaded_file and st.session_state.chat_session:
                    if FileProcessor.is_supported_file(uploaded_file.name):
                        with st.spinner("Processing file..."):
                            extracted_text = FileProcessor.process_uploaded_file(uploaded_file)
                            if extracted_text:
                                trace, model_used = st.session_state.chat_session.send_message(extracted_text)
                                st.session_state.messages.append({
                                    "role": "user",
                                    "content": f"📄 *Content from {uploaded_file.name}*"
                                })
                                response = st.session_state.chat_session.messages[-1]["content"][0]["text"]
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": response
                                })
                                st.rerun()

            st.divider()
            
            chat_container = st.container()
            with chat_container:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

            if prompt := st.chat_input("Type your message..."):
                if not st.session_state.chat_session:
                    st.error("⚠️ Please select a router first")
                    return

                st.session_state.messages.append({"role": "user", "content": prompt})
                
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        trace, model_used = st.session_state.chat_session.send_message(prompt)
                        response = st.session_state.chat_session.messages[-1]["content"][0]["text"]
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

        with stats_col:
            if st.session_state.chat_session:
                st.title("📈 Usage Stats")
                stats = st.session_state.chat_session.usage_stats
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Chats", stats.total_chats)
                with col2:
                    st.metric("Total Tokens", stats.total_input_tokens + stats.total_output_tokens)

                st.divider()
                
                st.subheader("Token Usage")
                st.metric("Input Tokens", stats.total_input_tokens)
                st.metric("Output Tokens", stats.total_output_tokens)
                
                st.divider()
                
                st.subheader("⚡ Model Usage")
                for model, count in stats.model_invocations.items():
                    st.metric(f"{model}", count, "calls")

                st.divider()
                elapsed_minutes = max(0.1, (time.time() - stats.start_time) / 60)
                st.metric("Session Time", f"{elapsed_minutes:.2f} min")

    def run(self):
        self.render_router_sidebar()
        self.render_chat_area()

if __name__ == "__main__":
    app = BedrockChatUI()
    app.run()