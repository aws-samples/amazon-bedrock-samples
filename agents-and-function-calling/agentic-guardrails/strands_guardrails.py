#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
from typing import Dict, List, Any, Tuple, Optional

# Install required packages:
# pip install strands-agents strands-agents-tools boto3 requests beautifulsoup4

# Set up AWS environment variables BEFORE importing strands
os.environ["AWS_PROFILE"] = "default"
os.environ["AWS_REGION"] = "us-west-2"

# Configure logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)

# Import Strands and built-in tools
from strands import Agent, tool
from strands.models import BedrockModel
import requests
from bs4 import BeautifulSoup
import boto3

# ------------------------
# 1. Configure guardrails
# ------------------------

# Set up Bedrock client
bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "us-west-2")
)

# Set up guardrail config
guardrail_id = "rj98tb9owwv2"  # Replace with your guardrail ID
guardrail_version = "DRAFT"

def apply_guardrails(content):
    # Type: (str) -> Tuple[str, Dict[str, Any]]
    """
    Apply AWS Bedrock Guardrails to content
    
    Args:
        content: Text content to analyze with guardrails
        
    Returns:
        Tuple containing guardrailed content and metadata
    """
    try:
        logging.info(f"Applying guardrail to content: {content[:50]}...")
        
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
        
        # Log the full response for debugging
        import json
        logging.info(f"Full guardrail response: {json.dumps(response, default=str, indent=2)}")
        
        # Parse response
        outputs = response.get('outputs', [])
        if outputs and len(outputs) > 0:
            guardrailed_content = outputs[0].get('text', content)
        else:
            guardrailed_content = content
        
        # Get guardrail action - this is the official way to determine if guardrails intervened
        # GUARDRAIL_INTERVENED - Guardrail modified or blocked the content
        # NONE - Guardrail did not modify or block the content
        action = response.get('action', 'NONE')
        
        # Check if the content was actually changed
        content_changed = guardrailed_content != content
        
        # Log more detailed information
        if action == "GUARDRAIL_INTERVENED":
            logging.info(f"Guardrail intervention details:")
            logging.info(f"- Action: {action}")
            logging.info(f"- Content actually changed: {content_changed}")
            logging.info(f"- Original content length: {len(content)}")
            logging.info(f"- Guardrailed content length: {len(guardrailed_content)}")
            
            # Log specific assessment details
            if 'assessments' in response:
                for idx, assessment in enumerate(response['assessments']):
                    logging.info(f"- Assessment #{idx+1}:")
                    if 'topicPolicy' in assessment:
                        topic_policy = assessment['topicPolicy']
                        if 'topics' in topic_policy:
                            for topic in topic_policy['topics']:
                                logging.info(f"  - Topic: {topic.get('name', 'Unknown')}")
                                logging.info(f"  - Type: {topic.get('type', 'Unknown')}")
                                logging.info(f"  - Action: {topic.get('action', 'Unknown')}")
                    
                    if 'contentPolicy' in assessment:
                        content_policy = assessment['contentPolicy']
                        if 'filters' in content_policy:
                            for filter_item in content_policy['filters']:
                                logging.info(f"  - Filter Type: {filter_item.get('type', 'Unknown')}")
                                logging.info(f"  - Filter Action: {filter_item.get('action', 'Unknown')}")
        
        # Create metadata dictionary with the complete response
        metadata_dict = {
            "action": action,
            "assessments": response.get('assessments', []),
            "content_changed": content_changed
        }
        
        return guardrailed_content, metadata_dict
    
    except Exception as e:
        logging.error(f"Error applying guardrails: {e}")
        import traceback
        traceback.print_exc()
        return content, {"action": "ERROR", "error": str(e), "assessments": []}

# ------------------------
# 2. Define custom tools
# ------------------------

@tool
def scrape_website(url):
    # Type: (str) -> str
    """
    Scrape content from a website URL.
    
    Args:
        url: The URL of the website to scrape
        
    Returns:
        The extracted text content from the website
    """
    try:
        logging.info(f"Scraping website: {url}")
        
        # Set headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        }
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract main content (paragraphs and headers)
        content = ""
        
        # Get all paragraph texts
        for paragraph in soup.find_all("p"):
            content += paragraph.get_text() + "\n\n"
        
        # Get all header texts
        for header in soup.find_all(["h1", "h2", "h3", "h4"]):
            content += header.get_text() + "\n\n"
        
        # Apply guardrails to the content
        guardrailed_content, metadata = apply_guardrails(content)
        
        # Check if guardrail intervened
        if metadata["action"] == "GUARDRAIL_INTERVENED":
            # Extract blocked topics if available
            blocked_topics = []
            try:
                assessments = metadata.get("assessments", [])
                for assessment in assessments:
                    topic_policy = assessment.get("topicPolicy", {})
                    topics = topic_policy.get("topics", [])
                    for topic in topics:
                        if topic.get("action") == "BLOCKED":
                            blocked_topics.append(topic.get("name", "Unknown"))
            except Exception as e:
                logging.error(f"Error extracting blocked topics: {e}")
            
            topic_str = ", ".join(blocked_topics) if blocked_topics else "policy restrictions"
            
            # Check if content was actually changed
            content_unchanged = metadata.get("content_changed", False) == False
            
            # Only log as intervention if content was actually changed
            if content_unchanged:
                logging.info(f"Guardrail flagged but content not actually modified (likely a false positive)")
            else:
                logging.info(f"Content was modified by guardrails. Action: {metadata['action']}")
            
            # If content was completely blocked, return message
            if any(phrase in guardrailed_content.lower() for phrase in ["sorry", "cannot", "unable to"]):
                return f"The content from this website was blocked by guardrails due to {topic_str}."
        
        logging.info(f"Scraped content length: {len(guardrailed_content)} characters")
        return guardrailed_content
    
    except Exception as e:
        logging.error(f"Error scraping website: {e}")
        return f"Error scraping website: {str(e)}"

@tool
def save_to_file(content, filepath):
    # Type: (str, str) -> str
    """
    Save content to a file.
    
    Args:
        content: Text content to save
        filepath: Path where the file should be saved
        
    Returns:
        Status message indicating success or failure
    """
    try:
        logging.info(f"Saving content to file: {filepath}")
        
        # Apply guardrails to the content before saving
        guardrailed_content, metadata = apply_guardrails(content)
        
        # Check if guardrail intervened
        if metadata["action"] == "GUARDRAIL_INTERVENED":
            # Extract blocked topics if available
            blocked_topics = []
            try:
                assessments = metadata.get("assessments", [])
                for assessment in assessments:
                    topic_policy = assessment.get("topicPolicy", {})
                    topics = topic_policy.get("topics", [])
                    for topic in topics:
                        if topic.get("action") == "BLOCKED":
                            blocked_topics.append(topic.get("name", "Unknown"))
            except Exception as e:
                logging.error(f"Error extracting blocked topics: {e}")
            
            topic_str = ", ".join(blocked_topics) if blocked_topics else "policy restrictions"
            logging.info(f"Content was modified by guardrails before saving. Action: {metadata['action']}")
            
            # If content was completely blocked, return message
            if any(phrase in guardrailed_content.lower() for phrase in ["sorry", "cannot", "unable to"]):
                return f"Cannot save the content as it was blocked by guardrails due to {topic_str}."
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Write content to file
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(guardrailed_content)
        
        return f"Successfully saved content to {filepath}"
    
    except Exception as e:
        logging.error(f"Error saving to file: {e}")
        return f"Error saving to file: {str(e)}"

@tool
def search_text(query, filepath):
    # Type: (str, str) -> str
    """
    Search within a text file for relevant information.
    
    Args:
        query: The search term or question to find information about
        filepath: Path to the file to search in
        
    Returns:
        The relevant text found in the file
    """
    try:
        logging.info(f"Searching for '{query}' in file: {filepath}")
        
        # Check if file exists
        if not os.path.exists(filepath):
            return f"Error: File {filepath} not found"
        
        # Apply guardrails to the query
        guardrailed_query, metadata = apply_guardrails(query)
        
        # Check if guardrail intervened
        if metadata["action"] == "GUARDRAIL_INTERVENED":
            # Extract blocked topics if available
            blocked_topics = []
            try:
                assessments = metadata.get("assessments", [])
                for assessment in assessments:
                    topic_policy = assessment.get("topicPolicy", {})
                    topics = topic_policy.get("topics", [])
                    for topic in topics:
                        if topic.get("action") == "BLOCKED":
                            blocked_topics.append(topic.get("name", "Unknown"))
            except Exception as e:
                logging.error(f"Error extracting blocked topics: {e}")
            
            topic_str = ", ".join(blocked_topics) if blocked_topics else "policy restrictions"
            logging.info(f"Query was modified by guardrails. Action: {metadata['action']}")
            
            # If query was completely blocked, return message
            if any(phrase in guardrailed_query.lower() for phrase in ["sorry", "cannot", "unable to"]):
                return f"The search query was blocked by guardrails due to {topic_str}."
        
        # Read file content
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Split content into paragraphs
        paragraphs = content.split("\n\n")
        
        # Find paragraphs containing the query terms
        # Simple search implementation
        results = []
        for paragraph in paragraphs:
            if guardrailed_query.lower() in paragraph.lower():
                results.append(paragraph)
        
        if not results:
            return f"No results found for '{guardrailed_query}' in {filepath}"
        
        # Join results and apply guardrails
        result_text = "\n\n".join(results[:3])  # Limit to first 3 matches
        guardrailed_result, metadata = apply_guardrails(result_text)
        
        # Check if guardrail intervened
        if metadata["action"] == "GUARDRAIL_INTERVENED":
            # Extract blocked topics if available
            blocked_topics = []
            try:
                assessments = metadata.get("assessments", [])
                for assessment in assessments:
                    topic_policy = assessment.get("topicPolicy", {})
                    topics = topic_policy.get("topics", [])
                    for topic in topics:
                        if topic.get("action") == "BLOCKED":
                            blocked_topics.append(topic.get("name", "Unknown"))
            except Exception as e:
                logging.error(f"Error extracting blocked topics: {e}")
            
            topic_str = ", ".join(blocked_topics) if blocked_topics else "policy restrictions"
            logging.info(f"Search results were modified by guardrails. Action: {metadata['action']}")
            
            # If results were completely blocked, return message
            if any(phrase in guardrailed_result.lower() for phrase in ["sorry", "cannot", "unable to"]):
                return f"The search results were blocked by guardrails due to {topic_str}."
        
        return guardrailed_result
    
    except Exception as e:
        logging.error(f"Error searching text: {e}")
        return f"Error searching text: {str(e)}"

# ------------------------
# 3. Set up the agent
# ------------------------

def create_agent():
    # Type: () -> Agent
    """
    Create and configure the Strands Agent
    
    Returns:
        Configured Strands Agent instance
    """
    # Configure the Bedrock model with guardrails
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",  # Use Claude 3.5 Haiku
        region_name=os.environ.get("AWS_REGION", "us-west-2"),
        temperature=0.7,
        guardrail_config={
            "guardrailIdentifier": guardrail_id,
            "guardrailVersion": guardrail_version,
            "trace": "enabled"
        }
    )
    
    # Create the agent with our tools
    agent = Agent(
        model=bedrock_model,
        tools=[scrape_website, save_to_file, search_text],
        # System prompt that defines the agent's behavior
        system_prompt="""You are an Educational AI Assistant that helps users find and process information.
        
        You have access to the following tools:
        1. scrape_website: Extracts text content from a website URL
        2. save_to_file: Saves content to a file
        3. search_text: Searches within a saved file for specific information
        
        Your workflow should follow these steps:
        1. When asked about a topic, first use scrape_website to gather information
        2. Save the scraped content to a file using save_to_file
        3. Use search_text to find specific answers within the saved content
        4. Provide a comprehensive and educational response
        
        Always be thorough and educational in your explanations.
        """
    )
    
    return agent

# ------------------------
# 4. Main Execution
# ------------------------

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Strands Agent with Bedrock Guardrails")
    parser.add_argument(
        "query", 
        type=str, 
        nargs="?", 
        default=None,
        help="The query to process (if not provided, will prompt for input)"
    )
    return parser.parse_args()

def run_agent(query):
    # Type: (str) -> str
    """
    Run the agent with the given query
    
    Args:
        query: User's question or instruction
        
    Returns:
        The agent's response
    """
    # Apply guardrails to the input query
    guardrailed_query, metadata = apply_guardrails(query)
    
    # Check if guardrail intervened
    if metadata["action"] == "GUARDRAIL_INTERVENED":
        logging.info(f"Input was modified by guardrails: {metadata}")
        
        # Extract blocked topics if available
        blocked_topics = []
        try:
            assessments = metadata.get("assessments", [])
            for assessment in assessments:
                topic_policy = assessment.get("topicPolicy", {})
                topics = topic_policy.get("topics", [])
                for topic in topics:
                    if topic.get("action") == "BLOCKED":
                        blocked_topics.append(topic.get("name", "Unknown"))
        except Exception as e:
            logging.error(f"Error extracting blocked topics: {e}")
        
        topic_str = ", ".join(blocked_topics) if blocked_topics else "Restricted content"
        
        # If query was completely blocked, return message
        if any(phrase in guardrailed_query.lower() for phrase in ["sorry", "cannot", "unable to"]):
            return f"This query was blocked by guardrails due to policy restrictions. Detected topic(s): {topic_str}"
    
    # Create the agent
    agent = create_agent()
    
    # Modify the query to ensure it follows our scrape-save-search workflow
    enhanced_query = f"""
    Process the following request: {guardrailed_query}
    
    Follow these steps:
    1. First scrape information from Wikipedia or another relevant site about this topic
    2. Save the information to a file called 'information.txt'
    3. Search within the file for the most relevant details
    4. Provide a comprehensive answer
    """
    
    # Execute the agent
    try:
        response = agent(enhanced_query)
        return response
    except Exception as e:
        logging.error(f"Error executing agent: {e}")
        return f"An error occurred: {str(e)}"

if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_arguments()
    
    # Get query from command-line arguments or prompt for input
    if args.query:
        query = args.query
    else:
        query = input("Enter your query: ")
    
    # Run the agent
    result = run_agent(query)
    
    # Display the result
    print("\n\n=== FINAL RESULT ===\n")
    print(result)