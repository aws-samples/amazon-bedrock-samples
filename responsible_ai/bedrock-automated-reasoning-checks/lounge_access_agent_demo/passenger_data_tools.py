"""
Strands Agent Tools: Passenger Data and Frequent Flier Status

These tools enable Strands agents to check frequent flier status, passenger data,
and lounge access eligibility using the @tool decorator pattern.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from strands.tools import tool

# Configure logging
logger = logging.getLogger(__name__)

# Global passenger data loaded once
_passenger_data = None

def _load_passenger_data() -> Dict[str, Dict[str, Any]]:
    """Load passenger data from JSON file (internal helper)"""
    global _passenger_data
    
    if _passenger_data is not None:
        return _passenger_data
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(current_dir, 'data', 'passenger_data.json')
        
        with open(data_file, 'r') as f:
            data_list = json.load(f)
        
        # Convert list to dict keyed by frequent flier number
        passenger_dict = {}
        for passenger in data_list:
            ff_number = passenger.get('frequent_flier_number')
            if ff_number:
                passenger_dict[ff_number] = passenger
        
        _passenger_data = passenger_dict
        return passenger_dict
        
    except Exception as e:
        logger.error(f"Error loading passenger data: {str(e)}")
        return {}

@tool
def lookup_passenger_by_ff_number(frequent_flier_number: str) -> Dict[str, Any]:
    """
    Look up passenger information using their frequent flier number.
    
    This tool retrieves complete passenger profile including tier status, miles,
    membership information, and lounge access privileges.
    
    Args:
        frequent_flier_number: The passenger's frequent flier number (e.g., "UA123456789")
        
    Returns:
        Dictionary containing passenger information or error if not found
        
    Examples:
        - lookup_passenger_by_ff_number("UA123456789")
        - lookup_passenger_by_ff_number("LH987654321")
    """
    try:
        if not frequent_flier_number or not frequent_flier_number.strip():
            return {
                "success": False,
                "error": "Frequent flier number is required",
                "passenger_data": None
            }
        
        passenger_data = _load_passenger_data()
        passenger = passenger_data.get(frequent_flier_number.strip())
        
        if passenger:
            return {
                "success": True,
                "passenger_data": passenger,
                "frequent_flier_number": frequent_flier_number,
                "found": True
            }
        else:
            return {
                "success": True,
                "passenger_data": None,
                "frequent_flier_number": frequent_flier_number,
                "found": False,
                "message": "Passenger not found in frequent flier database"
            }
            
    except Exception as e:
        logger.error(f"Error looking up passenger: {e}")
        return {
            "success": False,
            "error": f"Database lookup failed: {str(e)}",
            "passenger_data": None
        }

@tool
def lookup_passenger_by_name(passenger_name: str) -> Dict[str, Any]:
    """
    Look up passenger information using their name.
    
    Performs case-insensitive search for passenger by name. Handles various name formats
    including "LAST/FIRST" and "FIRST LAST" formats.
    
    Args:
        passenger_name: The passenger's name (various formats accepted)
        
    Returns:
        Dictionary containing passenger information or error if not found
        
    Examples:
        - lookup_passenger_by_name("DOE/JANE")
        - lookup_passenger_by_name("John Smith")
    """
    try:
        if not passenger_name or not passenger_name.strip():
            return {
                "success": False,
                "error": "Passenger name is required",
                "passenger_data": None
            }
        
        passenger_data = _load_passenger_data()
        name_normalized = passenger_name.strip().upper().replace('/', ' ')
        
        for ff_number, passenger in passenger_data.items():
            stored_name = passenger.get('name', '').upper()
            if stored_name == name_normalized:
                return {
                    "success": True,
                    "passenger_data": passenger,
                    "search_name": passenger_name,
                    "found": True,
                    "frequent_flier_number": ff_number
                }
        
        return {
            "success": True,
            "passenger_data": None,
            "search_name": passenger_name,
            "found": False,
            "message": "Passenger not found by name in database"
        }
        
    except Exception as e:
        logger.error(f"Error looking up passenger by name: {e}")
        return {
            "success": False,
            "error": f"Name lookup failed: {str(e)}",
            "passenger_data": None
        }


@tool
def check_star_alliance_gold_status(frequent_flier_number: str) -> Dict[str, Any]:
    """
    Check if a passenger has valid Star Alliance Gold status.
    
    Verifies Gold status, expiration date, airline affiliation, and associated benefits
    such as companion passes and tier levels.
    
    Args:
        frequent_flier_number: The passenger's frequent flier number
        
    Returns:
        Dictionary containing Gold status information and benefits
        
    Examples:
        - check_star_alliance_gold_status("UA123456789")
        - check_star_alliance_gold_status("LH987654321")
    """
    try:
        if not frequent_flier_number or not frequent_flier_number.strip():
            return {
                "success": False,
                "error": "Frequent flier number is required",
                "has_status": False
            }
        
        passenger_data = _load_passenger_data()
        passenger = passenger_data.get(frequent_flier_number.strip())
        
        if not passenger:
            return {
                "success": True,
                "has_status": False,
                "status_level": None,
                "expiry_date": None,
                "airline": None,
                "message": "Passenger not found in database"
            }
        
        # Check if membership is still valid
        expiry_date = passenger.get('membership_expiry')
        is_valid = True
        
        if expiry_date:
            try:
                expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
                is_valid = expiry_dt > datetime.now()
            except ValueError:
                is_valid = False
        
        has_gold_status = passenger.get('star_alliance_gold', False) and is_valid
        
        return {
            "success": True,
            "has_status": has_gold_status,
            "status_level": passenger.get('tier_status'),
            "expiry_date": expiry_date,
            "airline": passenger.get('airline'),
            "total_miles": passenger.get('total_miles', 0),
            "year_to_date_miles": passenger.get('year_to_date_miles', 0),
            "companion_passes": passenger.get('companion_passes', 0),
            "is_expired": not is_valid if expiry_date else False,
            "frequent_flier_number": frequent_flier_number
        }
        
    except Exception as e:
        logger.error(f"Error checking Gold status: {e}")
        return {
            "success": False,
            "error": f"Gold status check failed: {str(e)}",
            "has_status": False
        }


@tool
def check_paid_lounge_membership(frequent_flier_number: str) -> Dict[str, Any]:
    """
    Check if a passenger has valid paid lounge memberships.
    
    Identifies specific lounge memberships and maps them to eligible lounges
    across different airlines and locations.
    
    Args:
        frequent_flier_number: The passenger's frequent flier number
        
    Returns:
        Dictionary containing membership types and eligible lounges
        
    Examples:
        - check_paid_lounge_membership("UA123456789")
        - check_paid_lounge_membership("AC456789123")
    """
    try:
        if not frequent_flier_number or not frequent_flier_number.strip():
            return {
                "success": False,
                "error": "Frequent flier number is required",
                "has_membership": False
            }
        
        passenger_data = _load_passenger_data()
        passenger = passenger_data.get(frequent_flier_number.strip())
        
        if not passenger:
            return {
                "success": True,
                "has_membership": False,
                "membership_types": [],
                "eligible_lounges": [],
                "message": "Passenger not found in database"
            }
        
        lounge_memberships = passenger.get('lounge_memberships', [])
        
        # Map memberships to eligible lounges
        eligible_lounges = []
        for membership in lounge_memberships:
            if 'United Club' in membership:
                eligible_lounges.extend(['United Club', 'Star Alliance Business Lounge'])
            elif 'Air Canada Maple Leaf Club' in membership:
                eligible_lounges.extend(['Air Canada Maple Leaf Lounge', 'Star Alliance Business Lounge'])
            elif 'Lufthansa Business Lounge' in membership:
                eligible_lounges.extend(['Lufthansa Business Lounge', 'Star Alliance Business Lounge'])
            else:
                eligible_lounges.append(membership)
        
        return {
            "success": True,
            "has_membership": len(lounge_memberships) > 0,
            "membership_types": lounge_memberships,
            "eligible_lounges": list(set(eligible_lounges)),  # Remove duplicates
            "frequent_flier_number": frequent_flier_number
        }
        
    except Exception as e:
        logger.error(f"Error checking paid membership: {e}")
        return {
            "success": False,
            "error": f"Paid membership check failed: {str(e)}",
            "has_membership": False
        }


@tool
def get_passenger_flight_history(
    frequent_flier_number: str, 
    months_back: int = 12
) -> Dict[str, Any]:
    """
    Get a passenger's flight history for the specified time period.
    
    Returns recent flight activity including routes, class of service, miles earned,
    and flight status information.
    
    Args:
        frequent_flier_number: The passenger's frequent flier number
        months_back: Number of months of history to retrieve (1-24, default: 12)
        
    Returns:
        Dictionary containing flight history and statistics
        
    Examples:
        - get_passenger_flight_history("UA123456789")
        - get_passenger_flight_history("LH987654321", months_back=6)
    """
    try:
        if not frequent_flier_number or not frequent_flier_number.strip():
            return {
                "success": False,
                "error": "Frequent flier number is required",
                "flight_history": []
            }
        
        # Clamp months_back to reasonable range
        months_back = max(1, min(months_back, 24))
        
        passenger_data = _load_passenger_data()
        passenger = passenger_data.get(frequent_flier_number.strip())
        
        if not passenger:
            return {
                "success": True,
                "flight_history": [],
                "message": "Passenger not found in database",
                "total_flights": 0
            }
        
        # Generate mock flight history based on segments flown
        segments_flown = passenger.get('segments_flown', 0)
        airline_code = passenger.get('airline', 'UA')[:2]
        flight_history = []
        
        for i in range(min(segments_flown, 10)):  # Limit to last 10 flights for demo
            flight_date = datetime.now() - timedelta(days=i*30 + 15)
            
            # Mock flight data
            flight = {
                "flight_number": f"{airline_code}{1000 + i}",
                "date": flight_date.strftime('%Y-%m-%d'),
                "route": f"JFK-LAX" if i % 2 == 0 else f"LAX-SFO",
                "class": "Business" if i % 3 == 0 else "Economy",
                "miles_earned": 2500 if i % 3 == 0 else 1200,
                "status": "completed"
            }
            flight_history.append(flight)
        
        return {
            "success": True,
            "flight_history": flight_history,
            "total_flights": len(flight_history),
            "months_requested": months_back,
            "frequent_flier_number": frequent_flier_number
        }
        
    except Exception as e:
        logger.error(f"Error getting flight history: {e}")
        return {
            "success": False,
            "error": f"Flight history retrieval failed: {str(e)}",
            "flight_history": []
        }

@tool
def calculate_tier_qualification_progress(frequent_flier_number: str) -> Dict[str, Any]:
    """
    Calculate a passenger's progress toward the next tier qualification.
    
    Analyzes current miles, segments, and tier status to determine qualification
    progress and requirements for the next tier level.
    
    Args:
        frequent_flier_number: The passenger's frequent flier number
        
    Returns:
        Dictionary containing tier progress and requirements
        
    Examples:
        - calculate_tier_qualification_progress("UA123456789")
        - calculate_tier_qualification_progress("LH987654321")
    """
    try:
        if not frequent_flier_number or not frequent_flier_number.strip():
            return {
                "success": False,
                "error": "Frequent flier number is required",
                "current_tier": "None"
            }
        
        passenger_data = _load_passenger_data()
        passenger = passenger_data.get(frequent_flier_number.strip())
        
        if not passenger:
            return {
                "success": True,
                "current_tier": "None",
                "next_tier": "Bronze",
                "progress": 0,
                "miles_needed": 25000,
                "message": "Passenger not found in database"
            }
        
        current_miles = passenger.get('year_to_date_miles', 0)
        current_tier = passenger.get('tier_status', 'Bronze')
        
        # Define tier thresholds (simplified)
        tier_thresholds = {
            'Bronze': 0,
            'Silver': 25000,
            'Gold': 75000,
            'Platinum': 125000
        }
        
        # Find next tier
        next_tier = None
        miles_needed = 0
        
        for tier, threshold in tier_thresholds.items():
            if current_miles < threshold:
                next_tier = tier
                miles_needed = threshold - current_miles
                break
        
        if not next_tier:
            next_tier = "Platinum+"
            miles_needed = 0
        
        # Calculate progress percentage
        if next_tier in tier_thresholds:
            current_threshold = tier_thresholds.get(current_tier, 0)
            next_threshold = tier_thresholds[next_tier]
            if next_threshold > current_threshold:
                progress = min(100, ((current_miles - current_threshold) / 
                                   (next_threshold - current_threshold)) * 100)
            else:
                progress = 100
        else:
            progress = 100
        
        return {
            "success": True,
            "current_tier": current_tier,
            "next_tier": next_tier,
            "progress": round(progress, 1),
            "miles_needed": miles_needed,
            "current_year_miles": current_miles,
            "total_lifetime_miles": passenger.get('total_miles', 0),
            "frequent_flier_number": frequent_flier_number
        }
        
    except Exception as e:
        logger.error(f"Error calculating tier progress: {e}")
        return {
            "success": False,
            "error": f"Tier calculation failed: {str(e)}",
            "current_tier": "Unknown"
        }


@tool
def validate_lounge_access_eligibility(
    frequent_flier_number: str,
    cabin_class: str,
    is_international: bool = True,
    airline: str = ""
) -> Dict[str, Any]:
    """
    Comprehensive lounge access eligibility validation.
    
    Checks all possible access methods including Gold status, premium cabin,
    and paid memberships to determine lounge access eligibility.
    
    Args:
        frequent_flier_number: The passenger's frequent flier number
        cabin_class: Class of service (Economy, Business, First)
        is_international: Whether this is an international flight
        airline: Airline code or name
        
    Returns:
        Dictionary containing eligibility decision and reasoning
        
    Examples:
        - validate_lounge_access_eligibility("UA123456789", "First", True, "United")
        - validate_lounge_access_eligibility("LH987654321", "Economy", False, "Lufthansa")
    """
    try:
        if not frequent_flier_number or not frequent_flier_number.strip():
            return {
                "success": False,
                "error": "Frequent flier number is required",
                "eligible": False
            }
        
        passenger_data = _load_passenger_data()
        passenger = passenger_data.get(frequent_flier_number.strip())
        
        if not passenger:
            return {
                "success": True,
                "eligible": False,
                "reason": "Passenger not found in frequent flier database",
                "access_type": None,
                "guest_allowed": False
            }
        
        # Check Star Alliance Gold status
        gold_status_result = check_star_alliance_gold_status(frequent_flier_number)
        gold_status = gold_status_result.get('has_status', False)
        
        # Check paid lounge membership
        membership_result = check_paid_lounge_membership(frequent_flier_number)
        has_membership = membership_result.get('has_membership', False)
        
        eligibility_result = {
            "success": True,
            "eligible": False,
            "reason": "",
            "access_type": None,
            "guest_allowed": False,
            "guest_count": 0,
            "passenger_data": passenger,
            "gold_status": gold_status_result,
            "paid_membership": membership_result
        }
        
        # Check eligibility based on various criteria
        if cabin_class.upper() == 'FIRST' and is_international:
            eligibility_result.update({
                "eligible": True,
                "reason": "International First Class passenger",
                "access_type": "First Class",
                "guest_allowed": True,
                "guest_count": 1
            })
        elif cabin_class.upper() == 'BUSINESS':
            eligibility_result.update({
                "eligible": True,
                "reason": "Business Class passenger",
                "access_type": "Business Class",
                "guest_allowed": False,
                "guest_count": 0
            })
        elif cabin_class.upper() == 'FIRST' and not is_international:
            # Special handling for United domestic First Class
            if 'united' in airline.lower():
                if gold_status:
                    eligibility_result.update({
                        "eligible": True,
                        "reason": "United domestic First Class with Star Alliance Gold status",
                        "access_type": "Star Alliance Gold",
                        "guest_allowed": True,
                        "guest_count": gold_status_result.get('companion_passes', 1)
                    })
                else:
                    eligibility_result.update({
                        "eligible": False,
                        "reason": "United domestic First Class does not qualify without Gold status",
                        "access_type": None
                    })
            else:
                eligibility_result.update({
                    "eligible": True,
                    "reason": "Domestic First Class passenger",
                    "access_type": "First Class",
                    "guest_allowed": True,
                    "guest_count": 1
                })
        elif gold_status:
            eligibility_result.update({
                "eligible": True,
                "reason": f"Star Alliance Gold member ({gold_status_result.get('status_level')})",
                "access_type": "Star Alliance Gold",
                "guest_allowed": True,
                "guest_count": gold_status_result.get('companion_passes', 1)
            })
        elif has_membership:
            membership_types = membership_result.get('membership_types', [])
            eligibility_result.update({
                "eligible": True,
                "reason": f"Paid lounge membership: {', '.join(membership_types)}",
                "access_type": "Paid Membership",
                "guest_allowed": True,
                "guest_count": 1
            })
        else:
            eligibility_result.update({
                "eligible": False,
                "reason": "No valid lounge access privileges found",
                "access_type": None
            })
        
        return eligibility_result
        
    except Exception as e:
        logger.error(f"Error validating lounge access: {e}")
        return {
            "success": False,
            "error": f"Lounge access validation failed: {str(e)}",
            "eligible": False
        }

