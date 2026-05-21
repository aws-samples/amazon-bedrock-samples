import os
import sys
import argparse
from typing import Dict, List, Any, Tuple, Annotated, TypedDict, Optional
import json
import requests
from bs4 import BeautifulSoup

# Define our agent state type - extended to include file and scraping context
class AgentState(TypedDict):
    messages: List[Any]
    tools_output: List[str]
    should_search: bool
    should_scrape: bool
    should_save_file: bool
    scrape_url: Optional[str]
    file_path: Optional[str]
    scraped_content: Optional[str]
    search_query: Optional[str]

# AWS SDK
import boto3
from botocore.config import Config

# LangChain and LangGraph imports
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, START, END
from langchain_aws import ChatBedrockConverse
from langchain_community.tools import DuckDuckGoSearchRun

# Set up Bedrock client with appropriate configuration
bedrock_config = Config(
    region_name="us-west-2",
    retries={"max_attempts": 3, "mode": "standard"}
)

bedrock_client = boto3.client(
    "bedrock-runtime",
    config=bedrock_config,
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)

# Set up guardrail config
guardrail_id = "rj98tb9owwv2"
guardrail_version = "DRAFT"

# Function to apply Bedrock Guardrails to content directly
def apply_guardrails(content: str) -> Tuple[str, Dict]:
    """Apply AWS Bedrock Guardrails to content"""
    try:
        print(f"Applying guardrail to content: {content[:50]}...")
        response = bedrock_client.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source="INPUT",
            content=[
                {
                    "text": {
                        "text": content
                    }
                }
            ]
        )
        
        print(f"Guardrail response: {json.dumps(response, indent=2)[:200]}...")
        
        # Parse response
        outputs = response.get('outputs', [])
        if outputs and len(outputs) > 0:
            guardrailed_content = outputs[0].get('text', content)
        else:
            guardrailed_content = content
        
        # Get guardrail action
        action = response.get('action', 'NONE')
        
        # Create metadata dictionary
        metadata_dict = {
            "action": action,
            "assessments": response.get('assessments', [])
        }
        
        return guardrailed_content, metadata_dict
    
    except Exception as e:
        print(f"Error applying guardrails: {e}")
        return content, {"action": "ERROR", "error": str(e), "assessments": []}

# Set up Bedrock ChatModel with guardrails
llm = ChatBedrockConverse(
    model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    client=bedrock_client,
    temperature=0.7,
    guardrail_config={
        "guardrailIdentifier": guardrail_id,
        "guardrailVersion": guardrail_version,
        "trace": "enabled"
    }
)

# Define tools for the DataCamp use case

def scrape_website(url: str) -> str:
    """Scrape content from a website URL."""
    try:
        print(f"Scraping website: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract main content (basic approach - may need customization)
        main_content = ""
        
        # Extract paragraphs
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            main_content += p.get_text() + "\n\n"
        
        # Extract headers
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        for h in headers:
            main_content += h.get_text() + "\n\n"
        
        print(f"Scraped content length: {len(main_content)} characters")
        return main_content
    except Exception as e:
        print(f"Error scraping website: {e}")
        return f"Error: {str(e)}"

def save_to_file(content: str, filepath: str) -> str:
    """Save content to a file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)
        return f"Successfully saved content to {filepath}"
    except Exception as e:
        print(f"Error saving to file: {e}")
        return f"Error saving to file: {str(e)}"

def search_text_in_file(query: str, filepath: str) -> str:
    """Search within a text file for relevant information."""
    try:
        if not os.path.exists(filepath):
            return f"Error: File {filepath} not found"
        
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Simple search - in a real implementation, you might want to use 
        # more sophisticated text search methods
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        # Find paragraphs containing the query
        results = []
        for paragraph in paragraphs:
            if query.lower() in paragraph.lower():
                results.append(paragraph)
        
        if not results:
            return f"No results found for '{query}' in {filepath}"
        
        # Return the first few relevant paragraphs
        return "\n\n".join(results[:3])
    except Exception as e:
        print(f"Error searching text: {e}")
        return f"Error searching text: {str(e)}"

# Define agent nodes
def call_llm(state: AgentState) -> AgentState:
    """Generate a response using the LLM with guardrails applied"""
    # Format the messages for the LLM
    messages = []
    
    # Add system message
    messages.append({
        "role": "system", 
        "content": """You are an educator AI assistant tasked with helping users understand topics.
        You can perform these actions:
        1. Scrape websites for information
        2. Save information to files
        3. Search within saved files
        
        Based on the user's query, determine which action to take next.
        If the user wants to learn about a topic, suggest scraping a relevant website.
        If you have scraped content, suggest saving it to a file.
        If you need to answer a specific question, suggest searching within the saved file.
        """
    })
    
    # Add conversation history
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
    
    # Generate response using ChatBedrockConverse
    try:
        response = llm.invoke(messages)
        
        # Extract content from response
        # Handle different response structures that might be returned
        response_content = ""
        if hasattr(response, 'content'):
            # If response has a content attribute
            if isinstance(response.content, str):
                response_content = response.content
            elif isinstance(response.content, list):
                # If content is a list, join all string items
                response_content = " ".join([str(item) for item in response.content if isinstance(item, str)])
            else:
                # Convert other types to string
                response_content = str(response.content)
        elif isinstance(response, dict) and 'content' in response:
            # If response is a dictionary with content key
            if isinstance(response['content'], str):
                response_content = response['content']
            else:
                response_content = str(response['content'])
        else:
            # Last resort, convert entire response to string
            response_content = str(response)
            
        print(f"LLM response type: {type(response)}")
        print(f"Response content type: {type(response_content)}")
        print(f"Response content (first 100 chars): {response_content[:100]}")
        
        # Check what actions to take
        should_scrape = "scrape" in response_content.lower()
        should_save_file = "save" in response_content.lower() or "file" in response_content.lower()
        should_search = "search" in response_content.lower()
        
        # Determine URL to scrape if scraping is suggested
        scrape_url = state.get("scrape_url", None)
        if should_scrape and not scrape_url:
            # Default to Wikipedia AI page like the DataCamp example if no URL is provided
            scrape_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
        
        # Determine file path if saving is suggested
        file_path = state.get("file_path", None)
        if should_save_file and not file_path:
            # Default to ai.txt like the DataCamp example if no file path is provided
            file_path = "ai.txt"
        
        # Determine search query if search is suggested
        search_query = state.get("search_query", None)
        if should_search and not search_query:
            # Extract potential search terms from the query
            last_human_message = next((msg.content for msg in reversed(state["messages"]) 
                                if isinstance(msg, HumanMessage)), "")
            search_query = last_human_message
        
        # Update state
        return {
            "messages": state["messages"] + [AIMessage(content=response_content)],
            "should_scrape": should_scrape,
            "should_save_file": should_save_file,
            "should_search": should_search,
            "scrape_url": scrape_url,
            "file_path": file_path,
            "scraped_content": state.get("scraped_content", None),
            "search_query": search_query,
            "tools_output": state["tools_output"]
        }
    except Exception as e:
        print(f"Error calling LLM: {e}")
        import traceback
        traceback.print_exc()
        error_msg = f"I encountered an error: {str(e)}"
        return {
            "messages": state["messages"] + [AIMessage(content=error_msg)],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": False,
            "scrape_url": state.get("scrape_url", None),
            "file_path": state.get("file_path", None),
            "scraped_content": state.get("scraped_content", None),
            "search_query": state.get("search_query", None),
            "tools_output": state["tools_output"]
        }

def route_actions(state: AgentState) -> str:
    """Route to the appropriate action based on state flags."""
    print(f"Routing with state: scrape={state['should_scrape']}, save={state['should_save_file']}, search={state['should_search']}")
    
    # If we have scraped content but haven't saved it yet, prioritize saving
    if state["scraped_content"] and not state.get("file_saved", False):
        return "save_file"
    # Otherwise follow the flags
    elif state["should_scrape"]:
        return "scrape_website"
    elif state["should_save_file"]:
        return "save_file"
    elif state["should_search"]:
        return "search_file"
    else:
        return END

def scrape_website_node(state: AgentState) -> AgentState:
    """Execute website scraping"""
    try:
        url = state["scrape_url"]
        if not url:
            result = "No URL provided for scraping."
            content = None
        else:
            result = f"Scraping website: {url}"
            content = scrape_website(url)
            
            # Apply guardrails to scraped content
            guardrailed_content, metadata = apply_guardrails(content)
            if metadata["action"] == "GUARDRAIL_INTERVENED":
                result += f"\nContent was modified by guardrails: {metadata['action']}"
                content = guardrailed_content
            else:
                content = guardrailed_content
        
        # Update state
        return {
            "messages": state["messages"],
            "should_scrape": False,
            "should_save_file": True,  # Suggest saving next
            "should_search": False,
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": content,
            "search_query": state["search_query"],
            "tools_output": state["tools_output"] + [result]
        }
    except Exception as e:
        print(f"Error during website scraping: {e}")
        return {
            "messages": state["messages"],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": False,
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": None,
            "search_query": state["search_query"],
            "tools_output": state["tools_output"] + [f"Error during website scraping: {str(e)}"]
        }

def save_file_node(state: AgentState) -> AgentState:
    """Save content to a file"""
    try:
        content = state["scraped_content"]
        file_path = state["file_path"]
        
        if not content:
            result = "No content to save."
        elif not file_path:
            result = "No file path provided."
        else:
            save_result = save_to_file(content, file_path)
            result = f"File operation: {save_result}"
        
        # Update state
        return {
            "messages": state["messages"],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": True,  # Suggest searching next
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": state["scraped_content"],
            "search_query": state["search_query"],
            "tools_output": state["tools_output"] + [result],
            "file_saved": True  # Mark that we've saved the file
        }
    except Exception as e:
        print(f"Error during file save: {e}")
        return {
            "messages": state["messages"],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": False,
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": state["scraped_content"],
            "search_query": state["search_query"],
            "tools_output": state["tools_output"] + [f"Error during file save: {str(e)}"],
            "file_saved": False
        }

def search_file_node(state: AgentState) -> AgentState:
    """Search within a saved file"""
    try:
        query = state["search_query"]
        file_path = state["file_path"]
        
        if not query:
            result = "No search query provided."
        elif not file_path:
            result = "No file path to search in."
        else:
            search_result = search_text_in_file(query, file_path)
            result = f"Search results for '{query}':\n{search_result}"
            
            # Apply guardrails to search results
            guardrailed_result, metadata = apply_guardrails(result)
            if metadata["action"] == "GUARDRAIL_INTERVENED":
                result = guardrailed_result
        
        # Update state
        return {
            "messages": state["messages"],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": False,
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": state["scraped_content"],
            "search_query": state["search_query"],
            "tools_output": state["tools_output"] + [result]
        }
    except Exception as e:
        print(f"Error during file search: {e}")
        return {
            "messages": state["messages"],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": False,
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": state["scraped_content"],
            "search_query": state["search_query"],
            "tools_output": state["tools_output"] + [f"Error during file search: {str(e)}"]
        }

def generate_final_response(state: AgentState) -> AgentState:
    """Generate final response with all tool results incorporated"""
    # Format messages for the final response
    messages = []
    
    # Add system message with all tool results
    tool_info = "Process information:\n" + "\n".join(state["tools_output"])
    messages.append({
        "role": "system", 
        "content": f"""You are an educational AI assistant. Use the following information to provide a 
        comprehensive answer to the user's question. Based on the information from the website scraping 
        and file search, provide a clear explanation about the topic.
        
        Information from the tools:
        {tool_info}
        """
    })
    
    # Add the original query
    if state["messages"] and isinstance(state["messages"][0], HumanMessage):
        messages.append({"role": "user", "content": state["messages"][0].content})
    
    # Generate response
    try:
        response = llm.invoke(messages)
        
        # Apply guardrails to the final response
        final_content, metadata = apply_guardrails(response.content)
        
        # Update state with final response
        return {
            "messages": state["messages"][:-1] + [AIMessage(content=final_content)],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": False,
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": state["scraped_content"],
            "search_query": state["search_query"],
            "tools_output": state["tools_output"]
        }
    except Exception as e:
        print(f"Error generating final response: {e}")
        error_msg = f"I encountered an error when generating a final response: {str(e)}"
        return {
            "messages": state["messages"][:-1] + [AIMessage(content=error_msg)],
            "should_scrape": False,
            "should_save_file": False,
            "should_search": False,
            "scrape_url": state["scrape_url"],
            "file_path": state["file_path"],
            "scraped_content": state["scraped_content"],
            "search_query": state["search_query"],
            "tools_output": state["tools_output"]
        }

# Build the LangGraph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("llm", call_llm)
workflow.add_node("scrape_website", scrape_website_node)
workflow.add_node("save_file", save_file_node)
workflow.add_node("search_file", search_file_node)
workflow.add_node("generate_final_response", generate_final_response)

# Add edges
workflow.add_edge(START, "scrape_website")  # Start with website scraping
workflow.add_edge("scrape_website", "save_file")  # Then save to file
workflow.add_edge("save_file", "search_file")  # Then search the file
workflow.add_edge("search_file", "generate_final_response")  # Finally generate response
workflow.add_edge("generate_final_response", END)

# Compile the graph
agent_executor = workflow.compile()

# Example usage
def run_agent(query: str):
    """Run the agent with guardrails on user query"""
    # Apply input guardrails
    guardrailed_query, metadata = apply_guardrails(query)
    
    # If content is blocked or needs major modifications
    if metadata["action"] == "GUARDRAIL_INTERVENED":
        print(f"Input was modified by guardrails: {metadata}")
        
        # Check if the query appears to be blocked (contains typical block message)
        if "sorry" in guardrailed_query.lower() or "cannot answer" in guardrailed_query.lower():
            # Extract topic information from metadata if available
            blocked_topics = []
            try:
                assessments = metadata.get("assessments", [])
                for assessment in assessments:
                    topic_policy = assessment.get("topicPolicy", {})
                    topics = topic_policy.get("topics", [])
                    for topic in topics:
                        if topic.get("action") == "BLOCKED":
                            blocked_topics.append(topic.get("name", "Unknown"))
            except Exception:
                pass
            
            topic_str = ", ".join(blocked_topics) if blocked_topics else "Restricted content"
            return {
                "messages": [AIMessage(content=f"This query was blocked by guardrails due to policy restrictions. Detected topic(s): {topic_str}")]
            }
    
    # Set default values for DataCamp example
    initial_state = {
        "messages": [HumanMessage(content=guardrailed_query)],
        "tools_output": [],
        "should_scrape": True,  # Force scraping as the first step
        "should_save_file": False,
        "should_search": False,
        "scrape_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",  # Default URL
        "file_path": "ai.txt",  # Default file path
        "scraped_content": None,
        "search_query": query,  # Use the original query as the search term
        "file_saved": False
    }
    
    # Execute the graph
    result = agent_executor.invoke(initial_state)
    return result

# Command line argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description='LangGraph agent with Bedrock Guardrails')
    parser.add_argument('query', type=str, nargs='?', default=None, 
                        help='The query to process (if not provided, will prompt for input)')
    return parser.parse_args()

# Example execution
if __name__ == "__main__":
    args = parse_arguments()
    
    # Get query from command line arguments or prompt user for input
    if args.query:
        query = args.query
    else:
        query = input("Enter your query: ")
    
    result = run_agent(query)
    
    print("\n\n=== FINAL RESULT ===\n")
    
    # Print only the final assistant message
    for message in result["messages"]:
        if isinstance(message, AIMessage):
            final_message = message
    
    print(final_message.content)