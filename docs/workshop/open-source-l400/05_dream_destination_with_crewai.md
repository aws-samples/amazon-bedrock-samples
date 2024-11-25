<h1>Dream Destination Finder with CrewAI and Amazon Bedrock</h1>
<p>In this notebook, we will explore how to use the CrewAI framework with Amazon Bedrock to build an intelligent agent that can find dream travel destinations based on user preferences. The agent will utilize a large language model (LLM) and web search capabilities to research and recommend destinations that match the user's description.</p>
<h2>What's CrewAI:</h2>
<p>CrewAI is one of the leading open-source Python frameworks designed to help developers create and manage multi-agent AI systems.</p>
<p><img src="assets/crewai_diagram.png"></p>
<p>Diagram Representation of CrewAI architecture</p>
<p><strong>!pip install boto3 botocore crewai crewai_tools duckduckgo-search langchain-community -q</strong></p>
<p>We start by importing the necessary modules from the crewai and crewai_tools packages.</p>
<h4>Configuring AWS Credentials:</h4>
<p>Before using Amazon Bedrock, ensure that your AWS credentials are configured correctly. You can set them up using the AWS CLI or by setting environment variables. For this notebook, we’ll assume that the credentials are already configured.</p>
<p>To use bedrock we will use <a href="https://docs.crewai.com/how-to/llm-connections#supported-providers"><strong>CrewAI</strong> <strong>LLM</strong> api</a> </p>
<p><code>python
from crewai import Agent, Task, Crew, LLM
from crewai_tools import tool
from langchain_community.tools import DuckDuckGoSearchRun</code></p>
<h4>Define web-search tool:</h4>
<p><code>python
@tool('DuckDuckGoSearch')
def search(search_query: str):
    """Search the web for information on a given topic"""
    return DuckDuckGoSearchRun().run(search_query)</code></p>
<h3>Configuring the LLM</h3>
<p>We will use Anthropic’s Claude-3 model via Amazon Bedrock as our LLM. CrewAI uses LiteLLM under the hood to interact with different LLM providers.</p>
<p>```python</p>
<h1>Configure the LLM</h1>
<p>llm = LLM(model="bedrock/anthropic.claude-3-sonnet-20240229-v1:0")
```</p>
<h3>Defining the Agent</h3>
<p>We will create an agent with the role of a “Travel Destination Researcher.” This agent will be responsible for finding destinations that match the user’s travel preferences.</p>
<p>```python</p>
<h1>Define the Agent</h1>
<p>travel_agent = Agent(
    role='Travel Destination Researcher',
    goal='Find dream destinations matching user preferences',
    backstory="You are an experienced travel agent specializing in personalized travel recommendations.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[search]  # Tool for online searching
)
```</p>
<h3>Defining the Task</h3>
<p>We need to specify the task that the agent will perform. The task includes a description, expected output, and is assigned to the agent we just created.</p>
<p>```python</p>
<h1>Define the Task</h1>
<p>task = Task(
    description="Based on the user's travel preferences: {preferences}, research and recommend suitable travel destinations.",
    expected_output="A list of recommended destinations with brief descriptions.",
    agent=travel_agent
)
```</p>
<h3>Creating the Crew</h3>
<p>A crew is a team of agents working together to achieve a common goal. In this case, we have only one agent, but the framework allows for scalability.</p>
<p>```python</p>
<h1>Create the Crew</h1>
<p>crew = Crew(
    agents=[travel_agent],
    tasks=[task],
    verbose=True,
)
```</p>
<h3>Executing the Workflow</h3>
<p>Now, we can execute the crew with the user’s travel preferences as input.</p>
<p>```python</p>
<h1>User input for travel preferences</h1>
<p>user_input = {
    "preferences": "I want a tropical beach vacation with great snorkeling and vibrant nightlife."
}</p>
<h1>Execute the Crew</h1>
<p>result = crew.kickoff(inputs=user_input)
```</p>
<h4>As the crew executes, CrewAI will:</h4>
<p>•   Decompose the task into actions using ReAct (Reasoning and Act), optionally using the tools assigned to the agent.</p>
<p>•   Make multiple calls to Amazon Bedrock to complete each step from the previous phase.</p>
<p><code>python
from IPython.display import Markdown</code></p>
<p><code>python
Markdown(result.raw)</code></p>
<h3>Adding Memory to the Agent</h3>
<p>CrewAI supports <a href="https://docs.crewai.com/concepts/memory#implementing-memory-in-your-crew">several memory types</a>, which help agents remember and learn from past interactions. In this case, we’ll enable short-term memory using Amazon Bedrock’s embedding model.</p>
<p>```python</p>
<h1>Enabling Memory in the Agent</h1>
<p>crew_with_memory = Crew(
    agents=[travel_agent],
    tasks=[task],
    verbose=True,
    memory=True,  # Enable memory
    embedder={
        "provider": "aws_bedrock",
        "config": {
            "model": "amazon.titan-embed-text-v2:0",  # Embedding model for memory
            "vector_dimension": 1024
        }
    },</p>
<p>)
```</p>
<p>```python</p>
<h1>Executing the Crew with Memory</h1>
<p>result_with_memory = crew_with_memory.kickoff(inputs=user_input)
```</p>
<p><code>python
Markdown(result_with_memory.raw)</code></p>
<h3>Integrating Retrieval-Augmented Generation (RAG) with Amazon Bedrock Knowledge Base</h3>
<p>In this section, we will enhance our dream destination finder agent by incorporating Retrieval-Augmented Generation (RAG) using Amazon Bedrock’s Knowledge Base. This will allow our agent to access up-to-date and domain-specific travel information, improving the accuracy and relevance of its recommendations.</p>
<h4>What is Retrieval-Augmented Generation (RAG)?</h4>
<p>RAG is a technique that combines the capabilities of large language models (LLMs) with a retrieval mechanism to fetch relevant information from external data sources. By integrating RAG, our agent can retrieve the most recent and specific information from a knowledge base, overcoming the limitations of LLMs that may have outdated or insufficient data.</p>
<p>Setting Up Amazon Bedrock Knowledge Base</p>
<p>Before we proceed, ensure you have access to Amazon Bedrock and the necessary permissions to create and manage knowledge bases.</p>
<ul>
<li>Step 1: Prepare Your Data</li>
<li>Step 2: Create a Knowledge Base in Amazon Bedrock</li>
<li>Step 3: Note the Knowledge Base ID</li>
</ul>
<p>After the knowledge base is created, note down its Knowledge Base ID (kb_id), which will be used in our code.</p>
<p><img src="assets/KB-pannel.png"></p>
<p>Updating the Agent to Use RAG with CrewAI</p>
<p>We will modify our agent to include a custom tool that queries the Amazon Bedrock Knowledge Base. This allows the agent to retrieve up-to-date information during its reasoning process.</p>
<p>```python
import boto3</p>
<h1>Initialize the Bedrock client</h1>
<p>bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name="{YOUR-REGION}")
```</p>
<h3>Knowledge Base Tool Set up:</h3>
<p>Using the <strong>kb id</strong>, <strong>model arn</strong> (either foundational or custom) we can leverage Amazons Knowledge Bases. In this example the question will also be broken down using <strong>orchestrationConfiguration</strong> settings.</p>
<p>```python
@tool("TravelExpertSearchEngine")
def query_knowledge_base(question: str) -&gt; str:
    """Queries the Amazon Bedrock Knowledge Base for travel-related information."""
    kb_id = "XXXX"  # Replace with your Knowledge Base ID
    model_id = "foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"   # Use an available model in Bedrock
    model_arn = f'arn:aws:bedrock:YOUR-REGION::{model_id}'</p>
<pre><code>response = bedrock_agent_runtime_client.retrieve_and_generate(
    input={'text': question},
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration" : {'knowledgeBaseId': kb_id,
                                'modelArn': model_arn,
                                'orchestrationConfiguration': {
                                    'queryTransformationConfiguration': {
                                        'type': 'QUERY_DECOMPOSITION'
                                    }
                                }
                                        }
    }
)
try:
    return str({"Results": response['output']['text'], "Citations": response['citations'][0]})
except KeyError:
    return "No data available"
</code></pre>
<p>```</p>
<h3>Update the Agent with the New Tool</h3>
<p>We will update our agent to include the TravelExpert tool.</p>
<p>```python</p>
<h1>Configure the LLM</h1>
<p>llm = LLM(model="bedrock/anthropic.claude-3-sonnet-20240229-v1:0")</p>
<h1>Update the Agent</h1>
<p>agent_with_rag = Agent(
    role='Travel Destination Researcher',
    goal='Find dream destinations in the USA, first think about cities matching user preferences and then use information from the search engine, nothing else.',
    backstory="""You are an experienced travel agent specializing in personalized travel recommendations. 
                 Your approach is as follows: 
                 Deduce which regions within the USA will have those activities listed by the user.
                 List major cities within that region
                 Only then use the tool provided to look up information, look up should be done by passing city highlights and activities.
              """,
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[query_knowledge_base],  # Include the RAG tool
    max_iter=5
)</p>
<p>```</p>
<h3>Update the task and set up the Crew</h3>
<p>```python</p>
<h1>Define the Task</h1>
<p>task_with_rag = Task(
    description="Based on the user's travel request, research and recommend suitable travel destinations using the latest information. Only use output provided by the Travel Destination Researcher, nothing else: USER: {preferences}",
    expected_output="A place where they can travel to along with recommendations on what to see and do while there.",
    agent=agent_with_rag
)</p>
<h1>Create the Crew</h1>
<p>crew_with_rag = Crew(
    agents=[agent_with_rag],
    tasks=[task_with_rag],
    verbose=True,
)
```</p>
<p>```python</p>
<h1>User input for travel preferences</h1>
<p>user_input = {
    "preferences": "Where can I go for cowboy vibes, watch a rodeo, and a museum or two?"
}</p>
<h1>Execute the Crew</h1>
<p>result_with_rag = crew_with_rag.kickoff(inputs=user_input)</p>
<p>```</p>
<h3>Display the results</h3>
<p>```python</p>
<h1>Display the result</h1>
<p>Markdown(result_with_rag.raw)
```</p>
<p>```python</p>
<p>```</p>