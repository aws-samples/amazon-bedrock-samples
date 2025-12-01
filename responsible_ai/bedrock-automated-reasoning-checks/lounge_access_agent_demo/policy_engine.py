"""
Policy Engine for Airport Lounge Access Agent
Implements Star Alliance lounge access policies
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class AccessType(Enum):
    """Types of lounge access"""
    FIRST_CLASS_INTERNATIONAL = "International First Class"
    BUSINESS_CLASS_INTERNATIONAL = "International Business Class"
    FIRST_CLASS_DOMESTIC = "Domestic First Class"
    BUSINESS_CLASS_DOMESTIC = "Domestic Business Class"
    STAR_ALLIANCE_GOLD = "Star Alliance Gold"
    PAID_MEMBERSHIP = "Paid Lounge Membership"
    DENIED = "Access Denied"


class LoungeAccessPolicyEngine:
    """Implements lounge access policies based on the uploaded policy document"""
    
    def __init__(self):
        # Load the policy text for reference
        self.policy_text = self._load_policy_text()
        
        # Define access rules based on the policy
        self.access_rules = self._define_access_rules()
        
        # Special restrictions and exceptions
        self.special_restrictions = self._define_special_restrictions()
    
    def _load_policy_text(self) -> str:
        """Load the policy text from the uploaded file"""
        try:
            import os
            # Go up one directory to find uploads folder
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            policy_file = os.path.join(current_dir, 'uploads', 'Lounge Access Policy.txt')
            
            with open(policy_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not load policy file: {str(e)}")
            return "Policy file not available"
    
    def _define_access_rules(self) -> Dict[str, Dict[str, Any]]:
        """Define access rules based on Star Alliance policy"""
        return {
            "international_first": {
                "class_required": ["First"],
                "route_type": "International",
                "star_alliance_required": True,
                "guest_allowed": True,
                "guest_count": 1,
                "restrictions": ["same_day_departure", "star_alliance_logo"]
            },
            "international_business": {
                "class_required": ["Business"],
                "route_type": "International", 
                "star_alliance_required": True,
                "guest_allowed": False,
                "guest_count": 0,
                "restrictions": ["same_day_departure", "star_alliance_gold_logo"]
            },
            "domestic_first": {
                "class_required": ["First"],
                "route_type": "Domestic",
                "star_alliance_required": True,
                "guest_allowed": True,
                "guest_count": 1,
                "restrictions": ["same_day_departure", "member_airline_restrictions"]
            },
            "domestic_business": {
                "class_required": ["Business"],
                "route_type": "Domestic",
                "star_alliance_required": True,
                "guest_allowed": False,
                "guest_count": 0,
                "restrictions": ["same_day_departure", "member_airline_restrictions"]
            },
            "star_alliance_gold": {
                "class_required": ["First", "Business", "Premium Economy", "Economy"],
                "route_type": "Any",
                "star_alliance_required": True,
                "guest_allowed": True,
                "guest_count": 1,
                "gold_status_required": True,
                "restrictions": ["same_day_departure", "valid_gold_card", "star_alliance_gold_logo"]
            },
            "paid_membership": {
                "class_required": ["First", "Business", "Premium Economy", "Economy"],
                "route_type": "Any",
                "star_alliance_required": True,
                "membership_required": ["United Club", "Air Canada Maple Leaf Club - Worldwide"],
                "guest_allowed": True,
                "guest_count": 1,
                "restrictions": ["same_day_departure", "valid_membership_card"]
            }
        }
    
    def _define_special_restrictions(self) -> Dict[str, Dict[str, Any]]:
        """Define special restrictions and exceptions from the policy"""
        return {
            "united_domestic": {
                "description": "United Airlines domestic restrictions in USA",
                "applies_to": ["Domestic First Class", "Domestic Business Class"],
                "restriction": "Domestic First/Business Class customers do not have access to United's Club lounges in USA"
            },
            "united_gold_domestic": {
                "description": "United MileagePlus Gold domestic restriction", 
                "applies_to": ["Star Alliance Gold"],
                "restriction": "United MileagePlus Star Alliance Gold customers may only access United Clubs within the U.S. when departing on an international Star Alliance flight, not on domestic flights"
            },
            "ultra_premium_lounges": {
                "description": "Ultra-premium exclusive lounges",
                "lounges": [
                    "Lufthansa HON/First Class Lounges in Frankfurt and Munich",
                    "SWISS HON/First Class Lounges in Zurich and Geneva", 
                    "Austrian HON/First Class Lounges in Vienna",
                    "Thai Airways Spa Lounge in Bangkok",
                    "Singapore Airlines The Private Room in Singapore"
                ],
                "access": "Restricted to airline's own ultra-premium customers"
            },
            "contract_lounges": {
                "description": "Third-party contract lounges",
                "access_rules": {
                    "star_alliance_gold": True,
                    "first_class": True,
                    "paid_membership": False
                }
            },
            "time_restrictions": {
                "departure_window": "Same day departure or latest by 05:00 AM next morning",
                "guest_entry": "Guest must enter lounge together with eligible customer"
            }
        }
    
    def evaluate_access(self, passenger_info: Dict[str, Any], 
                       boarding_pass_info: Dict[str, Any],
                       flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to evaluate lounge access eligibility"""
        
        # Initialize result structure
        result = {
            "access_granted": False,
            "access_type": AccessType.DENIED.value,
            "guest_allowed": False,
            "guest_count": 0,
            "reason": "",
            "policy_details": "",
            "restrictions": [],
            "special_notes": []
        }
        
        # Basic validation
        if not self._validate_basic_requirements(boarding_pass_info, flight_info):
            result.update({
                "reason": "Flight does not meet basic requirements for lounge access",
                "policy_details": "Must be on a Star Alliance member airline operated flight departing same day or by 05:00 AM next morning"
            })
            return result
        
        # Check each access method in priority order
        access_methods = [
            self._check_international_first_access,
            self._check_international_business_access,
            self._check_domestic_first_access,
            self._check_domestic_business_access,
            self._check_star_alliance_gold_access,
            self._check_paid_membership_access
        ]
        
        for access_method in access_methods:
            access_result = access_method(passenger_info, boarding_pass_info, flight_info)
            if access_result["access_granted"]:
                result.update(access_result)
                break
        
        # Apply special restrictions
        result = self._apply_special_restrictions(result, passenger_info, boarding_pass_info, flight_info)
        
        return result
    
    def _validate_basic_requirements(self, boarding_pass_info: Dict[str, Any], 
                                   flight_info: Dict[str, Any]) -> bool:
        """Validate basic requirements for any lounge access"""
        
        # Must be Star Alliance flight
        if not flight_info.get("is_star_alliance", False):
            return False
        
        # Must depart same day or by 5 AM next morning
        if not flight_info.get("departure_today", False):
            return False
        
        # Flight must not be cancelled/departed/arrived
        invalid_statuses = ["Cancelled", "Departed", "Arrived"]
        if flight_info.get("status") in invalid_statuses:
            return False
        
        return True
    
    def _check_international_first_access(self, passenger_info: Dict[str, Any],
                                        boarding_pass_info: Dict[str, Any], 
                                        flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check International First Class access"""
        if (boarding_pass_info.get("class_of_service") == "First" and 
            flight_info.get("is_international", False)):
            
            return {
                "access_granted": True,
                "access_type": AccessType.FIRST_CLASS_INTERNATIONAL.value,
                "guest_allowed": True,
                "guest_count": 1,
                "reason": "International First Class passenger on Star Alliance flight",
                "policy_details": "First Class customers have access to International First Class and Star Alliance member carrier lounges (excluding ultra-premium exclusive lounges)",
                "restrictions": ["guest_must_be_on_same_flight", "same_day_departure"]
            }
        
        return {"access_granted": False}
    
    def _check_international_business_access(self, passenger_info: Dict[str, Any],
                                           boarding_pass_info: Dict[str, Any],
                                           flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check International Business Class access"""
        if (boarding_pass_info.get("class_of_service") == "Business" and 
            flight_info.get("is_international", False)):
            
            return {
                "access_granted": True,
                "access_type": AccessType.BUSINESS_CLASS_INTERNATIONAL.value,
                "guest_allowed": False,
                "guest_count": 0,
                "reason": "International Business Class passenger on Star Alliance flight",
                "policy_details": "Business Class customers have access to Star Alliance member carrier Business Class lounges",
                "restrictions": ["no_guest_privileges", "same_day_departure"]
            }
        
        return {"access_granted": False}
    
    def _check_domestic_first_access(self, passenger_info: Dict[str, Any],
                                   boarding_pass_info: Dict[str, Any],
                                   flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check Domestic First Class access"""
        if (boarding_pass_info.get("class_of_service") == "First" and 
            not flight_info.get("is_international", True)):
            
            return {
                "access_granted": True,
                "access_type": AccessType.FIRST_CLASS_DOMESTIC.value,
                "guest_allowed": True,
                "guest_count": 1,
                "reason": "Domestic First Class passenger on Star Alliance flight",
                "policy_details": "Some member airlines offer lounge access for Domestic First Class passengers. Guest must be on same Star Alliance flight.",
                "restrictions": ["guest_must_be_on_same_flight", "airline_specific_availability"],
                "special_notes": ["United Airlines domestic First Class customers do not have access to United's Club lounges in USA"]
            }
        
        return {"access_granted": False}
    
    def _check_domestic_business_access(self, passenger_info: Dict[str, Any],
                                      boarding_pass_info: Dict[str, Any],
                                      flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check Domestic Business Class access"""
        if (boarding_pass_info.get("class_of_service") == "Business" and 
            not flight_info.get("is_international", True)):
            
            return {
                "access_granted": True,
                "access_type": AccessType.BUSINESS_CLASS_DOMESTIC.value,
                "guest_allowed": False,
                "guest_count": 0,
                "reason": "Domestic Business Class passenger on Star Alliance flight",
                "policy_details": "Some member airlines offer lounge access for Domestic Business Class passengers.",
                "restrictions": ["no_guest_privileges", "airline_specific_availability"],
                "special_notes": ["United Airlines domestic Business Class customers do not have access to United's Club lounges in USA"]
            }
        
        return {"access_granted": False}
    
    def _check_star_alliance_gold_access(self, passenger_info: Dict[str, Any],
                                       boarding_pass_info: Dict[str, Any],
                                       flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check Star Alliance Gold status access"""
        
        gold_status = passenger_info.get("gold_status", {})
        if gold_status.get("has_status", False):
            
            return {
                "access_granted": True,
                "access_type": AccessType.STAR_ALLIANCE_GOLD.value,
                "guest_allowed": True,
                "guest_count": min(gold_status.get("companion_passes", 1), 1),  # Max 1 guest per policy
                "reason": f"Star Alliance Gold member ({gold_status.get('status_level', 'Gold')})",
                "policy_details": "Star Alliance Gold customers traveling in any class have access to member airline lounges displaying the Star Alliance Gold logo",
                "restrictions": ["guest_must_be_on_same_flight", "valid_gold_card_required", "star_alliance_gold_logo_required"]
            }
        
        return {"access_granted": False}
    
    def _check_paid_membership_access(self, passenger_info: Dict[str, Any],
                                    boarding_pass_info: Dict[str, Any],
                                    flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check paid lounge membership access"""
        
        paid_membership = passenger_info.get("paid_membership", {})
        if paid_membership.get("has_membership", False):
            
            eligible_memberships = ["United Club", "Air Canada Maple Leaf Club - Worldwide"]
            member_types = paid_membership.get("membership_types", [])
            
            if any(membership in str(member_types) for membership in eligible_memberships):
                return {
                    "access_granted": True,
                    "access_type": AccessType.PAID_MEMBERSHIP.value,
                    "guest_allowed": True,
                    "guest_count": 1,
                    "reason": f"Valid paid lounge membership: {', '.join(member_types)}",
                    "policy_details": "Eligible Paid Lounge Membership customers (United Club, Air Canada Maple Leaf Club) have access to Star Alliance Business Class lounges",
                    "restrictions": ["guest_must_be_on_same_flight", "valid_membership_card_required", "star_alliance_logo_required"]
                }
        
        return {"access_granted": False}
    
    def _apply_special_restrictions(self, result: Dict[str, Any],
                                  passenger_info: Dict[str, Any],
                                  boarding_pass_info: Dict[str, Any], 
                                  flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply special restrictions and exceptions"""
        
        if not result.get("access_granted", False):
            return result
        
        # United Airlines domestic restrictions
        airline = flight_info.get("airline", "").lower()
        is_domestic = not flight_info.get("is_international", True)
        
        if "united" in airline and is_domestic:
            access_type = result.get("access_type", "")
            
            # Domestic First/Business Class restriction
            if access_type in [AccessType.FIRST_CLASS_DOMESTIC.value, AccessType.BUSINESS_CLASS_DOMESTIC.value]:
                result.update({
                    "access_granted": False,
                    "reason": "United Airlines domestic First/Business Class customers do not have access to United's Club lounges in USA",
                    "policy_details": "Special restriction applies to United Airlines domestic flights in USA"
                })
                return result
            
            # Star Alliance Gold domestic restriction for United MileagePlus members
            if (access_type == AccessType.STAR_ALLIANCE_GOLD.value and 
                passenger_info.get("passenger_data", {}).get("airline") == "United Airlines"):
                
                result.update({
                    "access_granted": False,
                    "reason": "United MileagePlus Star Alliance Gold customers may only access United Clubs within the U.S. when departing on international flights",
                    "policy_details": "Special restriction for United MileagePlus Gold members on domestic flights"
                })
                return result
        
        # Add general restrictions
        if result.get("access_granted", False):
            general_restrictions = [
                "Flight must depart same day or by 05:00 AM next morning",
                "Lounge must display appropriate Star Alliance logo at entrance"
            ]
            
            if result.get("guest_allowed", False):
                general_restrictions.extend([
                    "Guest must enter lounge together with eligible customer",
                    "Guest must be traveling on same Star Alliance flight",
                    "Guest must depart from same airport on same day"
                ])
            
            # Merge with existing restrictions
            existing_restrictions = result.get("restrictions", [])
            result["restrictions"] = list(set(existing_restrictions + general_restrictions))
        
        return result
    
    def get_policy_text(self) -> str:
        """Get the full policy text for reference"""
        return self.policy_text
    
    def get_access_rules_summary(self) -> Dict[str, Any]:
        """Get a summary of all access rules"""
        return {
            "access_methods": list(self.access_rules.keys()),
            "special_restrictions": list(self.special_restrictions.keys()),
            "policy_loaded": len(self.policy_text) > 50
        }
    
    def validate_policy_compliance(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that a decision complies with the policy"""
        validation_result = {
            "compliant": True,
            "issues": [],
            "recommendations": []
        }
        
        if decision.get("access_granted", False):
            access_type = decision.get("access_type", "")
            
            # Check for proper justification
            if not decision.get("reason"):
                validation_result["issues"].append("Access granted without proper justification")
                validation_result["compliant"] = False
            
            # Check guest allowances
            guest_count = decision.get("guest_count", 0)
            guest_allowed = decision.get("guest_allowed", False)
            
            if guest_count > 0 and not guest_allowed:
                validation_result["issues"].append("Guest count specified but guests not allowed")
                validation_result["compliant"] = False
            
            if guest_allowed and guest_count > 1:
                validation_result["issues"].append("More than one guest allowed - policy limits to one guest")
                validation_result["compliant"] = False
            
            # Check for required restrictions
            restrictions = decision.get("restrictions", [])
            required_restrictions = ["same_day_departure"]
            
            missing_restrictions = [r for r in required_restrictions if r not in str(restrictions)]
            if missing_restrictions:
                validation_result["recommendations"].append(f"Consider adding restrictions: {missing_restrictions}")
        
        return validation_result


# Utility function to get policy engine
def get_policy_engine() -> LoungeAccessPolicyEngine:
    """Get a configured policy engine instance"""
    return LoungeAccessPolicyEngine()


# Demo function for testing policy scenarios
def create_test_scenarios() -> List[Dict[str, Any]]:
    """Create test scenarios for policy validation"""
    return [
        {
            "name": "International First Class - Valid",
            "passenger": {"gold_status": {"has_status": False}},
            "boarding_pass": {"class_of_service": "First"},
            "flight": {"is_international": True, "is_star_alliance": True, "departure_today": True, "status": "On Time"}
        },
        {
            "name": "Star Alliance Gold - Valid", 
            "passenger": {"gold_status": {"has_status": True, "status_level": "Gold", "companion_passes": 1}},
            "boarding_pass": {"class_of_service": "Economy"},
            "flight": {"is_international": False, "is_star_alliance": True, "departure_today": True, "status": "On Time"}
        },
        {
            "name": "United Domestic First - Restricted",
            "passenger": {"gold_status": {"has_status": False}},
            "boarding_pass": {"class_of_service": "First"},
            "flight": {"is_international": False, "is_star_alliance": True, "departure_today": True, "status": "On Time", "airline": "United Airlines"}
        },
        {
            "name": "Non-Star Alliance - Denied",
            "passenger": {"gold_status": {"has_status": False}},
            "boarding_pass": {"class_of_service": "First"},
            "flight": {"is_international": True, "is_star_alliance": False, "departure_today": True, "status": "On Time"}
        }
    ]
