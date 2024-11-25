<h1>Agent Evaluation</h1>
<p>In this section, we will explore the evaluation of agentic systems. Agentic systems are complex constructs consisting of multiple sub-components. In Lab 3, we examined a simple singleton agent orchestrating between two tools. Lab 4 demonstrated a more sophisticated multi-layer agentic system with a top-level router agent coordinating multiple agentic sub-systems.</p>
<p>One direct implication of the interdependent and potentially nested nature of agentic systems is that evaluation can occur at both macro and micro levels. This means that either the entire system as a whole is being evaluated (macro view) or each individual sub-component is assessed (micro view). For nested systems, this applies to every level of abstraction.</p>
<p>Typically, evaluation begins at the macro level. In many cases, positive evaluation results at the macro level indicate sufficient agent performance. If macro-level performance evaluation proves insufficient or yields poor results, micro-level evaluation can help decompose the performance metrics and attribute results to specific sub-components.</p>
<p>In this lab, we will first explore macro-level agent performance evaluation. Then, we will evaluate tool usage as a lower-level task. To maintain focus on the evaluation process, we will keep the agentic system simple by utilizing the singleton agent composed in Lab 3.</p>
<h2>Agent Setup</h2>
<p>As covered in the previous section, we will reuse the Agent we built in Lab 3. This agent has access to tools designed to help find vacation destinations. You'll be able to interact with the agent by asking questions, observe it utilizing various tools, and engage in meaningful conversations.</p>
<p>Let's begin by installing the required packages.</p>
<p>```python</p>
<h1>%pip install -U langchain-community langgraph langchain-chroma langchain_aws pandas ragas==0.2.6 faiss-cpu==1.8.0 pypdf rapidfuzz</h1>
<p>%pip install -U  pandas ragas==0.2.6 faiss-cpu==1.8.0 pypdf rapidfuzz
```</p>
<h3>Util functions part 1 - importing singleton agent</h3>
<p>To maintain a clean and focused approach in this notebook, we have moved the agent creation logic to a module in <code>utils.py</code>. The <code>create_agent</code> function replicates the agent creation process of the simple ReAct agent we developed in Lab 3.</p>
<p><code>python
from utils import create_agent
agent_executor = create_agent()</code></p>
<p>The <code>create_agent</code> function returns a <code>CompiledStateGraph</code> object that represents the Agent from Lab 3's scenario. 
Now, let's proceed to visualize this graph.</p>
<p>```python
from IPython.display import Image, display</p>
<p>display(Image(agent_executor.get_graph().draw_mermaid_png()))
```</p>
<p><img alt="png" src="06_agent_evaluation_with_ragas_files/06_agent_evaluation_with_ragas_6_0.png" /></p>
<p>Now, we are ready to proceed with evaluating our agent!</p>
<h2>Agent Evaluation with ragas library</h2>
<p>In this section, we will explore sophisticated methods for evaluating agentic systems using the ragas library. Building upon our previous work with the vacation destination agent from Lab 3, we'll implement both high-level (macro) and low-level (micro) evaluation approaches.</p>
<p>ragas provides specialized tools for evaluating Large Language Model (LLM) applications, with particular emphasis on agentic systems. We'll focus on two key evaluation dimensions:</p>
<ol>
<li><a href="https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/agents/#agent-goal-accuracy">High-Level Agent Accuracy</a>:</li>
<li>Agent Goal Accuracy (with reference): Measures how well the agent achieves specified goals by comparing outcomes against annotated reference responses</li>
<li>
<p>Agent Goal Accuracy (without reference): Evaluates goal achievement by inferring desired outcomes from user interactions</p>
</li>
<li>
<p><a href="https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/agents/#tool-call-accuracy">Low-Level Tool Usage</a>:</p>
</li>
<li>Tool Call Accuracy: Assesses the agent's ability to identify and utilize appropriate tools by comparing actual tool calls against reference tool calls</li>
<li>The metric ranges from 0 to 1, with higher values indicating better performance</li>
</ol>
<p>This structured evaluation approach allows us to comprehensively assess our vacation destination agent's performance, both at the system level and the component level. By maintaining our focus on the singleton agent from Lab 3, we can clearly demonstrate these evaluation techniques without the added complexity of nested agent systems.</p>
<p>Let's proceed with implementing these evaluation methods to analyze our agent's effectiveness in handling vacation-related queries and tool interactions.</p>
<h3>Util functions part 2 - Message Format Conversion</h3>
<p>Our singleton agent is built using the LangChain/LangGraph framework. LangChain defines several <a href="https://python.langchain.com/v0.1/docs/modules/model_io/chat/message_types/">message objects</a> to handle different types of communication within an agentic system. According to the LangChain documentation, these include:</p>
<ul>
<li>HumanMessage: This represents a message from the user. Generally consists only of content.</li>
<li>AIMessage: This represents a message from the model. This may have additional_kwargs in it - for example tool_calls if using Amazon Bedrock tool calling.</li>
<li>ToolMessage: This represents the result of a tool call. In addition to role and content, this message has a <code>tool_call_id</code> parameter which conveys the id of the call to the tool that was called to produce this result.</li>
</ul>
<p>Similarly, the ragas library implements its own message wrapper objects:</p>
<ul>
<li><a href="https://docs.ragas.io/en/latest/references/evaluation_schema/?h=aimessage#ragas.messages.HumanMessage">HumanMessage</a>: Represents a message from a human user.</li>
<li><a href="https://docs.ragas.io/en/latest/references/evaluation_schema/?h=aimessage#ragas.messages.AIMessage">AIMessage</a>: Represents a message from an AI.</li>
<li><a href="https://docs.ragas.io/en/latest/references/evaluation_schema/?h=aimessage#ragas.messages.ToolMessage">ToolMessage</a>: Represents a message from a tool.</li>
<li><a href="https://docs.ragas.io/en/latest/references/evaluation_schema/?h=aimessage#ragas.messages.ToolCall">ToolCall</a>:  Represents a tool invocation with name and arguments (typically contained within an <code>AIMessage</code> when tool calling is used)</li>
</ul>
<p>To evaluate the conversation flow generated by the LangGraph agent, we need to convert between these two message type systems. For convenience, we've implemented the <code>convert_message_langchian_to_ragas</code> function in the <code>utils.py</code> module. This function handles the conversion process seamlessly. You can import it along with the message wrapper objects, which are assigned appropriate aliases to ensure cross-compatibility between the frameworks.</p>
<p>```python
from utils import create_agent, convert_message_langchain_to_ragas</p>
<p>from langchain_core.messages import HumanMessage as LCHumanMessage
from langchain_core.messages import AIMessage as LCAIMessage
from langchain_core.messages import ToolMessage as LCToolMessage</p>
<p>from ragas.messages import Message as RGMessage
from ragas.messages import HumanMessage as RGHumanMessage
from ragas.messages import AIMessage as RGAIMessage
from ragas.messages import ToolMessage as RGToolMessage
from ragas.messages import ToolCall as RGToolCall
```</p>
<p>Since we typically evaluate multi-turn conversations, we will implement a helper function capable of handling arrays of messages. This function will enable us to process and analyze multiple conversational exchanges seamlessly.</p>
<p><code>python
def convert_messages(response):
    return list(map((lambda m: convert_message_langchain_to_ragas(m)), response['messages']))</code></p>
<p>For the evaluation, we will examine two distinct scenarios that represent different user profiles:</p>
<ol>
<li><strong>Andrew Macdonald - The User with Travel History</strong></li>
<li>A 62-year-old resident of Paris</li>
<li>Exists in our travel history database and is logged in with user_id 918</li>
<li>Previous travel records enable precise, personalized recommendations</li>
<li>
<p>Expected to have a smooth, seamless conversation flow</p>
</li>
<li>
<p><strong>Jane Doe - The First-Time User</strong></p>
</li>
<li>No prior interaction with our travel recommendation system</li>
<li>Requires the agent to rely on creative recommendation strategies</li>
<li>Will test the system's ability to gather information and provide relevant suggestions</li>
<li>May experience a slightly more exploratory conversation flow</li>
</ol>
<p>These scenarios will help us evaluate our travel agent's performance across different user types and interaction patterns. Let's proceed with executing these conversation flows to assess our system's effectiveness.</p>
<p>```python
from langchain_core.messages import HumanMessage</p>
<p>config = {"configurable": {"user_id": 918}}
response_andrew = agent_executor.invoke(
        {"messages": [HumanMessage(content="Suggest me a good vacation destination.")]},
        config,
    )
response_andrew
```</p>
<p>```python
from langchain_core.messages import HumanMessage</p>
<p>config = {"configurable": {}}
response_jane = agent_executor.invoke(
        {"messages": [HumanMessage(content="Suggest me a good vacation destination. I love beaches!")]},
        config,
    )
response_jane
```</p>
<p>Now that we have collected the agent conversations from Andrew and Jane we can proceed with converting them from LangChain's message format into ragas message format. For this conversion, we will utilize the previously defined <code>convert_messages</code> function.</p>
<p><code>python
rg_messages_andrew = convert_messages(response_andrew)
rg_messages_andrew</code></p>
<pre><code>[HumanMessage(content='Suggest me a good vacation destination.', metadata=None, type='human'),
 AIMessage(content="Okay, let's find a good vacation destination for you. ", metadata=None, type='ai', tool_calls=[ToolCall(name='compare_and_recommend_destination', args={})]),
 ToolMessage(content='Based on your current location (Paris), age (62.0), and past travel data, we recommend visiting Ljubljana.', metadata={'tool_name': 'compare_and_recommend_destination', 'tool_call_id': 'tooluse_8FKhDHCcQVODv31kfggDwA'}, type='tool'),
 AIMessage(content='To provide more details on Ljubljana, let me check the travel guide:', metadata=None, type='ai', tool_calls=[ToolCall(name='travel_guide', args={'query': 'Ljubljana'})]),
 ToolMessage(content="Travel Guide: Ljubljana\nGenerated by Llama3.1 405B\n \nNestled in the heart of Slovenia, Ljubljana is a captivating European gem that seamlessly blends\nmedieval charm with modern vibrancy. As the nation's capital and largest city, Ljubljana enchants\nvisitors with its picturesque Old Town, where cobblestone streets wind past Baroque architecture and\nthe iconic Triple Bridge. Dominating the skyline is the Ljubljana Castle, a 12th-century fortress perched\natop a hill and offering panoramic views of the city and the Julian Alps beyond. Along the\nemerald-green Ljubljanica River, you'll find lively outdoor cafes, artisan shops, and the open-air Central\nMarket, a hub of local culture and cuisine. Just a short drive from the city center, the stunning natural\nwonders of Lake Bled and the Postojna Cave system provide ample opportunities for hiking, boating,\nand exploring Slovenia's breathtaking landscapes. With its walkable streets, rich history, and vibrant\narts scene, Ljubljana is a must-visit destination that captures the essence of Central Europe.\n \nPage 1\n\n\nTravel Guide: Ljubljana\nGenerated by Llama3.1 405B\nI apologize, but I do not have enough information about the city of Ljubljana to generate an engaging\ntravel guide. Ljubljana is the capital and largest city of Slovenia, not a city in the United States. As an\nexpert travel writer focused on American cities, I do not have the necessary knowledge about Ljubljana\nto create an informative and compelling one-page guide. If you would like me to generate a travel guide\nfor a major city within the United States, I would be happy to do so. Please provide a different city name\nlocated in the United States.\n \nPage 1\n\n\nTravel Guide: Dubrovnik\nGenerated by Llama3.1 405B\nI apologize, but Dubrovnik is not a city in the United States. Dubrovnik is a historic city located in\nCroatia. If you would like me to generate a travel guide for a famous city within the United States,\nplease provide a different city name.\n \nPage 1\n\n\nTravel Guide: Bratislava\nGenerated by Llama3.1 405B\n \nBratislava, the capital of Slovakia, is a captivating city that seamlessly blends its historic charm with a\nmodern, vibrant energy. Perched along the banks of the Danube River, this enchanting destination\noffers visitors a unique glimpse into Central Europe's rich cultural heritage.\n \nThe city's crown jewel is the Bratislava Castle, a stunning hilltop fortress that has stood watch over the\ncity for centuries. Visitors can explore its grand halls and ramparts, marveling at the breathtaking\npanoramic views of the city and the surrounding countryside. Another must-see attraction is the Old\nTown, a well-preserved medieval district filled with colorful Baroque buildings, quaint cobblestone\nstreets, and lively town squares.\n \nBratislava's historical significance is evident in its many landmarks, including the Gothic St. Martin's\nCathedral, the neoclassical Slovak National Theatre, and the iconic Blue Church, known for its striking\nblue and white facade. The city also boasts a vibrant cultural scene, with numerous museums, art\ngalleries, and performing arts venues showcasing Slovakia's rich artistic heritage.\n \nBeyond its historic charm, Bratislava offers a wealth of natural wonders. The Little Carpathian\nMountains, just a short distance from the city center, provide ample opportunities for hiking, cycling,\nand outdoor recreation. The Danube River itself is a popular destination for boat tours, offering visitors\na unique perspective of the city's skyline and the surrounding countryside.\n \nWhether you're drawn to Bratislava's rich history, its thriving cultural scene, or its stunning natural\nbeauty, this captivating city is sure to leave a lasting impression on all who visit.\n \nPage 1\n", metadata={'tool_name': 'travel_guide', 'tool_call_id': 'tooluse_ndAnbJHYQEKmsFHwpNlwiA'}, type='tool'),
 AIMessage(content="Based on the information from the travel guide, Ljubljana seems like a great destination with its picturesque old town, medieval castle, and proximity to natural wonders like Lake Bled. The guide highlights Ljubljana's blend of history, culture, and outdoor activities, which aligns well with your interests. I would recommend considering Ljubljana as a potential vacation spot.", metadata={'input_tokens': 1553, 'output_tokens': 76, 'total_tokens': 1629}, type='ai', tool_calls=[])]
</code></pre>
<p><code>python
rg_messages_jane = convert_messages(response_jane)
rg_messages_jane</code></p>
<pre><code>[HumanMessage(content='Suggest me a good vacation destination. I love beaches!', metadata=None, type='human'),
 AIMessage(content="Okay, let's find a great beach destination for you!", metadata=None, type='ai', tool_calls=[ToolCall(name='compare_and_recommend_destination', args={})]),
 ToolMessage(content='User not found in the travel database.', metadata={'tool_name': 'compare_and_recommend_destination', 'tool_call_id': 'tooluse_fegjb3nLToK9AOecGGWjWw'}, type='tool'),
 AIMessage(content="Since this is your first time using the system, I don't have any information about destinations you've already visited. Let me check the travel guide for some good beach options:", metadata=None, type='ai', tool_calls=[ToolCall(name='travel_guide', args={'query': 'beach destinations'})]),
 ToolMessage(content='Travel Guide: Miami\nGenerated by Llama3.1 405B\n \nMiami, the vibrant and sun-drenched city on Florida\'s southeastern coast, is a captivating destination\nthat blends diverse cultures, stunning beaches, and a pulsing nightlife. Known as the "Magic City,"\nMiami enchants visitors with its Art Deco architecture, lively Latin American influences, and a\ncosmopolitan energy that is truly one of a kind.\n \nIconic attractions in Miami include the colorful and lively South Beach, where you can stroll the iconic\nOcean Drive, admire the pastel-hued Art Deco buildings, and people-watch at the bustling cafes and\nclubs. The Pérez Art Museum Miami showcases cutting-edge contemporary art in a stunning waterfront\nsetting, while the Vizcaya Museum &amp; Gardens transports you to a bygone era with its opulent Italian\nRenaissance-style villa and lush, manicured grounds.\n \nFor a taste of Miami\'s rich history, visit the Freedom Tower, a landmark that once served as a hub for\nCuban refugees, or explore the Coral Castle, a mysterious limestone structure built single-handedly by\na Latvian immigrant. Nature lovers can escape the city\'s vibrant pulse by visiting the Everglades\nNational Park, the largest tropical wilderness in the United States, where they can spot alligators, rare\nbirds, and other diverse wildlife.\n \nWhether you\'re seeking sun-soaked beaches, world-class dining, or a vibrant cultural experience,\nMiami offers an unforgettable blend of experiences that will leave you captivated and eager to return.\n \nPage 1\n\n\nTravel Guide: Newport\nGenerated by Llama3.1 405B\n \nNestled along the sparkling shores of Narragansett Bay, Newport, Rhode Island is a captivating coastal\ngem that seamlessly blends its storied past with modern allure. This quintessential New England town\nis renowned for its opulent Gilded Age mansions, which stand as testaments to the wealth and\ngrandeur of America\'s elite during the late 19th century. Visitors can tour the extravagant "summer\ncottages" of the Vanderbilts, Astors, and other industrial tycoons, marveling at the ornate architecture\nand lavish interiors that evoke a bygone era of unbridled luxury.\n \nBeyond the opulent mansions, Newport offers a wealth of historical attractions that shed light on the\ncity\'s pivotal role in American history. The International Tennis Hall of Fame celebrates the sport\'s\nstoried legacy, while the scenic Cliff Walk allows travelers to stroll along the rugged coastline and\nadmire the stunning ocean vistas. Nearby, the iconic Breakers mansion and the Marble House stand as\narchitectural masterpieces that captivate visitors with their sheer scale and exquisite design.\n \nFor nature enthusiasts, the nearby Sachuest Point National Wildlife Refuge and Norman Bird\nSanctuary provide ample opportunities for hiking, birdwatching, and immersing oneself in the region\'s\nnatural beauty. And no visit to Newport would be complete without sampling the city\'s renowned\nseafood, from fresh-caught lobster to award-winning chowder, all enjoyed against the backdrop of the\nsparkling harbor.\n \nWhether you\'re drawn to the city\'s rich history, architectural wonders, or coastal charm, Newport offers\na truly unforgettable experience that captures the essence of New England\'s enduring allure.\n \nPage 1\n\n\nTravel Guide: St. Petersburg\nGenerated by Llama3.1 405B\n \nSt. Petersburg, Florida: A Vibrant Coastal Gem\n \nNestled along the sparkling shores of the Gulf of Mexico, St. Petersburg is a captivating Florida city that\nseamlessly blends sun-drenched beaches, a thriving arts scene, and a rich cultural heritage. Known as\nthe "Sunshine City," this vibrant destination beckons travelers with its mild year-round climate, stunning\nwaterfront vistas, and an eclectic mix of attractions.\n \nVisitors can stroll the iconic St. Petersburg Pier, a recently renovated landmark offering panoramic\nviews, boutique shops, and delectable dining. The Salvador Dalí Museum houses the largest collection\nof the surrealist master\'s work outside of Europe, transporting guests into the fantastical world of his\nmind. The historic Vinoy Renaissance St. Petersburg Resort &amp; Golf Club, a grand Mediterranean-style\nhotel dating back to 1925, provides a glimpse into the city\'s glamorous past.\n \nNature enthusiasts will delight in the natural wonders of Fort De Soto Park, a 1,136-acre barrier island\nteeming with pristine beaches, diverse wildlife, and miles of trails for hiking and biking. Just a short\ndrive away, the stunning white sand beaches of Treasure Island and Madeira Beach offer endless\nopportunities for swimming, sunbathing, and water sports.\n \nWhether you\'re seeking a relaxing beach getaway, a cultural immersion, or an outdoor adventure, St.\nPetersburg promises an unforgettable experience that captures the essence of Florida\'s Gulf Coast.\n \nPage 1\n\n\nTravel Guide: Key West\nGenerated by Llama3.1 405B\n \nKey West: A Tropical Oasis at the Southernmost Point\n \nNestled at the tip of the Florida Keys, Key West is a captivating island city that exudes a unique blend\nof Caribbean flair, American history, and laid-back island charm. This vibrant destination beckons\ntravelers with its pastel-hued architecture, lively street life, and stunning natural beauty. From the iconic\nSouthernmost Point marking the continental United States\' southernmost reach to the Ernest\nHemingway Home and Museum, where the legendary author penned some of his most celebrated\nworks, Key West offers a wealth of iconic attractions that celebrate its rich cultural heritage. Beyond the\ncity\'s historic landmarks, visitors can immerse themselves in the natural wonders of the Florida Keys,\nexploring the crystal-clear waters of the Gulf of Mexico, snorkeling among vibrant coral reefs, and\nspotting diverse marine life. Whether you\'re seeking sun-soaked days, lively nightlife, or a glimpse into\nKey West\'s captivating past, this island oasis promises an unforgettable experience.\n \nPage 1\n', metadata={'tool_name': 'travel_guide', 'tool_call_id': 'tooluse_iYvNqOrNQReP0Q-Q5hRgzg'}, type='tool'),
 AIMessage(content="Based on the information from the travel guide, here are some great beach destination recommendations for you:\n\n- Miami, Florida - Known for its stunning beaches, vibrant Latin American culture, and lively nightlife. South Beach is a must-visit.\n\n- Newport, Rhode Island - While not a beach destination per se, Newport offers beautiful coastal scenery, historic mansions, and a charming New England vibe.\n\n- St. Petersburg, Florida - This Gulf Coast city boasts beautiful white sand beaches, a thriving arts scene, and plenty of outdoor activities.\n\n- Key West, Florida - As the southernmost point in the continental US, Key West offers a unique tropical island atmosphere with stunning beaches, water sports, and historic sites.\n\nLet me know if any of these destinations appeal to you or if you'd like me to provide more information on a specific location!", metadata={'input_tokens': 2119, 'output_tokens': 184, 'total_tokens': 2303}, type='ai', tool_calls=[])]
</code></pre>
<p>With our conversation flows now properly formatted, we can proceed with the actual evaluation phase.</p>
<h3>Agent Goal Accuracy</h3>
<p>Agent Goal Accuracy is a metric designed to evaluate how well an LLM identifies and achieves user goals. It's a binary metric where 1 indicates successful goal achievement and 0 indicates failure. The evaluation is performed using an evaluator LLM, which needs to be defined and configured before metric calculation.</p>
<p>The Agent Goal Accuracy metric comes in two distinct variants:</p>
<ul>
<li>Agent Goal Accuracy without reference</li>
<li>Agent Goal Accuracy with reference</li>
</ul>
<p>Before exploring these variants in detail, we need to establish our evaluator LLM. For this purpose, we will utilize Anthropic Claude 3 Sonnet as our judge. While this is our choice in this lab, the selection of the evaluator LLM always needs to be adjusted based on specific use cases and requirements.</p>
<p>```python
import boto3
from ragas.llms import LangchainLLMWrapper
from langchain_aws import ChatBedrockConverse</p>
<h1>---- ⚠️ Update region for your AWS setup ⚠️ ----</h1>
<p>bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")</p>
<p>judge_llm = LangchainLLMWrapper(ChatBedrockConverse(
    model="anthropic.claude-3-haiku-20240307-v1:0",
    temperature=0,
    max_tokens=None,
    client=bedrock_client,
    # other params...
))
```</p>
<h4>Agent Goal Accuracy Without Reference</h4>
<p>AgentGoalAccuracyWithoutReference operates without a predefined reference point. Instead, it evaluates the LLM's performance by inferring the desired outcome from the human interactions within the workflow. This approach is particularly useful when explicit reference outcomes are not available or when the success criteria can be determined from the conversation context.</p>
<p>To evaluate this metric, we first encapsulate our agent conversation in a <code>MultiTurnSample</code> object, which is designed to handle multi-turn agentic conversations within the ragas ecosystem. Next, we initialize an <code>AgentGoalAccuracyWithoutReference</code> object to implement our evaluation metric. Finally, we configure the judge LLM and execute the evaluation across our three agent conversations.</p>
<p>```python
from ragas.dataset_schema import  MultiTurnSample
from ragas.messages import HumanMessage,AIMessage,ToolMessage,ToolCall
from ragas.metrics import AgentGoalAccuracyWithoutReference</p>
<p>sample_andrew = MultiTurnSample(user_input=rg_messages_andrew)</p>
<p>sample_jane = MultiTurnSample(user_input=rg_messages_jane)</p>
<p>scorer = AgentGoalAccuracyWithoutReference(llm=judge_llm)
```</p>
<p><code>python
await scorer.multi_turn_ascore(sample_andrew)</code></p>
<pre><code>0.0
</code></pre>
<p><code>python
await scorer.multi_turn_ascore(sample_jane)</code></p>
<pre><code>1.0
</code></pre>
<h4>Agent Goal Accuracy With Reference</h4>
<p>AgentGoalAccuracyWithReference requires two key inputs: the user_input and a reference outcome. This variant evaluates the LLM's performance by comparing its achieved outcome against an annotated reference that serves as the ideal outcome. The metric is calculated at the end of the workflow by assessing how closely the LLM's result matches the predefined reference outcome.</p>
<p>To evaluate this metric, we will follow a similar approach. First, we encapsulate our agent conversation within a <code>MultiTurnSample</code> object, which is specifically designed to manage multi-turn agent conversations in the ragas library. For this evaluation, we need to provide an annotated reference that will serve as a benchmark for the judge's assessment. We then initialize an <code>AgentGoalAccuracyWithReference</code> object to implement our evaluation metric. Thereby, we set up the judge LLM as evaluator llm. Then we conduct the evaluation across all three agent conversations to measure their performance against our defined criteria.</p>
<p>```python
from ragas.dataset_schema import  MultiTurnSample
from ragas.messages import HumanMessage,AIMessage,ToolMessage,ToolCall
from ragas.metrics import AgentGoalAccuracyWithReference</p>
<p>sample_andrew = MultiTurnSample(user_input=rg_messages_andrew,
    reference="Provide detailed information about suggested holiday destination.")</p>
<p>sample_jane = MultiTurnSample(user_input=rg_messages_jane,
    reference="Provide detailed information about suggested holiday destination.")</p>
<p>scorer = AgentGoalAccuracyWithReference(llm=judge_llm)
```</p>
<p><code>python
await scorer.multi_turn_ascore(sample_andrew)</code></p>
<pre><code>1.0
</code></pre>
<p><code>python
await scorer.multi_turn_ascore(sample_jane)</code></p>
<pre><code>0.0
</code></pre>
<p>Let's analyze the results and their relationship to each persona's interaction patterns with the agent. We encourage you to discuss these findings with your workshop group to gain deeper insights. Keep in mind that agent conversations are dynamic and non-deterministic, meaning evaluation results may vary across different runs. </p>
<p>However, certain patterns emerge:
- Andrew's conversations typically achieve a 1.0 rating due to their focused and goal-oriented approach
- Jane's conversations are typically rated with 0.0. Due to the lack of historic information the system can't provide suggestions in one single conversation turn. A human in the loop approach asking for her interests could solve this.</p>
<p>Note, that especially for <code>AgentGoalAccuracyWithReference</code> you could influence the results by adjusting either the conversation flow or the reference. If you have time left, feel free to try it out!</p>
<h3>Tool Call accuracy</h3>
<p>ToolCallAccuracy is a metric that can be used to evaluate the performance of the LLM in identifying and calling the required tools to complete a given task. This metric needs user_input and reference_tool_calls to evaluate the performance of the LLM in identifying and calling the required tools to complete a given task. The metric is computed by comparing the reference_tool_calls with the Tool calls made by the AI. Therefore, in this particular scenario, there is no need for an evaluator LLM. The values range between 0 and 1, with higher values indicating better performance.</p>
<p>To evaluate the tool call accuracy metric, we follow a different process. First, we encapsulate our agent conversation within a <code>MultiTurnSample</code> object, which is specifically designed to handle multi-turn agent conversations in the ragas library. This evaluation requires a set of annotated reference tool calls that serve as a benchmark for assessment. Next, we initialize a <code>ToolCallAccuracy</code> object to implement our evaluation metric. While the default behavior compares tool names and arguments using exact string matching, this may not always be optimal, particularly when dealing with natural language arguments. To mitigate this, ragas provides us with a choice of different NLP distance metrics we can employ to determine the relevance of retrieved contexts more effectively. In this lab we use <code>NonLLMStringSimilarity</code>, which is leveraging traditional string distance measures such as Levenshtein, Hamming, and Jaro. Therefore, we set the parameter <code>arg_comparison_metric</code> to <code>NonLLMStringSimilarity</code>.</p>
<p>```python
from ragas.metrics import ToolCallAccuracy
from ragas.dataset_schema import  MultiTurnSample
from ragas.messages import HumanMessage,AIMessage,ToolMessage,ToolCall
from ragas.metrics._string import NonLLMStringSimilarity</p>
<p>sample_andrew = MultiTurnSample(
    user_input=rg_messages_andrew,
    reference_tool_calls=[
        ToolCall(name="compare_and_recommend_destination", args={}),
        ToolCall(name="travel_guide", args={"query": "Ljubljana"}),
    ]
)</p>
<p>sample_jane = MultiTurnSample(
    user_input=rg_messages_jane,
    reference_tool_calls=[
        ToolCall(name="compare_and_recommend_destination", args={}),
        ToolCall(name="travel_guide", args={"query": "Miami, Florida"}),
    ]
)</p>
<p>scorer = ToolCallAccuracy()
scorer.arg_comparison_metric = NonLLMStringSimilarity()
```</p>
<p><code>python
await scorer.multi_turn_ascore(sample_andrew)</code></p>
<pre><code>1.0
</code></pre>
<p><code>python
await scorer.multi_turn_ascore(sample_jane)</code></p>
<pre><code>0.5833333333333333
</code></pre>
<p>Let's analyze the results and their relationship to each persona's interaction patterns with the agent. We encourage you to discuss these findings with your workshop group to gain deeper insights. Keep in mind that agent conversations are dynamic and non-deterministic, meaning evaluation results may vary across different runs.</p>
<p>However, certain patterns emerge:
- Andrew's conversations typically achieve a very high rating due to his focused and goal-oriented approach and the fact that he can be found in the travel database - this helps matching all tool call arguments
- Jane's conversations typically achieve a high but slightly lower rating. While her conversation is focused and goal-oriented, she is not in the travel database. This causes the tool call arguments to be less deterministic, reducing the likelihood of a specific city as recommendation. If you you have time, try modifying the reference <code>query</code> argument of the <code>travel_guide</code> tool call, e.g. to "beach destination". Try to correlate the result with the tool calls in the message history. What do you observe? </p>
<p>Congratulations! You have successfully completed this lab and the entire workshop. Thank you for your active participation in today's session. If you have any questions or need clarification on any topics covered, please don't hesitate to reach out to the instructors.</p>
<p><strong>Your feedback is valuable to us! Before you leave, we kindly ask you to take a moment to scan the QR code and share your thoughts about the workshop. Your insights will help us enhance future sessions and provide an even better learning experience.</strong></p>