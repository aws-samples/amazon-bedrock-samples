# Building a Travel Planner with a Simple LangGraph

## Overview

This lab guides you through the process of creating a simple Travel Planner using LangGraph, a library for building stateful, multi-step applications with language models. The Travel Planner demonstrates how to structure a conversational AI application that collects user input and generates personalized travel itineraries.

## Intro to Agents
- Agents are leverage LLM to `think step by step` and then plan the execution
- Agents have access to tools
- Agents have access to memory. Below diagram illustrates this concept

#### Memory Management
Memory is key for any agentic conversation which is `Multi-Turn` or `Multi-Agent` colloboration conversation and more so if it spans multiple days. The 3 main aspects of Agents are:
1. Tools
2. Memory
3. Planners

- ![Agent memory](./images/agents_memory_light.png)

## Use Case Details

Our Travel Planner follows a straightforward, three-step process:

1. **Initial User Input**: 
   - The application prompts the user to enter their desired travel plan to get assistance from AI Agent.
   - This information is stored in the state.

2. **Interests Input**:
   - The user is asked to provide their interests for the trip.
   - These interests are stored as a list in the state.

3. **Itinerary Creation**:
   - Using the collected city and interests, the application leverages a language model to generate a personalized day trip itinerary.
   - The generated itinerary is presented to the user.

The flow between these steps is managed by LangGraph, which handles the state transitions and ensures that each step is executed in the correct order.

The below diagram illustrates this:

![Travel Planner Agent](./images/agents_itinerary.png)


```python

# %pip install -U --no-cache-dir  \
# langchain>=0.3.7 \ 
# langchain-anthropic>=0.1.15 \
# langchain-aws>=0.2.6 \
# langchain-community>=0.3.5 \
# langchain-core>=0.3.15 \
# langchain-text-splitters>=0.3.2 \
# langchainhub>=0.1.20 \
# langgraph>=0.2.45 \
# langgraph-checkpoint>=2.0.2 \
# langgraph-sdk>=0.1.35 \
# langsmith>=0.1.140 \
# sqlalchemy -U \
# "faiss-cpu>=1.7,<2" \
# "pypdf>=3.8,<4" \
# "ipywidgets>=7,<8" \
# matplotlib>=3.9.0 \

#%pip install -U --no-cache-dir transformers
#%pip install -U --no-cache-dir boto3
#%pip install grandalf==3.1.2
```

### Setup and Imports

First, let's import the necessary modules and set up our environment.


```python
import os
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.graph import MermaidDrawMethod
from IPython.display import display, Image
from dotenv import load_dotenv
import os
#load_dotenv()
```

## LangGraph -- State Graph, Nodes and Edges

First, we are initializing the ```StateGraph```. This object will encapsulate the graph being traversed during excecution.

Then we define the **nodes** in our graph. In LangGraph, nodes are typically python functions. There are two main nodes we will use for our graph:
- The agent node: responsible for deciding what (if any) actions to take.
- The tool node: This node will orchestrate calling the respective tool and returning the output. This means if the agent decides to take an action, this node will then execute that action.

**Edges** define how the logic is routed and how the graph decides to stop. This is a big part of how your agents work and how different nodes communicate with each other. There are a few key types of edges:

- Normal Edges: Go directly from one node to the next.
- Conditional Edges: Call a function to determine which node(s) to go to next.
- Entry Point: Which node to call first when user input arrives.
- Conditional Entry Point: Call a function to determine which node(s) to call first when user input arrives.

In our case we need to define a conditional edge that routes to the ```ToolNode``` when a tool get called in the agent node, i.e. when the LLM determines the requirement of tool use. With ```tools_condition```, LangGraph provides a preimplemented function handling this. Further, an edge from the ```START```node to the ```assistant```and from the ```ToolNode``` back to the ```assistant``` are required.

We are adding the nodes, edges as well as a persistant memory to the ```StateGraph``` before we compile it. 

### Define Agent State

We'll define the state that our agent will maintain throughout its operation. First, define the [State](https://langchain-ai.github.io/langgraph/concepts/low_level/#state) of the graph.  The State schema serves as the input schema for all Nodes and Edges in the graph.

Let's use the `TypedDict` class from python's `typing` module as our schema, which provides type hints for the keys.

### Key Components

1. **StateGraph**: The core of our application, defining the flow of our Travel Planner.
2. **PlannerState**: A custom type representing the state of our planning process.
3. **Node Functions**: Individual steps in our planning process (input_city, input_interests, create_itinerary).
4. **LLM Integration**: Utilizing a language model to generate the final itinerary.
5. **Memory Integration**: Utilizing long term and short term memory for conversations

#### Advanced concepts

Now we'll define the main functions nodes that our agent will use: get interests, create itinerary. 

- [Nodes](https://langchain-ai.github.io/langgraph/concepts/low_level/#nodes) are python functions.
- The first positional argument is the state, as defined above. 
- State is a `TypedDict` with schema as defined above, each node can access the key, `graph_state`, with `state['graph_state']`. 
- Each node returns a new value of the state key `graph_state`.
  
By default, the new value returned by each node [will override](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers) the prior state value.

### Memory

1. We will disscuss memory is detail in subsequent sections below how some some key points
2. We have `Conversational Memory` which is needed for all agents to have context since this is a `ChatBot` which needs history of conversations
3. We usually summarize these into a **Summary Conversation** alternating with Human | AI for multi session conversations
4. We have the concept of Graph State which is for Async workflows where we need to resume the workflow from a **certain point** in history

For `A-Sync` workflows where we need to persist the state of the graph and bring it back once we get the required data. below diagram explains this concept. 

![Graph state](./images/graph_state_light.png)


### Define Agent Nodes

we will create a simple graph with 
- user travel plans
- invoke with Bedrock
- generate the travel plan for the day 
- ability to add or modify the plan


```python
class PlannerState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage], "The messages in the conversation"]
    itinerary: str
    city: str
    user_message: str
```

### Set Up Language Model and Prompts



```python
#llm = ChatOpenAI(model="gpt-4o-mini")

from langchain_aws import ChatBedrockConverse
from langchain_aws import ChatBedrock
import boto3
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables.config import RunnableConfig
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ---- ⚠️ Update region for your AWS setup ⚠️ ----
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
#model_id = "anthropic.claude-3-sonnet-20240229-v1:0"#
#model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"

provider_id = "anthropic"

llm = ChatBedrockConverse(
    model=model_id,
    provider=provider_id,
    temperature=0,
    max_tokens=None,
    client=bedrock_client,
    # other params...
)


itinerary_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel assistant. Create a day trip itinerary for {city} based on the user's interests. Use the below chat conversation and the latest input from Human to get the user interests. Provide a brief, bulleted itinerary."),
    MessagesPlaceholder("chat_history"),
    ("human", "{user_message}"),
])
```

### Define the nodes and Edges


```python
def input_interests(state: PlannerState) -> PlannerState:
    user_message = state['user_message'] #input("Your input: ")
    #print(f"We are going to :: {user_message}:: for trip to {state['city']} based on your interests mentioned in the prompt....")

    if not state.get('messages', None) : state['messages'] = []
    return {
        **state,
    }

def create_itinerary(state: PlannerState) -> PlannerState:
    response = llm.invoke(itinerary_prompt.format_messages(city=state['city'], user_message=state['user_message'], chat_history=state['messages']))
    print("\nFinal Itinerary:")
    print(response.content)
    return {
        **state,
        "messages": state['messages'] + [HumanMessage(content=state['user_message']),AIMessage(content=response.content)],
        "itinerary": response.content
    }
```

### Create and Compile the Graph

Now we'll create our LangGraph workflow and compile it. We build the graph from our [components](
https://langchain-ai.github.io/langgraph/concepts/low_level/) defined above. The [StateGraph class](https://langchain-ai.github.io/langgraph/concepts/low_level/#stategraph) is the graph class that we can use.
 
First, we initialize a StateGraph with the `State` class we defined above. Then, we add our nodes and edges. We use the [`START` Node, a special node](https://langchain-ai.github.io/langgraph/concepts/low_level/#start-node) that sends user input to the graph, to indicate where to start our graph. The [`END` Node](https://langchain-ai.github.io/langgraph/concepts/low_level/#end-node) is a special node that represents a terminal node. 



```python
workflow = StateGraph(PlannerState)

#workflow.add_node("input_city", input_city)
workflow.add_node("input_interests", input_interests)
workflow.add_node("create_itinerary", create_itinerary)

workflow.set_entry_point("input_interests")

#workflow.add_edge("input_city", "input_interests")
workflow.add_edge("input_interests", "create_itinerary")
workflow.add_edge("create_itinerary", END)

# The checkpointer lets the graph persist its state
# this is a complete memory for the entire graph.
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

### Display the graph structure

Finally, we [compile our graph](https://langchain-ai.github.io/langgraph/concepts/low_level/#compiling-your-graph) to perform a few basic checks on the graph structure. We can visualize the graph as a [Mermaid diagram](https://github.com/mermaid-js/mermaid).


```python
display(
    Image(
        app.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API,
        )
    )
)
```


    
![jpeg](Travel_planner_with_langgraph_files/Travel_planner_with_langgraph_14_0.jpg)
    


### Define the function that runs the graph

When we compile the graph, we turn it into a LangChain Runnable, which automatically enables calling `.invoke()`, `.stream()` and `.batch()` with your inputs. In the following example, we run `stream()` to invoke the graph with inputs


```python
def run_travel_planner(user_request: str, config_dict: dict):
    print(f"Current User Request: {user_request}\n")
    init_input = {"user_message": user_request,"city" : "Seattle"}

    for output in app.stream(init_input, config=config_dict, stream_mode="values"):
        pass  # The nodes themselves now handle all printing
```

### Travel Planner Example

- To run this the system prompts and asks for user input for activities 
- We have initialized the graph state with city Seattle which usually will be dynamic and we will see in subsequrnt labs
- You can enter like boating, swiming


```python
config = {"configurable": {"thread_id": "1"}}

user_request = "Can you create a itinerary for boating, swim. Need a complete plan"
run_travel_planner(user_request, config)
```

    Current User Request: Can you create a itinerary for boating, swim. Need a complete plan
    
    
    Final Itinerary:
    Okay, based on your interest in boating and swimming, here is a suggested day trip itinerary for Seattle:
    
    Seattle Day Trip Itinerary:
    
    Morning:
    - Start your day at Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.
    - Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.
    
    Afternoon: 
    - Head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.
    - Have lunch at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.
    
    Late Afternoon:
    - Visit Seacrest Park in West Seattle, which has a public swimming pool, beach access, and a fishing pier. Spend time swimming, relaxing on the beach, or trying your luck at fishing.
    - As the day winds down, take the West Seattle Water Taxi back to downtown Seattle, enjoying the skyline views.
    
    Evening:
    - For dinner, consider a seafood-focused restaurant like Ivar's Acres of Clams on the Seattle Waterfront, with views of the Puget Sound.
    
    Let me know if you would like me to modify or expand on this Seattle day trip itinerary focused on boating and swimming activities.


#### Leverage the memory saver to manipulate the Graph State
- Since the `Conversation Messages` are part of the graph state we can leverage that
- However the graph state is tied to `session_id` which will be passed in as a `thread_id` which ties to a session
- If we add a request with different thread id it will create a new session which will not have the previous `Interests`
- However this this has the other check points variables as well and so this pattern is good for `A-Sync` workflow


```python
config = {"configurable": {"thread_id": "1"}}

user_request = "Can you add white water rafting to this itinerary"
run_travel_planner(user_request, config)
```

    Current User Request: Can you add white water rafting to this itinerary
    
    
    Final Itinerary:
    Okay, great, let's add white water rafting to the Seattle day trip itinerary:
    
    Seattle Day Trip Itinerary with White Water Rafting:
    
    Morning:
    - Start your day at Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.
    - Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.
    
    Mid-Morning:
    - Head out of the city to the Skykomish River, about a 1-hour drive from Seattle, for a white water rafting adventure. Spend 2-3 hours rafting down the river's class II-III rapids.
    
    Afternoon:
    - After your rafting trip, head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.
    - Have lunch at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.
    
    Late Afternoon:
    - Visit Seacrest Park in West Seattle, which has a public swimming pool, beach access, and a fishing pier. Spend time swimming, relaxing on the beach, or trying your luck at fishing.
    - As the day winds down, take the West Seattle Water Taxi back to downtown Seattle, enjoying the skyline views.
    
    Evening:
    - For dinner, consider a seafood-focused restaurant like Ivar's Acres of Clams on the Seattle Waterfront, with views of the Puget Sound.
    
    Let me know if you would like me to modify or expand on this updated Seattle day trip itinerary that includes white water rafting.


#### Run with another session

Now this session will not have the previous conversations and we see it will create a new travel plan with the `white water rafting`  interests, not boating or swim


```python
config = {"configurable": {"thread_id": "11"}}

user_request = "Can you add white water rafting to itinerary"
run_travel_planner(user_request, config)
```

    Current User Request: Can you add white water rafting to this itinerary
    
    
    Final Itinerary:
    Okay, got it. Based on our previous conversation and your latest request to add white water rafting, here is a suggested day trip itinerary for Seattle:
    
    Seattle Day Trip Itinerary:
    
    - Start your day with a visit to the iconic Pike Place Market - explore the bustling stalls, grab a coffee, and watch the famous fish throwing.
    - Head to the Space Needle for panoramic views of the city skyline and the Puget Sound.
    - Enjoy a white water rafting adventure on one of the nearby rivers, such as the Skykomish or Snoqualmie River. This will be an exhilarating way to experience the natural beauty around Seattle.
    - After the rafting, have lunch at one of the waterfront restaurants with views of the Puget Sound and the Olympic Mountains.
    - Spend the afternoon exploring the Museum of Pop Culture (MoPOP) and learning about Seattle's music and pop culture heritage.
    - End your day with a stroll through the Chihuly Garden and Glass, admiring the stunning glass sculptures.
    
    Let me know if you would like me to modify or add anything to this Seattle day trip itinerary!


### Explore `External Store` for memory


For Memory we further need short term and long term memory which can be explained below. Further reading can be at this [link](https://langchain-ai.github.io/langgraph/concepts/memory/#what-is-memory)

Conversation memory can be explained by this diagram below which explains the `turn by turn` conversations which needs to be accessed by agents and then saved as a summary for long term memory

![long term memory](./images/short-vs-long.png)



#### Create a `Store`

In this section we will leverage multi-thread, multi-session persistence to Chat Messages. Ideally you will leverage persistence like Redis Store etc to save messages per session


```python
from langgraph.store.base import BaseStore, Item, Op, Result
from langgraph.store.memory import InMemoryStore
from typing import Any, Iterable, Literal, NamedTuple, Optional, Union, cast

class CustomMemoryStore(BaseStore):

    def __init__(self, ext_store):
        self.store = ext_store

    def get(self, namespace: tuple[str, ...], key: str) -> Optional[Item]:
        return self.store.get(namespace,key)

    def put(self, namespace: tuple[str, ...], key: str, value: dict[str, Any]) -> None:
        return self.store.put(namespace, key, value)
    def batch(self, ops: Iterable[Op]) -> list[Result]:
        return self.store.batch(ops)
    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        return self.store.abatch(ops)

```

#### Quick look at how to use this store


```python
in_memory_store = CustomMemoryStore(InMemoryStore())
namespace_u = ("chat_messages", "user_id_1")
key_u="user_id_1"
in_memory_store.put(namespace_u, key_u, {"data":["list a"]})
item_u = in_memory_store.get(namespace_u, key_u)
print(item_u.value, item_u.value['data'])

in_memory_store.list_namespaces()
```

    {'data': ['list a']} ['list a']





    [('chat_messages', 'user_id_1')]



#### Create the similiar graph as earlier -- note we will not have any mesages in the Graph state as that has been externalized


```python
class PlannerState(TypedDict):
    itinerary: str
    city: str
    user_message: str
```


```python
def input_interests(state: PlannerState, config: RunnableConfig, *, store: BaseStore) -> PlannerState:
    user_message = state['user_message'] #input("Your input: ")
    return {
        **state,
    }

def create_itinerary(state: PlannerState, config: RunnableConfig, *, store: BaseStore) -> PlannerState:
    #- get the history from the store
    user_u = f"user_id_{config['configurable']['thread_id']}"
    namespace_u = ("chat_messages", user_u)
    store_item = store.get(namespace=namespace_u, key=user_u)
    chat_history_messages = store_item.value['data'] if store_item else []
    print(user_u,chat_history_messages)

    response = llm.invoke(itinerary_prompt.format_messages(city=state['city'], user_message=state['user_message'], chat_history=chat_history_messages))
    print("\nFinal Itinerary:")
    print(response.content)

    #- add back to the store
    store.put(namespace=namespace_u, key=user_u, value={"data":chat_history_messages+[HumanMessage(content=state['user_message']),AIMessage(content=response.content)]})
    
    return {
        **state,
        "itinerary": response.content
    }
```


```python
in_memory_store_n = CustomMemoryStore(InMemoryStore())

workflow = StateGraph(PlannerState)

#workflow.add_node("input_city", input_city)
workflow.add_node("input_interests", input_interests)
workflow.add_node("create_itinerary", create_itinerary)

workflow.set_entry_point("input_interests")

#workflow.add_edge("input_city", "input_interests")
workflow.add_edge("input_interests", "create_itinerary")
workflow.add_edge("create_itinerary", END)


app = workflow.compile(store=in_memory_store_n)
```


```python
def run_travel_planner(user_request: str, config_dict: dict):
    print(f"Current User Request: {user_request}\n")
    init_input = {"user_message": user_request,"city" : "Seattle"}

    for output in app.stream(init_input, config=config_dict, stream_mode="values"):
        pass  # The nodes themselves now handle all printing

config = {"configurable": {"thread_id": "1"}}

user_request = "Can you create a itinerary for boating, swim. Need a complete plan"
run_travel_planner(user_request, config)

```

    Current User Request: Can you create a itinerary for boating, swim. Need a complete plan
    
    user_id_1 []
    
    Final Itinerary:
    Okay, based on your interest in boating and swimming, here is a suggested day trip itinerary for Seattle:
    
    Seattle Day Trip Itinerary:
    
    Morning:
    - Start your day at Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.
    - Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.
    
    Afternoon: 
    - Head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.
    - Have lunch at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.
    
    Late Afternoon:
    - Visit Seacrest Park in West Seattle, which has a public swimming pool, beach access, and a fishing pier. Spend time swimming, relaxing, and taking in the views.
    - Consider taking the West Seattle Water Taxi back to downtown Seattle for a scenic ride across the harbor.
    
    Evening:
    - Finish your day with dinner at a waterfront restaurant in Seattle's vibrant Pike Place Market area, watching the sunset over the Puget Sound.
    
    Let me know if you would like me to modify or expand on this itinerary in any way!



```python
config = {"configurable": {"thread_id": "1"}}

user_request = "Can you add itinerary for white water rafting to this"
run_travel_planner(user_request, config)
```

    Current User Request: Can you add itinerary for white water rafting to this
    
    user_id_1 [HumanMessage(content='Can you create a itinerary for boating, swim. Need a complete plan', additional_kwargs={}, response_metadata={}), AIMessage(content="Okay, based on your interest in boating and swimming, here is a suggested day trip itinerary for Seattle:\n\nSeattle Day Trip Itinerary:\n\nMorning:\n- Start your day at Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.\n- Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.\n\nAfternoon: \n- Head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.\n- Have lunch at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.\n\nLate Afternoon:\n- Visit Seacrest Park in West Seattle, which has a public swimming pool, beach access, and a fishing pier. Spend time swimming, relaxing, and taking in the views.\n- Consider taking the West Seattle Water Taxi back to downtown Seattle for a scenic ride across the harbor.\n\nEvening:\n- Finish your day with dinner at a waterfront restaurant in Seattle's vibrant Pike Place Market area, watching the sunset over the Puget Sound.\n\nLet me know if you would like me to modify or expand on this itinerary in any way!", additional_kwargs={}, response_metadata={})]
    
    Final Itinerary:
    Okay, here's an updated day trip itinerary for Seattle that includes white water rafting:
    
    Seattle Day Trip Itinerary:
    
    Morning:
    - Start your day with a white water rafting adventure on the Skykomish River, about 1 hour east of Seattle. Spend 2-3 hours rafting down the scenic river with class III-IV rapids.
    
    Afternoon:
    - Head back to Seattle and visit Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.
    - Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.
    
    Late Afternoon:
    - Head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.
    - Have dinner at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.
    
    Evening:
    - Finish your day with a scenic ride on the West Seattle Water Taxi back to downtown Seattle, watching the sunset over the Puget Sound.
    
    Let me know if you would like me to modify or expand on this updated itinerary further.


#### Quick look at the store

it will show the History of the Chat Messages


```python
print(in_memory_store_n.list_namespaces())
print(in_memory_store_n.get(('chat_messages', 'user_id_1'),'user_id_1').value)
```

    [('chat_messages', 'user_id_1')]
    {'data': [HumanMessage(content='Can you create a itinerary for boating, swim. Need a complete plan', additional_kwargs={}, response_metadata={}), AIMessage(content="Okay, based on your interest in boating and swimming, here is a suggested day trip itinerary for Seattle:\n\nSeattle Day Trip Itinerary:\n\nMorning:\n- Start your day at Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.\n- Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.\n\nAfternoon: \n- Head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.\n- Have lunch at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.\n\nLate Afternoon:\n- Visit Seacrest Park in West Seattle, which has a public swimming pool, beach access, and a fishing pier. Spend time swimming, relaxing, and taking in the views.\n- Consider taking the West Seattle Water Taxi back to downtown Seattle for a scenic ride across the harbor.\n\nEvening:\n- Finish your day with dinner at a waterfront restaurant in Seattle's vibrant Pike Place Market area, watching the sunset over the Puget Sound.\n\nLet me know if you would like me to modify or expand on this itinerary in any way!", additional_kwargs={}, response_metadata={}), HumanMessage(content='Can you add itinerary for white water rafting to this', additional_kwargs={}, response_metadata={}), AIMessage(content="Okay, here's an updated day trip itinerary for Seattle that includes white water rafting:\n\nSeattle Day Trip Itinerary:\n\nMorning:\n- Start your day with a white water rafting adventure on the Skykomish River, about 1 hour east of Seattle. Spend 2-3 hours rafting down the scenic river with class III-IV rapids.\n\nAfternoon:\n- Head back to Seattle and visit Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.\n- Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.\n\nLate Afternoon:\n- Head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.\n- Have dinner at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.\n\nEvening:\n- Finish your day with a scenic ride on the West Seattle Water Taxi back to downtown Seattle, watching the sunset over the Puget Sound.\n\nLet me know if you would like me to modify or expand on this updated itinerary further.", additional_kwargs={}, response_metadata={})]}


### Finally we review the concept of having Ecah `Agent` be backed by it's own memory

For this we will leverage the RunnableWithMessageHistory when creating the agent
- Here we create to simulate a InMemoryChatMessageHistory, but this will be externalized in produftion use cases
- use this this as a sample


```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory


# ---- ⚠️ Update region for your AWS setup ⚠️ ----
bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
#model_id = "anthropic.claude-3-sonnet-20240229-v1:0"#
#model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"

provider_id = "anthropic"

chatbedrock_llm = ChatBedrockConverse(
    model=model_id,
    provider=provider_id,
    temperature=0,
    max_tokens=None,
    client=bedrock_client,
    # other params...
)

itinerary_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel assistant. Create a day trip itinerary for {city} based on the user's interests. Use the below chat conversation and the latest input from Human to get the user interests. Provide a brief, bulleted itinerary."),
    MessagesPlaceholder("chat_history"),
    ("human", "{user_message}"),
])
chain = itinerary_prompt | chatbedrock_llm 

history = InMemoryChatMessageHistory()
def get_history():
    return history

wrapped_chain = RunnableWithMessageHistory(
    chain,
    get_history,
    history_messages_key="chat_history",
)

```


```python
class PlannerState(TypedDict):
    itinerary: str
    city: str
    user_message: str

def input_interests(state: PlannerState, config: RunnableConfig, *, store: BaseStore) -> PlannerState:
    user_message = state['user_message'] #input("Your input: ")
    return {
        **state,
    }

def create_itinerary(state: PlannerState, config: RunnableConfig, *, store: BaseStore) -> PlannerState:
    #- each agent manages it's memory
    response = wrapped_chain.invoke({"city": state['city'], "user_message": state['user_message'], "input": state['user_message']} )
    print("\nFinal Itinerary:")
    print(response.content)
    
    return {
        **state,
        "itinerary": response.content
    }
```


```python
workflow = StateGraph(PlannerState)

#workflow.add_node("input_city", input_city)
workflow.add_node("input_interests", input_interests)
workflow.add_node("create_itinerary", create_itinerary)

workflow.set_entry_point("input_interests")

#workflow.add_edge("input_city", "input_interests")
workflow.add_edge("input_interests", "create_itinerary")
workflow.add_edge("create_itinerary", END)


app = workflow.compile()
```


```python
def run_travel_planner(user_request: str, config_dict: dict):
    print(f"Current User Request: {user_request}\n")
    init_input = {"user_message": user_request,"city" : "Seattle"}

    for output in app.stream(init_input, config=config_dict, stream_mode="values"):
        pass  # The nodes themselves now handle all printing

config = {"configurable": {"thread_id": "1"}}

user_request = "Can you create a itinerary for boating, swim. Need a complete plan"
run_travel_planner(user_request, config)
```

    Current User Request: Can you create a itinerary for boating, swim. Need a complete plan
    
    
    Final Itinerary:
    Okay, based on your interest in boating and swimming, here is a suggested day trip itinerary for Seattle:
    
    Seattle Day Trip Itinerary:
    
    Morning:
    - Start your day at Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.
    - Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.
    
    Afternoon: 
    - Head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.
    - Have lunch at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.
    
    Late Afternoon:
    - Visit Seacrest Park in West Seattle, which has a public swimming pool, beach access, and a fishing pier. Spend time swimming, relaxing, and taking in the views.
    - Consider taking the West Seattle Water Taxi back to downtown Seattle for a scenic ride across the harbor.
    
    Evening:
    - Finish your day with dinner at a waterfront restaurant in Seattle's vibrant Pike Place Market area, watching the sunset over the Puget Sound.
    
    Let me know if you would like me to modify or expand on this itinerary in any way!



```python
user_request = "Can you add white water rafting to this itinerary"
run_travel_planner(user_request, config)
```

    Current User Request: Can you add white water rafting to this itinerary
    
    
    Final Itinerary:
    Okay, great, let's add white water rafting to the Seattle day trip itinerary:
    
    Seattle Day Trip Itinerary with White Water Rafting:
    
    Morning:
    - Start your day at Fishermen's Terminal, a historic working waterfront. Rent a small boat or kayak and explore the scenic Lake Union.
    - Visit the Center for Wooden Boats and learn about the region's maritime history. You can even try your hand at sailing a historic vessel.
    
    Mid-Morning:
    - Head out of the city to the Skykomish River, about a 1-hour drive from Seattle, for a white water rafting adventure. Spend 2-3 hours navigating the Class III-IV rapids with an experienced guide.
    
    Afternoon:
    - After your rafting trip, head to Alki Beach, one of Seattle's best urban beaches. Spend a few hours swimming, sunbathing, and enjoying the views of the Puget Sound and the Olympic Mountains.
    - Have lunch at one of the beachfront restaurants or food trucks, enjoying fresh seafood and local cuisine.
    
    Late Afternoon: 
    - Visit Seacrest Park in West Seattle, which has a public swimming pool, beach access, and a fishing pier. Spend time swimming, relaxing, and taking in the views.
    - Consider taking the West Seattle Water Taxi back to downtown Seattle for a scenic ride across the harbor.
    
    Evening:
    - Finish your day with dinner at a waterfront restaurant in Seattle's vibrant Pike Place Market area, watching the sunset over the Puget Sound.
    
    Let me know if you would like me to modify this itinerary further!


## Conclusion

You have successfully executed a simple LangGraph implementation, this lab demonstrates how LangGraph can be used to create a simple yet effective Travel Planner. By structuring our application as a graph of interconnected nodes, we achieve a clear separation of concerns and a easily modifiable workflow. This approach can be extended to more complex applications, showcasing the power and flexibility of graph-based designs in AI-driven conversational interfaces.

Please proceed to the next lab


```python

```
