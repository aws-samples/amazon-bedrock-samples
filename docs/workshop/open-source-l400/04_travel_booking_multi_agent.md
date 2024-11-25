<h2>Multi agents using LangGraph</h2>
<h3>Challenges with single agents</h3>
<p>Single agent systems are not efficient for diverse tasks or for applications which may require multiple tools. Imagine input context size if have to use 100s of tools. Each tool has its own description and input/output schema. In such cases, it is difficult to use a single model that can handle all the tools.</p>
<p>Some of the common challenges are: 
- Infelxibility: our agentic application is limited to one LLM
- Contextual overload - too much information in the context
- Lack of parallel processing 
- Single point of failure </p>
<h3>What gets covered in this lab:</h3>
<p>we wil cover these aspects below:
- <code>Multi Agent</code> collaboration 
- Leverage memory for 'turn-by-turn' conversations
- Leverage Tools like <code>API's</code> and <code>RAG</code> for searching for answers.
- use Human In the loop for some critical workflows </p>
<h2>Multi agents</h2>
<p>In multi agent systems, each agent can have its own prompt, LLM and tools. </p>
<p>Benefits of multi agent systems:
- Agent can be more efficient as it has its on focused tasks
- Logical grouping of tools can give better results
- Easy to manage prompts for individual agents
- Each agent can be tested and evaluated separately</p>
<p>In this example we are going to use supervisor agentic pattern. In this pattern multiple agents are connected via supervisor agent and the conversation flows via the <code>supervisor</code> agents but each agent has its own scratchpad. </p>
<p>The supervisor agent acts as a central coordinator in a multi-agent system, orchestrating the interactions between various specialized agents. It delegates tasks to the appropriate agents based on their capabilities and the requirements of the task at hand. 
This approach allows for more efficient processing as each agent can focus on its specific tasks, reducing the complexity and context overload that a single agent might face. The supervisor agent ensures that the system is flexible, scalable, and can handle diverse tasks by leveraging the strengths of individual agents. It also facilitates parallel processing and minimizes the risk of a single point of failure by distributing tasks across multiple agents.</p>
<!-- ![image-2.png](assets/multi-agent-overview.png) -->

<!-- <img src="assets/multi-agent-overview.png" alt="image" style="width:800px;height:auto;"/> -->

<h3>Scenario</h3>
<!-- ![image.png](04_travel_booking_multi_agent_files/image.png) -->

<p>The below image shows the tools and the flow of data and Control as we progress with our <code>Travel Assistant bot</code></p>
<p><img src="./images/multi-agent-travel-bot.png" width="50%" alt=" The flow of data and control in our system"></p>
<h2>Flight agent</h2>
<p>The flight agent is designed to handle various tasks related to flight booking management. It utilizes a set of  tools to perform operations such as searching for available flights, retrieving detailed booking information, modifying existing flight bookings, and canceling reservations. By leveraging these tools, the flight agent can efficiently manage flight-related queries and actions. </p>
<p>The flight agent is equipped with a variety of tools.</p>
<p>These tools include:
- <strong>Flight Search Tool</strong>: Allows users to search for available flights between specified cities on a given date. It provides detailed information about airlines, departure and arrival times, flight duration, and pricing.</p>
<ul>
<li>
<p><strong>Booking Retrieval Tool</strong>: Enables the retrieval of detailed booking information using a booking ID. This tool is essential for users who need to review or confirm their flight details.</p>
</li>
<li>
<p><strong>Booking Modification Tool</strong>: Offers the capability to modify existing flight bookings. Users can change flight dates, times, or even cancel reservations if needed.</p>
</li>
<li>
<p><strong>Cancellation Tool</strong>: Facilitates the cancellation of flight bookings, ensuring that users can manage their travel plans with ease.</p>
</li>
</ul>
<h3>Flight Search tool</h3>
<p>The <code>search_flights</code> function is a tool designed to search for flights between two specified cities. </p>
<p><strong>Purpose</strong>: This tool simulates a flight search engine, providing mock flight data for given departure and arrival cities on a specified date.</p>
<p><strong>Note</strong>: This function is designed for demonstration and testing purposes, using randomly generated data rather than real flight information.</p>
<p>The tool provides a simulated flight search experience, allowing for the testing and development of flight booking systems or travel planning applications without accessing real flight data APIs.</p>
<h2>Setup</h2>
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
# "ipywidgets&gt;=7,&lt;8" \</p>
<h1>"matplotlib==3.9.0"</h1>
<p>```</p>
<p><code>python
import sqlite3
from contextlib import closing</code></p>
<p>```python
from langchain_core.tools import tool
import random
from datetime import datetime, timedelta
from langgraph.prebuilt import ToolNode
import sqlite3
import pandas as pd
from langchain_core.runnables.config import RunnableConfig</p>
<p>def read_travel_data(file_path: str = "data/synthetic_travel_data.csv") -&gt; pd.DataFrame:
    """Read travel data from CSV file"""
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        return pd.DataFrame(
            columns=["Id", "Name", "Current_Location", "Age", "Past_Travel_Destinations", "Number_of_Trips", "Flight_Number", "Departure_City", "Arrival_City", "Flight_Date"]
        )</p>
<p>@tool
def search_flights(config: RunnableConfig, arrival_city: str, date: str = None) -&gt; str:
    """
    Use this tool to search for flights between two cities. It knows the user's current location</p>
<pre><code>Args:
    arrival_city (str): The city of arrival
    date (str, optional): The date of the flight in YYYY-MM-DD format. If not provided, defaults to 7 days from now.

Returns:
    str: A formatted string containing flight information including airline, departure time, arrival time, duration, and price for multiple flights.
"""

df = read_travel_data()
user_id = config.get("configurable", {}).get("user_id")

if user_id not in df["Id"].values:
    return "User not found in the travel database."

user_data = df[df["Id"] == user_id].iloc[0]
current_location = user_data["Current_Location"]

departure_city = current_location.capitalize()
arrival_city = arrival_city.capitalize()

if date is None:
    date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

# Generate mock flight data
num_flights = random.randint(2, 5)
airlines = ["AirEurope", "SkyWings", "TransContinental", "EuroJet", "GlobalAir"]
flights = []

for _ in range(num_flights):
    airline = random.choice(airlines)
    duration = timedelta(minutes=2)
    price = random.randint(100, 400)
    departure_time = datetime.strptime(date, "%Y-%m-%d") + timedelta(
        hours=random.randint(0, 23), minutes=random.randint(0, 59)
    )
    arrival_time = departure_time + duration

    flights.append(
        {
            "airline": airline,
            "departure": departure_time.strftime("%H:%M"),
            "arrival": arrival_time.strftime("%H:%M"),
            "duration": str(duration),
            "price": price,
        }
    )

# Format the results
import json

flight_data = {
    "departure_city": departure_city,
    "arrival_city": arrival_city,
    "date": date,
    "flights": []
}
for i, flight in enumerate(flights, 1):
    flight_info = {
        "flight_number": i,
        "airline": flight['airline'],
        "departure": flight['departure'],
        "arrival": flight['arrival'],
        "duration": str(flight['duration']),
        "price": flight['price']
    }
    flight_data["flights"].append(flight_info)

return json.dumps(flight_data) + " FINISHED"
</code></pre>
<p>```</p>
<h3>Flight Booking Retrieval Tool</h3>
<p>The <code>retrieve_flight_booking</code> function is a tool designed to fetch flight booking information from a database. </p>
<p><strong>Purpose</strong>: This tool retrieves flight booking details based on a provided booking ID</p>
<p><strong>Note</strong>: This function is designed to work with a specific database schema, assuming a 'flight_bookings' table exists with 'booking_id' as a field.</p>
<p>```python
@tool
def retrieve_flight_booking(booking_id: int) -&gt; str:
    """
    Retrieve a flight booking by ID</p>
<pre><code>Args:
    booking_id (int): The unique identifier of the booking to retrieve

Returns:
    str: A string containing the booking information if found, or a message indicating no booking was found
"""
booking = None
with closing(sqlite3.connect("data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        # Execute the query to retrieve the booking
        cursor.execute("SELECT * FROM flight_bookings WHERE booking_id = ?", (booking_id,))
        booking = cursor.fetchone()
    # Close the connection
    conn.close()

if booking:
    return f"Booking found: {booking} FINISHED"
else:
    return f"No booking found with ID: {booking_id} FINISHED"
</code></pre>
<p>```</p>
<h3>Change Flight Booking Tool</h3>
<p>The <code>change_flight_booking</code> function is a tool designed to change flight booking information in the database. </p>
<p><strong>Purpose</strong>: This function allows for changing the departure date of an existing flight booking.</p>
<p><strong>Note</strong>: This function assumes the existence of a 'flight_bookings' table with 'booking_id' and 'departure_date' columns.</p>
<p>```python
@tool
def change_flight_booking(booking_id: int, new_date: str) -&gt; str:
    """
    Change the date of a flight booking</p>
<pre><code>Args:
    booking_id (int): The unique identifier of the booking to be changed
    new_date (str): The new date for the booking

Returns:
    str: A message indicating the result of the booking change operation
"""
# conn = sqlite3.connect("data/travel_bookings.db")
# cursor = conn.cursor()
result = ""
with closing(sqlite3.connect("data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        # Execute the query to update the booking date
        cursor.execute(
            "UPDATE flight_bookings SET departure_date = ? WHERE booking_id = ?",
            (new_date, booking_id),
        )
        conn.commit()

        # Check if the booking was updated
        if cursor.rowcount &gt; 0:
            result = f"Booking updated with ID: {booking_id}, new date: {new_date} FINISHED"
        else:
            result = f"No booking found with ID: {booking_id} FINISHED"

    # Close the connection
    conn.close()

return result
</code></pre>
<p>```</p>
<h3>Flight Cancellation tool</h3>
<p>The <code>cancel_flight_booking</code> function is a tool designed to cancel flight bookings in the database.</p>
<p><strong>Purpose</strong>: This function is designed to cancel an existing flight booking in the system.</p>
<p>```python
@tool
def cancel_flight_booking(booking_id: int) -&gt; str:
    """
    Cancel a flight booking. If the task complete, reply with "FINISHED"</p>
<pre><code>Args:
    booking_id (str): The unique identifier of the booking to be cancelled

Returns:
    str: A message indicating the result of the booking cancellation operation

"""
# conn = sqlite3.connect("data/travel_bookings.db")
# cursor  = conn.cursor()
result = ""
with closing(sqlite3.connect("data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        cursor.execute("DELETE FROM flight_bookings WHERE booking_id = ?", (booking_id,))
        conn.commit()
        # Check if the booking was deleted
        if cursor.rowcount &gt; 0:
            result = f"Booking canceled with ID: {booking_id} FINISHED"
        else:
            result = f"No booking found with ID: {booking_id} FINISHED"

    # Close the connection
    conn.close()

return result
</code></pre>
<p>```</p>
<h3>Language Model</h3>
<p>The LLM powering all of our agent implementations in this lab will be Claude 3 Sonnet via Amazon Bedrock. For easy access to the model we are going to use ChatBedrockConverse class of LangChain, which is a wrapper around Bedrock's Converse API.</p>
<p>```python
from langchain_aws import ChatBedrockConverse
from langchain_aws import ChatBedrock
import boto3</p>
<h1>---- ⚠️ Update region for your AWS setup ⚠️ ----</h1>
<p>bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")</p>
<p>llm = ChatBedrockConverse(
    model="anthropic.claude-3-haiku-20240307-v1:0",
    temperature=0,
    max_tokens=None,
    client=bedrock_client,
    # other params...
)
```</p>
<h3>Flight Agent setup</h3>
<p>We are going to use <code>create_react_agent</code> to create a flight agent. </p>
<p>We can customize the prompt using <code>state_modifier</code></p>
<p>In our case, the flight agent uses this framework to:
- Interpret user queries about flights
- Decide which tool (search, retrieve, change, or cancel) to use
- Execute the chosen tool and interpret the results
- Formulate responses based on the tool outputs</p>
<p>```python
import functools
import operator
from typing import Sequence, TypedDict</p>
<p>from langchain_core.messages import BaseMessage</p>
<p>from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import create_react_agent</p>
<p>from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver</p>
<p>class State(TypedDict):
    messages: Annotated[list, add_messages]
    next: str</p>
<p>memory = MemorySaver()</p>
<p>flight_agent = create_react_agent(
    llm,
    tools=[
        search_flights,
        retrieve_flight_booking,
        change_flight_booking,
        cancel_flight_booking,
    ],
    state_modifier="""
    First gather all the information required to call a tool. 
    If you are not able to find the booking the do not try again and just reply with "FINISHED". 
    If tool has returned the results then reply with "FINISHED"
    If all tasks are complete, reply with "FINISHED"
    """,
    checkpointer=memory,
)
```</p>
<p>```python
from IPython.display import Image, display</p>
<p>display(Image(flight_agent.get_graph().draw_mermaid_png()))
```</p>
<h3>Testing the Flight Agent</h3>
<p>Let's put the flight agent to the test with a sample query.</p>
<p>```python
config = {"configurable": {"thread_id": "127", "user_id":578}}
ret_messages = flight_agent.invoke({"messages": [("user", "Find flight to Amsterdam")]}, config)
ret_messages['messages'][-1].pretty_print()</p>
<h1>- un coment i you want to see the full orchesteration including the tool calling</h1>
<h1>ret_messages</h1>
<p>```</p>
<h2>Hotel Agent</h2>
<p>Just like flight agent we need to create few tools, which can manage hotel bookings. We will use the same approach as we did with flight agents. </p>
<p>The Hotel Agent will be responsible for handling various hotel-related tasks, including:
 1. Suggesting hotels based on city and check-in date
 2. Retrieving hotel booking details
 3. Modifying existing hotel bookings
 4. Cancelling hotel reservations</p>
<p>These functionalities will be implemented as separate tools, similar to the Flight Agent. The Hotel Agent will use these tools to interact with a simulated hotel booking system.</p>
<h3>Suggest hotel tool</h3>
<p>The <code>suggest_hotels</code> function is a tool designed to suggest hotels based on city and check-in date. It takes in a city name (e.g., "New York") and a check-in date (e.g., 2019-08-30) as input, and returns a list of suggested hotel names.</p>
<p><strong>Purpose</strong>: This tool simulates a hotel booking system that suggests hotels based on city and check-in date.</p>
<p><strong>Note</strong>: This function is designed for demonstration and testing purposes, using randomly generated data rather than real information from hotel booking system.</p>
<p>```python
@tool
def suggest_hotels(city: str, checkin_date: str) -&gt; dict:
    """
    Use this tool to search for hotels in these cities</p>
<pre><code>Args:
    city (str): The name of the city to search for hotels
    checkin_date (str): The check-in date in YYYY-MM-DD format

Returns:
    dict: A dictionary containing:
        - hotels (list): List of hotel names in the specified city
        - checkin_date (str): The provided check-in date
        - checkout_date (str): A randomly generated checkout date
        - price (int): A randomly generated price for the stay
"""
hotels = {
    "New York": ["Hotel A", "Hotel B", "Hotel C"],
    "Paris": ["Hotel D", "Hotel E", "Hotel F"],
    "Tokyo": ["Hotel G", "Hotel H", "Hotel I"],
}

# Generate random checkout date and price
checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
checkout = checkin + timedelta(days=random.randint(1, 10))
price = random.randint(100, 500)

hotel_list = hotels.get(city, ["No hotels found"])
return {
    "hotels": hotel_list,
    "checkin_date": checkin_date,
    "checkout_date": checkout.strftime("%Y-%m-%d"),
    "price": price,
}
</code></pre>
<p>```</p>
<h3>Hotel Booking Retrieval Tool</h3>
<p>The <code>retrieve_hotel_booking</code> function is a tool designed to fetch hotel booking information from a database. </p>
<p><strong>Purpose</strong>: This tool retrieves hotel booking details based on a provided booking ID</p>
<p><strong>Note</strong>: This function is designed to work with a specific database schema, assuming a 'hotel_bookings' table exists with 'booking_id' as a field.</p>
<p>```python
@tool
def retrieve_hotel_booking(booking_id: int) -&gt; str:
    """
    Retrieve a hotel booking by ID</p>
<pre><code>Args:
    booking_id (int): The unique identifier of the hotel booking to retrieve

Returns:
    str: A string containing the hotel booking information if found, or a message indicating no booking was found
"""
# conn = sqlite3.connect("data/travel_bookings.db")
# cursor = conn.cursor()
booking = ""
with closing(sqlite3.connect("./data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        cursor.execute(f"SELECT * FROM hotel_bookings WHERE booking_id='{booking_id}'")
        booking = cursor.fetchone()

    # Close the connection
    conn.close()

if booking:
    return f"Booking found: {booking}"
else:
    return f"No booking found with ID: {booking_id}"
</code></pre>
<p>```</p>
<h3>Change Hotel Booking Tool</h3>
<p>The <code>change_hotel_booking</code> function is a tool designed to change hotel booking information in the database. </p>
<p><strong>Purpose</strong>: This function allows for changing the new checkin and checkout date for the existing booking in the database.</p>
<p><strong>Note</strong>: This function assumes the existence of a 'hotel_bookings' table with 'booking_id' and 'check_in_date' columns.</p>
<p>```python
from datetime import datetime</p>
<p>@tool
def change_hotel_booking(booking_id: int, new_checkin_date: str = None, new_checkout_date: str = None) -&gt; str:
    """
    Change the dates of a hotel booking in the database. If the task completes, reply with "FINISHED"</p>
<pre><code>Args:
booking_id (int): The unique identifier of the booking to be changed
new_checkin_date (str, optional): The new check-in date in YYYY-MM-DD format
new_checkout_date (str, optional): The new check-out date in YYYY-MM-DD format

Returns:
str: A message indicating the result of the booking change operation
"""

# conn = sqlite3.connect("data/travel_bookings.db")  # Replace with your actual database file
# cursor = conn.cursor()

with closing(sqlite3.connect("./data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        try:
            # First, fetch the current booking details
            cursor.execute(
                """
                SELECT * FROM hotel_bookings WHERE booking_id = ?
            """,
                (booking_id,),
            )

            booking = cursor.fetchone()

            if booking is None:
                return f"No hotel booking found with ID: {booking_id}"

            # Unpack the booking details
            ( _, user_id,user_name,city,hotel_name,check_in_date,check_out_date,nights,price_per_night,total_price,num_guests,room_type,) = booking

            # Update check-in and check-out dates if provided
            if new_checkin_date:
                check_in_date = new_checkin_date
            if new_checkout_date:
                check_out_date = new_checkout_date

            # Recalculate nights and total price
            checkin = datetime.strptime(check_in_date, "%Y-%m-%d")
            checkout = datetime.strptime(check_out_date, "%Y-%m-%d")
            nights = (checkout - checkin).days
            total_price = nights * price_per_night

            # Update the booking in the database
            cursor.execute(
                """
                UPDATE hotel_bookings
                SET check_in_date = ?, check_out_date = ?, nights = ?, total_price = ?
                WHERE booking_id = ?
            """,
                (check_in_date, check_out_date, nights, total_price, booking_id),
            )

            conn.commit()

            return f"Hotel booking updated: Booking ID {booking_id}, New check-in: {check_in_date}, New check-out: {check_out_date}, Nights: {nights}, Total Price: {total_price} FINISHED"

        except sqlite3.Error as e:
            conn.rollback()
            return f"An error occurred: {str(e)} Booking ID {booking_id}, New check-in: {check_in_date} FINISHED"

        finally:
            conn.close()
</code></pre>
<p>```</p>
<h3>Hotel Cancellation tool</h3>
<p>The <code>cancel_hotel_booking</code> function is a tool designed to cancel hotel bookings in the database.</p>
<p><strong>Purpose</strong>: This function is designed to cancel an existing hotel booking in the system.</p>
<p>```python
@tool
def cancel_hotel_booking(booking_id: int) -&gt; str:
    """
    Cancel a hotel booking. If the task completes, reply with "FINISHED"</p>
<pre><code>Args:
    booking_id (str): The unique identifier of the booking to be cancelled

Returns:
    str: A message indicating the result of the booking cancellation operation
"""
# conn = sqlite3.connect("data/travel_bookings.db")
# cursor  = conn.cursor()
result=""
with closing(sqlite3.connect("data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        cursor.execute("DELETE FROM hotel_bookings WHERE booking_id = ?", (booking_id,))
        conn.commit()

        # Check if the booking was deleted
        if cursor.rowcount &gt; 0:
            result = f"Booking canceled with ID: {booking_id} FINISHED"
        else:
            result = f"No booking found with ID: {booking_id} FINISHED"

    # Close the connection
    conn.close()

return result
</code></pre>
<p>```</p>
<h2>Hotel agent</h2>
<p>So far we have seen how to create agent using <code>create_react_agent</code> class of LangGraph, which has simplified things for us. But we need human confirmation before changing hotel booking or before cancelling hotel booking. We need our agent to ask ask for confirmation before executing these tools. We will create a custom agent that can handle these things. We will create a separate node that can handel booking cancellation or modification. Agent execution will be interrupted at this node to get the confirmation. </p>
<p>So we will create 2 separate nodes <code>search</code> and then for <code>cancel</code> where we need <code>Human-in-the-loop</code> . The below diagram illustrates this</p>
<p><img src="./images/Hotel_booking_confirmation_light.png" width="20%"  height="20%" /></p>
<h3>Hotel Booking Assistant Setup</h3>
<p>The <code>HumanApprovalToolNode</code> class is a custom implementation for managing hotel bookings. It extends the functionality of a standard LangChain agent by adding the ability to ask for additional information from the user when needed. </p>
<p>The <code>hotel_agent</code> function is set up to invoke the agent which will be a <code>Return of Control</code> style which will ask the application to execute the tool. The tools bound to this agent themselves can either ToolNode or our custom HumanApprovalToolNode allowing us to easily execute this step</p>
<p>This code sets up a hotel booking assistant using LangChain components. It includes:</p>
<ul>
<li>We have 2 distinct set of tools set up a nodes on the graph 1/ which need Human confirmation like cancel booking and 2/ which do not need human intervention</li>
<li><code>hotel_agent</code> function that manages interactions with the language model. This is set up with complete knowledge of all the tools</li>
<li>prompt template for the primary assistant, focused on hotel bookings.</li>
<li>set of hotel-related tools for tasks like suggesting hotels and managing bookings.</li>
<li>runnable object that combines the prompt, language model, and tools.</li>
</ul>
<p>The assistant can handle hotel inquiries, make suggestions, and perform booking operations.
It also has the ability to ask for additional information when needed.</p>
<p>```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig</p>
<p>primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant who manage hotel bookings"</p>
<pre><code>    ),
    ("placeholder", "{messages}"),
]
</code></pre>
<p>)
hotel_tools = [
    suggest_hotels,
    retrieve_hotel_booking,
    change_hotel_booking,
    cancel_hotel_booking,
]</p>
<p>runnable_with_tools = primary_assistant_prompt | llm.bind_tools(
    hotel_tools
)</p>
<p>def hotel_agent(state: State):
    return {"messages": [runnable_with_tools.invoke(state)]}
```</p>
<p>Now we will create 2 separate nodes for <code>search_and_retrieve_node</code> and <code>change_and_cancel_node</code>, so that we can interrupt for human approval when <code>change_and_cancel_node</code> is executed.</p>
<p>```python
import json</p>
<p>from langchain_core.messages import ToolMessage</p>
<p>class HumanApprovalToolNode:
    """A node that runs the tools requested in the last AIMessage."""</p>
<pre><code>def __init__(self, tools: list) -&gt; None:
    self.tools_by_name = {tool.name: tool for tool in tools}

def __call__(self, inputs: dict):
    if messages := inputs.get("messages", []):
        message = messages[-1]
    else:
        raise ValueError("No message found in input")
    outputs = []
    for tool_call in message.tool_calls:
        user_input = input(
            "Do you approve of the above actions? Type 'y' to continue;"
            " otherwise, explain your requested changed.\n\n"
        )
        if user_input.lower() == "y":
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        else:
            outputs.append(
                ToolMessage(
                    content=f"API call denied by user. Reasoning: '{user_input}'. ",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
    return {"messages": outputs}
</code></pre>
<p>```</p>
<p>```python
from langgraph.prebuilt import ToolNode, tools_condition</p>
<p>search_and_retrieve_node = ToolNode([suggest_hotels, retrieve_hotel_booking])
change_and_cancel_node = HumanApprovalToolNode(
    [change_hotel_booking, cancel_hotel_booking]
)
```</p>
<p>We need to check which node is executed next. This function can check the state and decide which node to execute next of end the execution. </p>
<p><code>python
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "end"
    elif last_message.tool_calls[0]["name"] in [
        "change_hotel_booking",
        "cancel_hotel_booking",
    ]:
        return "human_approval"
    # Otherwise if there is, we continue
    else:
        return "continue"</code></p>
<h3>Assembling the Hotel Agent Graph</h3>
<p>Let's add all the nodes in the graph and compile it to create our custom hotel agent.</p>
<p>This graph will define the flow of our hotel booking system, including:</p>
<ol>
<li>The main hotel agent node for processing requests</li>
<li>A tool node for executing search and retrieve hotel booking</li>
<li>Another tool node for cancelling and changing hotel booking</li>
</ol>
<p>The graph will use conditional edges to determine the next step based on the current state, allowing for a dynamic and responsive workflow. We'll also set up memory management to maintain state across interactions.</p>
<p>```python
from langgraph.graph import END, StateGraph, MessagesState
from IPython.display import Image, display</p>
<h1>Create a new graph workflow</h1>
<p>hotel_workflow = StateGraph(MessagesState)</p>
<p>hotel_workflow.add_node("hotel_agent", hotel_agent)
hotel_workflow.add_node("search_and_retrieve_node", search_and_retrieve_node)
hotel_workflow.add_node("change_and_cancel_node", change_and_cancel_node)</p>
<p>hotel_workflow.add_edge(START, "hotel_agent")</p>
<h1>We now add a conditional edge</h1>
<p>hotel_workflow.add_conditional_edges(
    "hotel_agent",
    # Next, we pass in the function that will determine which node is called next.
    should_continue,
    {
        # If agent decides to use <code>suggest_hotels</code> or  <code>retrieve_hotel_booking</code>
        "continue": "search_and_retrieve_node",
        # If agent decides to use <code>change_hotel_booking</code> or  <code>cancel_hotel_booking</code>
        "human_approval": "change_and_cancel_node",
        "end": END,
    },
)</p>
<p>hotel_workflow.add_edge("search_and_retrieve_node", "hotel_agent")
hotel_workflow.add_edge("change_and_cancel_node", "hotel_agent")</p>
<h1>Set up memory</h1>
<p>from langgraph.checkpoint.memory import MemorySaver</p>
<p>memory = MemorySaver()</p>
<p>hotel_graph_compiled = hotel_workflow.compile(
    checkpointer=memory
)</p>
<p>display(Image(hotel_graph_compiled.get_graph().draw_mermaid_png()))
```</p>
<h3>Testing the Custom Hotel Agent</h3>
<p>Now we can test this agent </p>
<p>```python
import uuid
from langchain_core.messages import ToolMessage
thread_id = str(uuid.uuid4())</p>
<p>_printed = set()
config = {"configurable": {"thread_id": thread_id}}</p>
<p>events = hotel_graph_compiled.stream(
    {"messages": ("user", "Get details of my booking id 203")},
    config,
    stream_mode="values",
)
for event in events:
    event["messages"][-1].pretty_print()
```</p>
<p>```python
thread_id = str(uuid.uuid4())</p>
<p>config = {"configurable": {"thread_id": thread_id}}</p>
<p>events = hotel_graph_compiled.stream(
    {"messages": ("user", "cancel my hotel booking id 203")},
    config,
    stream_mode="values",
)
for event in events:
    event["messages"][-1].pretty_print()
```</p>
<h2>Supervisor agent</h2>
<p>Now its time to create supervisor agent that will be in charge of deciding which child agent to call based on the user input and based on the conversation history. </p>
<p>The Supervisor Agent is responsible for:
1. Analyzing the conversation history and user input
2. Deciding which child agent (flight_agent or hotel_agent) to call next
3. Determining when to finish the conversation</p>
<p>We will create this agent with LangChain runnable chain created using supervisor prompt. We need to get the <code>next_step</code> from the chain and we use <code>with_structured_output</code> to return next step.</p>
<p>The Supervisor Agent  routes  tasks and maintains the overall flow of the conversation between the user and child agents.</p>
<p>```python
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph.message import add_messages
from typing import Annotated, Sequence, List
from langchain_core.messages import HumanMessage</p>
<p>from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core import <strong>version</strong> as core_version
from packaging import version</p>
<p>core_version = version.parse(core_version)
if (core_version.major, core_version.minor) &lt; (0, 3):
    from pydantic.v1 import BaseModel
else:
    from pydantic import BaseModel
from typing import Literal</p>
<p>members = ["flight_agent", "hotel_agent"]
options = ["FINISH"] + members</p>
<p>class routeResponse(BaseModel):
    """
    Return next agent name.
    """
    next: Literal[*options]</p>
<p>class AskHuman(BaseModel):
    """Ask missing information from the user"""</p>
<pre><code>question: str
</code></pre>
<p>prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
        Given the conversation below who should act next?
        1. To search or cancel flight return 'flight_agent'
        2. To search for hotel or cancel hotel booking return 'hotel_agent'
        3. If you have the answer return 'FINISH'
        4. When member has finished the task, and you notice FINISHED in the message then don't repeat same member again
        5. Do not return next which is not related to user query. Example if user is asking about flight then do not call 'hotel_agent'
        Or should we FINISH? ONLY return one of these {options}. Do not explain the process.</p>
<pre><code>    """,
    ),
    ("placeholder", "{messages}"),
]
</code></pre>
<p>).partial(options=str(options), members=", ".join(members))</p>
<p>supervisor_chain = prompt | llm.with_structured_output(routeResponse)</p>
<p>def supervisor_agent(state):
    result = supervisor_chain.invoke(state)
    output = {
        "next": result.next,
        "messages": [
            HumanMessage(
                content=f"Supervisor decided: {result.next}", name="supervisor"
            )
        ],
    }
    print(f"Supervisor output: {output}")
    return output
```</p>
<p>We can test our supervisor agent to check if it is returning correct next step based on the user input.</p>
<p><code>python
supervisor_agent({"messages": [("user", "I want to book a flight")]})</code></p>
<h2>Assembling the Multi-Agent System</h2>
<p>Now it's time to put all agents together in a workflow. We will start with the <code>supervisor</code>. </p>
<p><code>python
class State(TypedDict):
    messages: Annotated[list, add_messages]
    next: str</code></p>
<p>```python
full_workflow = StateGraph(State)
full_workflow.add_node("supervisor", supervisor_agent)</p>
<p>full_workflow.add_edge(START, "supervisor")</p>
<p>```</p>
<h3>Creating the flight agent node</h3>
<p>We need a helper function to take output from the flight search agent and add it to the messages list in the state. </p>
<p>```python
from langchain_core.messages import AIMessage</p>
<p>def agent_node(state, agent, name):
    result = agent.invoke(state)
    return {
        "messages": [HumanMessage(content=result["messages"][-1].content, name=name)]
    }
```</p>
<p><code>python
flight_node = functools.partial(agent_node, agent=flight_agent, name="flight_agent")</code></p>
<p>Let's add this node to the workflow</p>
<p><code>python
full_workflow.add_node("flight_agent", flight_node)</code></p>
<h3>Adding the Hotel Agent as a Subgraph</h3>
<p>We can add <code>hotel_agent</code> as subgraph to this workflow. This is is a good example of how to use subgraphs in workflows. This also give us more control over the workflow.</p>
<p><code>python
full_workflow.add_node("hotel_agent", hotel_graph_compiled)</code></p>
<p>Once we get the output from hotel agent we need to make sure that it has correct structure that supervisor agent can process. For this we need to add a node to the workflow that will process the output from hotel agent.</p>
<p><code>python
def process_output(state):
    messages = state["messages"]
    for message in reversed(messages):
        if isinstance(message, AIMessage) and isinstance(message.content, str):
           print(message.content)
           return {
                "messages": [
                    HumanMessage(content=message.content, name="hotel_agent")
                ]
            }
    return None</code></p>
<p>```python</p>
<p>full_workflow.add_node("process_output", process_output)
```</p>
<h3>Connecting the Agents</h3>
<p>Now we can add edges to the workflow that will connect all the agents. We need to add an edge from the flight agent to the supervisor, and from the hotel agent to the process output node and then to the supervisor.</p>
<ol>
<li>We'll connect the <code>flight_agent</code> directly to the <code>supervisor</code>.</li>
<li>For the <code>hotel_agent</code>, we'll first connect it to the <code>process_output</code> node, which will format its output.</li>
<li>The <code>process_output</code> node will then be connected to the <code>supervisor</code>.</li>
<li>We'll set up conditional edges from the supervisor to all other agents (including itself) and to a FINISH state.</li>
</ol>
<p>```python
full_workflow.add_edge("flight_agent", "supervisor")
full_workflow.add_edge("hotel_agent", "process_output")
full_workflow.add_edge("process_output", "supervisor")</p>
<p>conditional_map = {k: k for k in members}
conditional_map["FINISH"] = END
full_workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
```</p>
<p>```python
from IPython.display import Image, display</p>
<p>supervisor_agent_graph = full_workflow.compile(
    checkpointer=memory,
)</p>
<h1>display subgraph using xray=1</h1>
<p>display(Image(supervisor_agent_graph.get_graph(xray=1).draw_mermaid_png()))
```</p>
<p>We need to create a utility function to extract tool id from the subgraph. </p>
<p>```python
def extract_tool_id(pregel_task):
    # Navigate to the messages in the state
    messages = pregel_task.state.values.get("messages", [])</p>
<pre><code># Find the last AIMessage
for message in reversed(messages):
    if isinstance(message, AIMessage):
        # Check if the message has tool_calls
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            # Return the id of the first tool call
            return tool_calls[0]["id"]
</code></pre>
<p>```</p>
<h3>Testing full graph</h3>
<p>Now we are ready to test the graph. We will create a unique thread_id to manage memory. We have few sample questions to test the graph. </p>
<p>```python
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}</p>
<p>events = supervisor_agent_graph.stream(
    {"messages": ("user", "Get details of my flight booking id 200")},
    config,
    stream_mode="values",
    subgraphs=True,
)
for event in events:
    event[1]["messages"][-1].pretty_print()
```</p>
<p>```python
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}</p>
<p>events = supervisor_agent_graph.stream(
    {"messages": ("user", "cancel my hotel booking id 193")},
    config,
    stream_mode="values",
    subgraphs=True,
)
for event in events:
    event[1]["messages"][-1].pretty_print()
```</p>
<h4>in case you need to see the contents of the hotel database</h4>
<p>hotel database</p>
<p>```python
import sqlite3
from contextlib import closing</p>
<p>with closing(sqlite3.connect("data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        cursor.execute("""SELECT * FROM hotel_bookings""")
        #cursor.execute("""SELECT * FROM hotel_bookings where booking_id='203'""")
        for idx in range(5):
            print(cursor.fetchone())
    conn.close()
```</p>
<p>flights database</p>
<p>```python
import sqlite3
from contextlib import closing</p>
<p>with closing(sqlite3.connect("data/travel_bookings.db", timeout=10.0)) as conn:
    with closing(conn.cursor()) as cursor:
        cursor.execute("""SELECT * FROM flight_bookings""")
        #cursor.execute("""SELECT * FROM hotel_bookings where booking_id='203'""")
        for idx in range(5):
            print(cursor.fetchone())
    conn.close()
```</p>
<h2>Conclusion</h2>
<p>In this lab we have seen implementation of a multi-agent system for travel booking using LangGraph. The implementation showcases several key concepts:</p>
<ol>
<li>
<p><strong>Multi-Agent Architecture</strong>: The system effectively divides responsibilities between specialized agents (Flight and Hotel agents) coordinated by a Supervisor agent, demonstrating how complex tasks can be broken down into manageable components</p>
</li>
<li>
<p><strong>Subgraph Pattern</strong>: The Hotel agent implementation as a subgraph shows how complex agent behaviors can be encapsulated and managed independently, while still integrating seamlessly with the larger system</p>
</li>
<li>
<p><strong>Tool Integration</strong>: Each agent has access to specific tools relevant to its domain, showing how specialized capabilities can be effectively distributed across different agents</p>
</li>
<li>
<p><strong>Supervisor Pattern</strong>: The supervisor agent demonstrates effective orchestration of multiple specialized agents, making decisions about task routing and completion</p>
</li>
<li>
<p><strong>State Management</strong>: The implementation shows how to manage state across multiple agents and handle complex interactions between them</p>
</li>
</ol>
<p>Key benefits of this approach include:
- Improved modularity and maintainability
- Better separation of concerns
- Efficient handling of domain-specific tasks
- Flexible architecture that can be extended with additional agents</p>
<p>This pattern can be adapted for various complex applications where multiple specialized agents need to work together to accomplish a larger goal.</p>