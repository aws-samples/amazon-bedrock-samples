<h2>Lab 1: AI Travel Assistant Use Case Introduction</h2>
<h3>Introduction</h3>
<p>In this first Lab, we will introduce the AI Travel Assistant use case, discuss the data sources, core features of AI Agents with Bedrock and Open Source Agent Framework LangChain and set up the packages and dependencies that is required for the rest of the Labs.</p>
<p>The use case is to help create a bot which 
- FFind <code>My Dream Destination</code> which finds similiar destinations based on the user preferences using <code>RAG</code>
- Can <code>book travel</code> including hotel and flight
- Leverages <code>Tools</code> to exeute the actions
- Asks for <code>Human Confirmation</code> for critical exeution flows</p>
<h3>Use Case</h3>
<p>Imagine having an AI assistant that can help you plan your next vacation, catering to all your preferences and needs. That's exactly what our "AI Travel Assistant" does—a cutting-edge, agentic AI system built using LangGraph and Amazon Bedrock Models. This assistant is designed to make travel planning seamless, offering personalized and data-driven suggestions every step of the way.</p>
<p>We will cover following scenarios in this workshop</p>
<ol>
<li><strong>Lab 2: Introduction to the concepts of Agents including building blocks for LangGrah and ReACT agents. We will introduce memory concepts in this lab to show how to have 'Multi-Turn' conversations. We will show short term and long term memory:</strong> </li>
</ol>
<p>Understand what it takes to build a agentic system.</p>
<ol>
<li><strong>Lab 3: Dream Destination Planning with Introduction of RAG to the pipeline for Customized Travel Itineraries. We will show different types of Agents incuding concepts like 'Human-In-The-Loop': We will also introduce Multi-Modal concept in this lab</strong> </li>
</ol>
<p>Get personalized recommendations for your next dream destination. Create vacation plans tailored specifically to your preferences and based on your past travels.</p>
<ol>
<li><strong>Lab 4: Multi-Agent colloboration. We will leverage all the work from the previous labs and then assemble the building blocks to create a multi agent colloboration. We will use Similar Travelers Based Recommendations, book hotels and flights:</strong> </li>
</ol>
<p>Receive recommendations influenced by the preferences of travelers in a similar age group and geographic location.Book, modify, and cancel flight and hotel reservations—all through one assistant.</p>
<ol>
<li><strong>Lab 5: [Optional] Dream Destination with crew.ai for comparisions:</strong> </li>
</ol>
<p>Book, modify, and cancel flight and hotel reservations—all through one assistant.</p>
<ol>
<li><strong>Lab 6: Agentic Evaluation with RAGAS:</strong> </li>
</ol>
<p>Understand how to evaluate the Agentic workflows using the open soyrce RAGAS library.</p>
<p>The diagram will be similiar to this below</p>
<p><img src="./images/travel_agent_light.png" width="65%" alt='travel_agent_light.png'/> </p>
<h3>Dataset</h3>
<p>Introduction to the data set we wil be using for this workshop</p>
<h4>1. Travel History:</h4>
<p>We have synthetically created travel history dataset we will levearge in this workshop, it contains following fields</p>
<ul>
<li>Name: The individual's full name.</li>
<li>Current_Location: The city where the individual currently resides.</li>
<li>Age: The individual's age in years.</li>
<li>Past_Travel_Destinations: Cities the individual has previously visited, listed as comma-separated values.</li>
<li>Number_of_Trips: The total count of trips the individual has taken.</li>
<li>Flight_Number: The flight number associated with each trip taken.</li>
<li>Departure_City: The city from which each flight departed.</li>
<li>Arrival_City: The destination city for each flight.</li>
<li>Flight_Date: The date of each flight taken.</li>
</ul>
<p>```python
import pandas as pd</p>
<p>df = pd.read_csv("./data/synthetic_travel_data.csv")
df.head(10)
```</p>
<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Id</th>
      <th>Name</th>
      <th>Current_Location</th>
      <th>Age</th>
      <th>Past_Travel_Destinations</th>
      <th>Number_of_Trips</th>
      <th>Past_Travel_Destinations.1</th>
      <th>Number_of_Trips.1</th>
      <th>Flight_Number</th>
      <th>Departure_City</th>
      <th>Arrival_City</th>
      <th>Flight_Date</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>24.0</td>
      <td>Philip Cook</td>
      <td>Zurich</td>
      <td>29.0</td>
      <td>Ljubljana</td>
      <td>1.0</td>
      <td>Ljubljana</td>
      <td>1.0</td>
      <td>Z1823</td>
      <td>Zurich</td>
      <td>Ljubljana</td>
      <td>2024-10-11</td>
    </tr>
    <tr>
      <th>1</th>
      <td>918.0</td>
      <td>Andrew Macdonald</td>
      <td>Paris</td>
      <td>62.0</td>
      <td>Lisbon, Lisbon, Bergen, Paris, Warsaw</td>
      <td>5.0</td>
      <td>Lisbon, Lisbon, Bergen, Paris, Warsaw</td>
      <td>5.0</td>
      <td>O1142</td>
      <td>Paris</td>
      <td>Lisbon</td>
      <td>2024-10-21</td>
    </tr>
    <tr>
      <th>2</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>U7234</td>
      <td>Paris</td>
      <td>Lisbon</td>
      <td>2024-03-23</td>
    </tr>
    <tr>
      <th>3</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>H9041</td>
      <td>Paris</td>
      <td>Bergen</td>
      <td>2024-03-25</td>
    </tr>
    <tr>
      <th>4</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>Y7505</td>
      <td>Paris</td>
      <td>Paris</td>
      <td>2023-09-13</td>
    </tr>
    <tr>
      <th>5</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>X8568</td>
      <td>Paris</td>
      <td>Warsaw</td>
      <td>2023-05-17</td>
    </tr>
    <tr>
      <th>6</th>
      <td>709.0</td>
      <td>Jonathan Garcia</td>
      <td>Sacramento</td>
      <td>43.0</td>
      <td>New York</td>
      <td>1.0</td>
      <td>New York</td>
      <td>1.0</td>
      <td>P8336</td>
      <td>Sacramento</td>
      <td>New York</td>
      <td>2023-07-10</td>
    </tr>
    <tr>
      <th>7</th>
      <td>314.0</td>
      <td>Wendy Yu</td>
      <td>Moscow</td>
      <td>34.0</td>
      <td>Prague, Valencia, Reykjavik, London</td>
      <td>4.0</td>
      <td>Prague, Valencia, Reykjavik, London</td>
      <td>4.0</td>
      <td>P6922</td>
      <td>Moscow</td>
      <td>Prague</td>
      <td>2023-01-02</td>
    </tr>
    <tr>
      <th>8</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>I1305</td>
      <td>Moscow</td>
      <td>Valencia</td>
      <td>2024-05-26</td>
    </tr>
    <tr>
      <th>9</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>S2309</td>
      <td>Moscow</td>
      <td>Reykjavik</td>
      <td>2023-04-14</td>
    </tr>
  </tbody>
</table>
</div>

<h4>2. US and Europe City Dataset</h4>
<p>For the purpose of the Retrieval Augmented generation(RAG) demonstrations in the labs, we have synthetically created PDF datasets to be ingested in the Vector DBs. Following is a sample PDF organises in <code>/data/us</code> and <code>/data/europe</code> folders respectively. We have used an Agentic implementation to create the dataset. You can check this out in the optional notebook provided</p>
<p><code>python
from IPython.display import Image
Image(filename='./images/vegas.png')</code></p>
<p><img alt="png" src="01_usecase_introduction_files/01_usecase_introduction_9_0.png" /></p>
<h3>Amazon Bedrock Model Access</h3>
<p><a href="https://aws.amazon.com/bedrock/">Amazon Bedrock</a> offers a variety of foundation models (FMs) that are optimized for different use cases, making it a versatile platform for building generative AI applications. For agentic workflows, where models interact with tools, make decisions, and carry out complex tasks autonomously, choosing the right FM is crucial. For the purposes of this demostration, we will use the foundational models available on Amazon Bedrock with a focus on Anthropic Claude, Meta’s models, and Amazon’s own models, highlighting their capabilities for demonstration purposes. You can take a look <a href="https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html">Supported foundation models in Amazon Bedrock</a></p>
<p>```python
import boto3</p>
<p>region = 'us-east-1'
bedrock = boto3.client(
    service_name = 'bedrock-runtime',
    region_name = region,
)
```</p>
<h4>Anthropic's Claude in Amazon Bedrock</h4>
<p>The <code>langchain_aws</code> package is a tool for integrating and interacting with Amazon Bedrock's language models through the LangChain framework. It provides following benefits</p>
<ul>
<li>Simplified Access to Amazon Bedrock Models</li>
<li>
<p>Support for Conversational AI and Agentic Workflows</p>
</li>
<li>
<p><code>from langchain_aws.chat_models.bedrock:</code> This imports the ChatBedrock class from the langchain_aws package, specifically from the chat_models module.</p>
</li>
<li><code>ChatBedrock:</code> This is a class that allows interaction with Amazon Bedrock’s chat models, enabling users to create conversational AI applications using different foundational models available on Bedrock.</li>
</ul>
<p>Refer <a href="https://aws.amazon.com/bedrock/claude/">Anthropic's Claude in Amazon Bedrock</a> for more details</p>
<h3>Converse API</h3>
<p><img src="./images/converse_api.png" width="40%" alt=" conver api simplifies" /></p>
<p>```python
%pip install -U --no-cache-dir  \
"langchain==0.3.7" \
"langchain-aws==0.2.6" \
"langchain-community==0.3.5" \
"langchain-text-splitters==0.3.2" \
"langchainhub==0.1.20" \
"langgraph==0.2.45" \
"langgraph-checkpoint==2.0.2" \
"langgraph-sdk==0.1.35" \
"langsmith==0.1.140" \
"pypdf==3.8,&lt;4" \
"ipywidgets&gt;=7,&lt;8" \
"matplotlib==3.9.0" \
"faiss-cpu==1.8.0"</p>
<p>%pip install -U --no-cache-dir boto3</p>
<h1>%pip install grandalf==3.1.2</h1>
<p>```</p>
<p>```python
from langchain_aws.chat_models.bedrock import ChatBedrock
from rich.console import Console
from rich.text import Text</p>
<h1>Create a console object</h1>
<p>console = Console()</p>
<p>modelId = 'anthropic.claude-3-haiku-20240307-v1:0'
llm = ChatBedrock(
    model_id=modelId,
    client=bedrock,
    beta_use_converse_api=True
)</p>
<p>response = llm.invoke("I am planning a trip  with my family to Hawai next summer, can you give me a travel iternary for 5 days").content</p>
<h1>Format the text as a rich Text object</h1>
<p>formatted_text = Text.from_markup(response)</p>
<h1>Print the formatted response using rich</h1>
<p>console.print(formatted_text)
```</p>
<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace">Certainly! Here's a suggested 5-day travel itinerary for a trip to Hawaii:

Day 1:
- Arrive at the Honolulu International Airport on the island of Oahu
- Check-in to your hotel or resort
- Explore Waikiki Beach and its lively shops, restaurants, and beachfront
- Visit the iconic Diamond Head State Monument for a scenic hike

Day 2:
- Take a day trip to the island of Maui
- Visit the stunning Haleakala National Park and watch the sunrise (or sunset) from the summit
- Explore the lush Iao Valley State Park
- Enjoy the charming town of Lahaina with its historic sites and art galleries

Day 3:
- Spend the day exploring the island of Oahu
- Visit the Pearl Harbor National Memorial and learn about the history of the attack
- Explore the North Shore, known for its giant waves, surfing culture, and the Dole Pineapple Plantation
- Stop at the Banzai Pipeline to watch the surfers (during the winter months)

Day 4:
- Take a day trip to the island of Kauai
- Hike the Napali Coast or take a boat tour to witness its dramatic cliffs and waterfalls
- Explore the Waimea Canyon, often referred to as the "Grand Canyon of the Pacific"
- Relax on the beautiful beaches of Poipu or Princeville

Day 5:
- Spend the day in Honolulu
- Visit the iconic Iolani Palace, the only royal palace in the United States
- Explore the Bernice Pauahi Bishop Museum, which showcases the rich cultural heritage of Hawaii
- Enjoy a sunset dinner or luau experience to cap off your Hawaiian adventure

Remember, this is just a suggested itinerary, and you can adjust it to fit your interests and travel preferences. 
Additionally, be sure to factor in time for relaxation, exploring local cuisine, and enjoying the stunning natural 
beauty that Hawaii has to offer.
</pre>

<h3>Course-grained model comparison</h3>
<p>In this section, we experiment with multiple models available on Amazon Bedrock and run course-grained evaluation on one of our task of interest. With the thousands of available models on the market, it is intractable to evaluation every single one. Hence, it is generally necessary to pre-filter for the ones that are not only from trusted providers, but have shown strong performance on a variety of benchmarks. </p>
<p>Amazon Bedrock allows you to make a quick short-list by supporting a growing list providers such as Anthropic, Meta, Mistral, Cohere, AI21Labs, Stability AI and Amazon. This lets you start with a strong base to continue the model selection process.</p>
<p>Next we perform course-grained model evalution on the following models to inform our initial choice of model for our task of interest:
- Anthropic: Claude 3 Haiku</p>
<p>For this workshop we have access to 1 model only. Ideally in your own accounts you can use multiple models to run this evaluation.</p>
<p>To perform an initial evaluation, we create a small curated dataset of 10 examples. The optimal initial number of examples should be sufficiently big to roughly cover the types of queries our customers will send our model. Since this stage of the model evaluation process is meant to get a rough idea, the number of examples can be small.</p>
<p>To start, our scenario can be described by summarization (<strong>task</strong>) of vacation destinations (<strong>what</strong>) asked by travelers (<strong>who</strong>) at the time of development (<strong>when</strong>) in English (<strong>language</strong>). The set of initial questions can be found in <a href="./data/examples.txt">examples.txt</a>. We could expand our test by changing one or more of the variables composing the scenario of interesting. For instance, we could generate equivalent examples, but asked by people who aren't travelers or by others speaking in any other languages.</p>
<p><code>python
with open("./data/examples.txt", "r") as file:
    examples = file.read().splitlines()</code></p>
<p>```python
import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from rich.console import Console
from rich.text import Text</p>
<p>pd.set_option('display.max_colwidth', None)</p>
<h1>Create a console object</h1>
<p>console = Console()</p>
<p>def generate_answers(
    examples: list = [],
    system_prompt: SystemMessage = None
):
    modelIds = [
        "anthropic.claude-3-haiku-20240307-v1:0",
    ]
    output = pd.DataFrame({
        'example': [],
        'Claude3Haiku': [],
    })
    for example in examples:
        results = [example]
        for modelId in modelIds:
            messages = [
                system_prompt if system_prompt else SystemMessage(content=""),
                HumanMessage(content=example)
            ]
            llm = ChatBedrock(
                model_id=modelId,
                client=bedrock,
                beta_use_converse_api=True
            )
            resp = llm.invoke(messages).content
            results.append(resp)
        output.loc[len(output)] = results
    return output
```</p>
<p><code>python
one_example = examples
output = generate_answers(one_example)
output.head()</code></p>
<h3>Conclusion</h3>
<p>In this notebook, we established 
- the use case scope of the labs covered in this workshop
- datasets we will be using all the labs
- Amazon bedrock models used in this</p>
<p>Please proceed to the next labs</p>