import pandas as pd
import boto3
import pickle

from collections import Counter
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from langchain_aws import ChatBedrockConverse
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws.embeddings.bedrock import BedrockEmbeddings
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools.retriever import create_retriever_tool
from langchain_community.vectorstores import FAISS
from langchain.retrievers import ParentDocumentRetriever


from ragas.messages import HumanMessage as RGHumanMessage
from ragas.messages import AIMessage as RGAIMessage
from ragas.messages import ToolMessage as RGToolMessage
from ragas.messages import ToolCall as RGToolCall

from io import BytesIO

def convert_message_langchain_to_ragas(lc_message):
    message_dict = lc_message.model_dump()
    if message_dict['type'] == 'human':
        rg_message = RGHumanMessage(content=message_dict['content'])
    if message_dict['type'] == 'ai':
        if type(message_dict['content']) == list:
            text = list(filter((lambda x: x['type'] == 'text'), message_dict['content']))
            tool = list(filter((lambda x: x['type'] == 'tool_use'), message_dict['content']))
            if len(text) > 0 and len(tool) > 0:

                if len(list(tool[0]['input'].keys())) > 0:
                    dyn_args = {'query': tool[0]['input'][list(tool[0]['input'].keys())[0]]}
                else: 
                    dyn_args = {}
                
                rg_message = RGAIMessage(content=text[0]['text'], tool_calls=[RGToolCall(name=tool[0]['name'], args= dyn_args)])
            elif len(text) > 0:
                rg_message = RGAIMessage(content=text[0]['text'])
            elif len(tool) > 0:
                rg_message = RGAIMessage(content='', tool_calls=[RGToolCall(name=tool[0]['name'], args={#'id': tool[0]['id'], 
                                                                                                        'query': tool[0]['input'][list(tool[0]['input'].keys())[0]]})])
        else:
            rg_message = RGAIMessage(content= message_dict['content'], tool_calls=message_dict['tool_calls'], metadata=message_dict['usage_metadata'])
    if message_dict['type'] == 'tool':
        rg_message = RGToolMessage(content=message_dict['content'], metadata={"tool_name": message_dict['name'], "tool_call_id": message_dict['tool_call_id']})
    return rg_message


def create_agent(enable_memory = False):
    # ---- ⚠️ Update region for your AWS setup ⚠️ ----
    bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
    
    
    
    llm = ChatBedrockConverse(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        temperature=0,
        max_tokens=None,
        client=bedrock_client,
        # other params...
    )
    
    def read_travel_data(file_path: str = "data/synthetic_travel_data.csv") -> pd.DataFrame:
        """Read travel data from CSV file"""
        try:
            df = pd.read_csv(file_path)
            return df
        except FileNotFoundError:
            return pd.DataFrame(
                columns=["Id", "Name","Current_Location","Age","Past_Travel_Destinations", "Number_of_Trips", "Flight_Number", "Departure_City","Arrival_City","Flight_Date",]
            )
    
    
    @tool
    def compare_and_recommend_destination(config: RunnableConfig) -> str:
        """This tool is used to check which destinations user has already traveled.
        If user has already been to a city then do not recommend that city.
    
        Returns:
            str: Destination to be recommended.
    
        """
    
        df = read_travel_data()
        user_id = config.get("configurable", {}).get("user_id")
    
        if user_id not in df["Id"].values:
            return "User not found in the travel database."
    
        user_data = df[df["Id"] == user_id].iloc[0]
        current_location = user_data["Current_Location"]
        age = user_data["Age"]
        past_destinations = user_data["Past_Travel_Destinations"].split(", ")
    
        # Get all past destinations of users with similar age (±5 years) and same current location
        similar_users = df[(df["Current_Location"] == current_location) & (df["Age"].between(age - 5, age + 5))]
        all_destinations = [dest for user_dests in similar_users["Past_Travel_Destinations"].str.split(", ") for dest in user_dests ]
    
        # Count occurrences of each destination
        destination_counts = Counter(all_destinations)
    
        # Remove user's current location and past destinations from recommendations
        for dest in [current_location] + past_destinations:
            if dest in destination_counts:
                del destination_counts[dest]
    
        if not destination_counts:
            return f"No new recommendations found for users in {current_location} with similar age."
    
        # Get the most common destination
        recommended_destination = destination_counts.most_common(1)[0][0]
    
        return f"Based on your current location ({current_location}), age ({age}), and past travel data, we recommend visiting {recommended_destination}."
    
    
    embeddings_model = BedrockEmbeddings(
        client=bedrock_client, model_id="amazon.titan-embed-text-v1"
    )
    
    child_splitter = RecursiveCharacterTextSplitter(
        separators=["\n", "\n\n"], chunk_size=2000, chunk_overlap=250
    )
    
    in_memory_store_file = "data/section_doc_store.pkl"
    vector_store_file = "data/section_vector_store.pkl"
    
    store = pickle.load(open(in_memory_store_file, "rb"))
    vector_db_buff = BytesIO(pickle.load(open(vector_store_file, "rb")))
    vector_db = FAISS.deserialize_from_bytes(
        serialized=vector_db_buff.read(),
        embeddings=embeddings_model,
        allow_dangerous_deserialization=True,
    )

    retriever = ParentDocumentRetriever(
        vectorstore=vector_db,
        docstore=store,
        child_splitter=child_splitter,
    )    
    
    retriever_tool = create_retriever_tool(
        retriever,
        "travel_guide",
        """Holds information from travel guide books containing city details to find information matching the user's interests in various cities. Only search based on the keyword mentioned in user input.

        Args:
            query (str): place to query travel guide.
        Returns:
            str: Information about destination from travel guide.
        
        """,
    )
    
    tools = [compare_and_recommend_destination, retriever_tool]

    if enable_memory:

        memory = MemorySaver()
        agent = create_react_agent(llm, tools, checkpointer = memory)

    else:
        agent = create_react_agent(llm, tools)
    
    return agent