```python
import warnings
import boto3
from dotenv import load_dotenv
import os
from botocore.config import Config

warnings.filterwarnings('ignore')
load_dotenv()

my_config = Config(
    region_name = 'us-west-2',
    signature_version = 'v4',
    retries = {
        'max_attempts': 10,
        'mode': 'standard'
    }
)
```

## Set up: Introduction to ChatBedrock and prompt templates

**Supports the following**
1. Multiple Models from Bedrock 
2. Converse API
3. Ability to do tool binding
4. Ability to plug with LangGraph flows

⚠️ ⚠️ ⚠️ Before running this notebook, ensure you've run the  set up libraries if you do not have the versions installed ⚠️ ⚠️ ⚠️


```python
# %pip install -U langchain-community>=0.2.12, langchain-core>=0.2.34
# %pip install -U --no-cache-dir  \
#     "langchain>=0.2.14" \
#     "faiss-cpu>=1.7,<2" \
#     "pypdf>=3.8,<4" \
#     "ipywidgets>=7,<8" \
#     matplotlib>=3.9.0 \
#     "langchain-aws>=0.1.17"
#%pip install -U --no-cache-dir boto3
#%pip install grandalf==3.1.2
```

### Set up classes

- helper methods to set up the boto 3 connection client which wil be used in any class used to connect to Bedrock
- this method accepts parameters like `region` and `service` and if you want to `assume any role` for the invocations
- if you set the  AWS credentials then it will use those


```python
import warnings

from io import StringIO
import sys
import textwrap
import os
from typing import Optional

# External Dependencies:
import boto3
from botocore.config import Config

warnings.filterwarnings('ignore')

def print_ww(*args, width: int = 100, **kwargs):
    """Like print(), but wraps output to `width` characters (default 100)"""
    buffer = StringIO()
    try:
        _stdout = sys.stdout
        sys.stdout = buffer
        print(*args, **kwargs)
        output = buffer.getvalue()
    finally:
        sys.stdout = _stdout
    for line in output.splitlines():
        print("\n".join(textwrap.wrap(line, width=width)))
        

def get_boto_client_tmp_cred(
    retry_config = None,
    target_region: Optional[str] = None,
    runtime: Optional[bool] = True,
    service_name: Optional[str] = None,
):

    if not service_name:
        if runtime:
            service_name='bedrock-runtime'
        else:
            service_name='bedrock'

    bedrock_client = boto3.client(
        service_name=service_name,
        config=retry_config,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN',""),

    )
    print("boto3 Bedrock client successfully created!")
    print(bedrock_client._endpoint)
    return bedrock_client    

def get_boto_client(
    assumed_role: Optional[str] = None,
    region: Optional[str] = None,
    runtime: Optional[bool] = True,
    service_name: Optional[str] = None,
):
    """Create a boto3 client for Amazon Bedrock, with optional configuration overrides

    Parameters
    ----------
    assumed_role :
        Optional ARN of an AWS IAM role to assume for calling the Bedrock service. If not
        specified, the current active credentials will be used.
    region :
        Optional name of the AWS Region in which the service should be called (e.g. "us-east-1").
        If not specified, AWS_REGION or AWS_DEFAULT_REGION environment variable will be used.
    runtime :
        Optional choice of getting different client to perform operations with the Amazon Bedrock service.
    """
    if region is None:
        target_region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION"))
    else:
        target_region = region

    print(f"Create new client\n  Using region: {target_region}")
    session_kwargs = {"region_name": target_region}
    client_kwargs = {**session_kwargs}

    profile_name = os.environ.get("AWS_PROFILE", None)
    retry_config = Config(
        region_name=target_region,
        signature_version = 'v4',
        retries={
            "max_attempts": 10,
            "mode": "standard",
        },
    )
    if profile_name:
        print(f"  Using profile: {profile_name}")
        session_kwargs["profile_name"] = profile_name
    else: # use temp credentials -- add to the client kwargs
        print(f"  Using temp credentials")

        return get_boto_client_tmp_cred(retry_config=retry_config,target_region=target_region, runtime=runtime, service_name=service_name)

    session = boto3.Session(**session_kwargs)

    if assumed_role:
        print(f"  Using role: {assumed_role}", end='')
        sts = session.client("sts")
        response = sts.assume_role(
            RoleArn=str(assumed_role),
            RoleSessionName="langchain-llm-1"
        )
        print(" ... successful!")
        client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
        client_kwargs["aws_secret_access_key"] = response["Credentials"]["SecretAccessKey"]
        client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]

    if not service_name:
        if runtime:
            service_name='bedrock-runtime'
        else:
            service_name='bedrock'

    bedrock_client = session.client(
        service_name=service_name,
        config=retry_config,
        **client_kwargs
    )

    print("boto3 Bedrock client successfully created!")
    print(bedrock_client._endpoint)
    return bedrock_client
```

### Boto3 client
- Create the run time client which we will use to run through the various classes


```python
#os.environ["AWS_PROFILE"] = '<replace with your profile if you have that set up>'
region_aws = 'us-east-1' #- replace with your region
boto3_bedrock = get_boto_client(region=region_aws, runtime=True, service_name='bedrock-runtime')
```


```python
from langchain_aws import ChatBedrock
# from langchain_community.chat_models import BedrockChaat
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatBedrock(client=boto3_bedrock, #credentials_profile_name='~/.aws/credentials',
                  model_id="anthropic.claude-3-haiku-20240307-v1:0",
                  model_kwargs=dict(temperature=0))
```


```python
messages = [
    HumanMessage(
        content="what is the weather like in Seattle WA"
    )
]
ai_msg = llm.invoke(messages)
ai_msg
```

## Naive inferencing: The root challenge in creating Chatbots and Virtual Assistants and the Agentic solution:

As seen in previous tutorials, LLM conversational interfaces such as chatbots or virtual assistants can be used to enhance the user experience of customers. These can be improved even more by giving them context from related sources such as chat history, documents, websites, social media platforms, and / or messaging apps, this is called RAG (Retrieval Augmented Generation) and is a fundamental backbone of designing robust AI solutions. 

One persistent bottleneck however is the inability of LLMs to assess whether data extracted and or its response, based on said data, is accurate and fully encapsulates a user requests (hallucinating). A way to mitigate this risk brought up by naive, inferencing with RAG is through the use of Agents. Agents are defined as a workflow that uses data, tools, and its own inferences to check that the response provided is accurate and meets users goals.

![Amazon Bedrock - Agents Interface](./images/agents.jpg)

### Key Elements of Agents
 
- Agents are designed for tasks that require multistep reasoning; Think questions that intuitively require multiple steps, for example how old was Henry Ford when he founded his company.
- They are designed to plan ahead, remember past actions and check its own responses.
- Agents can be made to deconstruct complex requests into manageable smaller sub-tasks such as data retrieval, comparison and tool usage.
- Agents might be designed as standalone solutions or paired with other agents to enhance the agentic workflow.


 Let's build an agentic workflow from scratch to see how it works, for this use case we will use Calude 3 Sonnet to power our agentic workflow.

### Architecture [Retriever with LangGraph]

The core benefit of agentic workflows lies in its flexibility to adjust to your needs. You have full control on the design the flow by properly defining what the agents do and what tools and information is available to them. One popular framework for the use of Agents is called Langgraph, a low-level framework that offers the ability of adding cycles (using previous inferences as context to either fix or build on it), controllability of the flow and state of your application, and persistence, giving the agents the ability to involve humans in the loop and the memory to recall past agentic flows.

#### For this scenario we'll define 3 agents:

1. We defined a supervisor agent responsible for deciding the steps needed to fulfill the users request, this can take the shape of using tools or data retrieval. 
2. Then a task-driven agent to retrieve documents which can be invoked only when the orchestrator agent deems it necessary to fulfill the users request. 
3. Finally, a data retriever agent will query an embedding database containing Medical history if its deemed necessary to use this information to answer the users question.


### Dependencies and helper functions:


```python
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.document_loaders import CSVLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import BedrockEmbeddings
import warnings
from io import StringIO
import sys
import textwrap

warnings.filterwarnings('ignore')


```

### Build the retriever chain to be used with LangGraph
1. Create `create_retriever_pain` which is used when the solution requires data retrieval from our documents
2. Define the system prompt to enforce the correct use of context retrieved, it also ensures that the agent does not hallucinate
3. Define the vectorstore using FAISS, a light weight in-memory vector DB and our documents stored in _'medi_history.csv'_
4. Define the sessions persistent memory store for the agents use


```python
store = {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


def create_retriever_pain():

    br_embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=boto3_bedrock)
    
    loader = CSVLoader("./rag_data/medi_history.csv") # --- > 219 docs with 400 chars, each row consists in a question column and an answer column
    documents_aws = loader.load() #
    print(f"Number of documents={len(documents_aws)}")

    docs = CharacterTextSplitter(chunk_size=2000, chunk_overlap=400, separator=",").split_documents(documents_aws)

    print(f"Number of documents after split and chunking={len(docs)}")
        
    vectorstore_faiss_aws = FAISS.from_documents(
        documents=docs,
        embedding = br_embeddings
    )

    print(f"vectorstore_faiss_aws: number of elements in the index={vectorstore_faiss_aws.index.ntotal}::")

    model_parameter = {"temperature": 0.0, "top_p": .5, "max_tokens_to_sample": 2000}
    modelId = "meta.llama3-8b-instruct-v1:0" #"anthropic.claude-v2"
    chatbedrock_llm = ChatBedrock(
        model_id=modelId,
        client=boto3_bedrock,
        model_kwargs=model_parameter, 
        beta_use_converse_api=True
    )

    qa_system_prompt = """You are an assistant for question-answering tasks. \
    Use the following pieces of retrieved context to answer the question. \
    If the answer is not present in the context, just say you do not have enough context to answer. \
    If the input is not present in the context, just say you do not have enough context to answer. \
    If the question is not present in the context, just say you do not have enough context to answer. \
    If you don't know the answer, just say that you don't know. \
    Use three sentences maximum and keep the answer concise.\

    {context}"""

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])
    question_answer_chain = create_stuff_documents_chain(chatbedrock_llm, qa_prompt)

    pain_rag_chain = create_retrieval_chain(vectorstore_faiss_aws.as_retriever(), 
                                            question_answer_chain)

    pain_retriever_chain = RunnableWithMessageHistory(
        pain_rag_chain,
        get_session_history=get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
    return pain_retriever_chain

```

#### Testing the rag chain:


```python
pain_rag_chain = create_retriever_pain()    
result = pain_rag_chain.invoke(
    {"input": "What all pain medications can be used for headache?", 
     "chat_history": []},
     config={'configurable': {'session_id': 'TEST-123'}},
)
result['answer']
```

### Book / Cancel Appointments: An agent with tools:

In this module we will create an agent responsible for booking and canceling doctor appointments. This agent will take a booking request to create or cancel an appointment and its action will be guided by the 4 tools available to it.
1. _book_appointment_: Used by the agent to book an appointment give the users request as long as it meets the criteria, valid date and time within office hours.
2. _cancel_appointment_: If an exiting appointment is found, it will remove its respective 'booking id' from the list of appointments.
3. _reject_appointment_: If an appointment cannot be booked due to inability or invalid date or time the agent will use this tool to reject the users request.
4. _need_more_info_: Returns the earliest date and time needed for the booking an appointment back to the agent as well as informing the agent that it should request further details from the user.



```python
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from datetime import datetime, timedelta 
import dateparser


appointments = ['ID_100'] # Default appointment
def create_book_cancel_agent():
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    formatted_tomorrow = tomorrow.strftime("%B %d, %Y")
    start_time = datetime.strptime("9:00 am", "%I:%M %p").time()
    end_time = datetime.strptime("5:00 pm", "%I:%M %p").time()
            
    def check_date_time(date: str, time: str) -> str:
        """Helper function is used by book appointment tool to check that the date and time passed by the user are within the date time params"""
        _date = dateparser.parse(date)
        _time = dateparser.parse(time)
        if not _date or not _time:
            return 'ERROR: Date and time parameters are not valid'
        
        input_date = _date.date()
        input_time = _time.time()
        if input_date < tomorrow.date():
            return f'ERROR: Appointment date must be at least one day from today: {today.strftime("%B %d, %Y")}'
        elif input_date.weekday() > 4:
            return f'ERROR: Appointments are only available on weekdays, date {input_date.strftime("%B %d, %Y")} falls on a weekend.'
        elif start_time > input_time >= end_time:
            return f'ERROR: Appointments bust be between the hours of 9:00 am to 5:00 pm'
        return 'True'
        
        
    @tool("book_appointment")
    def book_appointment(date: str, time: str) -> dict:
        """Use this function to book an appointment. This function returns the booking ID"""

        print(date, time)
        is_valid = check_date_time(date, time)
        if 'ERROR' in is_valid :
            return {"status" : False, "date": date, "time": time, "booking_id": is_valid}

        last_appointment = appointments[-1]
        new_appointment = f"ID_{int(last_appointment[3:]) + 1}"
        appointments.append(new_appointment)
            
        return {"status" : True, "date": date, "time": time, "booking_id": new_appointment}
    
    @tool("reject_appointment")
    def reject_appointment() -> dict:
        """Use this function to reject an appointment if the status of book_appointment is False"""
        return {"status" : False, "date": "", "time": "", "booking_id": ""}
        
    @tool("cancel_appointment")
    def cancel_appointment(booking_id: str) -> dict:
        """Use this function to cancel an existing appointment and remove it from the schedule. This function needs a booking id to cancel the appointment."""

        print(booking_id)
        status = any(app == booking_id for app in appointments)
        if not status:
            booking_id = "ERROR: No ID for given booking found. Please provide valid id"
        appointments.remove(booking_id)
        return {"status" : status, "booking_id": booking_id}

    @tool("need_more_info")
    def need_more_info() -> dict:
        """Use this function to get more information from the user. This function returns the earliest date and time needed for the booking an appointment """
        return {"date after": formatted_tomorrow, "time between": "09:00 AM to 05:00 PM", "week day within": "Monday through Friday"}


    prompt_template_sys = """
    You are a booking assistant.
    Make sure you use one the the following tools ["book_appointment", "cancel_appointment", "need_more_info", "reject_appointment"]
    """

    chat_prompt_template = ChatPromptTemplate.from_messages(
            messages = [
                ("system", prompt_template_sys),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
    )

    model_id = "anthropic.claude-3-sonnet-20240229-v1:0" #"us.anthropic.claude-3-5-sonnet-20240620-v1:0" 
    model_parameter = {"temperature": 0.0, "top_p": .1, "max_tokens_to_sample": 400}
    chat_bedrock_appointment = ChatBedrock(
        model_id=model_id,
        client=boto3_bedrock,
        model_kwargs=model_parameter, 
        beta_use_converse_api=True
    )

    tools_list_book = [book_appointment, cancel_appointment, need_more_info, reject_appointment]

    # Construct the Tools agent
    book_cancel_agent_t = create_tool_calling_agent(chat_bedrock_appointment, 
                                                    tools_list_book, 
                                                    chat_prompt_template)
    
    agent_executor_t = AgentExecutor(agent=book_cancel_agent_t, 
                                     tools=tools_list_book, 
                                     verbose=True, 
                                     max_iterations=5, 
                                     return_intermediate_steps=True)
    return agent_executor_t

```


```python
appointments
```

### Test the Booking Agent with history:


```python
# Add context for the agent to use
book_cancel_history = InMemoryChatMessageHistory()
book_cancel_history.add_user_message("can you book an appointment?")
book_cancel_history.add_ai_message("What is the date and time you wish for the appointment")
book_cancel_history.add_user_message("I need for Oct 10, 2023 at 10:00 am?")

user_query = "can you book an appointment for me for September 14, 2024, at 10:00 am?"
agent_executor_book_cancel = create_book_cancel_agent()
    
result = agent_executor_book_cancel.invoke(
    {"input": user_query, 
     "chat_history": book_cancel_history.messages}, 
    config={"configurable": {"session_id": "session_1"}}
)
```


```python
result['output'][0]['text']
```


```python
book_cancel_history.messages
```


```python
agent_executor_book_cancel.invoke(
    {"input": "can you book an appointment for me?", "chat_history": []}, 
    config={"configurable": {"session_id": "session_1"}}
)
```


```python
agent_executor_book_cancel.invoke({"input": "can you cancel my appointment with booking id of ID_100"})
```

### An AI doctor: Medical advice agent based on conversations with the patient
This function will be the backbone of the language agent responsible for giving medical advice given the historical interactions the user had with the Chatbot. This model will use its knowledge of the medical field along with the conversations with the patient to give well founded advice.


```python
from langchain_aws.chat_models.bedrock import ChatBedrock


def extract_chat_history(chat_history):
    user_map = {'human':'user', 'ai':'assistant'}
    if not chat_history:
        chat_history = []
    messages_list=[{'role':user_map.get(msg.type), 'content':[{'text':msg.content}]} for msg in chat_history]
    return messages_list


def ask_doctor_advice(boto3_bedrock, chat_history):
    modelId = "anthropic.claude-3-sonnet-20240229-v1:0" 
    response = boto3_bedrock.converse(
        messages=chat_history,
        modelId=modelId,
        inferenceConfig={
            "temperature": 0.5,
            "maxTokens": 100,
            "topP": 0.9
        }
    )
    response_body = response['output']['message']['content'][0]['text']
    return response_body

```

### Testing the AI Doc agent


```python
chat_history=InMemoryChatMessageHistory()
chat_history.add_user_message("what are the effects of Asprin")
ask_doctor_advice(boto3_bedrock, extract_chat_history(chat_history.messages))
```

### The supervisor agent, the orchestrator of the LangGraph workflow
1. This agent has the list of tools / nodes it can invoke based on the nodes
2. Based on that the supervisor will route and invoke the correct LangGraph chain and node
3. Output will be a predefine chain of thought leveraging the available tools and agents to complete and validate the task
4. `ToolsAgentOutputParser` is used to parse the output of the tools


```python
from langchain_core.runnables import RunnablePassthrough
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser


members = ["book_cancel_agent","pain_retriever_chain","ask_doctor_advice" ]
options = ["FINISH"] + members

def create_supervisor_agent():

    prompt_finish_template_simple = """
    Given the conversation below who should act next?
    1. To book or cancel an appointment return 'book_cancel_agent'
    2. To answer question about pain medications return 'pain_retriever_chain'
    3. To answer question about any medical issue return 'ask_doctor_advice'
    4. If you have the answer return 'FINISH'
    Or should we FINISH? ONLY return one of these {options}. Do not explain the process.Select one of: {options}
    
    {history_chat}
    
    Question: {input}

    """
    modelId = "anthropic.claude-3-sonnet-20240229-v1:0"
    supervisor_llm = ChatBedrock(
        model_id=modelId,
        client=boto3_bedrock,
        beta_use_converse_api=True
    )

    supervisor_chain_t = (
        RunnablePassthrough()
        | ChatPromptTemplate.from_template(prompt_finish_template_simple)
        | supervisor_llm
        | ToolsAgentOutputParser()
    )
    return supervisor_chain_t

supervisor_wrapped_chain = create_supervisor_agent()

```

### Test the supervisor agent
Our supervisor will litigate the user query to the respective agent or end the chain.


```python
temp_messages = InMemoryChatMessageHistory()
temp_messages.add_user_message("What does medical doctor do?")

supervisor_wrapped_chain.invoke({
    "input": "What does medical doctor do?", 
    "options": options, 
    "history_chat": extract_chat_history(temp_messages.messages)
})

#  Adding Memory
temp_message_2 = InMemoryChatMessageHistory()
temp_message_2.add_user_message("Can you book an appointment for me?")
temp_message_2.add_ai_message("Sure I have booked the appointment booked for Sept 24, 2024 at 10 am")

response = supervisor_wrapped_chain.invoke({
    "input": "can you book an appointment for me?", 
    "options": options, 
    "history_chat": extract_chat_history(temp_message_2.messages)})

response
```

### Putting it all together: Defining the Graph architecture
1. The `GraphState` class defines how we want our nodes to behave  
2. Wrap our agents into nodes that will take a graph state as input
3. Short term or 'buffer' memory for the graph will be provided by the `ConversationBufferMemory` object
4. Finally `add_user_message` and `add_ai_message` apis are used to add the messages to the buffer memory


```python
import operator
from typing import Annotated, Dict, Sequence, TypedDict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from langchain_core.chat_history import InMemoryChatMessageHistory


# The agent state is the input to each node in the graph
class GraphState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # The 'next_node' field indicates where to route to next
    next_node: str
    # initial user query
    user_query: str
    # instantiate memory
    convo_memory: InMemoryChatMessageHistory
    # options for the supervisor agent to decide which node to follow
    options: list
    # session id for the supervisor since that is another option for managing memory
    curr_session_id: str 


def input_first(state: GraphState) -> Dict[str, str]:
    print_ww(f"""start input_first()....::state={state}::""")
    init_input = state.get("user_query", "").strip()
    # store the input
    convo_memory =  InMemoryChatMessageHistory()
    convo_memory.add_user_message(init_input)
    options = ['FINISH', 'book_cancel_agent', 'pain_retriever_chain', 'ask_doctor_advice'] 
    return {"user_query":init_input, "options": options, "convo_memory": convo_memory}


def agent_node(state, final_result, name):
    state.get("convo_memory").add_ai_message(final_result)
    print(f"\nAgent:name={name}::AgentNode:state={state}::return:result={final_result}:::returning END now\n")
    return {"next_node": END, "answer": final_result}


def retriever_node(state: GraphState) -> Dict[str, str]:
    global pain_rag_chain
    print_ww(f"use this to go the retriever way to answer the question():: state::{state}")    
    init_input = state.get("user_query", "").strip()
    chat_history = extract_chat_history(state.get("convo_memory").messages)
    if pain_rag_chain == None:
        pain_rag_chain = create_retriever_pain()    
    
    # This agent is used to get the context for any questions related to medical issues such as aches, headache or body pain
    result = pain_rag_chain.invoke(
        {"input": init_input, "chat_history": chat_history},
        config={'configurable': {'session_id': 'TEST-123'}}
    )
    return agent_node(state, result['answer'], 'pain_retriever_chain')


def doctor_advice_node(state: GraphState) -> Dict[str, str]:
    print_ww(f"use this to answer about the Doctors advice from FINE TUNED Model::{state}::")
    chat_history = extract_chat_history(state.get("convo_memory").messages)
    # init_input = state.get("user_query", "").strip()
    result = ask_doctor_advice(boto3_bedrock, chat_history) 
    return agent_node(state, result, name="ask_doctor_advice")


def book_cancel_node(state: GraphState) -> Dict[str, str]:
    global book_cancel_agent, agent_executor_book_cancel
    print_ww(f"use this to book or cancel an appointment::{state}::")
    init_input = state.get("user_query", "").strip()
    agent_executor_book_cancel = create_book_cancel_agent()
    
    result = agent_executor_book_cancel.invoke(
        {"input": init_input, "chat_history": state.get("convo_memory").messages}, 
        config={"configurable": {"session_id": "session_1"}}
    ) 
    ret_val = result['output'][0]['text']
    return agent_node(state, ret_val, name="book_cancel_agent")


def error(state: GraphState) -> Dict[str, str]:
    print_ww(f"""start error()::state={state}::""")
    return {"final_result": "error", "first_word": "error", "second_word": "error"}


def supervisor_node(state: GraphState) -> Dict[str, str]:
    global supervisor_wrapped_chain
    print_ww(f"""supervisor_node()::state={state}::""") 
    init_input = state.get("user_query", "").strip()
    options = state.get("options", ['FINISH', 'book_cancel_agent', 'pain_retriever_chain', 'ask_doctor_advice']  )

    convo_memory = state.get("convo_memory")
    print(f"\nsupervisor_node():History of messages so far :::{convo_memory.messages}\n")
    
    supervisor_wrapped_chain = create_supervisor_agent()    
    result = supervisor_wrapped_chain.invoke({
        "input": init_input, 
        "options": options, 
        "history_chat": extract_chat_history(convo_memory.messages)
    })

    print_ww(f"\n\nsupervisor_node():result={result}......\n\n")
    return {"next_node": result.return_values["output"]}

```

## Set up the workflow:
LangGraph works by seamlessly knitting together our agents into a coherent workflow allowing us to set up the flow that is essential for agentic architectures. 


```python
workflow = StateGraph(GraphState)
workflow.add_node("pain_retriever_chain", retriever_node)
workflow.add_node("ask_doctor_advice", doctor_advice_node)
workflow.add_node("book_cancel_agent", book_cancel_node)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("init_input", input_first)
print(workflow)

members = ['pain_retriever_chain', 'ask_doctor_advice', 'book_cancel_agent', 'init_input'] 
print_ww(f"members of the nodes={members}")

# The supervisor populates the "next" field in the graph state which routes to a node or finishes
conditional_map = {k: k for k in members}
conditional_map["FINISH"] = END
workflow.add_conditional_edges("supervisor", lambda x: x["next_node"], conditional_map)

# add end just for all the nodes  
for member in members[:-1]:
    workflow.add_edge(member, END)

# entry node to supervisor
workflow.add_edge("init_input", "supervisor")

# Finally, add entrypoint
workflow.set_entry_point("init_input") 

graph = workflow.compile()
```

##### Finally, we visualize the entire workflow to make sure it meets our expectations. In our usecase the supervisor can 'litigate' the work to other agents or end the workflow itself.


```python
graph.get_graph().print_ascii()
```


```python
graph.invoke(
    {"user_query": "what is the general function of a doctor, what do they do?", "recursion_limit": 2, "curr_session_id": "session_1"},
)
```


```python
graph.invoke(
    {"user_query": "what are the effects of Asprin?", "recursion_limit": 2, "curr_session_id": "session_1"},
)
```


```python
graph.invoke(
    {"user_query": "what is the general function of a doctor, what do they do?", "recursion_limit": 2, "curr_session_id": "session_1"},
)
```


```python
graph.invoke(
    {"user_query": "Can you book an appointment for me?", "recursion_limit": 2, "curr_session_id": "session_1"},
)
```


```python
graph.invoke(
    {"user_query": "Can you book an appointment for Sept 24, 2024 10 am?", "recursion_limit": 2, "curr_session_id": "session_1"},
)
```


```python
appointments
```


```python
graph.invoke(
    {"user_query": "can you cancel my appointment with booking id of ID_100", "recursion_limit": 2, "curr_session_id": "session_1"},
)
```


```python
appointments
```


```python

```
