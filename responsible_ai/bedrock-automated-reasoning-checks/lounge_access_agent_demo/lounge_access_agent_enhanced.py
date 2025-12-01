"""
Enhanced Airport Lounge Access Agent with Automated Reasoning Guardrails
Implements selective guardrail triggering and passenger context extraction
"""

import os
import json
import re
from typing import Dict, Any
from datetime import datetime
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands.hooks import HookProvider, HookRegistry, MessageAddedEvent

# Import passenger data tools
from passenger_data_tools import (
    lookup_passenger_by_ff_number,
    lookup_passenger_by_name,
    check_star_alliance_gold_status,
    check_paid_lounge_membership,
    get_passenger_flight_history,
    calculate_tier_qualification_progress,
    validate_lounge_access_eligibility
)

import logging
logger = logging.getLogger(__name__)

# Get environmental variables
GUARDRAIL_ID = os.getenv("GUARDRAIL_ID")
GUARDRAIL_VERSION = os.getenv("GUARDRAIL_VERSION", "DRAFT")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")
MODEL_ID = os.getenv("MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

# Create a session object (this will pick up credentials and region from your environment/config)
SESSION = boto3.session.Session()

# Get the region name from the session, with a fallback default
CURRENT_REGION = SESSION.region_name or AWS_DEFAULT_REGION
logger.info(f"Region set to : {CURRENT_REGION}")

@tool
def retrieve_lounge_information(
    query: str,
    knowledge_base_id: str = KNOWLEDGE_BASE_ID,
    max_results: int = 5,
    region_name: str = CURRENT_REGION
) -> Dict[str, Any]:
    """
    Retrieve information from the Bedrock Knowledge Base about airport lounges, policies, and procedures.
    
    This tool queries the comprehensive lounge documentation including access policies, amenities, 
    dining options, business facilities, and frequently asked questions.
    
    Args:
        query: Natural language query about lounge access, amenities, policies, or procedures
        knowledge_base_id: Knowledge Base ID to query (optional)  
        max_results: Maximum number of results to return (1-10, default: 5)
        region_name: The AWS region to use
        
    Returns:
        Dictionary containing query results, metadata, and success status
    """
    try:
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region_name)
        
        # Validate inputs
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Query parameter is required and cannot be empty",
                "results": [],
                "query": query
            }
        
        # Clamp max_results to valid range
        max_results = max(1, min(max_results, 10))
            
        # Execute knowledge base retrieval
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results,
                    'overrideSearchType': 'HYBRID'  # Use both semantic and keyword search
                }
            }
        )
        
        # Process and format results
        formatted_results = []
        for result in response.get('retrievalResults', []):
            content_text = result.get('content', {}).get('text', '')
            formatted_result = {
                "content": content_text,
                "relevance_score": result.get('score', 0),
                "metadata": result.get('metadata', {}),
                "location": result.get('location', {})
            }
            formatted_results.append(formatted_result)
        
        # Sort by relevance score (highest first)
        formatted_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "timestamp": datetime.now().isoformat(),
            "knowledge_base_id": knowledge_base_id
        }
        
    except Exception as e:
        logger.error(f"Error executing knowledge base query: {e}")
        return {
            "success": False,
            "error": f"Knowledge base query failed: {str(e)}",
            "results": [],
            "query": query,
            "timestamp": datetime.now().isoformat()
        }


class EnhancedGuardrailsHook(HookProvider):
    """
    Enhanced Guardrail Hook that:
    1. Only triggers on agent responses that include validate_lounge_access_eligibility tool usage
    2. Includes passenger context extracted from tool results
    3. Passes comprehensive passenger variables to the Automated Reasoning policy
    """
    
    def __init__(self, guardrail_id: str, guardrail_version: str, region_name: str = CURRENT_REGION):
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.region_name = region_name
        self.bedrock_client = boto3.client("bedrock-runtime", region_name=region_name)
        
        # Store message history and tool usage tracking
        self.message_history = []
        self.recent_tool_results = {}
        self.validate_eligibility_used = False
        
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self.process_message)
    
    def detect_validate_eligibility_tool_usage(self, content: str) -> bool:
        """
        Detect if validate_lounge_access_eligibility tool was used in the message
        """
        # Look for the tool call pattern in the message content
        tool_patterns = [
            r"validate_lounge_access_eligibility",
            r"validate.*eligibility", 
            r"Comprehensive lounge access eligibility validation",
            r'"tool_name":\s*"validate_lounge_access_eligibility"',
            r"I'll check your lounge access eligibility",
            r"checking.*eligibility",
            r"eligibility.*validated",
            r"access eligibility.*check",
            r"Tool #\d+: validate_lounge_access_eligibility",
            r"Now let me validate your lounge access eligibility"
        ]
        
        content_lower = content.lower()
        tool_detected = any(re.search(pattern, content_lower) for pattern in tool_patterns)
        
        # Also set the flag if we detect the tool usage
        if tool_detected:
            self.validate_eligibility_used = True
            print(f"[ENHANCED_GUARDRAIL] Tool validate_lounge_access_eligibility detected in content!")
        
        return tool_detected
    
    def extract_passenger_context_from_tool_results(self) -> Dict[str, Any]:
        """
        Extract passenger context from validate_lounge_access_eligibility tool results
        and message history
        """
        context = {
            "passenger_details": {},
            "flight_details": {},
            "eligibility_factors": {},
            "tool_results": self.recent_tool_results,
            "conversation_context": []
        }
        
        # Extract from recent tool results if available
        if "validate_lounge_access_eligibility" in self.recent_tool_results:
            tool_result = self.recent_tool_results["validate_lounge_access_eligibility"]
            
            # Extract passenger data from tool result
            passenger_data = tool_result.get("passenger_data", {})
            if passenger_data:
                context["passenger_details"]["frequent_flier_number"] = passenger_data.get("frequent_flier_number", "")
                context["passenger_details"]["name"] = passenger_data.get("name", "")
                context["passenger_details"]["tier_status"] = passenger_data.get("tier_status", "")
                context["passenger_details"]["airline"] = passenger_data.get("airline", "")
                context["passenger_details"]["total_miles"] = passenger_data.get("total_miles", 0)
            
            # Extract Gold status info
            gold_status = tool_result.get("gold_status", {})
            if gold_status:
                context["eligibility_factors"]["gold_status"] = gold_status.get("has_status", False)
                context["eligibility_factors"]["status_level"] = gold_status.get("status_level", "")
                context["eligibility_factors"]["companion_passes"] = gold_status.get("companion_passes", 0)
            
            # Extract eligibility decision
            context["eligibility_factors"]["eligible"] = tool_result.get("eligible", False)
            context["eligibility_factors"]["access_type"] = tool_result.get("access_type", "")
            context["eligibility_factors"]["reason"] = tool_result.get("reason", "")
        
        # Extract additional information from message history
        for message in self.message_history:
            content = message.get('content', '')
            role = message.get('role', '')
            
            # Extract frequent flier numbers
            ff_numbers = re.findall(r'\b([A-Z]{2}\d{8,9})\b', content)
            if ff_numbers and not context["passenger_details"].get("frequent_flier_numbers"):
                context["passenger_details"]["frequent_flier_numbers"] = ff_numbers
            
            # Extract flight information
            flight_numbers = re.findall(r'\b([A-Z]{2}\d{3,4})\b', content)
            if flight_numbers:
                context["flight_details"]["flight_numbers"] = flight_numbers
            
            # Extract class of service mentions
            class_mentions = re.findall(r'\b(First Class|Business Class|Premium Economy|Economy)\b', content, re.IGNORECASE)
            if class_mentions:
                context["flight_details"]["class_mentions"] = class_mentions
            
            # Store conversation context (limited)
            context["conversation_context"].append({
                "role": role,
                "content": content[:150],  # First 150 chars
                "timestamp": datetime.now().isoformat()
            })
        
        return context
    
    def extract_policy_variables_from_context(self, passenger_context: Dict[str, Any], message_content: str) -> Dict[str, Any]:
        """
        Extract variables needed for the Automated Reasoning policy from passenger context
        """
        variables = {
            # Passenger identification
            "passenger_frequent_flier_numbers": passenger_context.get("passenger_details", {}).get("frequent_flier_numbers", []),
            "passenger_names": passenger_context.get("passenger_details", {}).get("names", []),
            
            # Flight details
            "flight_numbers": passenger_context.get("flight_details", {}).get("flight_numbers", []),
            "class_of_service": passenger_context.get("flight_details", {}).get("class_mentions", []),
            
            # Status and eligibility factors
            "membership_status": passenger_context.get("eligibility_factors", {}).get("status_mentions", []),
            "access_decision_terms": passenger_context.get("eligibility_factors", {}).get("access_mentions", []),
            
            # Message analysis
            "response_contains_eligibility": self.detect_validate_eligibility_tool_usage(message_content),
            "message_length": len(message_content),
            "timestamp": datetime.now().isoformat(),
            
            # Extracted policy-relevant information
            "mentioned_lounges": [],
            "mentioned_airlines": [],
            "mentioned_airports": []
        }
        
        # Extract lounge names
        lounge_patterns = [
            r"\b(United Club|Star Alliance|Polaris|Lufthansa|Air Canada Maple Leaf|British Airways)\s*(?:Lounge|Club)\b",
            r"\b([A-Z][a-z]+\s+(?:Lounge|Club))\b"
        ]
        for pattern in lounge_patterns:
            matches = re.findall(pattern, message_content, re.IGNORECASE)
            variables["mentioned_lounges"].extend(matches)
        
        # Extract airline names
        airline_pattern = r"\b(United Airlines|Lufthansa|Air Canada|British Airways|Singapore Airlines|Thai Airways)\b"
        airline_matches = re.findall(airline_pattern, message_content, re.IGNORECASE)
        variables["mentioned_airlines"] = airline_matches
        
        # Extract airport codes
        airport_pattern = r"\b([A-Z]{3})\b"
        airport_matches = re.findall(airport_pattern, message_content)
        variables["mentioned_airports"] = airport_matches
        
        return variables
    
    def evaluate_content_with_context(self, content: str, source: str = "INPUT"):
        """
        Enhanced content evaluation that only triggers guardrails when validate_lounge_access_eligibility tool is used
        """
        print(f"[ENHANCED_GUARDRAIL] [evaluate_content]: source: {source}, content length: {len(content)}")
        
        if source == "INPUT":
            # Store input for context and reset tool usage tracking
            self.message_history.append({"role": "user", "content": content})
            self.validate_eligibility_used = False
            self.recent_tool_results = {}
            return
        
        # For OUTPUT messages, first detect if validate_lounge_access_eligibility tool was used
        if source == "OUTPUT":
            tool_detected = self.detect_validate_eligibility_tool_usage(content)
            if not tool_detected:
                return None
        
        # Only process OUTPUT messages when validate_eligibility tool is detected
        if source == "OUTPUT" and self.validate_eligibility_used:
            print(f"[ENHANCED_GUARDRAIL] Tool usage flag set, applying guardrail validation...")
            
            # Extract tool results from message content (simplified for this implementation)
            # In a real implementation, this would capture actual tool execution results
            self._extract_tool_results_from_content(content)
            
            # Extract comprehensive passenger context from tool results and history
            passenger_context = self.extract_passenger_context_from_tool_results()
            
            # Extract policy variables
            policy_variables = self.extract_policy_variables_from_context(passenger_context, content)
            
            # Get the most recent user input for context
            recent_input = ""
            for msg in reversed(self.message_history):
                if msg.get("role") == "user":
                    recent_input = msg.get("content", "")
                    break
            
            # Create enriched query with passenger context embedded
            enriched_query = f"""User Query: {recent_input}

Passenger Context for Policy Evaluation:
{json.dumps(passenger_context, indent=2)}

Policy Variables Extracted:
{json.dumps(policy_variables, indent=2)}

Tool Used: validate_lounge_access_eligibility"""

            # Create content for guardrail validation using only valid qualifiers
            content_to_validate = [
                {
                    "text": {
                        "text": enriched_query, 
                        "qualifiers": ["query"]
                    }
                },
                {
                    "text": {
                        "text": content, 
                        "qualifiers": ["guard_content"]
                    }
                }
            ]
            
            print(f"[ENHANCED_GUARDRAIL] Applying guardrail with embedded passenger context:")
            print(f"[ENHANCED_GUARDRAIL] - Tool detected: validate_lounge_access_eligibility")
            print(f"[ENHANCED_GUARDRAIL] - Policy variables: {len(policy_variables)} items")
            print(f"[ENHANCED_GUARDRAIL] - Passenger context: {len(passenger_context)} sections")
            print(f"[ENHANCED_GUARDRAIL] - Enriched query length: {len(enriched_query)} chars")
            
            try:
                response = self.bedrock_client.apply_guardrail(
                    guardrailIdentifier=self.guardrail_id,
                    guardrailVersion=self.guardrail_version,
                    source="OUTPUT",
                    content=content_to_validate
                )
                
                print(f"[ENHANCED_GUARDRAIL] Guardrail response: {response.get('action', 'UNKNOWN')} - {response.get('actionReason', 'No reason provided')}")
                
                # Print the complete guardrail response for analysis
                print(f"[ENHANCED_GUARDRAIL] ========== COMPLETE GUARDRAIL RESPONSE ==========")
                print(json.dumps(response, indent=2, default=str))
                print(f"[ENHANCED_GUARDRAIL] ================================================")
                
                # Specifically extract and display automatedReasoningPolicy findings
                if response.get('assessments'):
                    print(f"[ENHANCED_GUARDRAIL] ========== AUTOMATED REASONING FINDINGS ==========")
                    for i, assessment in enumerate(response.get('assessments', [])):
                        print(f"[ENHANCED_GUARDRAIL] Assessment {i + 1}:")
                        
                        # Look for automatedReasoningPolicy findings
                        if 'automatedReasoningPolicy' in assessment:
                            ar_policy = assessment['automatedReasoningPolicy']
                            print(f"[ENHANCED_GUARDRAIL] Automated Reasoning Policy Results:")
                            print(json.dumps(ar_policy, indent=4, default=str))
                        
                        # Log processing metrics
                        if assessment.get('invocationMetrics'):
                            metrics = assessment['invocationMetrics']
                            print(f"[ENHANCED_GUARDRAIL] Processing latency: {metrics.get('guardrailProcessingLatency', 0)}ms")
                    
                    print(f"[ENHANCED_GUARDRAIL] ==============================================")
                else:
                    print(f"[ENHANCED_GUARDRAIL] No assessments found in guardrail response")
                
                return response
                
            except Exception as e:
                print(f"[ENHANCED_GUARDRAIL] Error applying guardrail: {str(e)}")
                return None
        else:
            # For messages without validate_lounge_access_eligibility tool usage, just log
            print(f"[ENHANCED_GUARDRAIL] No validate_lounge_access_eligibility tool usage detected, skipping guardrail validation")
            return None
    
    def _extract_tool_results_from_content(self, content: str):
        """
        Extract tool results from message content (simplified implementation)
        In a real implementation, this would hook into the actual tool execution
        """
        # Look for patterns that indicate tool results in the content
        if "eligible" in content.lower() and ("lounge access" in content.lower() or "access" in content.lower()):
            # Mock tool result for demonstration
            self.recent_tool_results["validate_lounge_access_eligibility"] = {
                "eligible": "eligible" in content.lower() and "not eligible" not in content.lower(),
                "reason": "Extracted from content analysis",
                "access_type": "Detected from response",
                "passenger_data": {},
                "gold_status": {},
                "paid_membership": {}
            }
    
    def process_message(self, event: MessageAddedEvent) -> None:
        """Process messages and maintain context"""
        print(f'[ENHANCED_GUARDRAIL] [process_message] Processing message from: {event.message.get("role")}')
        
        if event.message.get("role") == "user":
            content = "".join(block.get("text", "") for block in event.message.get("content", []))
            if content:
                self.evaluate_content_with_context(content, "INPUT")
        
        elif event.message.get("role") == "assistant":
            content = "".join(block.get("text", "") for block in event.message.get("content", []))
            if content:
                # Add to message history for context
                self.message_history.append({"role": "assistant", "content": content})
                # Evaluate content with guardrails
                self.evaluate_content_with_context(content, "OUTPUT")


def create_enhanced_lounge_agent(guardrail_id: str = GUARDRAIL_ID, guardrail_version: str = GUARDRAIL_VERSION, model_id: str = MODEL_ID) -> Agent:
    """
    Create an enhanced lounge access agent with selective guardrail triggering
    """
    
    # Create Bedrock model
    bedrock_model = BedrockModel(
        model_id=model_id,
        max_tokens=64000,
        additional_request_fields={
            "thinking": {
                "type": "disabled",
            }
        },
    )
    
    # System prompt
    system_prompt = """
    You are a professional Airport Lounge Access Agent. You help passengers determine their 
    lounge access eligibility and provide information about lounge amenities and policies.

    IMPORTANT TOOLS AVAILABLE:
    - lookup_passenger_by_ff_number: Look up passenger by frequent flier number
    - lookup_passenger_by_name: Look up passenger by name  
    - check_star_alliance_gold_status: Check Gold status and benefits
    - check_paid_lounge_membership: Check paid lounge memberships
    - validate_lounge_access_eligibility: Comprehensive eligibility check
    - get_passenger_flight_history: Get recent flight history
    - calculate_tier_qualification_progress: Check tier progress
    - retrieve_lounge_information: Query lounge knowledge base

    USAGE GUIDELINES:
    1. Always use tools to look up passenger data when provided with FF numbers or names
    2. Use validate_lounge_access_eligibility for comprehensive lounge access decisions
    3. Use retrieve_lounge_information to answer questions about lounge amenities, policies, or procedures
    4. Be helpful, accurate, and professional in all responses
    5. Clearly explain lounge access rules and any restrictions

    When making eligibility decisions, always provide:
    - Clear eligibility status (eligible/not eligible)
    - Specific reasons for the decision
    - Passenger details that were considered
    - Alternative options if access is denied
    """
    
    # Create agent with enhanced guardrail hook
    agent = Agent(
        system_prompt=system_prompt,
        model=bedrock_model,
        tools=[
            lookup_passenger_by_ff_number,
            lookup_passenger_by_name,
            check_star_alliance_gold_status,
            check_paid_lounge_membership,
            validate_lounge_access_eligibility,
            get_passenger_flight_history,
            calculate_tier_qualification_progress,
            retrieve_lounge_information
        ],
        hooks=[EnhancedGuardrailsHook(guardrail_id, guardrail_version)]
    )
    
    return agent

def create_enhanced_lounge_agent_without_guardrail(model_id: str = MODEL_ID) -> Agent:
    """
    Create an enhanced lounge access agent with selective guardrail triggering
    """
    
    # Create Bedrock model
    bedrock_model = BedrockModel(
        model_id=model_id,
        max_tokens=64000,
        additional_request_fields={
            "thinking": {
                "type": "disabled",
            }
        },
    )
    
    # System prompt
    system_prompt = """
    You are a professional Airport Lounge Access Agent. You help passengers determine their 
    lounge access eligibility and provide information about lounge amenities and policies.

    IMPORTANT TOOLS AVAILABLE:
    - lookup_passenger_by_ff_number: Look up passenger by frequent flier number
    - lookup_passenger_by_name: Look up passenger by name  
    - check_star_alliance_gold_status: Check Gold status and benefits
    - check_paid_lounge_membership: Check paid lounge memberships
    - validate_lounge_access_eligibility: Comprehensive eligibility check
    - get_passenger_flight_history: Get recent flight history
    - calculate_tier_qualification_progress: Check tier progress
    - retrieve_lounge_information: Query lounge knowledge base

    USAGE GUIDELINES:
    1. Always use tools to look up passenger data when provided with FF numbers or names
    2. Use validate_lounge_access_eligibility for comprehensive lounge access decisions
    3. Use retrieve_lounge_information to answer questions about lounge amenities, policies, or procedures
    4. Be helpful, accurate, and professional in all responses
    5. Clearly explain lounge access rules and any restrictions

    When making eligibility decisions, always provide:
    - Clear eligibility status (eligible/not eligible)
    - Specific reasons for the decision
    - Passenger details that were considered
    - Alternative options if access is denied
    """
    
    # Create agent with enhanced guardrail hook
    agent = Agent(
        system_prompt=system_prompt,
        model=bedrock_model,
        tools=[
            lookup_passenger_by_ff_number,
            lookup_passenger_by_name,
            check_star_alliance_gold_status,
            check_paid_lounge_membership,
            validate_lounge_access_eligibility,
            get_passenger_flight_history,
            calculate_tier_qualification_progress,
            retrieve_lounge_information
        ]
    )
    
    return agent


def test_enhanced_agent():
    """Test the enhanced agent with guardrail functionality"""
    
    print("Creating enhanced lounge access agent...")
    agent = create_enhanced_lounge_agent(GUARDRAIL_ID, GUARDRAIL_VERSION)
    
    # Test queries
    test_queries = [
        "Check lounge access for frequent flier number UA123456789 flying First Class internationally",
        "What dining options are available in the lounge?",
        "Look up passenger LH987654321 and check their Gold status",
        "Can United domestic First Class passengers access the lounge?",
        "What are the lounge operating hours?"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test Query {i}: {query}")
        print('='*60)
        
        try:
            response = agent(query)
            print(f"Response: {response}")
            
        except Exception as e:
            print(f"Error processing query: {e}")
            
    print(f"\n{'='*60}")
    print("Enhanced Strands agent with selective guardrail testing completed")
    print('='*60)


if __name__ == "__main__":
    test_enhanced_agent()
