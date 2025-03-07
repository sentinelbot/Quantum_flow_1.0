import json
import time
import hashlib
import random
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

def generate_unique_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    timestamp = int(time.time() * 1000)
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{prefix}{timestamp}{random_str}"

def format_currency(value: float, currency: str = "USD", precision: int = 2) -> str:
    """Format a value as currency string"""
    if currency.upper() in ["BTC", "ETH", "SOL"]:
        # Use more decimal places for crypto
        precision = 8
    return f"{value:.{precision}f} {currency.upper()}"

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / abs(old_value)) * 100.0

def convert_timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert unix timestamp to datetime object"""
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

def convert_datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime object to unix timestamp"""
    return int(dt.timestamp() * 1000)

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely load JSON string with default fallback"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def truncate_string(s: str, max_length: int = 100) -> str:
    """Truncate string to maximum length with ellipsis"""
    if len(s) <= max_length:
        return s
    return s[:max_length-3] + "..."

def hash_data(data: Any) -> str:
    """Create SHA-256 hash of any data"""
    if not isinstance(data, str):
        data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()

def retry_operation(func, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry a function with exponential backoff"""
    retry_count = 0
    while retry_count < max_retries:
        try:
            return func()
        except Exception as e:
            retry_count += 1
            if retry_count == max_retries:
                raise e
            time.sleep(delay)
            delay *= backoff