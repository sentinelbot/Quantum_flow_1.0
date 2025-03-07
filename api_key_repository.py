import logging
import uuid
from typing import Optional
from database.models.api_key import ApiKey
from database.models.user import User

logger = logging.getLogger(__name__)

class ApiKeyRepository:
    """Repository for managing API keys"""
    
    def __init__(self, db_manager=None, encryption_service=None):
        """
        Initialize repository with database manager and encryption service
        
        Args:
            db_manager: Database manager instance
            encryption_service: Encryption service for secure storage
        """
        self.db = db_manager
        self.encryption = encryption_service
        
    def save_api_key(self, user_id: int, exchange: str, api_key: str, api_secret: str) -> Optional[str]:
        """
        Save API key for a user
        
        Args:
            user_id: User ID
            exchange: Exchange name (e.g., 'binance')
            api_key: API key
            api_secret: API secret
            
        Returns:
            API key ID if successful, None otherwise
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return None
            
        session = self.db.get_session()
        try:
            # Generate a UUID for the API key
            key_id = str(uuid.uuid4())
            
            # Encrypt the API key and secret
            encrypted_key = self.encryption.encrypt(api_key)
            encrypted_secret = self.encryption.encrypt(api_secret)
            
            # Create a new API key record
            api_key_obj = ApiKey(
                id=key_id,
                user_id=user_id,
                exchange=exchange,
                encrypted_api_key=encrypted_key,
                encrypted_api_secret=encrypted_secret
            )
            
            session.add(api_key_obj)
            session.commit()
            
            # Update the user's api_key_id reference
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.api_key_id = key_id
                session.commit()
                
            logger.info(f"API key saved for user {user_id}, exchange {exchange}")
            return key_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving API key: {str(e)}", exc_info=True)
            return None
        finally:
            session.close()
            
    def get_api_key(self, api_key_id: str) -> Optional[tuple]:
        """
        Get API key and secret by ID
        
        Args:
            api_key_id: API key ID
            
        Returns:
            Tuple of (api_key, api_secret) or None if not found
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return None
            
        session = self.db.get_session()
        try:
            api_key = session.query(ApiKey).filter(ApiKey.id == api_key_id).first()
            if not api_key:
                return None
                
            # Decrypt the API key and secret
            decrypted_key = self.encryption.decrypt(api_key.encrypted_api_key)
            decrypted_secret = self.encryption.decrypt(api_key.encrypted_api_secret)
            
            return (decrypted_key, decrypted_secret)
        except Exception as e:
            logger.error(f"Error getting API key: {str(e)}", exc_info=True)
            return None
        finally:
            session.close()
            
    def get_user_api_keys(self, user_id: int) -> list:
        """
        Get all API keys for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of API key objects
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
            
        session = self.db.get_session()
        try:
            api_keys = session.query(ApiKey).filter(
                ApiKey.user_id == user_id,
                ApiKey.is_active == True
            ).all()
            
            return api_keys
        except Exception as e:
            logger.error(f"Error getting user API keys: {str(e)}", exc_info=True)
            return []
        finally:
            session.close()