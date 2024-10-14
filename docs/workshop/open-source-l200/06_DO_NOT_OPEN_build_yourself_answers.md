# Retrieval Augmented Generation with Amazon Bedrock - Building your Own Application!

> *PLEASE NOTE: This notebook should work well with the **`Data Science 3.0`** kernel in SageMaker Studio*

---

## Purpose of this Notebook

Now that you have learned about how to use many strategies for RAG with Amazon Bedrock, it's your turn to apply what you've learned today and build your own RAG application! In this exercise, we have provided an incomplete notebook which needs to be filled in with your own RAG implementation using Amazon Bedrock. Your task is to build an interactive chatbot which is able to answer questions about [Amazon's annual shareholder letter from 2022](https://www.aboutamazon.com/news/company-news/amazon-ceo-andy-jassy-2022-letter-to-shareholders).


## Getting Started 

Anywhere you see a "`[FILL IN]`" comment in this notebook is where you are expected to write your own code. At the end of each "Task" section, the expected results are provided to help guide your experimentation. Make sure to reference the previous notebooks from this workshop! All the code you need is included in the workshop, this section is about pulling it all together now!

Please note: because this is a generative solution, there is no true correct way to accomplish this task. Use this time to experiment, be creative, and explore the boundaries of what Amazon Bedrock can generate for you!3

---
## Setup `boto3` Connection

Let's set up the same boto3 client side connection to Bedrock which we have used in the previous notebooks.


```python
import boto3
import os
from IPython.display import Markdown, display

region = os.environ.get("AWS_REGION")
boto3_bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=region,
)
```

---
## Setup Vector Store (Already Complete)

In order to speed up this process for you, we have provided a pre-built langchain FAISS index for a new dataset in `faiss-diy` directory. Lets connect to the vector database below.


```python
from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores import FAISS

embedding_model = BedrockEmbeddings(
    client=boto3_bedrock,
    model_id="amazon.titan-embed-text-v1"
)
vs = FAISS.load_local('../faiss-diy/', embedding_model, allow_dangerous_deserialization=True)
```

---
## Task 1: Basic Retrieval

Okay lets get started filling in the code yourself! In the section below, all you need to do is use the vector store (`vs`) to retrieve the passage which matches to the user query supplied.


```python
user_query = 'how is amazon looking at the logistics of its retail business this year?'

# [FILL IN] retrieve the most relevant passage to the query above
search_results = vs.similarity_search(
    user_query, k=1
)
display(Markdown(search_results[0].page_content))
```

**Expected output:**

The most relevant passage should start with... `During the early part of the pandemic, with many physical stores shut down, our consumer business grew at an extraordinary clip, with annual revenue increasing from $245B in 2019 to $434B in 2022...`

---
## Task 2: Reformatting Queries for Retrieval via Prompt Engineering

Just like in notebook 03, it is useful to rephrase a user input before retrieval from our vector database. In the task below, write a prompt which will intelligently reformat the user query to be well conditioned for retrieval from the vector database.

Note: Prompt engineering is extremely iterative. We recommend trying a few different prompts here and seeing how the retrieval is impacted by these changes.



```python
from langchain import PromptTemplate

# [FILL IN] write a prompt which reformats the user query for more accurate retrieval
REFORMAT_TEMPLATE = """\
<chat-history>
{chat_history}
</chat-history>

<follow-up-message>
{question}
<follow-up-message>

Human: Given the conversation history and the follow-up question,\
what is the single most important question which the Human is looking for\
based on the conversation history and the follow-up question?

Do NOT include any assumptions about the state of the world which are not\
directly stated in the conversation.

Assistant: Standalone Question:"""
REFORMAT_PROMPT = PromptTemplate.from_template(REFORMAT_TEMPLATE)
```


```python
chat_history = '''Human: What can you do?

Assistant: I can answer questions about Amazon's 2022 Annual letter to shareholders.'''
user_query = 'What is happening with computer chips?'

# [FILL IN] modify your prompt given the context below
prompt = REFORMAT_PROMPT.format(chat_history=chat_history, question=user_query)

# [FILL IN] invoke the anthropic.claude-3-haiku-20240307-v1:0 model with your prompt to reformat the query
from langchain.llms import Bedrock
llm = Bedrock(
    client=boto3_bedrock,
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    model_kwargs={
        "max_tokens_to_sample": 500,
        "temperature": 0.0,
    },
)
new_question = llm(prompt).strip()
# new_question = 'What kind of work is Amazon doing with computer chips?'
print(new_question)

# [FILL IN] query the FAISS vector store with the reformatted query from Claude
search_results = vs.similarity_search(
    new_question, k=1
)
display(Markdown(search_results[0].page_content))
```

**Expected output:**

An example reformatted query would look something like... 
> What kind of work is Amazon doing with computer chips?

---
## Task 3: Answering Contextual Questions via Prompt Engineering



```python
# [FILL IN] write a prompt which answers the user query based on retrieved context
RAG_TEMPLATE = """\
<context>
{context}
</context>

Human: Given the context above, answer the question inside the <q></q> XML tags.

<q>{question}</q>

If the answer is not in the context say "Sorry, I don't know as the answer was not found in the context". Do not use any XML tags in the answer.

Assistant:"""

RAG_PROMPT = PromptTemplate.from_template(RAG_TEMPLATE)
```


```python
# [FILL IN] modify your prompt given the context from task 2 including the relevant passage and reformatted user query
prompt = RAG_PROMPT.format(context=f"{search_results[0].page_content}", question=new_question)

# [FILL IN] invoke the anthropic.claude-3-haiku-20240307-v1:0 model with your prompt to answer the question
answer = llm(prompt).strip()
display(Markdown(answer))
```

**Expected output:**

An example answer would be something like... 

> According to the passage, Amazon is doing significant work developing their own computer chips specifically designed for different types of computing workloads:
> 
> - They have developed general-purpose CPU processors called Graviton that provide better price-performance than comparable x86 chips. The latest Graviton3 chips provide 25% better performance than the previous Graviton2 chips.
> - They have developed specialized chips called Trainium for machine learning training workloads. Trainium-based instances are up to 140% faster than GPU-based instances for common machine learning models. 
> - They also developed specialized chips called Inferentia for machine learning inference workloads. The latest Inferentia2 chips offer up to four times higher throughput and ten times lower latency than the original Inferentia chips.
> 
> So in summary, Amazon is developing their own computer chips customized for different types of computing like general-purpose CPUs, machine learning training, and machine learning inference, in order to provide better performance and lower costs for customers on AWS.
```

---
## Task 4: Automate the RAG Workflow



```python
# [FILL IN] create conversational retrieval system here
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain

memory_chain = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    human_prefix="Human",
    ai_prefix="Assistant"
)
memory_chain.chat_memory.add_user_message(
    'Hello, what are you able to do?'
)
memory_chain.chat_memory.add_ai_message(
    "I can answer questions about Amazon's 2022 Annual letter to shareholders."
)

qa = ConversationalRetrievalChain.from_llm(
    llm=llm, # this is our claude model
    retriever=vs.as_retriever(), # this is our FAISS vector database
    memory=memory_chain, # this is the conversational memory storage class
    condense_question_prompt=REFORMAT_PROMPT, # this is the prompt for condensing user inputs
    verbose=False, # change this to True in order to see the logs working in the background
)
qa.combine_docs_chain.llm_chain.prompt = RAG_PROMPT # this is the prompt in order to respond to condensed questions
```


```python
# [FILL IN] respond to the following queries with conversational context included
query_1 = 'Are you able to answer questions about 2021?'
query_2 = 'What is the space business amazon has been talking about?'
query_3 = 'What kind of products is that business working on building?'

display(Markdown(qa.run({'question': query_1})))
display(Markdown(qa.run({'question': query_2})))
display(Markdown(qa.run({'question': query_3})))
```

**Expected output:**

An example conversation might look something like... 

> **Input**: Are you able to answer questions about 2021?
> 
> **Output**: No, I'm only able to answer questions about the 2022 shareholder letter provided in the context.
> 
> **Input**: What is the space business amazon has been talking about?
> 
> **Output**:  The space business Amazon is referring to in the letter is called Kuiper. Kuiper is Amazon's project to create a low-Earth orbit satellite system to deliver...
> 
> **Input**: What kind of products is that business working on building?
> 
> **Output**: Based on the information provided in the shareholder letter, the Kuiper space business is working on developing two main types of products...
