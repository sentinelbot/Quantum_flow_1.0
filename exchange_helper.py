import logging
from typing import Optional

from exchange.exchange_factory import ExchangeFactory
from database.repository.api_key_repository import ApiKeyRepository
from database.repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

class ExchangeHelper:
    """
    Helper class to connect exchange instances with user API keys
    """
    
    def __init__(self, exchange_factory, api_key_repository, user_repository):
        """
        Initialize helper with required repositories
        
        Args:
            exchange_factory: Factory for creating exchange instances
            api_key_repository: Repository for API keys
            user_repository: Repository for user data
        """
        self.exchange_factory = exchange_factory
        self.api_key_repo = api_key_repository
        self.user_repo = user_repository
        
    def get_user_exchange(self, user_id: int, exchange_name: Optional[str] = None) -> Optional[object]:
        """
        Get exchange instance for a user with their API keys
        
        Args:
            user_id: User ID
            exchange_name: Exchange name (optional, defaults to user's preferred exchange)
            
        Returns:
            Exchange instance or None if not available
        """
        try:
            # Get user data
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None
                
            # Determine exchange name
            if not exchange_name:
                exchange_name = user.preferred_exchange or "binance"
                
            # Get API key ID from user
            api_key_id = user.api_key_id
            if not api_key_id:
                logger.warning(f"User {user_id} has no API key configured")
                return None
                
            # Get API credentials
            credentials = self.api_key_repo.get_api_key(api_key_id)
            if not credentials:
                logger.warning(f"API key {api_key_id} not found")
                return None
                
            api_key, api_secret = credentials
            
            # Create exchange instance
            exchange = self.exchange_factory.create_exchange(
                exchange_name=exchange_name,
                api_key=api_key,
                api_secret=api_secret
            )
            
            # Initialize the exchange
            if exchange and not exchange.initialize():
                logger.warning(f"Failed to initialize exchange {exchange_name} for user {user_id}")
                return None
                
            return exchange
        except Exception as e:
            logger.error(f"Error getting user exchange: {str(e)}", exc_info=True)
            return None