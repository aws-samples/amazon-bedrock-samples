"""
Streamlit Demo for Airport Lounge Access Agent with Automated Reasoning
This demo showcases the complete workflow and Automated Reasoning safeguards
"""

import boto3
import streamlit as st
import json
import os
import re
import traceback
from typing import Dict, Any, List
from datetime import datetime
from botocore.config import Config as BotocoreConfig

from lounge_access_agent_enhanced import create_enhanced_lounge_agent, create_enhanced_lounge_agent_without_guardrail
from boarding_pass_validator import create_sample_boarding_passes
from flight_status_service import create_sample_flight_queries
from policy_engine import create_test_scenarios


# Capture environmental variables
GUARDRAIL_ID = os.getenv("GUARDRAIL_ID")
GUARDRAIL_VERSION = os.getenv("GUARDRAIL_VERSION", "DRAFT")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")
MODEL_ID = os.getenv("MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

# Get the current region
SESSION = boto3.session.Session()
CURRENT_REGION = SESSION.region_name or AWS_DEFAULT_REGION

# Page configuration
st.set_page_config(
    page_title="Airport Lounge Access Agent Demo",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = create_enhanced_lounge_agent(
        guardrail_id=GUARDRAIL_ID,
        guardrail_version=GUARDRAIL_VERSION
    )
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

def main():
    st.title("🛫 Airport Lounge Access Agent with Automated Reasoning")
    st.markdown("### AWS re:Invent 2025 Workshop Demo")
    
    # Sidebar for navigation and configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Agent status
        with st.expander("Agent Status", expanded=False):
            st.json({
                "agent_type": "Enhanced Lounge Access Agent",
                "model": MODEL_ID,
                "guardrail_id": GUARDRAIL_ID,
                "knowledge_base_id": KNOWLEDGE_BASE_ID,
                "tools_available": [
                    "lookup_passenger_by_ff_number",
                    "lookup_passenger_by_name", 
                    "check_star_alliance_gold_status",
                    "check_paid_lounge_membership",
                    "validate_lounge_access_eligibility",
                    "get_passenger_flight_history",
                    "calculate_tier_qualification_progress",
                    "retrieve_lounge_information"
                ],
                "enhanced_guardrails": "Active - triggers on validate_lounge_access_eligibility"
            })
        
        st.header("🎯 Demo Scenarios")
        demo_mode = st.selectbox(
            "Choose Demo Mode:",
            [
                "Interactive Chat",
                "Boarding Pass Analysis", 
                "Automated Reasoning Showcase",
                "Knowledge Base Queries"
            ]
        )
    
    # Main content area
    if demo_mode == "Interactive Chat":
        show_interactive_chat()
    elif demo_mode == "Boarding Pass Analysis":
        show_boarding_pass_analysis()
    elif demo_mode == "Automated Reasoning Showcase":
        show_automated_reasoning_showcase()
    elif demo_mode == "Knowledge Base Queries":
        show_knowledge_base_queries()

def show_interactive_chat():
    """Interactive chat interface with the agent"""
    
    st.header("💬 Interactive Chat")
    st.markdown("Chat with the Airport Lounge Access Agent. You can ask questions, provide boarding pass information, or request lounge details.")
    
    # Chat interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Conversation")
        
        # Display conversation history
        if st.session_state.conversation_history:
            for i, exchange in enumerate(st.session_state.conversation_history):
                with st.chat_message("user"):
                    st.write(exchange["user"])
                with st.chat_message("assistant"):
                    # Display the final message (could be original or rewritten)
                    if exchange.get("rewritten_response"):
                        st.success("✅ **Response validated and corrected by Automated Reasoning:**")
                        st.write(exchange["rewritten_response"])
                        
                        # Show original vs rewritten comparison
                        with st.expander("🔍 See Original Response vs AR Corrected", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Original Response:**")
                                st.info(exchange["assistant"])
                            with col2:
                                st.markdown("**AR Corrected Response:**")
                                st.success(exchange["rewritten_response"])
                    else:
                        st.write(exchange["assistant"])
                    
                    # Show guardrail status
                    if exchange.get("guardrail_invoked"):
                        if exchange.get("ar_findings"):
                            st.warning(f"🛡️ **Guardrails Triggered**: {exchange['ar_findings']}")
                        else:
                            st.info("🛡️ **Guardrails Applied**: Eligibility validation performed")
                    
                    # Show AR findings if available
                    if exchange.get("ar_findings") and exchange["ar_findings"] != "No violations found":
                        with st.expander("🧠 Automated Reasoning Findings", expanded=False):
                            st.text(exchange["ar_findings"])
                    
                    # Show processing steps if available
                    if exchange.get("processing_steps"):
                        with st.expander("Processing Steps", expanded=False):
                            for step in exchange["processing_steps"]:
                                st.text(step)
                                
                st.divider()
        
        # Chat input
        user_input = st.chat_input("Type your message here...")
        
        if user_input:
            # Process user input with Strands agent
            with st.spinner("Processing your request..."):
                try:
                    # Get the agent response
                    agent_result = st.session_state.agent(user_input)
                    
                    # Extract just the message content from AgentResult
                    if hasattr(agent_result, 'content'):
                        # Handle Strands AgentResult format
                        message_content = ""
                        for content_block in agent_result.content:
                            if hasattr(content_block, 'text'):
                                message_content += content_block.text
                            elif isinstance(content_block, dict) and 'text' in content_block:
                                message_content += content_block['text']
                            else:
                                message_content += str(content_block)
                    else:
                        # Fallback for string responses
                        message_content = str(agent_result)
                    
                    # Check if guardrails were invoked (this will be captured via logging)
                    # For now, we'll simulate this - in real implementation, this would come from the hook
                    guardrail_invoked = "validate_lounge_access_eligibility" in message_content.lower() or \
                                      "eligibility" in message_content.lower() and "lounge" in message_content.lower()
                    
                    # Add to conversation history
                    exchange = {
                        "user": user_input,
                        "assistant": message_content,
                        "guardrail_invoked": guardrail_invoked,
                        "ar_findings": None,  # Will be populated by hook if available
                        "rewritten_response": None,
                        "processing_steps": [],
                        "result": {"conversation_response": message_content}
                    }
                    st.session_state.conversation_history.append(exchange)
                except Exception as e:
                    st.error(f"Error processing request: {str(e)}")
            st.rerun()
    
    with col2:
        st.subheader("Quick Actions")
        
        # Sample queries
        st.markdown("**Try these sample queries:**")
        
        sample_queries = [
            "I'm flying UA1234 in First Class, do I have lounge access?",
            "What amenities are available in the lounge?",
            "I'm a Star Alliance Gold member on LH441",
            "Can my guest enter the lounge with me?"
        ]
        
        for query in sample_queries:
            if st.button(query, key=f"quick_{hash(query)}"):
                with st.spinner("Processing query..."):
                    try:
                        # Get the agent response
                        agent_result = st.session_state.agent(query)
                        
                        # Extract just the message content from AgentResult
                        if hasattr(agent_result, 'content'):
                            # Handle Strands AgentResult format
                            message_content = ""
                            for content_block in agent_result.content:
                                if hasattr(content_block, 'text'):
                                    message_content += content_block.text
                                elif isinstance(content_block, dict) and 'text' in content_block:
                                    message_content += content_block['text']
                                else:
                                    message_content += str(content_block)
                        else:
                            # Fallback for string responses
                            message_content = str(agent_result)
                        
                        # Check if guardrails were invoked
                        guardrail_invoked = "validate_lounge_access_eligibility" in message_content.lower() or \
                                          "eligibility" in message_content.lower() and "lounge" in message_content.lower()
                        
                        exchange = {
                            "user": query,
                            "assistant": message_content,
                            "guardrail_invoked": guardrail_invoked,
                            "ar_findings": None,
                            "rewritten_response": None,
                            "processing_steps": [],
                            "result": {"conversation_response": message_content}
                        }
                        st.session_state.conversation_history.append(exchange)
                    except Exception as e:
                        st.error(f"Error processing query: {str(e)}")
                st.rerun()
        
        # Clear conversation
        if st.button("Clear Conversation", type="secondary"):
            st.session_state.conversation_history = []
            st.rerun()

def show_boarding_pass_analysis():
    """Detailed boarding pass analysis interface"""
    
    st.header("📄 Boarding Pass Analysis")
    st.markdown("Upload or paste boarding pass information for detailed analysis.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Boarding Pass Input")
        
        # Sample boarding passes
        st.markdown("**Use a sample boarding pass:**")
        sample_passes = create_sample_boarding_passes()
        
        for i, sample in enumerate(sample_passes):
            if st.button(f"Sample {i+1}", key=f"sample_bp_{i}"):
                st.session_state.selected_boarding_pass = sample
        
        # Text input for boarding pass
        boarding_pass_text = st.text_area(
            "Or paste your boarding pass text:",
            value=st.session_state.get('selected_boarding_pass', ''),
            height=200,
            help="Paste the text from your boarding pass or use one of the samples above"
        )
        
        # Analyze button
        if st.button("🔍 Analyze Boarding Pass", type="primary"):
            if boarding_pass_text.strip():
                analyze_boarding_pass(boarding_pass_text)
            else:
                st.error("Please provide boarding pass information")
    
    with col2:
        st.subheader("Analysis Results")
        
        # Show results if available
        if hasattr(st.session_state, 'bp_analysis_result'):
            show_analysis_results(st.session_state.bp_analysis_result)

def parse_boarding_pass(boarding_pass_text: str) -> Dict[str, Any]:
    """
    Parse boarding pass text to extract key information
    """
    
    
    parsed_info = {
        "passenger_name": None,
        "flight_number": None,
        "airline": None,
        "origin": None,
        "destination": None,
        "class_of_service": None,
        "seat": None,
        "date": None,
        "time": None,
        "gate": None,
        "is_international": False,
        "is_star_alliance": False
    }
    
    lines = boarding_pass_text.strip().split('\n')
    text = ' '.join(lines).upper()
    
    # Extract passenger name
    name_patterns = [
        r'PASSENGER[:\s]+([A-Z]+[/,\s][A-Z]+)',
        r'NAME[:\s]+([A-Z]+[/,\s][A-Z]+)',
        r'([A-Z]+[/,][A-Z]+)'
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            parsed_info["passenger_name"] = match.group(1).replace('/', ' ').replace(',', ' ')
            break
    
    # Extract flight number
    flight_match = re.search(r'FLIGHT[:\s]*([A-Z]{2}\d{3,4})|([A-Z]{2}\d{3,4})', text)
    if flight_match:
        parsed_info["flight_number"] = flight_match.group(1) or flight_match.group(2)
        # Extract airline from flight number
        if parsed_info["flight_number"]:
            airline_code = parsed_info["flight_number"][:2]
            airline_map = {
                'UA': 'UNITED AIRLINES',
                'LH': 'LUFTHANSA',
                'AC': 'AIR CANADA',
                'BA': 'BRITISH AIRWAYS',
                'SQ': 'SINGAPORE AIRLINES',
                'TG': 'THAI AIRWAYS',
                'AA': 'AMERICAN AIRLINES',
                'DL': 'DELTA AIR LINES'
            }
            parsed_info["airline"] = airline_map.get(airline_code, airline_code)
            
            # Check if Star Alliance
            star_alliance_codes = ['UA', 'LH', 'AC', 'BA', 'SQ', 'TG']
            parsed_info["is_star_alliance"] = airline_code in star_alliance_codes
    
    # Extract airline if mentioned explicitly
    airline_patterns = [
        r'(UNITED AIRLINES)',
        r'(LUFTHANSA)',
        r'(AIR CANADA)',
        r'(BRITISH AIRWAYS)',
        r'(SINGAPORE AIRLINES)',
        r'(THAI AIRWAYS)',
        r'(AMERICAN AIRLINES)',
        r'(DELTA AIR LINES)'
    ]
    for pattern in airline_patterns:
        match = re.search(pattern, text)
        if match:
            parsed_info["airline"] = match.group(1)
            break
    
    # Extract origin and destination
    route_patterns = [
        r'FROM[:\s]*([A-Z]{3})\s*TO[:\s]*([A-Z]{3})',
        r'([A-Z]{3})\s*TO\s*([A-Z]{3})',
        r'([A-Z]{3})\s*[-→]\s*([A-Z]{3})'
    ]
    for pattern in route_patterns:
        match = re.search(pattern, text)
        if match:
            parsed_info["origin"] = match.group(1)
            parsed_info["destination"] = match.group(2)
            break
    
    # Determine if international
    if parsed_info["origin"] and parsed_info["destination"]:
        us_airports = ['JFK', 'LAX', 'ORD', 'DFW', 'DEN', 'ATL', 'SFO', 'SEA', 'MIA', 'BOS']
        origin_us = parsed_info["origin"] in us_airports
        dest_us = parsed_info["destination"] in us_airports
        parsed_info["is_international"] = not (origin_us and dest_us)
    
    # Extract class of service
    class_patterns = [
        r'CLASS[:\s]*(FIRST|BUSINESS|PREMIUM\s*ECONOMY|ECONOMY)',
        r'SEAT[:\s]*[A-Z0-9]+\s*(FIRST|BUSINESS|PREMIUM\s*ECONOMY|ECONOMY)',
        r'(FIRST|BUSINESS|PREMIUM\s*ECONOMY|ECONOMY)\s*CLASS'
    ]
    for pattern in class_patterns:
        match = re.search(pattern, text)
        if match:
            parsed_info["class_of_service"] = match.group(1).strip()
            break
    
    # Extract seat
    seat_match = re.search(r'SEAT[:\s]*([A-Z0-9]+)', text)
    if seat_match:
        parsed_info["seat"] = seat_match.group(1)
    
    # Extract date
    date_patterns = [
        r'DATE[:\s]*(\d{4}-\d{2}-\d{2})',
        r'DATE[:\s]*(\d{2}-\d{2}-\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}-\d{2}-\d{4})'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            parsed_info["date"] = match.group(1)
            break
    
    # Extract time
    time_match = re.search(r'TIME[:\s]*(\d{2}:\d{2})', text)
    if time_match:
        parsed_info["time"] = time_match.group(1)
    
    # Extract gate
    gate_match = re.search(r'GATE[:\s]*([A-Z]?\d+[A-Z]?)', text)
    if gate_match:
        parsed_info["gate"] = gate_match.group(1)
    
    return parsed_info

def analyze_boarding_pass(boarding_pass_text: str):
    """Analyze the boarding pass and show results with direct ApplyGuardrail validation"""
    
    with st.spinner("Parsing boarding pass..."):
        # Step 1: Parse the boarding pass
        parsed_bp = parse_boarding_pass(boarding_pass_text)
        
        # Display parsed information
        st.info("📋 Boarding Pass Parsed Successfully")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Passenger", parsed_bp.get("passenger_name", "Unknown"))
            st.metric("Flight", parsed_bp.get("flight_number", "Unknown"))
            st.metric("Route", f"{parsed_bp.get('origin', '?')} → {parsed_bp.get('destination', '?')}")
        
        with col2:  
            st.metric("Class", parsed_bp.get("class_of_service", "Unknown"))
            st.metric("Date", parsed_bp.get("date", "Unknown"))
            st.metric("Seat", parsed_bp.get("seat", "Unknown"))
        
        with col3:
            st.metric("Airline", parsed_bp.get("airline", "Unknown"))
            st.metric("Flight Type", "International" if parsed_bp.get("is_international") else "Domestic")
            st.metric("Star Alliance", "Yes" if parsed_bp.get("is_star_alliance") else "No")
    
    with st.spinner("Getting lounge access agent decision..."):
        # Step 2: Get agent decision using parsed boarding pass data
        query = f"""Please determine lounge access eligibility for this passenger:

Passenger: {parsed_bp.get('passenger_name', 'Unknown')}
Flight: {parsed_bp.get('flight_number', 'Unknown')} ({parsed_bp.get('airline', 'Unknown')})
Route: {parsed_bp.get('origin', 'Unknown')} to {parsed_bp.get('destination', 'Unknown')}
Class: {parsed_bp.get('class_of_service', 'Unknown')}
Flight Type: {'International' if parsed_bp.get('is_international') else 'Domestic'}
Star Alliance: {'Yes' if parsed_bp.get('is_star_alliance') else 'No'}
Date: {parsed_bp.get('date', 'Unknown')}

Please provide a clear decision on whether this passenger can access the lounge."""

        try:
            # Get agent decision
            agent_result = st.session_state.agent(query)
            
            # Extract message content from AgentResult
            if hasattr(agent_result, 'content'):
                agent_response = ""
                for content_block in agent_result.content:
                    if hasattr(content_block, 'text'):
                        agent_response += content_block.text
                    elif isinstance(content_block, dict) and 'text' in content_block:
                        agent_response += content_block['text']
                    else:
                        agent_response += str(content_block)
            else:
                agent_response = str(agent_result)
            
            st.success("✅ Agent decision received!")
            st.info(f"**Agent Decision:** {agent_response[:200]}..." if len(agent_response) > 200 else agent_response)
            
        except Exception as e:
            st.error(f"Error getting agent decision: {str(e)}")
            # Fallback agent response
            agent_response = f"""Based on the boarding pass analysis for {parsed_bp.get('passenger_name', 'Unknown')} on flight {parsed_bp.get('flight_number', 'Unknown')}, this passenger is {'eligible' if parsed_bp.get('is_star_alliance') or parsed_bp.get('class_of_service') in ['FIRST', 'BUSINESS'] else 'not eligible'} for lounge access."""
    
    with st.spinner("Applying Automated Reasoning validation..."):
        # Step 3: Create comprehensive content for ApplyGuardrail validation
        # Include both the parsed boarding pass data AND the agent response
        parsed_bp_text = f"""Parsed Boarding Pass Information:
- Passenger: {parsed_bp.get('passenger_name', 'Unknown')}
- Flight: {parsed_bp.get('flight_number', 'Unknown')} ({parsed_bp.get('airline', 'Unknown')})
- Route: {parsed_bp.get('origin', 'Unknown')} → {parsed_bp.get('destination', 'Unknown')}
- Class: {parsed_bp.get('class_of_service', 'Unknown')}
- Seat: {parsed_bp.get('seat', 'Unknown')}
- Date: {parsed_bp.get('date', 'Unknown')}
- Flight Type: {'International' if parsed_bp.get('is_international') else 'Domestic'}
- Star Alliance: {'Yes' if parsed_bp.get('is_star_alliance') else 'No'}"""

        user_query = f"Can this passenger access the airport lounge?\n\n{parsed_bp_text}"

        # Step 4: Apply Guardrail with both boarding pass data and agent response
        try:
            bedrock_client = boto3.client("bedrock-runtime", region_name=CURRENT_REGION)
            
            # Create content for guardrail validation
            content_to_validate = [
                {
                    "text": {
                        "text": user_query, 
                        "qualifiers": ["query"]
                    }
                },
                {
                    "text": {
                        "text": agent_response, 
                        "qualifiers": ["guard_content"]
                    }
                }
            ]
            
            st.info("🛡️ Applying ApplyGuardrails validation...")
            
            # Apply guardrail
            guardrail_response = bedrock_client.apply_guardrail(
                guardrailIdentifier=GUARDRAIL_ID,
                guardrailVersion=GUARDRAIL_VERSION,
                source="OUTPUT",
                content=content_to_validate
            )
            
            st.success("✅ ApplyGuardrails validation completed!")
            
            # Extract Automated Reasoning findings
            ar_findings = None
            finding_type = "NO_VALIDATION"
            findings_count = 0
            validation_result_type = None
            action = guardrail_response.get('action', 'NONE')
            
            if guardrail_response.get('assessments'):
                for assessment in guardrail_response.get('assessments', []):
                    if 'automatedReasoningPolicy' in assessment:
                        ar_policy = assessment['automatedReasoningPolicy']
                        ar_findings = ar_policy
                        finding_type = ar_policy.get('finding_type', 'AUTOMATED_REASONING_VALIDATION')
                        findings_count = len(ar_policy.get('findings', []))
                        
                        # Check the validation type from AR findings
                        if ar_policy.get('findings'):
                            for finding in ar_policy['findings']:
                                if 'translationAmbiguous' in finding:
                                    validation_result_type = 'translationAmbiguous'
                                elif 'valid' in finding or 'Valid' in finding:
                                    validation_result_type = 'Valid'
                                elif 'invalid' in finding or 'Invalid' in finding:
                                    validation_result_type = 'Invalid'
                                elif 'noTranslations' in finding:
                                    validation_result_type = 'noTranslations'
                        break
            
            # Determine access based on AR validation result
            ar_access_granted = validation_result_type == 'Valid'
            ar_reason = ""
            
            if validation_result_type == 'Valid':
                ar_reason = "Automated Reasoning validation: VALID - Access granted"
            elif validation_result_type == 'translationAmbiguous':
                ar_reason = "Automated Reasoning validation: TRANSLATION_AMBIGUOUS - Please contact Lounge Staff member for assistance"
            elif validation_result_type == 'Invalid':
                ar_reason = "Automated Reasoning validation: INVALID - Please contact Lounge Staff member for assistance"
            elif validation_result_type == 'noTranslations':
                ar_reason = "Automated Reasoning validation: NO_TRANSLATIONS - Please contact Lounge Staff member for assistance"
            else:
                ar_reason = f"Automated Reasoning validation: {validation_result_type or 'UNKNOWN'} - Please contact Lounge Staff member for assistance"
            
            # Step 5: Create comprehensive result with actual AR findings
            result = {
                "conversation_response": agent_response,
                "decision": "ANALYZED", 
                "access_granted": ar_access_granted,
                "reason": ar_reason,
                "guardrail_invoked": True,
                "processing_steps": [
                    "Step 1: Boarding pass parsed",
                    "Step 2: Passenger details extracted", 
                    "Step 3: ApplyGuardrails validation applied",
                    "Step 4: Automated Reasoning findings analyzed"
                ],
                "boarding_pass_info": parsed_bp,
                "flight_info": {
                    "flight_number": parsed_bp.get("flight_number"),
                    "airline": parsed_bp.get("airline"),
                    "origin": parsed_bp.get("origin"),
                    "destination": parsed_bp.get("destination"),
                    "is_international": parsed_bp.get("is_international"),
                    "is_star_alliance": parsed_bp.get("is_star_alliance"),
                    "date": parsed_bp.get("date"),
                    "gate": parsed_bp.get("gate"),
                    "status": "Scheduled"
                },
                "validation_result": {
                    "finding_type": finding_type,
                    "findings_count": findings_count,
                    "validation_type": validation_result_type,
                    "findings": json.dumps(ar_findings, indent=2) if ar_findings else "Automated Reasoning validation completed",
                    "message": f"Guardrail action: {action} - {guardrail_response.get('actionReason', 'Policy validation performed')}",
                    "raw_guardrail_response": guardrail_response
                }
            }
            
            st.session_state.bp_analysis_result = result
            
            # Display real-time feedback
            st.info("🔄 Processing Steps Completed:")
            for step in result["processing_steps"]:
                st.text(f"  ✓ {step}")
            
            # Display guardrail action
            if action == "BLOCKED":
                st.error(f"🚫 Access BLOCKED by Automated Reasoning: {guardrail_response.get('actionReason', 'Policy violation detected')}")
            elif action == "NONE":
                st.success("✅ Access APPROVED - No policy violations detected")
            else:
                st.warning(f"⚠️ Guardrail Action: {action}")
            
            # Show AR findings if available
            if ar_findings:
                st.info("🧠 Automated Reasoning Findings Detected")
                with st.expander("View Raw AR Findings", expanded=False):
                    st.json(ar_findings)
                
        except Exception as e:
            st.error(f"Error during ApplyGuardrail validation: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            
            # Fallback result without AR validation
            result = {
                "conversation_response": agent_response,
                "decision": "ANALYZED", 
                "access_granted": "eligible" in agent_response.lower(),
                "reason": f"Boarding pass analysis completed (AR validation failed: {str(e)})",
                "guardrail_invoked": False,
                "processing_steps": [
                    "Step 1: Boarding pass parsed",
                    "Step 2: Passenger details extracted", 
                    "Step 3: ApplyGuardrails validation failed"
                ],
                "boarding_pass_info": parsed_bp,
                "flight_info": {
                    "flight_number": parsed_bp.get("flight_number"),
                    "airline": parsed_bp.get("airline"),
                    "origin": parsed_bp.get("origin"),  
                    "destination": parsed_bp.get("destination"),
                    "is_international": parsed_bp.get("is_international"),
                    "is_star_alliance": parsed_bp.get("is_star_alliance"),
                    "date": parsed_bp.get("date"),
                    "gate": parsed_bp.get("gate"),
                    "status": "Scheduled"
                },
                "validation_result": None
            }
            
            st.session_state.bp_analysis_result = result

def show_automated_reasoning_results(result: Dict[str, Any]):
    """Display Automated Reasoning validation results prominently"""
    
    validation_result = result.get('validation_result')
    
    if not validation_result:
        st.info("🛡️ No Automated Reasoning validation performed")
        return
    
    st.subheader("🧠 Automated Reasoning Validation")
    
    # Create columns for better layout  
    col1, col2 = st.columns([1, 1])
    
    with col1:
        finding_type = validation_result.get('finding_type', 'None')
        if finding_type:
            finding_type_display = str(finding_type).replace('_', ' ').title()
        else:
            finding_type_display = 'None'
        
        st.markdown("**Finding Type**")
        st.markdown(f"<div style='font-size: 14px; color: #1f77b4;'>{finding_type_display}</div>", unsafe_allow_html=True)
    
    with col2:
        validation_type = validation_result.get('validation_type', 'Unknown')
        st.markdown("**Validation Type**")
        st.markdown(f"<div style='font-size: 14px; color: #1f77b4;'>{validation_type}</div>", unsafe_allow_html=True)
    
    # Show detailed findings
    if validation_result.get('findings'):
        st.subheader("🔍 Detailed AR Findings")
        
        with st.expander("View Detailed Policy Analysis", expanded=True):
            # Display the formatted findings
            st.markdown("**Policy Analysis Results:**")
            findings_text = validation_result.get('findings', '')
            if findings_text:
                st.text(findings_text)
            else:
                st.info("No detailed findings available")
    
    # Show validation message
    if validation_result.get('message'):
        st.subheader("📋 Validation Summary")
        message = validation_result.get('message')
        
        if 'error' in message.lower():
            st.error(f"❌ {message}")
        elif validation_result.get('rewritten'):
            st.success(f"✅ {message}")
        else:
            st.info(f"ℹ️ {message}")
    
    # Show raw validation data for debugging
    with st.expander("🔧 Raw Validation Data (Debug)", expanded=False):
        st.json(validation_result)

def show_analysis_results(result: Dict[str, Any]):
    """Display detailed analysis results"""
    
    # Decision summary
    decision = result.get("decision", "UNKNOWN")
    access_granted = result.get("access_granted", False)
    reason = result.get('reason', 'No reason provided')
    
    if access_granted:
        st.success(f"✅ Access Granted ({decision})")
    else:
        st.error(f"❌ Access Denied ({decision})")
    
    # Make "contact staff" message more prominent
    if "contact Lounge Staff member for assistance" in reason:
        st.warning("⚠️ **Please contact Lounge Staff member for assistance**")
        st.write(f"**AR Validation Result:** {reason}")
    else:
        st.write(f"**Reason:** {reason}")
    
    # Show Automated Reasoning results prominently
    show_automated_reasoning_results(result)
    
    # Tabbed results
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎫 Boarding Pass", "✈️ Flight Info", "👤 Passenger", "📋 Policy", "🧠 AR Details"])
    
    with tab1:
        if result.get("boarding_pass_info"):
            st.json(result["boarding_pass_info"])
        else:
            st.info("No boarding pass information parsed")
    
    with tab2:
        if result.get("flight_info"):
            flight_info = result["flight_info"]
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Flight", flight_info.get("flight_number", "N/A"))
                st.metric("Status", flight_info.get("status", "N/A"))
                st.metric("Gate", flight_info.get("gate", "N/A"))
            
            with col2:
                st.metric("Route", f"{flight_info.get('origin', 'N/A')} → {flight_info.get('destination', 'N/A')}")
                st.metric("Type", "International" if flight_info.get("is_international") else "Domestic")
                st.metric("Star Alliance", "Yes" if flight_info.get("is_star_alliance") else "No")
        else:
            st.info("No flight information available")
    
    with tab3:
        if result.get("passenger_info"):
            passenger_info = result["passenger_info"]
            
            # Passenger data
            if passenger_info.get("passenger_data"):
                st.subheader("Passenger Profile")
                passenger_data = passenger_info["passenger_data"]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Name:** {passenger_data.get('name', 'N/A')}")
                    st.write(f"**Airline:** {passenger_data.get('airline', 'N/A')}")
                    st.write(f"**Tier Status:** {passenger_data.get('tier_status', 'N/A')}")
                
                with col2:
                    st.write(f"**Total Miles:** {passenger_data.get('total_miles', 0):,}")
                    st.write(f"**YTD Miles:** {passenger_data.get('year_to_date_miles', 0):,}")
                    st.write(f"**Segments:** {passenger_data.get('segments_flown', 0)}")
            
            # Gold status
            if passenger_info.get("gold_status", {}).get("has_status"):
                st.subheader("⭐ Star Alliance Gold Status")
                gold_status = passenger_info["gold_status"]
                st.success(f"Valid {gold_status.get('status_level', 'Gold')} status")
                st.write(f"**Companion Passes:** {gold_status.get('companion_passes', 0)}")
            
            # Paid membership
            if passenger_info.get("paid_membership", {}).get("has_membership"):
                st.subheader("💳 Lounge Memberships")
                memberships = passenger_info["paid_membership"]["membership_types"]
                for membership in memberships:
                    st.write(f"• {membership}")
        else:
            st.info("No passenger information found")
    
    with tab4:
        if result.get("policy_evaluation"):
            policy_eval = result["policy_evaluation"]
            
            st.subheader("Policy Evaluation")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Access Type", policy_eval.get("access_type", "N/A"))
                st.metric("Guest Allowed", "Yes" if policy_eval.get("guest_allowed") else "No")
                if policy_eval.get("guest_allowed"):
                    st.metric("Guest Count", policy_eval.get("guest_count", 0))
            
            with col2:
                st.write("**Policy Details:**")
                st.write(policy_eval.get("policy_details", "No details available"))
            
            # Restrictions
            if policy_eval.get("restrictions"):
                st.subheader("Restrictions")
                for restriction in policy_eval["restrictions"]:
                    st.write(f"• {restriction}")
            
            # Special notes
            if policy_eval.get("special_notes"):
                st.subheader("Special Notes")
                for note in policy_eval["special_notes"]:
                    st.warning(note)
    
    with tab5:
        st.subheader("🧠 Automated Reasoning Details")
        
        validation_result = result.get('validation_result')
        if validation_result:
            # AR Validation Metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Finding Type", validation_result.get('finding_type', 'None'))
            
            with col2:
                st.metric("Findings Count", validation_result.get('findings_count', 0))
            
            with col3:
                st.metric("Response Rewritten", "Yes" if validation_result.get('rewritten') else "No")
            
            # Detailed findings
            if validation_result.get('findings'):
                st.subheader("📋 Detailed Findings")
                st.text(validation_result.get('findings'))
            
            # Validation message
            if validation_result.get('message'):
                st.subheader("📄 Validation Message")
                st.info(validation_result.get('message'))
            
            # Original vs Rewritten comparison
            if validation_result.get('rewritten_response'):
                st.subheader("📝 Response Comparison")
                
                col_orig, col_rewritten = st.columns(2)
                with col_orig:
                    st.markdown("**Original Response:**")
                    st.info(result.get('conversation_response', 'No original response'))
                
                with col_rewritten:
                    st.markdown("**Rewritten Response:**")
                    st.success(validation_result.get('rewritten_response'))
            
            # Raw AR data
            with st.expander("Raw AR Validation Data", expanded=False):
                st.json(validation_result)
        else:
            st.info("No Automated Reasoning validation was performed for this request.")
    
    # Processing steps
    with st.expander("🔄 Processing Steps", expanded=False):
        for step in result.get("processing_steps", []):
            st.text(step)
    

def show_policy_violation_examples():
    """Show examples of policy violations and how they're handled"""
    
    st.header("⚠️ Policy Violation Examples")
    st.markdown("See how Automated Reasoning catches and corrects policy violations.")
    
    # Create test scenarios that might violate policies
    violation_scenarios = [
        {
            "name": "United Domestic First Class (Should be Denied)",
            "description": "United Airlines domestic First Class passenger - should be denied access per policy",
            "boarding_pass": """
            UNITED AIRLINES
            PASSENGER: DOE/JANE
            FLIGHT: UA5678
            FROM: JFK TO: LAX
            SEAT: 2A CLASS: FIRST
            DATE: 2024-10-18 TIME: 15:30
            GATE: C15
            """,
            "expected": "Access should be denied due to United domestic First Class restriction"
        },
        {
            "name": "Non-Star Alliance Flight",
            "description": "Passenger on non-Star Alliance airline",
            "boarding_pass": """
            AMERICAN AIRLINES
            PASSENGER: SMITH/BOB
            FLIGHT: AA1234
            FROM: JFK TO: LHR
            SEAT: 3D CLASS: BUSINESS
            DATE: 2024-10-18 TIME: 20:00
            """,
            "expected": "Access should be denied - not a Star Alliance member airline"
        },
        {
            "name": "Cancelled Flight",
            "description": "Star Alliance flight that has been cancelled",
            "boarding_pass": """
            LUFTHANSA
            PASSENGER: WILSON/SARA
            FLIGHT: LH999
            FROM: FRA TO: JFK
            SEAT: 7A CLASS: BUSINESS
            STATUS: CANCELLED
            DATE: 2024-10-18 TIME: 14:00
            """,
            "expected": "Access should be denied - flight is cancelled"
        }
    ]
    
    st.subheader("Test Policy Violations")
    
    for i, scenario in enumerate(violation_scenarios):
        with st.expander(f"Scenario {i+1}: {scenario['name']}", expanded=False):
            st.markdown(f"**Description:** {scenario['description']}")
            st.markdown(f"**Expected Result:** {scenario['expected']}")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.code(scenario['boarding_pass'], language='text')
            
            with col2:
                if st.button(f"Test Scenario {i+1}", key=f"violation_{i}"):
                    with st.spinner("Testing scenario..."):
                        result = st.session_state.agent.process_lounge_access_request(
                            "Please check my lounge access eligibility",
                            boarding_pass_text=scenario['boarding_pass']
                        )
                    
                    # Show result
                    if result.get("access_granted"):
                        st.error("❌ Unexpected: Access was granted (this might indicate a policy issue)")
                    else:
                        st.success("✅ Expected: Access correctly denied")
                    
                    st.write(f"**Reason:** {result.get('reason', 'No reason provided')}")
                    
                    # Show validation results
                    if result.get("validation_result"):
                        validation = result["validation_result"]
                        if validation.get("findings"):
                            st.subheader("Automated Reasoning Findings:")
                            findings_text = validation.get("findings", "")
                            if isinstance(findings_text, str):
                                st.text(findings_text)
                            else:
                                st.write("Validation findings detected but could not display details")

def show_automated_reasoning_showcase():
    """Showcase the Automated Reasoning capabilities"""
    
    st.header("🧠 Automated Reasoning Showcase")
    st.markdown("Demonstrate how Automated Reasoning validates and rewrites agent responses.")
    
    tab1, tab2 = st.tabs(["🔍 Validation Process", "✏️ Response Rewriting"])
    
    with tab1:
        st.subheader("How Automated Reasoning Works")
        
        st.markdown("""
        The Automated Reasoning system provides an additional layer of validation:
        
        1. **Agent Decision**: The AI agent makes an initial lounge access decision
        2. **Policy Validation**: Automated Reasoning checks the decision against formal policies
        3. **Issue Detection**: Any policy violations or inconsistencies are flagged
        4. **Response Rewriting**: If issues are found, the response is automatically rewritten
        5. **Final Output**: The validated (and possibly rewritten) response is provided
        """)
        
        # Flow diagram (text-based)
        st.markdown("""
        **Process Flow:**
        
        ```
        User Query
            ↓
        Agent Processing
            ↓
        Initial Decision
            ↓
        Automated Reasoning Validation
            ↓
        Policy Violations?
           ↙        ↘
        No           Yes
        ↓            ↓
        Validated    Response Rewriting
        Response     ↓
        ↓            Rewritten Response
        ↓            ↓
        Final Output ←
        ```
        """)
    
    with tab2:
        st.subheader("Response Rewriting Demo")
        
        # Custom scenario for rewriting
        st.markdown("**Test Response Rewriting:**")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            user_query = st.text_area(
                "User Query:",
                "I'm flying United domestic First Class from JFK to LAX. Can I access the lounge?",
                help="This should trigger a policy violation"
            )
            
            if st.button("Test Automated Reasoning Validation", type="primary"):
                test_automated_reasoning_workflow(user_query, "")
        
        with col2:
            if hasattr(st.session_state, 'validation_demo_result'):
                result = st.session_state.validation_demo_result
                
                st.subheader("Validation Results")
                
                if result.get("findings"):
                    st.warning("⚠️ Policy Violations Detected:")
                    for finding in result["findings"]:
                        st.write(f"• **Policy:** {finding.get('policy_name', 'Unknown')}")
                        st.write(f"  **Verdict:** {finding.get('verdict', 'Unknown')}")
                        st.write(f"  **Confidence:** {finding.get('confidence', 'Unknown')}")
                    
                    if result.get("rewritten_response"):
                        st.success("✅ Response Automatically Rewritten:")
                        st.write(result["rewritten_response"])
                else:
                    st.success("✅ No policy violations found")

def show_knowledge_base_queries():
    """Show Knowledge Base integration for lounge information"""
    
    st.header("📚 Knowledge Base Queries")
    st.markdown("Query the Knowledge Base for detailed lounge information and amenities.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Ask About the Lounge")
        
        # Predefined queries
        st.markdown("**Quick Questions:**")
        quick_questions = [
            "What dining options are available?",
            "What are the lounge operating hours?",
            "What amenities does the lounge offer?",
            "Is there WiFi in the lounge?",
            "Does the lounge have shower facilities?",
            "What is the dress code for the lounge?",
            "Are there quiet areas in the lounge?"
        ]
        
        for question in quick_questions:
            if st.button(question, key=f"kb_{hash(question)}"):
                query_knowledge_base(question)
        
        # Custom query
        st.markdown("**Custom Question:**")
        custom_query = st.text_input("Ask your own question about the lounge:")
        
        if st.button("Ask Question", type="primary") and custom_query:
            query_knowledge_base(custom_query)
    
    with col2:
        st.subheader("Knowledge Base Response")
        
        if hasattr(st.session_state, 'kb_response'):
            st.write(st.session_state.kb_response)
        else:
            st.info("Ask a question to see the Knowledge Base response")
        
        # Show raw knowledge base data
        with st.expander("Raw Lounge Data", expanded=False):
            try:
                
                with open('data/lounge_info.json', 'r') as f:
                    lounge_data = json.load(f)
                st.json(lounge_data)
            except FileNotFoundError:
                st.error("Lounge data file not found")

def query_knowledge_base(query: str):
    """Query the knowledge base and show response"""
    
    with st.spinner("Querying Knowledge Base..."):
        try:
            agent_result = st.session_state.agent(query)
            
            # Extract just the message content from AgentResult
            if hasattr(agent_result, 'content'):
                # Handle Strands AgentResult format
                kb_response = ""
                for content_block in agent_result.content:
                    if hasattr(content_block, 'text'):
                        kb_response += content_block.text
                    elif isinstance(content_block, dict) and 'text' in content_block:
                        kb_response += content_block['text']
                    else:
                        kb_response += str(content_block)
            else:
                # Fallback for string responses
                kb_response = str(agent_result)
                
            st.session_state.kb_response = kb_response
        except Exception as e:
            st.session_state.kb_response = f"Error querying knowledge base: {str(e)}"
        
    st.rerun()

def test_automated_reasoning_workflow(user_query: str, original_response: str):
    """Test the complete Automated Reasoning workflow with proper agent and ApplyGuardrail usage"""
    
    with st.spinner("Step 1: Creating agent without guardrail..."):
        try:
            # Create agent without guardrail to get raw response
            raw_agent = create_enhanced_lounge_agent_without_guardrail()
            st.success("✅ Agent created successfully")
        except Exception as e:
            st.error(f"Error creating agent: {str(e)}")
            return
    
    with st.spinner("Step 2: Getting raw agent response..."):
        try:
            # Get agent response
            agent_result = raw_agent(user_query)
            
            # Extract message content from AgentResult
            if hasattr(agent_result, 'content'):
                agent_response = ""
                for content_block in agent_result.content:
                    if hasattr(content_block, 'text'):
                        agent_response += content_block.text
                    elif isinstance(content_block, dict) and 'text' in content_block:
                        agent_response += content_block['text']
                    else:
                        agent_response += str(content_block)
            else:
                agent_response = str(agent_result)
            
            # Print to console as requested
            print(f"[AUTOMATED_REASONING_SHOWCASE] Raw Agent Response: {agent_response}")
            
            st.success("✅ Agent response received")
            
        except Exception as e:
            st.error(f"Error getting agent response: {str(e)}")
            # Fallback to original response if agent fails
            agent_response = original_response
    
    with st.spinner("Step 3: Applying ApplyGuardrail validation..."):
        try:
            bedrock_client = boto3.client("bedrock-runtime", region_name=CURRENT_REGION)
            
            # Create content for guardrail validation
            content_to_validate = [
                {
                    "text": {
                        "text": user_query, 
                        "qualifiers": ["query"]
                    }
                },
                {
                    "text": {
                        "text": agent_response, 
                        "qualifiers": ["guard_content"]
                    }
                }
            ]
            
            # Apply guardrail
            guardrail_response = bedrock_client.apply_guardrail(
                guardrailIdentifier=GUARDRAIL_ID,
                guardrailVersion=GUARDRAIL_VERSION,
                source="OUTPUT",
                content=content_to_validate
            )
            
            st.success("✅ ApplyGuardrail validation completed")
            
            # Extract Automated Reasoning findings
            ar_findings = None
            validation_result_type = None
            action = guardrail_response.get('action', 'NONE')
            has_violations = False
            
            if guardrail_response.get('assessments'):
                for assessment in guardrail_response.get('assessments', []):
                    if 'automatedReasoningPolicy' in assessment:
                        ar_policy = assessment['automatedReasoningPolicy']
                        ar_findings = ar_policy
                        
                        # Check the validation type from AR findings
                        if ar_policy.get('findings'):
                            for finding in ar_policy['findings']:
                                if 'translationAmbiguous' in finding:
                                    validation_result_type = 'translationAmbiguous'
                                    has_violations = True
                                elif 'invalid' in finding or 'Invalid' in finding:
                                    validation_result_type = 'Invalid'
                                    has_violations = True
                                elif 'noTranslations' in finding:
                                    validation_result_type = 'noTranslations'
                                    has_violations = True
                                elif 'valid' in finding or 'Valid' in finding:
                                    validation_result_type = 'Valid'
                        break
            
        except Exception as e:
            st.error(f"Error during ApplyGuardrail validation: {str(e)}")
            guardrail_response = None
            ar_findings = None
            has_violations = False
    
    with st.spinner("Step 4: Response rewriting (if needed)..."):
        rewritten_response = None
        if has_violations and ar_findings:
            try:
                # Use Claude to rewrite the response based on AR findings
                rewrite_prompt = f"""The following agent response has been flagged by Automated Reasoning as having policy violations:

Original Query: {user_query}

Agent Response: {agent_response}

Automated Reasoning Findings: {json.dumps(ar_findings, indent=2)}

Please rewrite the agent response to address the policy violations. The rewritten response should:
1. Correct any policy violations identified
2. Provide accurate information based on the lounge access policies
3. Maintain a helpful and professional tone
4. Include appropriate guidance if access should be denied

Rewritten Response:"""

                # Use the same bedrock client for rewriting
                bedrock_model = boto3.client(
                    "bedrock-runtime", 
                    region_name=CURRENT_REGION,
                    config=BotocoreConfig(
                        retries={'max_attempts': 3, 'mode': 'adaptive'}
                    )
                )
                
                response = bedrock_model.converse(
                    modelId=MODEL_ID,
                    messages=[{
                        "role": "user",
                        "content": [{"text": rewrite_prompt}]
                    }],
                    inferenceConfig={
                        "maxTokens": 2000,
                        "temperature": 0.1
                    }
                )
                
                rewritten_response = response['output']['message']['content'][0]['text']
                st.success("✅ Response rewritten to address policy violations")
                
            except Exception as e:
                st.warning(f"Could not rewrite response: {str(e)}")
                rewritten_response = "Response needs to be rewritten to address policy violations, but rewriting failed."
        else:
            st.info("ℹ️ No policy violations found - no rewriting needed")
    
    # Store results for display
    st.session_state.validation_demo_result = {
        "user_query": user_query,
        "raw_agent_response": agent_response,
        "guardrail_response": guardrail_response,
        "ar_findings": ar_findings,
        "validation_type": validation_result_type,
        "has_violations": has_violations,
        "rewritten_response": rewritten_response,
        "action": action if guardrail_response else "ERROR"
    }
    
    # Display results immediately in the right column
    result = st.session_state.validation_demo_result
    
    st.subheader("🔄 Workflow Results")
    
    # Show step by step results
    st.markdown("### Step 1: Raw Agent Response")
    st.info(result["raw_agent_response"][:500] + "..." if len(result["raw_agent_response"]) > 500 else result["raw_agent_response"])
    
    st.markdown("### Step 2: Guardrail Analysis")
    if result.get("guardrail_response"):
        action = result["action"]
        if action == "BLOCKED":
            st.error(f"🚫 Guardrail Action: {action}")
        elif action == "NONE":
            st.success(f"✅ Guardrail Action: {action} (No violations)")
        else:
            st.warning(f"⚠️ Guardrail Action: {action}")
        
        # Show AR findings
        if result.get("ar_findings"):
            st.markdown("**Automated Reasoning Findings:**")
            validation_type = result.get("validation_type", "Unknown")
            st.write(f"**Validation Type:** {validation_type}")
            
            with st.expander("View Detailed AR Findings", expanded=False):
                st.json(result["ar_findings"])
        else:
            st.info("No Automated Reasoning findings detected")
        
        # Show full Guardrail response
        with st.expander("🛡️ View Complete Guardrail Response", expanded=False):
            st.json(result["guardrail_response"])
    else:
        st.error("❌ Guardrail validation failed")
    
    st.markdown("### Step 3: Final Response")
    if result.get("rewritten_response"):
        st.success("✅ **Response Rewritten by AR Policy:**")
        st.success(result["rewritten_response"])
        
        # Show comparison
        with st.expander("📋 Compare Original vs Rewritten", expanded=True):
            col_orig, col_new = st.columns(2)
            with col_orig:
                st.markdown("**Original Response:**")
                st.info(result["raw_agent_response"])
            with col_new:
                st.markdown("**Rewritten Response:**")
                st.success(result["rewritten_response"])
    else:
        if result.get("has_violations"):
            st.warning("⚠️ Response needs rewriting but rewriting process failed")
            st.info(result["raw_agent_response"])
        else:
            st.success("✅ **Original Response Validated - No Changes Needed:**")
            st.info(result["raw_agent_response"])

# Run the demo
if __name__ == "__main__":
    main()
