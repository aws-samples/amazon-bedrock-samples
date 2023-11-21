import streamlit as st
import sql_query_chain
import re
import sqlite_helper
import pandas as pd


def ask_question(question):
    sql_chain_response = sql_query_chain.sql_chain(question)
    return sql_chain_response

def is_query_present(response):
    pattern = r'\bSQLQuery:\s*(.+)'
    return re.search(pattern, response, re.IGNORECASE | re.DOTALL)

def extract_query(ai_response):
    query_text = ""
    pattern = r'\bSQLQuery:\s*(.+)'
    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
    if match:
        query_text = match.group(1).strip()
    return query_text

def run_query(query):
    status, columns, query_result = sqlite_helper.run_query(query)
    if query_result and status=="success":
        df = pd.DataFrame(query_result)
        return df

# Initialize chat history
hello_message = f"""Hello 👋. I am SQL assistant. I can take a natural language question as input, analyze the intent and context, and generate a valid SQLite query that answers the question based on the [Nortwhind](https://docs.yugabyte.com/preview/sample-data/northwind/) dataset. Feel free to ask any questions along those lines!
Here are a few examples of questions I can help answer by generating a SQLite query:

- What are the total sales amounts by year?

- What are the top 5 most expensive products? 

- What customers have spent over $1000 in total?

- What products were sold in the last month?

- What is the total revenue for each employee?"""

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": hello_message, "type": "text"}]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type", "text") == "code":
            st.code(message["content"], language="sql")
        else:
            st.markdown(message["content"])

prompt = st.chat_input("Write your question")

if prompt:
     # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt, "type": "text"})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        response_list = []
        response = ask_question(prompt)
        response_list.append(response)

        for response in response_list:
            full_response += response
            message_placeholder.code(full_response + "▌", language="sql")
        message_placeholder.code(full_response, language="sql")
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        if is_query_present(response):
            query = extract_query(response)
            if query:
               df = run_query(query=query)
               if df is not None and not df.empty:
                   message_placeholder.dataframe(df)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response, "type": "code"})
