import time
import logging
import functools
from typing import Callable, Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def log_execution(func):
    """Decorator to log function execution time and result"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.4f} seconds: {str(e)}")
            raise
    return wrapper

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions=(Exception,)):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (in seconds)
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Function {func.__name__} failed after {attempt} attempts: {str(e)}")
                        raise
                    
                    logger.warning(f"Retry {attempt}/{max_attempts} for {func.__name__} in {current_delay:.2f}s: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

def admin_required(func):
    """Decorator to ensure user is an admin"""
    @functools.wraps(func)
    def wrapper(self, update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if not hasattr(self, 'admin_ids') or user_id not in self.admin_ids:
            logger.warning(f"Unauthorized access attempt to {func.__name__} by user {user_id}")
            update.message.reply_text("You are not authorized to use this command.")
            return
        return func(self, update, context, *args, **kwargs)
    return wrapper

def validate_input(validator: Callable):
    """
    Decorator to validate function input using a validator function
    
    The validator function should return (is_valid, error_message) tuple
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            is_valid, error = validator(*args, **kwargs)
            if not is_valid:
                logger.warning(f"Validation failed for {func.__name__}: {error}")
                raise ValueError(error)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def cache_result(ttl_seconds: int = 60):
    """
    Decorator to cache function results for specified time
    
    Args:
        ttl_seconds: Time to live for cached results in seconds
    """
    cache = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create key from function name, args and kwargs
            key = str(func.__name__) + str(args) + str(sorted(kwargs.items()))
            
            # Check if result is in cache and still valid
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        
        # Add function to clear cache
        wrapper.clear_cache = lambda: cache.clear()
        return wrapper
    return decorator