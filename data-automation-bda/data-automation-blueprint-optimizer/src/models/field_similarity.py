"""
Field type detection and specialized similarity functions for different field types.
"""
from enum import Enum
import re
from typing import Optional
import datetime
from dateutil import parser as date_parser
import numpy as np
from sentence_transformers import SentenceTransformer, util


class FieldType(Enum):
    """
    Enum for different field types.
    """
    TEXT = "text"
    DATE = "date"
    NUMERIC = "numeric"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"


def detect_field_type(field_name: str, expected_output: str, schema_type: str = "string") -> FieldType:
    """
    Detect the field type based on field name, expected output, and schema type.
    
    Args:
        field_name: Name of the field
        expected_output: Expected output value
        schema_type: Type from schema.json
        
    Returns:
        FieldType: Detected field type
    """
    # Convert field name to lowercase for case-insensitive matching
    field_name_lower = field_name.lower()
    
    # Check for name fields (which should be text, not date)
    name_keywords = ["name", "vendor", "company", "organization", "client", "customer", "supplier"]
    if any(keyword in field_name_lower for keyword in name_keywords):
        return FieldType.TEXT
    
    # Check for date fields
    date_keywords = ["date", "day", "month", "year", "dob", "birth", "expiry", "expiration", "start", "end"]
    if any(keyword in field_name_lower for keyword in date_keywords):
        return FieldType.DATE
    
    # Check for numeric fields
    numeric_keywords = ["amount", "price", "cost", "fee", "number", "count", "quantity", "total", "sum", "percent", "rate"]
    if any(keyword in field_name_lower for keyword in numeric_keywords):
        return FieldType.NUMERIC
    
    # Check for email fields
    email_keywords = ["email", "e-mail", "mail"]
    if any(keyword in field_name_lower for keyword in email_keywords):
        return FieldType.EMAIL
    
    # Check for phone fields
    phone_keywords = ["phone", "mobile", "cell", "telephone", "fax"]
    if any(keyword in field_name_lower for keyword in phone_keywords):
        return FieldType.PHONE
    
    # Check for address fields
    address_keywords = ["address", "street", "city", "state", "zip", "postal", "country"]
    if any(keyword in field_name_lower for keyword in address_keywords):
        return FieldType.ADDRESS
    
    # If no match by field name, try to detect from expected output format
    
    # Check if expected output looks like an email
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', expected_output):
        return FieldType.EMAIL
    
    # Check if expected output looks like a phone number
    if re.match(r'^\+?[\d\s\(\)-]{7,}$', expected_output):
        return FieldType.PHONE
    
    # Check if expected output looks like a number
    if re.match(r'^[$€£¥]?\s*\d+([.,]\d+)?%?$', expected_output):
        return FieldType.NUMERIC
    
    # Check if expected output looks like a date
    # This check is moved lower in priority to avoid false positives
    try:
        date_parser.parse(expected_output)
        # If parsing succeeds and the string contains separators like /, -, or spaces
        if re.search(r'[/\-\s]', expected_output):
            return FieldType.DATE
    except (ValueError, TypeError):
        pass
    
    # Default to text
    return FieldType.TEXT


def calculate_date_similarity(date1_str: str, date2_str: str) -> float:
    """
    Calculate similarity between two dates.
    
    Args:
        date1_str: First date as string
        date2_str: Second date as string
        
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        # Parse dates
        date1 = date_parser.parse(date1_str)
        date2 = date_parser.parse(date2_str)
        
        # Calculate difference in days
        diff_days = abs((date1 - date2).days)
        
        # Normalize to 0-1 range (closer to 1 is more similar)
        # Using a sigmoid-like function that gives high similarity for small differences
        # and rapidly decreases for larger differences
        similarity = 1.0 / (1.0 + (diff_days / 7.0))  # 7 days difference gives 0.5 similarity
        
        return similarity
    except Exception:
        # Fallback to text similarity if date parsing fails
        return calculate_semantic_similarity(date1_str, date2_str)


def calculate_numeric_similarity(num1_str: str, num2_str: str) -> float:
    """
    Calculate similarity between two numeric values.
    
    Args:
        num1_str: First number as string
        num2_str: Second number as string
        
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        # Clean and parse numbers
        num1_clean = re.sub(r'[^\d.]', '', num1_str.replace(',', '.'))
        num2_clean = re.sub(r'[^\d.]', '', num2_str.replace(',', '.'))
        
        num1 = float(num1_clean)
        num2 = float(num2_clean)
        
        # Handle zero values to avoid division by zero
        if num1 == 0 and num2 == 0:
            return 1.0
        elif num1 == 0 or num2 == 0:
            return 0.0
        
        # Calculate relative difference
        max_val = max(abs(num1), abs(num2))
        min_val = min(abs(num1), abs(num2))
        
        # Similarity based on ratio (always between 0 and 1)
        similarity = min_val / max_val
        
        return similarity
    except Exception:
        # Fallback to text similarity if numeric parsing fails
        return calculate_semantic_similarity(num1_str, num2_str)


def calculate_email_similarity(email1: str, email2: str) -> float:
    """
    Calculate similarity between two email addresses.
    
    Args:
        email1: First email
        email2: Second email
        
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        # Normalize emails to lowercase
        email1 = email1.lower().strip()
        email2 = email2.lower().strip()
        
        # Exact match
        if email1 == email2:
            return 1.0
        
        # Split into username and domain
        try:
            username1, domain1 = email1.split('@')
            username2, domain2 = email2.split('@')
            
            # Domain match is weighted higher (0.6) than username match (0.4)
            domain_similarity = 1.0 if domain1 == domain2 else 0.0
            username_similarity = calculate_semantic_similarity(username1, username2)
            
            return 0.6 * domain_similarity + 0.4 * username_similarity
        except ValueError:
            # If splitting fails, use text similarity
            return calculate_semantic_similarity(email1, email2)
    except Exception:
        # Fallback to text similarity
        return calculate_semantic_similarity(email1, email2)


def calculate_phone_similarity(phone1: str, phone2: str) -> float:
    """
    Calculate similarity between two phone numbers.
    
    Args:
        phone1: First phone number
        phone2: Second phone number
        
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        # Normalize phone numbers (remove non-digit characters)
        digits1 = re.sub(r'\D', '', phone1)
        digits2 = re.sub(r'\D', '', phone2)
        
        # Exact match after normalization
        if digits1 == digits2:
            return 1.0
        
        # If one is a substring of the other (e.g., with/without country code)
        if digits1 in digits2 or digits2 in digits1:
            # Calculate similarity based on length ratio
            return min(len(digits1), len(digits2)) / max(len(digits1), len(digits2))
        
        # Calculate digit-by-digit similarity
        # Focus on the last digits which are usually more important
        min_len = min(len(digits1), len(digits2))
        if min_len < 4:
            return 0.0
        
        # Compare last N digits
        last_digits_to_compare = min(min_len, 8)  # Compare up to last 8 digits
        last_digits1 = digits1[-last_digits_to_compare:]
        last_digits2 = digits2[-last_digits_to_compare:]
        
        # Count matching digits
        matches = sum(d1 == d2 for d1, d2 in zip(last_digits1, last_digits2))
        
        return matches / last_digits_to_compare
    except Exception:
        # Fallback to text similarity
        return calculate_semantic_similarity(phone1, phone2)


def calculate_address_similarity(addr1: str, addr2: str) -> float:
    """
    Calculate similarity between two addresses.
    
    Args:
        addr1: First address
        addr2: Second address
        
    Returns:
        float: Similarity score between 0 and 1
    """
    # Preprocess addresses
    addr1 = preprocess_address(addr1)
    addr2 = preprocess_address(addr2)
    
    # For addresses, semantic similarity works well
    return calculate_semantic_similarity(addr1, addr2)


def preprocess_address(address: str) -> str:
    """
    Preprocess address by normalizing common abbreviations.
    
    Args:
        address: Address string
        
    Returns:
        str: Preprocessed address
    """
    # Convert to lowercase
    address = address.lower()
    
    # Normalize common abbreviations
    replacements = {
        'st.': 'street',
        'st ': 'street ',
        'rd.': 'road',
        'rd ': 'road ',
        'ave.': 'avenue',
        'ave ': 'avenue ',
        'blvd.': 'boulevard',
        'blvd ': 'boulevard ',
        'apt.': 'apartment',
        'apt ': 'apartment ',
        'ste.': 'suite',
        'ste ': 'suite ',
        'n.': 'north',
        'n ': 'north ',
        's.': 'south',
        's ': 'south ',
        'e.': 'east',
        'e ': 'east ',
        'w.': 'west',
        'w ': 'west ',
    }
    
    for abbr, full in replacements.items():
        address = address.replace(abbr, full)
    
    return address


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two texts using sentence embeddings.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        float: Similarity score between 0 and 1
    """
    try:
        # Handle empty strings
        if not text1 or not text2:
            return 0.0 if (not text1 and text2) or (text1 and not text2) else 1.0
        
        # Convert to string if not already
        text1 = str(text1)
        text2 = str(text2)
        
        # Exact match
        if text1.lower() == text2.lower():
            return 1.0
        
        # Load the model (this should ideally be cached)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Encode texts
        embeddings = model.encode([text1, text2], convert_to_tensor=True)
        
        # Calculate cosine similarity
        similarity = util.cos_sim(embeddings[0], embeddings[1])
        
        return float(similarity.item())
    except Exception as e:
        print(f"Error in semantic similarity calculation: {e}")
        
        # Fallback to simple string matching
        text1 = str(text1).lower()
        text2 = str(text2).lower()
        
        if text1 == text2:
            return 1.0
        elif text1 in text2 or text2 in text1:
            return 0.8
        else:
            return 0.0


def calculate_field_similarity(field_name: str, expected: str, actual: str, field_type: Optional[FieldType] = None) -> float:
    """
    Calculate similarity based on detected or provided field type.
    
    Args:
        field_name: Name of the field
        expected: Expected output value
        actual: Actual output value
        field_type: Field type (optional)
        
    Returns:
        float: Similarity score between 0 and 1
    """
    # Handle None or empty values
    if expected is None or actual is None:
        return 0.0 if (expected is None and actual is not None) or (expected is not None and actual is None) else 1.0
    
    expected = str(expected).strip()
    actual = str(actual).strip()
    
    # Exact match check
    if expected.lower() == actual.lower():
        return 1.0
    
    # Detect field type if not provided
    if field_type is None:
        field_type = detect_field_type(field_name, expected)
    
    # Select appropriate similarity function
    if field_type == FieldType.DATE:
        return calculate_date_similarity(expected, actual)
    elif field_type == FieldType.NUMERIC:
        return calculate_numeric_similarity(expected, actual)
    elif field_type == FieldType.EMAIL:
        return calculate_email_similarity(expected, actual)
    elif field_type == FieldType.PHONE:
        return calculate_phone_similarity(expected, actual)
    elif field_type == FieldType.ADDRESS:
        return calculate_address_similarity(expected, actual)
    else:  # Default to semantic similarity for text
        return calculate_semantic_similarity(expected, actual)
