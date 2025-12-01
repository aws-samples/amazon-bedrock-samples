"""
Boarding Pass Validator for Airport Lounge Access Agent
Handles parsing and validation of boarding pass information
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, validator


class BoardingPassInfo(BaseModel):
    """Structured boarding pass information"""
    passenger_name: str
    flight_number: str
    airline_code: str
    airline_name: str
    departure_airport: str
    arrival_airport: str
    departure_date: str
    departure_time: str
    seat_number: str
    class_of_service: str
    ticket_number: str
    frequent_flier_number: Optional[str] = None
    gate: Optional[str] = None
    boarding_group: Optional[str] = None
    
    @validator('class_of_service')
    def validate_class_of_service(cls, v):
        valid_classes = ['First', 'Business', 'Premium Economy', 'Economy']
        if v not in valid_classes:
            return 'Economy'  # Default fallback
        return v


class BoardingPassValidator:
    """Validates and extracts information from boarding passes"""
    
    # Star Alliance member airlines mapping
    STAR_ALLIANCE_AIRLINES = {
        'AC': 'Air Canada',
        'AD': 'Azul Brazilian Airlines',
        'AI': 'Air India', 
        'AV': 'Avianca',
        'BR': 'EVA Air',
        'CA': 'Air China',
        'CM': 'Copa Airlines',
        'ET': 'Ethiopian Airlines',
        'LH': 'Lufthansa',
        'LO': 'LOT Polish Airlines',
        'LX': 'Swiss International Air Lines',
        'MS': 'EgyptAir',
        'NH': 'All Nippon Airways',
        'NZ': 'Air New Zealand',
        'OS': 'Austrian Airlines',
        'OU': 'Croatia Airlines',
        'OZ': 'Asiana Airlines',
        'SA': 'South African Airways',
        'SK': 'SAS Scandinavian Airlines',
        'SN': 'Brussels Airlines',
        'SQ': 'Singapore Airlines',
        'TG': 'Thai Airways International',
        'TK': 'Turkish Airlines',
        'TP': 'TAP Air Portugal',
        'UA': 'United Airlines'
    }
    
    # International route patterns (simplified for demo)
    INTERNATIONAL_ROUTES = {
        # North America to Europe
        'US-EU': ['JFK-LHR', 'LAX-FRA', 'ORD-ZUR', 'SFO-MUC'],
        # North America to Asia  
        'US-AS': ['SFO-NRT', 'LAX-ICN', 'SEA-TPE', 'JFK-DEL'],
        # Europe to Asia
        'EU-AS': ['LHR-SIN', 'FRA-BKK', 'ZUR-HKG', 'MUC-NRT'],
        # Transcontinental
        'TRANS': ['LAX-SYD', 'JFK-GRU', 'LHR-JNB', 'FRA-CPT']
    }
    
    def __init__(self):
        self.domestic_airports_us = [
            'JFK', 'LAX', 'ORD', 'DFW', 'DEN', 'SFO', 'SEA', 'LAS', 'PHX', 'IAH',
            'MCO', 'EWR', 'MSP', 'DTW', 'PHL', 'LGA', 'FLL', 'BWI', 'MDW', 'DCA'
        ]
    
    def parse_boarding_pass(self, boarding_pass_text: str) -> Optional[BoardingPassInfo]:
        """Parse boarding pass text and extract information"""
        try:
            # Clean the input text
            text = boarding_pass_text.strip().upper()
            
            # Extract basic flight information using regex patterns
            flight_pattern = r'([A-Z]{2})(\d{3,4})'
            flight_match = re.search(flight_pattern, text)
            
            if not flight_match:
                return None
            
            airline_code = flight_match.group(1)
            flight_number = airline_code + flight_match.group(2)
            
            # Get airline name
            airline_name = self.STAR_ALLIANCE_AIRLINES.get(airline_code, f"Unknown Airline ({airline_code})")
            
            # Extract airports (simplified pattern)
            airport_pattern = r'\b([A-Z]{3})\b'
            airports = re.findall(airport_pattern, text)
            
            if len(airports) < 2:
                # Provide defaults for demo
                airports = ['JFK', 'LAX']
            
            departure_airport = airports[0]
            arrival_airport = airports[1]
            
            # Extract passenger name (simplified)
            name_patterns = [
                r'([A-Z]+/[A-Z]+)',  # LASTNAME/FIRSTNAME format
                r'MR\s+([A-Z\s]+)',   # MR FIRSTNAME LASTNAME
                r'MS\s+([A-Z\s]+)',   # MS FIRSTNAME LASTNAME  
            ]
            
            passenger_name = "DEMO PASSENGER"
            for pattern in name_patterns:
                match = re.search(pattern, text)
                if match:
                    passenger_name = match.group(1).replace('/', ' ')
                    break
            
            # Extract seat number
            seat_pattern = r'\b(\d{1,2}[A-F])\b'
            seat_match = re.search(seat_pattern, text)
            seat_number = seat_match.group(1) if seat_match else "12A"
            
            # Determine class of service based on seat or keywords
            class_of_service = self._determine_class_of_service(text, seat_number)
            
            # Extract or generate other fields
            ticket_number = self._extract_ticket_number(text)
            frequent_flier_number = self._extract_frequent_flier_number(text)
            gate = self._extract_gate(text)
            boarding_group = self._determine_boarding_group(class_of_service)
            
            # Generate realistic date/time
            departure_date, departure_time = self._generate_flight_datetime()
            
            return BoardingPassInfo(
                passenger_name=passenger_name,
                flight_number=flight_number,
                airline_code=airline_code,
                airline_name=airline_name,
                departure_airport=departure_airport,
                arrival_airport=arrival_airport,
                departure_date=departure_date,
                departure_time=departure_time,
                seat_number=seat_number,
                class_of_service=class_of_service,
                ticket_number=ticket_number,
                frequent_flier_number=frequent_flier_number,
                gate=gate,
                boarding_group=boarding_group
            )
            
        except Exception as e:
            print(f"Error parsing boarding pass: {str(e)}")
            return None
    
    def _determine_class_of_service(self, text: str, seat_number: str) -> str:
        """Determine class of service from text and seat number"""
        text_upper = text.upper()
        
        # Check for explicit class indicators
        if any(keyword in text_upper for keyword in ['FIRST', 'F CLASS', '1ST']):
            return 'First'
        elif any(keyword in text_upper for keyword in ['BUSINESS', 'J CLASS', 'BUS']):
            return 'Business'
        elif any(keyword in text_upper for keyword in ['PREMIUM', 'PREM ECO', 'W CLASS']):
            return 'Premium Economy'
        
        # Infer from seat number (simplified logic)
        if seat_number:
            row_num = int(re.search(r'\d+', seat_number).group())
            if row_num <= 3:
                return 'First'
            elif row_num <= 10:
                return 'Business'
            elif row_num <= 20:
                return 'Premium Economy'
        
        return 'Economy'
    
    def _extract_ticket_number(self, text: str) -> str:
        """Extract ticket number from boarding pass text"""
        # Look for various ticket number patterns
        patterns = [
            r'TKT\s*(\d{13})',
            r'TICKET\s*(\d{13})',
            r'\b(\d{13})\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Generate demo ticket number
        return f"0{datetime.now().strftime('%y%m%d')}{hash(text) % 100000:05d}"
    
    def _extract_frequent_flier_number(self, text: str) -> Optional[str]:
        """Extract frequent flier number from boarding pass text"""
        patterns = [
            r'FF\s*([A-Z]{2}\d{6,12})',
            r'FREQ\s*([A-Z]{2}\d{6,12})',
            r'\b([A-Z]{2}\d{9})\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_gate(self, text: str) -> Optional[str]:
        """Extract gate information from boarding pass text"""
        gate_pattern = r'GATE\s*([A-Z]?\d{1,3}[A-Z]?)'
        match = re.search(gate_pattern, text)
        if match:
            return match.group(1)
        
        # Generate demo gate
        return f"A{hash(text) % 30 + 1:02d}"
    
    def _determine_boarding_group(self, class_of_service: str) -> str:
        """Determine boarding group based on class of service"""
        if class_of_service == 'First':
            return '1'
        elif class_of_service == 'Business':
            return '2'
        elif class_of_service == 'Premium Economy':
            return '3'
        else:
            return '5'
    
    def _generate_flight_datetime(self) -> tuple:
        """Generate realistic flight date and time"""
        # Generate a date within next 24 hours for demo
        now = datetime.now()
        flight_time = now + timedelta(hours=2, minutes=30)
        
        departure_date = flight_time.strftime('%Y-%m-%d')
        departure_time = flight_time.strftime('%H:%M')
        
        return departure_date, departure_time
    
    def is_star_alliance_flight(self, airline_code: str) -> bool:
        """Check if the flight is operated by a Star Alliance member"""
        return airline_code in self.STAR_ALLIANCE_AIRLINES
    
    def is_international_flight(self, departure_airport: str, arrival_airport: str) -> bool:
        """Determine if flight is international based on airports"""
        # Simplified logic - check if both airports are in the same country
        # For demo purposes, assume US domestic if both are in US airport list
        
        us_domestic = (departure_airport in self.domestic_airports_us and 
                      arrival_airport in self.domestic_airports_us)
        
        return not us_domestic
    
    def validate_boarding_pass_eligibility(self, boarding_pass: BoardingPassInfo) -> Dict[str, Any]:
        """Validate boarding pass for lounge access eligibility"""
        validation_result = {
            "valid": True,
            "issues": [],
            "is_star_alliance": False,
            "is_international": False,
            "departure_today": False
        }
        
        # Check if Star Alliance flight
        if not self.is_star_alliance_flight(boarding_pass.airline_code):
            validation_result["issues"].append("Not a Star Alliance member airline flight")
        else:
            validation_result["is_star_alliance"] = True
        
        # Check if international
        validation_result["is_international"] = self.is_international_flight(
            boarding_pass.departure_airport, boarding_pass.arrival_airport
        )
        
        # Check if departure is today or early tomorrow
        try:
            flight_date = datetime.strptime(boarding_pass.departure_date, '%Y-%m-%d')
            now = datetime.now()
            tomorrow_5am = (now + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
            
            validation_result["departure_today"] = flight_date.date() == now.date() or flight_date <= tomorrow_5am
            
            if not validation_result["departure_today"]:
                validation_result["issues"].append("Flight departure not within eligible time window")
                
        except ValueError:
            validation_result["issues"].append("Invalid departure date format")
        
        validation_result["valid"] = len(validation_result["issues"]) == 0
        
        return validation_result


# Demo function to create sample boarding passes
def create_sample_boarding_passes() -> List[str]:
    """Create sample boarding pass texts for testing"""
    return [
        """
        BOARDING PASS
        UNITED AIRLINES
        PASSENGER: SMITH/JOHN
        FLIGHT: UA1234
        FROM: JFK TO: LAX
        DATE: 2024-10-18 TIME: 14:30
        SEAT: 3A GATE: B12
        CLASS: FIRST
        TICKET: 0161234567890
        FF: UA123456789
        """,
        """
        LUFTHANSA
        JOHNSON/SARAH
        LH441 BUSINESS CLASS
        FRA -> SIN
        SEAT 8C GATE A15
        DATE 18OCT24 1930
        TKT: 0201987654321
        """,
        """
        AIR CANADA AC8845
        CHEN/MICHAEL  
        YYZ-NRT
        ECONOMY 24F
        GATE C22
        DEP: 18-10-2024 08:15
        MAPLE LEAF: AC555777999
        """
    ]
