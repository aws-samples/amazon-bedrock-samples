import os
import sys
import argparse
from typing import Dict, List, Any, Tuple
import json

# AWS SDK
import boto3
from botocore.config import Config

# CrewAI imports
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# New tool imports from DataCamp example
from crewai_tools import ScrapeWebsiteTool, FileWriterTool, TXTSearchTool

# Set environment variables for AWS credentials
os.environ["AWS_REGION_NAME"] = "us-west-2"
# Make sure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are already set in your environment

# Set up Bedrock client with appropriate configuration
bedrock_config = Config(
    region_name="us-west-2",
    retries={"max_attempts": 3, "mode": "standard"}
)

# Set up guardrail config
guardrail_id = "rj98tb9owwv2"
guardrail_version = "DRAFT"

# Function to apply Bedrock Guardrails to content directly
def apply_guardrails(content: str) -> Tuple[str, Dict]:
    """Apply AWS Bedrock Guardrails to content"""
    try:
        print(f"Applying guardrail to content: {content[:50]}...")
        
        bedrock_client = boto3.client(
            "bedrock-runtime",
            config=bedrock_config,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        
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

# Set up Bedrock LLM with CrewAI's LLM class
llm = LLM(
    model="bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
    temperature=0.7,
)

# Initialize website scraping tool with guardrails
@tool
def scrape_website(url: str) -> str:
    """Scrape content from a website URL."""
    try:
        # Initialize the scraping tool
        scrape_tool = ScrapeWebsiteTool(website_url=url)
        
        # Extract the text
        text = scrape_tool.run()
        
        # Apply guardrails to the scraped content
        guardrailed_content, metadata = apply_guardrails(text)
        
        # Check if guardrail blocked the content
        if metadata["action"] == "GUARDRAIL_INTERVENED":
            if "sorry" in guardrailed_content.lower() or "cannot answer" in guardrailed_content.lower():
                return "The scraped content was blocked by guardrails. Please try a different website."
            
        return guardrailed_content
    except Exception as e:
        return f"Scraping error: {str(e)}"

# Initialize file writer tool
@tool
def save_to_file(filename: str, content: str, directory: str = "") -> str:
    """Save content to a file."""
    try:
        # Initialize the file writer tool
        file_writer_tool = FileWriterTool()
        
        # Apply guardrails to the content before saving
        guardrailed_content, metadata = apply_guardrails(content)
        
        # Write content to file
        result = file_writer_tool._run(filename=filename, content=guardrailed_content, directory=directory)
        
        return result
    except Exception as e:
        return f"File writing error: {str(e)}"

# Initialize text search tool with guardrails
@tool
def search_text(query: str, txt_file: str) -> str:
    """Search within a text file for relevant information."""
    try:
        # Initialize the text search tool
        search_tool = TXTSearchTool(txt=txt_file)
        
        # Apply guardrails to the query
        guardrailed_query, metadata = apply_guardrails(query)
        
        # Check if guardrail blocked the query
        if metadata["action"] == "GUARDRAIL_INTERVENED":
            if "sorry" in guardrailed_query.lower() or "cannot answer" in guardrailed_query.lower():
                return "The search query was blocked by guardrails. Please try a different query."
        
        # Perform the search
        result = search_tool.run(guardrailed_query)
        
        # Apply guardrails to the search result
        guardrailed_result, metadata = apply_guardrails(result)
        
        return guardrailed_result
    except Exception as e:
        return f"Text search error: {str(e)}"

# Define CrewAI Agent based on DataCamp example
data_analyst_agent = Agent(
    role="Educator",
    goal="Analyze information and provide comprehensive answers based on the given context",
    backstory="You are a data expert who can take raw information and turn it into insightful, well-organized responses.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[scrape_website, save_to_file, search_text]
)

# Function to run the Crew with input query
def run_agent(query: str):
    """Run the CrewAI agent with the input query"""
    # Apply guardrails to the query
    guardrailed_query, metadata = apply_guardrails(query)
    
    # Check if guardrail has blocked the query
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
            return f"This query was blocked by guardrails due to policy restrictions. Detected topic(s): {topic_str}"
    
    # Create task
    analysis_task = Task(
        description=f"Understand and answer the query: {guardrailed_query}",
        expected_output="A comprehensive, well-structured response that addresses the original query.",
        agent=data_analyst_agent
    )
    
    # Create a crew with the analysis task
    analysis_crew = Crew(
        agents=[data_analyst_agent],
        tasks=[analysis_task],
        verbose=True,
        process=Process.sequential
    )
    
    # Run the crew
    print("Running analysis task...")
    try:
        final_result = analysis_crew.kickoff()
        
        # Apply guardrails to the final result
        guardrailed_result, result_metadata = apply_guardrails(str(final_result))
        
        # Check if guardrail blocked the result
        if result_metadata["action"] == "GUARDRAIL_INTERVENED":
            if "sorry" in guardrailed_result.lower() or "cannot answer" in guardrailed_result.lower():
                return "The response was blocked by guardrails due to policy restrictions."
        
        return guardrailed_result
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        return f"An error occurred: {str(e)}"

# Command line argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description='CrewAI agent with Bedrock Guardrails')
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
    print(result)