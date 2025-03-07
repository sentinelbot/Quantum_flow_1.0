import re
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime

# Email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# API key validation regex (example pattern)
API_KEY_REGEX = re.compile(r"^[A-Za-z0-9]{32,64}$")

def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email format"""
    if not email:
        return False, "Email cannot be empty"
   
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"
       
    return True, None

def validate_api_keys(api_key: str, api_secret: str) -> Tuple[bool, Optional[str]]:
    """Validate API key and secret format"""
    if not api_key:
        return False, "API key cannot be empty"
       
    if not api_secret:
        return False, "API secret cannot be empty"
       
    if not API_KEY_REGEX.match(api_key):
        return False, "Invalid API key format"
       
    if len(api_secret) < 32:
        return False, "API secret too short"
       
    return True, None

def validate_trade_parameters(trading_pair: str, quantity: float, price: float = None) -> Tuple[bool, Optional[str]]:
    """Validate trade parameters"""
    # Validate trading pair
    if not trading_pair or not isinstance(trading_pair, str):
        return False, "Invalid trading pair"
   
    if not re.match(r"^[A-Z0-9]{2,8}/[A-Z0-9]{2,8}$", trading_pair):
        return False, "Trading pair must be in format BASE/QUOTE (e.g., BTC/USDT)"
   
    # Validate quantity
    if not quantity or quantity <= 0:
        return False, "Quantity must be greater than zero"
   
    # Validate price if provided
    if price is not None and price <= 0:
        return False, "Price must be greater than zero"
   
    return True, None

def validate_risk_level(risk_level: str) -> Tuple[bool, Optional[str]]:
    """Validate risk level setting"""
    valid_levels = ["LOW", "MEDIUM", "HIGH"]
   
    if not risk_level:
        return False, "Risk level cannot be empty"
   
    if risk_level.upper() not in valid_levels:
        return False, f"Risk level must be one of: {', '.join(valid_levels)}"
   
    return True, None

def validate_percentage(value: float, min_value: float = 0.0, max_value: float = 100.0) -> Tuple[bool, Optional[str]]:
    """Validate percentage value is within range"""
    if value < min_value or value > max_value:
        return False, f"Percentage must be between {min_value} and {max_value}"
   
    return True, None

def validate_user_settings(settings: Dict[str, Any]) -> Dict[str, str]:
    """Validate user settings dictionary and return dict of errors"""
    errors = {}
   
    # Validate risk level if present
    if "risk_level" in settings:
        is_valid, error = validate_risk_level(settings["risk_level"])
        if not is_valid:
            errors["risk_level"] = error
   
    # Validate trading pairs if present
    if "trading_pairs" in settings:
        if not isinstance(settings["trading_pairs"], list):
            errors["trading_pairs"] = "Trading pairs must be a list"
        else:
            for pair in settings["trading_pairs"]:
                is_valid, error = validate_trade_parameters(pair, 0.0)
                if not is_valid:
                    errors["trading_pairs"] = f"Invalid trading pair: {error}"
                    break
   
    # Validate other settings fields
    # ...
   
    return errors

def validate_config(config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate configuration and return tuple of (is_valid, error_message)"""
    errors = validate_user_settings(config)
    
    if errors:
        # Join all error messages into one string
        error_message = "; ".join([f"{key}: {value}" for key, value in errors.items()])
        return False, error_message
    
    return True, None