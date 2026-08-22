"""
Field type detection for the BDA optimization application.
"""
import re
from typing import Literal

# Define field types
FieldType = Literal["text", "date", "numeric", "email", "phone", "address", "unknown"]

def detect_field_type(field_name: str, expected_output: str) -> FieldType:
    """
    Detect the likely type of a field based on name and expected output.
    
    Args:
        field_name: Name of the field
        expected_output: Expected output value
        
    Returns:
        FieldType: Detected field type
    """
    # Check for date patterns
    date_patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY, DD/MM/YYYY
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY/MM/DD
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'  # Month DD, YYYY
    ]
    
    # Check for numeric patterns
    numeric_patterns = [
        r'^\d+$',                          # Integers
        r'^\d+\.\d+$',                     # Decimals
        r'^\$\d+(?:\.\d{2})?$',            # Currency
        r'^\d{1,3}(?:,\d{3})*(?:\.\d+)?$'  # Formatted numbers
    ]
    
    # Check for email patterns
    email_patterns = [
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'  # Basic email pattern
    ]
    
    # Check for phone patterns
    phone_patterns = [
        r'^\+?1?\s*\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',  # US/Canada phone
        r'^\+?[0-9]{1,3}\s*\(?[0-9]{1,4}\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}$'  # International
    ]
    
    # Check field name for type hints
    name_lower = field_name.lower()
    if any(term in name_lower for term in ['date', 'day', 'month', 'year', 'time']):
        return "date"
    elif any(term in name_lower for term in ['amount', 'price', 'cost', 'fee', 'total', 'sum', 'number']):
        return "numeric"
    elif any(term in name_lower for term in ['email', 'mail']):
        return "email"
    elif any(term in name_lower for term in ['phone', 'fax', 'mobile', 'cell']):
        return "phone"
    elif any(term in name_lower for term in ['address', 'street', 'city', 'state', 'zip', 'postal']):
        return "address"
    
    # Check expected output for patterns
    for pattern in date_patterns:
        if re.search(pattern, expected_output):
            return "date"
    
    for pattern in numeric_patterns:
        if re.search(pattern, expected_output):
            return "numeric"
    
    for pattern in email_patterns:
        if re.search(pattern, expected_output):
            return "email"
    
    for pattern in phone_patterns:
        if re.search(pattern, expected_output):
            return "phone"
    
    # Default to text if no specific type detected
    return "text"
