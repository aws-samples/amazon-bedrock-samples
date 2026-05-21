import streamlit as st
import streamlit_authenticator as stauth
from websearch_page import main as websearch_main

def main():
    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Show login form only if not authenticated
    if not st.session_state.authenticated:
        st.title("Login Page")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")

            if submit_button:
                if (username == "Customer1" or username == "Customer2") and password == "password":
                    st.session_state.authenticated = True
                    st.session_state.user_name = username
                    st.success("Login successful!")
                    st.rerun()  # This will refresh the page
                else:
                    st.error("Invalid username or password")
    else:
        # Only show websearch page when authenticated
        websearch_main()

if __name__ == "__main__":
    main()
