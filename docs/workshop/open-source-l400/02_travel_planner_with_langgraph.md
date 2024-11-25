<h1>Lab 2: Building a Travel Planner with a Simple LangGraph</h1>
<h2>Overview</h2>
<p>This lab guides you through the process of creating a simple Travel Planner using LangGraph, a library for building stateful, multi-step applications with language models. The Travel Planner demonstrates how to structure a conversational AI application that collects user input and generates personalized travel itineraries.</p>
<h4>What gets covered in this lab:</h4>
<p>we wil cover these aspects below:
- LangGraph constructs for how to build Agentic systems with Graph
- Introduction to short term and long term memory for 'turn-by-turn' conversations</p>
<h2>Intro to Agents</h2>
<p>Agents are intelligent systems or components that utilize Large Language Models (LLMs) to perform tasks in a dynamic and autonomous manner. Here's a breakdown of the key concepts:</p>
<h3>What Are Agents?</h3>
<ol>
<li>Step-by-Step Thinking: Agents leverage LLMs to think and reason through problems in a structured way, often referred to as chain-of-thought reasoning. This allows them to plan, evaluate, and execute tasks effectively.</li>
<li>Access to Tools: Agents can utilize external tools (e.g., calculators, databases, APIs) to enhance their decision-making and problem-solving capabilities.</li>
<li>Access to Memory: Agents can store and retrieve context, enabling them to work on tasks over time, adapt to user interactions, and handle complex workflows.</li>
</ol>
<p><strong>Key characteristics of AI agents include:</strong></p>
<p><strong>Perception:</strong> The ability to gather information from their environment through sensors or data inputs.
<strong>Decision-making:</strong> Using AI algorithms to process information and determine the best course of action.
<strong>Action:</strong> The capability to execute decisions and interact with the environment or users.
<strong>Learning:</strong> The ability to improve performance over time through experience and feedback.
<strong>Autonomy:</strong> Operating independently to some degree, without constant human intervention.
<strong>Goal-oriented:</strong> Working towards specific objectives or tasks.</p>
<p><img alt="agents_memory_light.png" src="images/agents_memory_light.png" /></p>
<h2>Use Case Details</h2>
<p>Our Travel Planner follows a straightforward, three-step process:</p>
<ol>
<li><strong>Initial User Input</strong>: </li>
<li>The application prompts the user to enter their desired travel plan to get assistance from AI Agent.</li>
<li>
<p>This information is stored in the state.</p>
</li>
<li>
<p><strong>Interests Input</strong>:</p>
</li>
<li>The user is asked to provide their interests for the trip.</li>
<li>
<p>These interests are stored as a list in the state.</p>
</li>
<li>
<p><strong>Itinerary Creation</strong>:</p>
</li>
<li>Using the collected city and interests, the application leverages a language model to generate a personalized day trip itinerary.</li>
<li>The generated itinerary is presented to the user.</li>
</ol>
<p>The flow between these steps is managed by LangGraph, which handles the state transitions and ensures that each step is executed in the correct order.</p>
<h3>Setup and Imports</h3>
<p>First, let's import the necessary modules and set up our environment.</p>
<p>```python
# %pip install -U --no-cache-dir  \
# "langchain==0.3.7" \
# "langchain-aws==0.2.6" \
# "langchain-community==0.3.5" \
# "langchain-text-splitters==0.3.2" \
# "langchainhub==0.1.20" \
# "langgraph==0.2.45" \
# "langgraph-checkpoint==2.0.2" \
# "langgraph-sdk==0.1.35" \
# "langsmith==0.1.140" \
# "pypdf==3.8,&lt;4" \
# "ipywidgets&gt;=7,&lt;8" \
# "matplotlib==3.9.0" \</p>
<h1>"faiss-cpu==1.8.0"</h1>
<h1>%pip install -U --no-cache-dir transformers</h1>
<h1>%pip install -U --no-cache-dir boto3</h1>
<h1>%pip install grandalf==3.1.2</h1>
<p>```</p>
<p>```python
import os
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.graph import MermaidDrawMethod
from IPython.display import display, Image
from dotenv import load_dotenv
import os</p>
<h1>load_dotenv()</h1>
<p>```</p>
<h2>LangGraph Basics</h2>
<h3>Key Components</h3>
<ol>
<li><strong>StateGraph</strong></li>
<li>This object will encapsulate the graph being traversed during excecution.</li>
<li>The core of our application, defining the flow of our Travel Planner.</li>
<li>
<p>PlannerState, a custom type representing the state of our planning process.</p>
</li>
<li>
<p><strong>Nodes</strong></p>
<ul>
<li>In LangGraph, nodes are typically python functions.</li>
<li>There are two main nodes we will use for our graph:<ul>
<li>The agent node: responsible for deciding what (if any) actions to take.</li>
<li>The tool node: This node will orchestrate calling the respective tool and returning the output. </li>
</ul>
</li>
</ul>
</li>
<li><strong>Edges</strong></li>
<li>Defines how the logic is routed and how the graph decides to stop.</li>
<li>Defines how your agents work and how different nodes communicate with each other.</li>
<li>
<p>There are a few key types of edges:
        - Normal Edges: Go directly from one node to the next.
        - Conditional Edges: Call a function to determine which node(s) to go to next.
        - Entry Point: Which node to call first when user input arrives.
        - Conditional Entry Point: Call a function to determine which node(s) to call first when user input arrives.</p>
</li>
<li>
<p><strong>LLM Integration</strong>: Utilizing a language model to generate the final itinerary.</p>
</li>
<li><strong>Memory Integration</strong>: Utilizing long term and short term memory for conversations</li>
</ol>
<h3>Define Agent State</h3>
<p>We'll define the state that our agent will maintain throughout its operation. First, define the <a href="https://langchain-ai.github.io/langgraph/concepts/low_level/#state">State</a> of the graph.  The State schema serves as the input schema for all Nodes and Edges in the graph.</p>
<p><code>python
class PlannerState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage], "The messages in the conversation"]
    itinerary: str
    city: str
    user_message: str</code></p>
<h3>Set Up Language Model and Prompts</h3>
<p>```python
from langchain_aws import ChatBedrockConverse
from langchain_aws import ChatBedrock
import boto3
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables.config import RunnableConfig
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder</p>
<h1>---- ⚠️ Update region for your AWS setup ⚠️ ----</h1>
<p>bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
provider_id = "anthropic"</p>
<p>llm = ChatBedrockConverse(
    model=model_id,
    provider=provider_id,
    temperature=0,
    max_tokens=None,
    client=bedrock_client,
)</p>
<p>itinerary_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful travel assistant. Create a day trip itinerary for {city} based on the user's interests. 
    Follow these instructions:
    1. Use the below chat conversation and the latest input from Human to get the user interests.
    2. Always account for travel time and meal times - if its not possible to do everything, then say so.
    3. If the user hasn't stated a time of year or season, assume summer season in {city} and state this assumption in your response.
    4. If the user hasn't stated a travel budget, assume a reasonable dollar amount and state this assumption in your response.
    5. Provide a brief, bulleted itinerary in chronological order with specific hours of day."""),
    MessagesPlaceholder("chat_history"),
    ("human", "{user_message}"),
])
```</p>
<h3>Define the nodes and Edges</h3>
<p>We are adding the nodes, edges as well as a persistant memory to the <code>StateGraph</code> before we compile it. 
- user travel plans
- invoke with Bedrock
- generate the travel plan for the day 
- ability to add or modify the plan</p>
<p>```python
def input_interests(state: PlannerState) -&gt; PlannerState:
    user_message = state['user_message'] #input("Your input: ")
    #print(f"We are going to :: {user_message}:: for trip to {state['city']} based on your interests mentioned in the prompt....")</p>
<pre><code>if not state.get('messages', None) : state['messages'] = []
return {
    **state,
}
</code></pre>
<p>def create_itinerary(state: PlannerState) -&gt; PlannerState:
    response = llm.invoke(itinerary_prompt.format_messages(city=state['city'], user_message=state['user_message'], chat_history=state['messages']))
    print("\nFinal Itinerary:")
    print(response.content)
    return {
        **state,
        "messages": state['messages'] + [HumanMessage(content=state['user_message']), AIMessage(content=response.content)],
        "itinerary": response.content
    }
```</p>
<h3>Create and Compile the Graph</h3>
<p>Now we'll create our LangGraph workflow and compile it. </p>
<ul>
<li>First, we initialize a StateGraph with the <code>State</code> class we defined above.</li>
<li>Then, we add our nodes and edges.</li>
<li>We use the <a href="https://langchain-ai.github.io/langgraph/concepts/low_level/#start-node"><code>START</code> Node, a special node</a> that sends user input to the graph, to indicate where to start our graph.</li>
<li>The <a href="https://langchain-ai.github.io/langgraph/concepts/low_level/#end-node"><code>END</code> Node</a> is a special node that represents a terminal node. </li>
</ul>
<p>```python
workflow = StateGraph(PlannerState)</p>
<h1>workflow.add_node("input_city", input_city)</h1>
<p>workflow.add_node("input_interests", input_interests)
workflow.add_node("create_itinerary", create_itinerary)</p>
<p>workflow.set_entry_point("input_interests")</p>
<h1>workflow.add_edge("input_city", "input_interests")</h1>
<p>workflow.add_edge("input_interests", "create_itinerary")
workflow.add_edge("create_itinerary", END)</p>
<h1>The checkpointer lets the graph persist its state</h1>
<h1>this is a complete memory for the entire graph.</h1>
<p>memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```</p>
<h3>Display the graph structure</h3>
<p>Finally, we <a href="https://langchain-ai.github.io/langgraph/concepts/low_level/#compiling-your-graph">compile our graph</a> to perform a few basic checks on the graph structure. We can visualize the graph as a <a href="https://github.com/mermaid-js/mermaid">Mermaid diagram</a>.</p>
<p><code>python
display(
    Image(
        app.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )
    )
)</code></p>
<h3>Define the function that runs the graph</h3>
<p>When we compile the graph, we turn it into a LangChain Runnable, which automatically enables calling <code>.invoke()</code>, <code>.stream()</code> and <code>.batch()</code> with your inputs. In the following example, we run <code>stream()</code> to invoke the graph with inputs</p>
<p>```python
def run_travel_planner(user_request: str, config_dict: dict):
    print(f"Current User Request: {user_request}\n")
    init_input = {"user_message": user_request,"city" : "Seattle"}</p>
<pre><code>for output in app.stream(init_input, config=config_dict, stream_mode="values"):
    pass  # The nodes themselves now handle all printing
</code></pre>
<p>```</p>
<h3>Travel Planner Example</h3>
<ul>
<li>To run this the system prompts and asks for user input for activities </li>
<li>We have initialized the graph state with city Seattle which usually will be dynamic and we will see in subsequrnt labs</li>
<li>You can enter like boating, swiming</li>
</ul>
<p>```python
config = {"configurable": {"thread_id": "1"}}</p>
<p>user_request = "Can you create a itinerary for a day trip in Seattle with boating and swimming options. Need a complete plan"
run_travel_planner(user_request, config)
```</p>
<h4>Leverage the memory saver to manipulate the Graph State</h4>
<ul>
<li>Since the <code>Conversation Messages</code> are part of the graph state we can leverage that</li>
<li>However the graph state is tied to <code>session_id</code> which will be passed in as a <code>thread_id</code> which ties to a session</li>
<li>If we add a request with different thread id it will create a new session which will not have the previous <code>Interests</code></li>
<li>However this this has the other check points variables as well and so this pattern is good for <code>A-Sync</code> workflow</li>
</ul>
<p>```python
config = {"configurable": {"thread_id": "1"}}</p>
<p>user_request = "Can you add white water rafting to this itinerary"
run_travel_planner(user_request, config)
```</p>
<h4>Run with another session</h4>
<p>Now this session will not have the previous conversations and we see it will create a new travel plan with the <code>white water rafting</code>  interests, not boating or swim</p>
<p>```python
config = {"configurable": {"thread_id": "11"}}</p>
<p>user_request = "Can you add white water rafting to itinerary"
run_travel_planner(user_request, config)
```</p>
<h2>Memory</h2>
<p>Memory is key for any agentic conversation which is <code>Multi-Turn</code> or <code>Multi-Agent</code> colloboration conversation and more so if it spans multiple days. The 3 main aspects of Agents are:
1. Tools
2. Memory
3. Planners</p>
<h3>Explore <code>External Store</code> for memory</h3>
<p>There are 2 types of memory for AI Agents, short term and long term memory which can be explained below. 
Further reading can be at this <a href="https://langchain-ai.github.io/langgraph/concepts/memory/#what-is-memory">link</a></p>
<p>Conversation memory can be explained by this diagram below which explains the <code>turn by turn</code> conversations which needs to be accessed by agents and then saved as a summary for long term memory</p>
<p><img src="./images/short-vs-long.png" width="35%"/></p>
<h4>Create an external <code>Memory persistence</code></h4>
<p>In this section we will leverage multi-thread, multi-session persistence to Chat Messages. Ideally you will leverage persistence like Redis Store etc to save messages per session</p>
<h5>Memory Management</h5>
<ul>
<li>We can have several Patterns - we can have each Agents with it's own Session memory</li>
<li>Or we can have the whole Graph have a combined memory in which case each agent will get it's own memory</li>
</ul>
<p>The MemorySaver or the Store have the concept of separating sections of memory by Namespaces or by Thread ID's and those can be leveraged to either 1/ Use the graph level message or memory 2/ Ecah agent can have it's own memory via space in saver or else having it's own saver like we do in the <code>ReACT agent</code></p>
<p><img src="./images/multi_memory_light.png" width="45%" alt='multi_memory_light.png' /> </p>
<p>```python
from langgraph.store.base import BaseStore, Item, Op, Result
from langgraph.store.memory import InMemoryStore
from typing import Any, Iterable, Literal, NamedTuple, Optional, Union, cast</p>
<p>class CustomMemoryStore(BaseStore):</p>
<pre><code>def __init__(self, ext_store):
    self.store = ext_store

def get(self, namespace: tuple[str, ...], key: str) -&gt; Optional[Item]:
    return self.store.get(namespace,key)

def put(self, namespace: tuple[str, ...], key: str, value: dict[str, Any]) -&gt; None:
    return self.store.put(namespace, key, value)
def batch(self, ops: Iterable[Op]) -&gt; list[Result]:
    return self.store.batch(ops)
async def abatch(self, ops: Iterable[Op]) -&gt; list[Result]:
    return self.store.abatch(ops)
</code></pre>
<p>```</p>
<h4>Quick look at how to use this store</h4>
<p>```python
in_memory_store = CustomMemoryStore(InMemoryStore())
namespace_u = ("chat_messages", "user_id_1")
key_u="user_id_1"
in_memory_store.put(namespace_u, key_u, {"data":["list a"]})
item_u = in_memory_store.get(namespace_u, key_u)
print(item_u.value, item_u.value['data'])</p>
<p>in_memory_store.list_namespaces()
```</p>
<h4>Create the similiar graph as earlier -- note we will not have any mesages in the Graph state as that has been externalized</h4>
<p><code>python
class PlannerState(TypedDict):
    itinerary: str
    city: str
    user_message: str</code></p>
<p>```python
def input_interests(state: PlannerState, config: RunnableConfig, <em>, store: BaseStore) -&gt; PlannerState:
    user_message = state['user_message'] #input("Your input: ")
    return {
        </em>*state,
    }</p>
<p>def create_itinerary(state: PlannerState, config: RunnableConfig, *, store: BaseStore) -&gt; PlannerState:
    #- get the history from the store
    user_u = f"user_id_{config['configurable']['thread_id']}"
    namespace_u = ("chat_messages", user_u)
    store_item = store.get(namespace=namespace_u, key=user_u)
    chat_history_messages = store_item.value['data'] if store_item else []
    print(user_u,chat_history_messages)</p>
<pre><code>response = llm.invoke(itinerary_prompt.format_messages(city=state['city'], user_message=state['user_message'], chat_history=chat_history_messages))
print("\nFinal Itinerary:")
print(response.content)

#- add back to the store
store.put(namespace=namespace_u, key=user_u, value={"data":chat_history_messages+[HumanMessage(content=state['user_message']),AIMessage(content=response.content)]})

return {
    **state,
    "itinerary": response.content
}
</code></pre>
<p>```</p>
<p>```python
in_memory_store_n = CustomMemoryStore(InMemoryStore())</p>
<p>workflow = StateGraph(PlannerState)</p>
<h1>workflow.add_node("input_city", input_city)</h1>
<p>workflow.add_node("input_interests", input_interests)
workflow.add_node("create_itinerary", create_itinerary)</p>
<p>workflow.set_entry_point("input_interests")</p>
<h1>workflow.add_edge("input_city", "input_interests")</h1>
<p>workflow.add_edge("input_interests", "create_itinerary")
workflow.add_edge("create_itinerary", END)</p>
<p>app = workflow.compile(store=in_memory_store_n)
```</p>
<p>```python
def run_travel_planner(user_request: str, config_dict: dict):
    print(f"Current User Request: {user_request}\n")
    init_input = {"user_message": user_request,"city" : "Seattle"}</p>
<pre><code>for output in app.stream(init_input, config=config_dict, stream_mode="values"):
    pass  # The nodes themselves now handle all printing
</code></pre>
<p>config = {"configurable": {"thread_id": "1"}}</p>
<p>user_request = "Can you create a itinerary for a day trip in california with boating and swimming options.  I need a complete plan that budgets for travel time and meal time."
run_travel_planner(user_request, config)</p>
<p>```</p>
<p>```python
config = {"configurable": {"thread_id": "1"}}</p>
<p>user_request = "Can you add itinerary for white water rafting to this"
run_travel_planner(user_request, config)
```</p>
<h4>Quick look at the store</h4>
<p>it will show the History of the Chat Messages</p>
<p><code>python
print(in_memory_store_n.list_namespaces())
print(in_memory_store_n.get(('chat_messages', 'user_id_1'),'user_id_1').value)</code></p>
<h3>Finally we review the concept of having Each <code>Agent</code> be backed by it's own memory</h3>
<p>For this we will leverage the RunnableWithMessageHistory when creating the agent
- Here we create to simulate a InMemoryChatMessageHistory, but this will be externalized in produftion use cases
- use this this as a sample</p>
<p>```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory</p>
<h1>---- ⚠️ Update region for your AWS setup ⚠️ ----</h1>
<p>bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
model_id = "anthropic.claude-3-haiku-20240307-v1:0"</p>
<h1>model_id = "anthropic.claude-3-sonnet-20240229-v1:0"</h1>
<h1>model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"</h1>
<p>provider_id = "anthropic"</p>
<p>chatbedrock_llm = ChatBedrockConverse(
    model=model_id,
    provider=provider_id,
    temperature=0,
    max_tokens=None,
    client=bedrock_client,
    # other params...
)</p>
<p>itinerary_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful travel assistant. Create a day trip itinerary for {city} based on the user's interests. 
    Follow these instructions:
    1. Use the below chat conversation and the latest input from Human to get the user interests.
    2. Always account for travel time and meal times - if its not possible to do everything, then say so.
    3. If the user hasn't stated a time of year or season, assume summer season in {city} and state this assumption in your response.
    4. If the user hasn't stated a travel budget, assume a reasonable dollar amount and state this assumption in your response.
    5. Provide a brief, bulleted itinerary in chronological order with specific hours of day."""),
    MessagesPlaceholder("chat_history"),
    ("human", "{user_message}"),
])
chain = itinerary_prompt | chatbedrock_llm </p>
<p>history = InMemoryChatMessageHistory()
def get_history():
    return history</p>
<p>wrapped_chain = RunnableWithMessageHistory(
    chain,
    get_history,
    history_messages_key="chat_history",
)</p>
<p>```</p>
<p>```python
class PlannerState(TypedDict):
    itinerary: str
    city: str
    user_message: str</p>
<p>def input_interests(state: PlannerState, config: RunnableConfig, <em>, store: BaseStore) -&gt; PlannerState:
    user_message = state['user_message'] #input("Your input: ")
    return {
        </em>*state,
    }</p>
<p>def create_itinerary(state: PlannerState, config: RunnableConfig, *, store: BaseStore) -&gt; PlannerState:
    #- each agent manages it's memory
    response = wrapped_chain.invoke({"city": state['city'], "user_message": state['user_message'], "input": state['user_message']} )
    print("\nFinal Itinerary:")
    print(response.content)</p>
<pre><code>return {
    **state,
    "itinerary": response.content
}
</code></pre>
<p>```</p>
<p>```python
workflow = StateGraph(PlannerState)</p>
<h1>workflow.add_node("input_city", input_city)</h1>
<p>workflow.add_node("input_interests", input_interests)
workflow.add_node("create_itinerary", create_itinerary)</p>
<p>workflow.set_entry_point("input_interests")</p>
<h1>workflow.add_edge("input_city", "input_interests")</h1>
<p>workflow.add_edge("input_interests", "create_itinerary")
workflow.add_edge("create_itinerary", END)</p>
<p>app = workflow.compile()
```</p>
<p>```python
def run_travel_planner(user_request: str, config_dict: dict):
    print(f"Current User Request: {user_request}\n")
    init_input = {"user_message": user_request,"city" : "Seattle"}</p>
<pre><code>for output in app.stream(init_input, config=config_dict, stream_mode="values"):
    pass  # The nodes themselves now handle all printing
</code></pre>
<p>config = {"configurable": {"thread_id": "1"}}</p>
<p>user_request = "Can you create a itinerary for boating, swim. Need a complete plan"
run_travel_planner(user_request, config)
```</p>
<p><code>python
user_request = "Can you add white water rafting to this itinerary"
run_travel_planner(user_request, config)</code></p>
<h2>Conclusion</h2>
<p>You have successfully executed a simple LangGraph implementation, this lab demonstrates how LangGraph can be used to create a simple yet effective Travel Planner. By structuring our application as a graph of interconnected nodes, we achieve a clear separation of concerns and a easily modifiable workflow. This approach can be extended to more complex applications, showcasing the power and flexibility of graph-based designs in AI-driven conversational interfaces.</p>
<p>Please proceed to the next lab</p>