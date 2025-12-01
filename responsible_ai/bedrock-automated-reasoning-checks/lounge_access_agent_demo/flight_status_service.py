"""
Flight Status Service for Airport Lounge Access Agent
Handles flight status lookup and validation
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum


class FlightStatus(Enum):
    """Flight status enumeration"""
    ON_TIME = "On Time"
    DELAYED = "Delayed"
    CANCELLED = "Cancelled"
    DEPARTED = "Departed"
    ARRIVED = "Arrived"
    BOARDING = "Boarding"
    GATE_CLOSED = "Gate Closed"


class FlightType(Enum):
    """Flight type enumeration"""
    DOMESTIC = "Domestic"
    INTERNATIONAL = "International"
    CONNECTING = "Connecting"


class FlightStatusService:
    """Service for looking up flight status and information"""
    
    def __init__(self):
        # Mock flight database for demonstration
        self.flight_database = self._initialize_flight_database()
        
        # Airport country mapping (simplified)
        self.airport_countries = {
            # North America
            'JFK': 'US', 'LAX': 'US', 'ORD': 'US', 'DFW': 'US', 'DEN': 'US',
            'SFO': 'US', 'SEA': 'US', 'YYZ': 'CA', 'YVR': 'CA', 'YUL': 'CA',
            
            # Europe
            'LHR': 'GB', 'CDG': 'FR', 'FRA': 'DE', 'AMS': 'NL', 'ZUR': 'CH',
            'MUC': 'DE', 'FCO': 'IT', 'MAD': 'ES', 'ARN': 'SE', 'CPH': 'DK',
            'VIE': 'AT', 'ZAG': 'HR', 'WAW': 'PL', 'LIS': 'PT', 'BRU': 'BE',
            
            # Asia Pacific
            'NRT': 'JP', 'ICN': 'KR', 'SIN': 'SG', 'BKK': 'TH', 'HKG': 'HK',
            'TPE': 'TW', 'PVG': 'CN', 'DEL': 'IN', 'SYD': 'AU', 'MEL': 'AU',
            
            # Middle East & Africa
            'DXB': 'AE', 'DOH': 'QA', 'CAI': 'EG', 'IST': 'TR', 'JNB': 'ZA',
            'CPT': 'ZA', 'ADD': 'ET',
            
            # South America
            'GRU': 'BR', 'EZE': 'AR', 'SCL': 'CL', 'BOG': 'CO', 'LIM': 'PE'
        }
        
        # Regional groupings for international determination
        self.regions = {
            'North_America': ['US', 'CA', 'MX'],
            'Europe': ['GB', 'FR', 'DE', 'NL', 'CH', 'IT', 'ES', 'SE', 'DK', 'AT', 'HR', 'PL', 'PT', 'BE'],
            'Asia_Pacific': ['JP', 'KR', 'SG', 'TH', 'HK', 'TW', 'CN', 'IN', 'AU', 'NZ'],
            'Middle_East_Africa': ['AE', 'QA', 'EG', 'TR', 'ZA', 'ET'],
            'South_America': ['BR', 'AR', 'CL', 'CO', 'PE']
        }
    
    def _initialize_flight_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize mock flight database"""
        flights = {}
        
        # Generate mock flight data
        base_time = datetime.now()
        
        sample_flights = [
            {"flight": "UA1234", "origin": "JFK", "destination": "LAX", "airline": "United Airlines"},
            {"flight": "LH441", "origin": "FRA", "destination": "SIN", "airline": "Lufthansa"},
            {"flight": "AC8845", "origin": "YYZ", "destination": "NRT", "airline": "Air Canada"},
            {"flight": "SQ25", "origin": "SIN", "destination": "JFK", "airline": "Singapore Airlines"},
            {"flight": "TG917", "origin": "BKK", "destination": "FRA", "airline": "Thai Airways"},
            {"flight": "OS51", "origin": "VIE", "destination": "JFK", "airline": "Austrian Airlines"},
            {"flight": "LX8", "origin": "ZUR", "destination": "JFK", "airline": "Swiss International"},
            {"flight": "TK1", "origin": "IST", "destination": "JFK", "airline": "Turkish Airlines"},
            {"flight": "NH9", "origin": "NRT", "destination": "ORD", "airline": "ANA"},
            {"flight": "SK925", "origin": "ARN", "destination": "ORD", "airline": "SAS"}
        ]
        
        for i, flight_info in enumerate(sample_flights):
            flight_number = flight_info["flight"]
            departure_time = base_time + timedelta(hours=i*2 + 1)
            arrival_time = departure_time + timedelta(hours=8 + i)
            
            flights[flight_number] = {
                "flight_number": flight_number,
                "airline": flight_info["airline"],
                "origin": flight_info["origin"],
                "destination": flight_info["destination"],
                "scheduled_departure": departure_time.strftime('%Y-%m-%d %H:%M'),
                "scheduled_arrival": arrival_time.strftime('%Y-%m-%d %H:%M'),
                "actual_departure": None,
                "actual_arrival": None,
                "status": FlightStatus.ON_TIME.value if i % 3 != 0 else FlightStatus.DELAYED.value,
                "gate": f"A{10 + i}",
                "terminal": "1" if i % 2 == 0 else "2",
                "aircraft_type": "Boeing 777" if i % 2 == 0 else "Airbus A350",
                "delay_minutes": 0 if i % 3 != 0 else 30 + (i * 15),
                "delay_reason": None if i % 3 != 0 else "Air traffic control delay"
            }
        
        return flights
    
    def lookup_flight_status(self, flight_number: str) -> Optional[Dict[str, Any]]:
        """Look up flight status by flight number"""
        flight_number = flight_number.upper().strip()
        
        flight_info = self.flight_database.get(flight_number)
        if not flight_info:
            # Generate mock flight info if not found
            return self._generate_mock_flight_status(flight_number)
        
        # Add computed fields
        flight_info_copy = flight_info.copy()
        flight_info_copy.update({
            "flight_type": self.determine_flight_type(flight_info["origin"], flight_info["destination"]),
            "is_international": self.is_international_flight(flight_info["origin"], flight_info["destination"]),
            "estimated_duration": self._calculate_flight_duration(flight_info["origin"], flight_info["destination"]),
            "next_update": (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M')
        })
        
        return flight_info_copy
    
    def _generate_mock_flight_status(self, flight_number: str) -> Dict[str, Any]:
        """Generate mock flight status for unknown flights"""
        # Extract airline code from flight number
        airline_code = flight_number[:2] if len(flight_number) > 2 else "XX"
        
        # Default to common route for demo
        origin = "JFK"
        destination = "LAX"
        
        # Generate realistic times
        now = datetime.now()
        departure_time = now + timedelta(hours=2, minutes=30)
        arrival_time = departure_time + timedelta(hours=6)
        
        return {
            "flight_number": flight_number,
            "airline": f"Airline {airline_code}",
            "origin": origin,
            "destination": destination,
            "scheduled_departure": departure_time.strftime('%Y-%m-%d %H:%M'),
            "scheduled_arrival": arrival_time.strftime('%Y-%m-%d %H:%M'),
            "actual_departure": None,
            "actual_arrival": None,
            "status": FlightStatus.ON_TIME.value,
            "gate": "TBD",
            "terminal": "1",
            "aircraft_type": "Boeing 737",
            "delay_minutes": 0,
            "delay_reason": None,
            "flight_type": self.determine_flight_type(origin, destination),
            "is_international": self.is_international_flight(origin, destination),
            "estimated_duration": self._calculate_flight_duration(origin, destination),
            "next_update": (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M'),
            "data_source": "mock_generated"
        }
    
    def is_international_flight(self, origin: str, destination: str) -> bool:
        """Determine if a flight is international based on origin and destination"""
        origin_country = self.airport_countries.get(origin.upper())
        dest_country = self.airport_countries.get(destination.upper())
        
        # If we can't determine countries, assume international for safety
        if not origin_country or not dest_country:
            return True
        
        # Same country = domestic
        return origin_country != dest_country
    
    def determine_flight_type(self, origin: str, destination: str) -> str:
        """Determine flight type (Domestic, International, or Connecting)"""
        if self.is_international_flight(origin, destination):
            return FlightType.INTERNATIONAL.value
        else:
            return FlightType.DOMESTIC.value
    
    def _calculate_flight_duration(self, origin: str, destination: str) -> str:
        """Calculate estimated flight duration"""
        # Simplified duration calculation based on common routes
        duration_map = {
            ('JFK', 'LAX'): "6h 00m",
            ('LAX', 'JFK'): "5h 30m",
            ('JFK', 'LHR'): "7h 00m",
            ('LHR', 'JFK'): "8h 00m",
            ('FRA', 'SIN'): "12h 30m",
            ('SIN', 'FRA'): "13h 00m",
            ('YYZ', 'NRT'): "13h 30m",
            ('NRT', 'YYZ'): "11h 45m"
        }
        
        route = (origin.upper(), destination.upper())
        reverse_route = (destination.upper(), origin.upper())
        
        if route in duration_map:
            return duration_map[route]
        elif reverse_route in duration_map:
            return duration_map[reverse_route]
        else:
            # Estimate based on international vs domestic
            if self.is_international_flight(origin, destination):
                return "10h 30m"  # Default international
            else:
                return "3h 45m"   # Default domestic
    
    def validate_flight_eligibility(self, flight_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate flight for lounge access eligibility"""
        validation_result = {
            "valid": True,
            "issues": [],
            "departure_today": False,
            "is_star_alliance": False,
            "eligible_for_lounge": False
        }
        
        # Check if departure is within eligible timeframe (today or early tomorrow)
        try:
            scheduled_departure = datetime.strptime(
                flight_info.get('scheduled_departure', ''), '%Y-%m-%d %H:%M'
            )
            
            now = datetime.now()
            tomorrow_5am = (now + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
            
            if scheduled_departure.date() == now.date() or scheduled_departure <= tomorrow_5am:
                validation_result["departure_today"] = True
            else:
                validation_result["issues"].append("Flight departure not within eligible time window")
                
        except (ValueError, TypeError):
            validation_result["issues"].append("Invalid departure time format")
        
        # Check flight status eligibility
        status = flight_info.get('status', '')
        if status in [FlightStatus.CANCELLED.value, FlightStatus.DEPARTED.value, FlightStatus.ARRIVED.value]:
            validation_result["issues"].append(f"Flight status not eligible for lounge access: {status}")
        
        # Check if it's a Star Alliance flight (simplified check)
        airline = flight_info.get('airline', '').lower()
        star_alliance_airlines = [
            'united', 'lufthansa', 'air canada', 'singapore airlines', 'thai airways',
            'austrian', 'swiss', 'turkish', 'ana', 'sas', 'air china', 'asiana'
        ]
        
        validation_result["is_star_alliance"] = any(sa_airline in airline for sa_airline in star_alliance_airlines)
        
        if not validation_result["is_star_alliance"]:
            validation_result["issues"].append("Not a Star Alliance member airline flight")
        
        # Overall eligibility
        validation_result["eligible_for_lounge"] = (
            validation_result["departure_today"] and 
            validation_result["is_star_alliance"] and
            status not in [FlightStatus.CANCELLED.value, FlightStatus.DEPARTED.value, FlightStatus.ARRIVED.value]
        )
        
        validation_result["valid"] = len(validation_result["issues"]) == 0
        
        return validation_result
    
    def get_regional_info(self, airport_code: str) -> Dict[str, Any]:
        """Get regional information for an airport"""
        country = self.airport_countries.get(airport_code.upper(), 'Unknown')
        
        region = 'Unknown'
        for region_name, countries in self.regions.items():
            if country in countries:
                region = region_name.replace('_', ' ')
                break
        
        return {
            "airport_code": airport_code.upper(),
            "country": country,
            "region": region,
            "timezone": self._get_airport_timezone(airport_code)
        }
    
    def _get_airport_timezone(self, airport_code: str) -> str:
        """Get timezone for airport (simplified mapping)"""
        timezone_map = {
            # US
            'JFK': 'EST', 'LAX': 'PST', 'ORD': 'CST', 'DFW': 'CST',
            'DEN': 'MST', 'SFO': 'PST', 'SEA': 'PST',
            
            # Canada
            'YYZ': 'EST', 'YVR': 'PST', 'YUL': 'EST',
            
            # Europe
            'LHR': 'GMT', 'CDG': 'CET', 'FRA': 'CET', 'AMS': 'CET',
            'ZUR': 'CET', 'MUC': 'CET', 'VIE': 'CET',
            
            # Asia
            'NRT': 'JST', 'ICN': 'KST', 'SIN': 'SGT', 'BKK': 'ICT',
            'HKG': 'HKT', 'TPE': 'CST', 'PVG': 'CST', 'DEL': 'IST'
        }
        
        return timezone_map.get(airport_code.upper(), 'UTC')
    
    def check_connecting_flights(self, primary_flight: str, connection_window_hours: int = 24) -> List[Dict[str, Any]]:
        """Check for potential connecting flights within specified window"""
        primary_info = self.lookup_flight_status(primary_flight)
        if not primary_info:
            return []
        
        primary_arrival = datetime.strptime(primary_info['scheduled_arrival'], '%Y-%m-%d %H:%M')
        connecting_flights = []
        
        # Look for flights departing from the same destination airport
        destination = primary_info['destination']
        
        for flight_number, flight_info in self.flight_database.items():
            if flight_info['origin'] == destination:
                departure_time = datetime.strptime(flight_info['scheduled_departure'], '%Y-%m-%d %H:%M')
                
                # Check if within connection window
                time_diff = (departure_time - primary_arrival).total_seconds() / 3600
                
                if 1 <= time_diff <= connection_window_hours:  # 1-24 hour connection window
                    connecting_flights.append({
                        "flight_number": flight_number,
                        "departure": flight_info['scheduled_departure'],
                        "destination": flight_info['destination'],
                        "connection_time": f"{time_diff:.1f} hours",
                        "airline": flight_info['airline']
                    })
        
        return sorted(connecting_flights, key=lambda x: x['departure'])
    
    def update_flight_status(self, flight_number: str, status_update: Dict[str, Any]) -> bool:
        """Update flight status (mock operation for demo)"""
        if flight_number in self.flight_database:
            self.flight_database[flight_number].update(status_update)
            return True
        return False


# Utility functions
def get_flight_status_service() -> FlightStatusService:
    """Get a configured flight status service instance"""
    return FlightStatusService()


def create_sample_flight_queries() -> List[str]:
    """Create sample flight numbers for testing"""
    return [
        "UA1234",   # United Airlines - JFK to LAX (domestic)
        "LH441",    # Lufthansa - FRA to SIN (international)
        "AC8845",   # Air Canada - YYZ to NRT (international)
        "SQ25",     # Singapore Airlines - SIN to JFK (international)
        "TG917",    # Thai Airways - BKK to FRA (international)
        "XX9999"    # Non-existent flight (will generate mock data)
    ]
