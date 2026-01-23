"""
Input Validation Utilities
"""
import re
from typing import Dict, Optional
from config import config, VALID_ROLES
from .app_settings import get_setting

def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email format
    Returns (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, None


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password
    Returns (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    min_password_length = get_setting('min_password_length', config.MIN_PASSWORD_LENGTH)

    if len(password) < min_password_length:
        return False, f"Password must be at least {min_password_length} characters"

    return True, None


def validate_phone(phone: str) -> tuple[bool, Optional[str]]:
    """
    Validate phone number (basic validation)
    Returns (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if it's all digits and reasonable length
    if not cleaned.isdigit() or len(cleaned) < 8 or len(cleaned) > 15:
        return False, "Invalid phone number format"
    
    return True, None


def validate_name(name: str, field_name: str = "Name") -> tuple[bool, Optional[str]]:
    """
    Validate name fields
    Returns (is_valid, error_message)
    """
    if not name:
        return False, f"{field_name} is required"
    
    if len(name) < 2:
        return False, f"{field_name} must be at least 2 characters"
    
    if len(name) > 100:
        return False, f"{field_name} must be less than 100 characters"
    
    return True, None


def validate_role(role: str) -> tuple[bool, Optional[str]]:
    """
    Validate role
    Returns (is_valid, error_message)
    """
    if not role:
        return False, "Role is required"
    
    if role not in VALID_ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
    
    return True, None


def validate_registration_data(data: Dict) -> tuple[bool, Optional[Dict]]:
    """
    Validate registration data
    Returns (is_valid, errors_dict)
    """
    errors = {}
    
    # Validate email
    valid, error = validate_email(data.get('email', ''))
    if not valid:
        errors['email'] = error
    
    # Validate password
    valid, error = validate_password(data.get('password', ''))
    if not valid:
        errors['password'] = error
    
    # Validate first name
    valid, error = validate_name(data.get('first_name', ''), "First name")
    if not valid:
        errors['first_name'] = error
    
    # Validate last name
    valid, error = validate_name(data.get('last_name', ''), "Last name")
    if not valid:
        errors['last_name'] = error
    
    # Validate phone (optional but if provided, must be valid)
    phone = data.get('phone')
    if phone:
        valid, error = validate_phone(phone)
        if not valid:
            errors['phone'] = error
    
    return len(errors) == 0, errors if errors else None


def validate_login_data(data: Dict) -> tuple[bool, Optional[Dict]]:
    """
    Validate login data
    Returns (is_valid, errors_dict)
    """
    errors = {}
    
    # Validate email
    valid, error = validate_email(data.get('email', ''))
    if not valid:
        errors['email'] = error
    
    # Validate password
    if not data.get('password'):
        errors['password'] = "Password is required"
    
    return len(errors) == 0, errors if errors else None


def validate_verification_data(data: Dict) -> tuple[bool, Optional[Dict]]:
    """
    Validate verification data
    Returns (is_valid, errors_dict)
    """
    errors = {}
    
    # Validate user_id
    if not data.get('user_id'):
        errors['user_id'] = "User ID is required"
    
    # Validate code
    code = data.get('code', '')
    if not code:
        errors['code'] = "Verification code is required"
    elif not code.isdigit():
        errors['code'] = "Verification code must be numeric"
    elif len(code) != 6:
        errors['code'] = "Verification code must be 6 digits"
    
    # Validate code_type
    code_type = data.get('code_type', '')
    if not code_type:
        errors['code_type'] = "Code type is required"
    elif code_type not in ['email', 'sms']:
        errors['code_type'] = "Code type must be 'email' or 'sms'"
    
    return len(errors) == 0, errors if errors else None
