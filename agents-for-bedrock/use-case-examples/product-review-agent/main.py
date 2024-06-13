import streamlit as st
import datetime
import time
from agent import ProductReviewAgent
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-id','--id')
parser.add_argument('-alias','--alias')
args = parser.parse_args()
agent = ProductReviewAgent(args)

st.title('Agent with custom knowledge base query')

date_range = st.date_input(
    "Select date range",
    (datetime.date(2020,1,1), datetime.date(2021,1,1)),
    format='DD.MM.YYYY'
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt_template = """
The start date and end date are placed in <start_date></start_date> and <end_date></end_date> tags.
{user_prompt}
<start_date>{start_date}</start_date>
<end_date>{end_date}</end_date>
"""
# Accept user input
if user_input := st.chat_input("Ask me questions on product reviews."):
    prompt = prompt_template.format(
        user_prompt=user_input,
        start_date=time.mktime(date_range[0].timetuple())*1000,
        end_date=time.mktime(date_range[1].timetuple())*1000
    )
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(agent.invoke_agent(prompt))
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})