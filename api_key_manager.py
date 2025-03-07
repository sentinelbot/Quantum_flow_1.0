"""
API Key Management
"""

import logging
import time
import uuid
from typing import Dict, Optional, Tuple

from database.db import Database
from security.encryption import Encryption

logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Manages API keys for exchanges
    """
    def __init__(self, db: Database, encryption=None):
        self.db = db
        self.encryption = encryption if encryption else Encryption()
        self.logger = logger
        
    def add_api_keys(self, user_id: int, exchange: str, api_key: str, api_secret: str) -> bool:
        """
        Add API keys for a user
        
        Args:
            user_id: User ID
            exchange: Exchange name
            api_key: API key
            api_secret: API secret
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Encrypt API keys
            encrypted_key = self.encryption.encrypt(api_key)
            encrypted_secret = self.encryption.encrypt(api_secret)
            
            # Get user repository
            user_repo = self.db.get_repository('user')
            
            # Store encrypted keys
            result = user_repo.save_api_keys(
                user_id=user_id,
                exchange=exchange,
                api_key=encrypted_key,
                api_secret=encrypted_secret
            )
            
            return result
        except Exception as e:
            logger.error(f"Failed to add API keys for user {user_id}: {str(e)}")
            return False
    
    def get_api_keys(self, user_id: int, exchange: str = None) -> Optional[Dict[str, str]]:
        """
        Get API keys for a user
        
        Args:
            user_id: User ID
            exchange: Exchange name (optional)
            
        Returns:
            Dict with api_key and secret_key, or None if not found
        """
        try:
            # Get user repository
            user_repo = self.db.get_repository('user')
            
            # Get encrypted keys
            encrypted_keys = user_repo.get_api_keys(user_id, exchange)
            
            if not encrypted_keys:
                return None
                
            # Decrypt keys
            return {
                'api_key': self.encryption.decrypt(encrypted_keys['api_key']),
                'secret_key': self.encryption.decrypt(encrypted_keys['api_secret']),
                'exchange': encrypted_keys['exchange']
            }
        except Exception as e:
            logger.error(f"Failed to get API keys for user {user_id}: {str(e)}")
            return None
    
    def delete_api_keys(self, user_id: int, exchange: str = None) -> bool:
        """
        Delete API keys for a user
        
        Args:
            user_id: User ID
            exchange: Exchange name (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get user repository
            user_repo = self.db.get_repository('user')
            
            # Delete keys
            result = user_repo.delete_api_keys(user_id, exchange)
            
            return result
        except Exception as e:
            logger.error(f"Failed to delete API keys for user {user_id}: {str(e)}")
            return False
    
    def validate_api_keys(self, exchange: str, api_key: str, api_secret: str) -> bool:
        """
        Validate API keys with exchange
        
        Args:
            exchange: Exchange name
            api_key: API key
            api_secret: API secret
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Create exchange instance to test keys
            from exchange.exchange_factory import ExchangeFactory
            factory = ExchangeFactory()
            
            exchange_instance = factory.create_exchange(exchange, api_key, api_secret)
            if not exchange_instance:
                return False
                
            # Test connection
            result = exchange_instance.initialize()
            exchange_instance.close()
            
            return result
        except Exception as e:
            logger.error(f"Failed to validate API keys: {str(e)}")
            return False
            
    def verify_binance_keys(self, api_key: str, api_secret: str) -> Tuple[bool, Optional[str]]:
        """
        Verify Binance API keys by testing with the account endpoint
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            
        Returns:
            Tuple[bool, Optional[str]]: (Success status, Error message if any)
        """
        try:
            import hmac
            import hashlib
            import time
            import requests
            
            # Test endpoint
            endpoint = "https://api.binance.com/api/v3/account"
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"
            
            # Create signature
            signature = hmac.new(
                api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Make request
            headers = {'X-MBX-APIKEY': api_key}
            url = f"{endpoint}?{query_string}&signature={signature}"
            response = requests.get(url, headers=headers)
            
            # Check response
            if response.status_code == 200:
                self.logger.info("API key verification successful")
                return True, None
            else:
                error_msg = f"API key verification failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error verifying API keys: {e}"
            self.logger.error(error_msg)
            return False, error_msg