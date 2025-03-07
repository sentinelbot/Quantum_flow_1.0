# security/auth.py
import logging
import time
from typing import Dict, Any, Optional, Tuple
import jwt
import secrets
import string
import uuid

from security.encryption import Encryption

logger = logging.getLogger(__name__)

class Auth:
    """
    Authentication system
    """
    def __init__(self, db, jwt_secret: str, token_expiry: int = 86400):
        self.db = db
        self.jwt_secret = jwt_secret
        self.token_expiry = token_expiry
        self.encryption = Encryption()
        
        logger.info("Auth system initialized")
        
    def register_user(self, email: str, password: str, telegram_id: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Register a new user
        
        Args:
            email: User email
            password: User password
            telegram_id: User's Telegram ID
            
        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and user data or error
        """
        try:
            # Check if user already exists
            user_repo = self.db.get_repository('user')
            if user_repo:
                # Check if email exists
                existing_user = user_repo.get_user_by_email(email)
                if existing_user:
                    logger.warning(f"User with email {email} already exists")
                    return False, {"error": "Email already registered"}
                    
                # Check if Telegram ID exists
                if telegram_id:
                    existing_user = user_repo.get_user_by_telegram_id(telegram_id)
                    if existing_user:
                        logger.warning(f"User with Telegram ID {telegram_id} already exists")
                        return False, {"error": "Telegram ID already registered"}
                        
                # Hash password
                hashed_password, salt = self.encryption.hash_password(password)
                
                # Generate referral code
                referral_code = self._generate_referral_code()
                
                # Create user
                user = user_repo.create_user(
                    email=email,
                    telegram_id=telegram_id,
                    password_hash=hashed_password,
                    password_salt=salt,
                    referral_code=referral_code
                )
                
                if user:
                    logger.info(f"User registered: {email}")
                    
                    # Return user data
                    return True, {
                        "user_id": user.id,
                        "email": user.email,
                        "telegram_id": user.telegram_id,
                        "referral_code": user.referral_code
                    }
                    
            logger.error(f"Failed to register user: {email}")
            return False, {"error": "Registration failed"}
            
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return False, {"error": str(e)}
            
    def login(self, email: str, password: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Login user with email and password
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and user data with token or error
        """
        try:
            # Get user
            user_repo = self.db.get_repository('user')
            if user_repo:
                user = user_repo.get_user_by_email(email)
                
                if user:
                    # Verify password
                    if self.encryption.verify_password(password, user.password_hash, user.password_salt):
                        # Generate token
                        token = self.generate_token(user.id)
                        
                        # Update last login
                        user_repo.update_user(user.id, last_login_at=int(time.time()))
                        
                        logger.info(f"User logged in: {email}")
                        
                        # Return user data with token
                        return True, {
                            "user_id": user.id,
                            "email": user.email,
                            "telegram_id": user.telegram_id,
                            "token": token
                        }
                    else:
                        logger.warning(f"Invalid password for user: {email}")
                        return False, {"error": "Invalid email or password"}
                else:
                    logger.warning(f"User not found: {email}")
                    return False, {"error": "Invalid email or password"}
                    
            logger.error(f"Failed to login user: {email}")
            return False, {"error": "Login failed"}
            
        except Exception as e:
            logger.error(f"Error logging in user: {str(e)}")
            return False, {"error": str(e)}
            
    def telegram_login(self, telegram_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Login user with Telegram ID
        
        Args:
            telegram_id: User's Telegram ID
            
        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and user data with token or error
        """
        try:
            # Get user
            user_repo = self.db.get_repository('user')
            if user_repo:
                user = user_repo.get_user_by_telegram_id(telegram_id)
                
                if user:
                    # Generate token
                    token = self.generate_token(user.id)
                    
                    # Update last login
                    user_repo.update_user(user.id, last_login_at=int(time.time()))
                    
                    logger.info(f"User logged in via Telegram: {telegram_id}")
                    
                    # Return user data with token
                    return True, {
                        "user_id": user.id,
                        "email": user.email,
                        "telegram_id": user.telegram_id,
                        "token": token
                    }
                else:
                    logger.warning(f"User not found with Telegram ID: {telegram_id}")
                    return False, {"error": "User not found"}
                    
            logger.error(f"Failed to login user with Telegram ID: {telegram_id}")
            return False, {"error": "Login failed"}
            
        except Exception as e:
            logger.error(f"Error logging in user with Telegram ID: {str(e)}")
            return False, {"error": str(e)}
            
    def verify_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify authentication token
        
        Args:
            token: JWT token
            
        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and payload or error
        """
        try:
            # Verify token
            payload = self.encryption.verify_token(token, self.jwt_secret)
            
            if payload:
                # Check if user exists
                user_repo = self.db.get_repository('user')
                if user_repo:
                    user = user_repo.get_user_by_id(payload.get('user_id'))
                    
                    if user:
                        return True, payload
                    else:
                        logger.warning(f"User not found for token: {payload.get('user_id')}")
                        return False, {"error": "Invalid token"}
                        
            logger.warning("Invalid token")
            return False, {"error": "Invalid token"}
            
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return False, {"error": str(e)}
            
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change user password
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get user
            user_repo = self.db.get_repository('user')
            if user_repo:
                user = user_repo.get_user_by_id(user_id)
                
                if user:
                    # Verify current password
                    if self.encryption.verify_password(current_password, user.password_hash, user.password_salt):
                        # Hash new password
                        hashed_password, salt = self.encryption.hash_password(new_password)
                        
                        # Update password
                        success = user_repo.update_user(
                            user_id,
                            password_hash=hashed_password,
                            password_salt=salt
                        )
                        
                        if success:
                            logger.info(f"Password changed for user {user_id}")
                            return True
                            
                    else:
                        logger.warning(f"Invalid current password for user {user_id}")
                        return False
                        
            logger.error(f"Failed to change password for user {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return False
            
    def reset_password(self, email: str) -> Tuple[bool, str]:
        """
        Reset user password
        
        Args:
            email: User email
            
        Returns:
            Tuple[bool, str]: Success flag and reset token or error
        """
        try:
            # Get user
            user_repo = self.db.get_repository('user')
            if user_repo:
                user = user_repo.get_user_by_email(email)
                
                if user:
                    # Generate reset token
                    reset_token = str(uuid.uuid4())
                    
                    # Store reset token
                    success = user_repo.update_user(
                        user.id,
                        password_reset_token=reset_token,
                        password_reset_expiry=int(time.time()) + 86400  # 24 hours
                    )
                    
                    if success:
                        logger.info(f"Password reset initiated for user {user.id}")
                        return True, reset_token
                        
                else:
                    logger.warning(f"User not found: {email}")
                    return False, "User not found"
                    
            logger.error(f"Failed to reset password for user: {email}")
            return False, "Reset failed"
            
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            return False, str(e)
            
    def complete_password_reset(self, reset_token: str, new_password: str) -> bool:
        """
        Complete password reset process
        
        Args:
            reset_token: Password reset token
            new_password: New password
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get user by reset token
            user_repo = self.db.get_repository('user')
            if user_repo:
                user = user_repo.get_user_by_reset_token(reset_token)
                
                if user:
                    # Check if token is expired
                    if user.password_reset_expiry < int(time.time()):
                        logger.warning(f"Reset token expired for user {user.id}")
                        return False
                        
                    # Hash new password
                    hashed_password, salt = self.encryption.hash_password(new_password)
                    
                    # Update password and clear reset token
                    success = user_repo.update_user(
                        user.id,
                        password_hash=hashed_password,
                        password_salt=salt,
                        password_reset_token=None,
                        password_reset_expiry=None
                    )
                    
                    if success:
                        logger.info(f"Password reset completed for user {user.id}")
                        return True
                        
                else:
                    logger.warning(f"Invalid reset token: {reset_token}")
                    return False
                    
            logger.error(f"Failed to complete password reset")
            return False
            
        except Exception as e:
            logger.error(f"Error completing password reset: {str(e)}")
            return False
            
    def generate_token(self, user_id: int) -> str:
        """
        Generate authentication token
        
        Args:
            user_id: User ID
            
        Returns:
            str: JWT token
        """
        try:
            # Create payload
            payload = {
                "user_id": user_id,
                "iat": int(time.time()),
                "jti": str(uuid.uuid4())
            }
            
            # Generate token
            token = self.encryption.generate_token(payload, self.jwt_secret, self.token_expiry)
            
            return token
            
        except Exception as e:
            logger.error(f"Error generating token: {str(e)}")
            return ""
            
    def _generate_referral_code(self, length: int = 8) -> str:
        """
        Generate a random referral code
        
        Args:
            length: Length of the referral code
            
        Returns:
            str: Referral code
        """
        # Define character set
        characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
        
        # Generate code
        code = ''.join(secrets.choice(characters) for _ in range(length))
        
        return code
        
    def validate_email(self, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        import re
        
        # Simple email validation regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        return bool(re.match(pattern, email))
        
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple[bool, str]: Valid flag and reason if invalid
        """
        # Check length
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
            
        # Check for at least one digit
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
            
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
            
        # Check for at least one lowercase letter
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
            
        return True, ""


# Add these standalone functions to support the dashboard API

def authenticate_admin(username, password):
    """
    Authenticate an admin user based on credentials.
    
    Args:
        username: Admin username (email)
        password: Admin password
        
    Returns:
        User object if authenticated as admin, None otherwise
    """
    from database.db import DatabaseManager
    from config.app_config import AppConfig
    
    # Get database and config instances
    db = DatabaseManager.get_instance()
    config = AppConfig.get_instance()
    
    # Create auth instance
    auth = Auth(db, config.get("security.jwt_secret"))
    
    # Authenticate user
    success, user_data = auth.login(username, password)
    
    # Check if user is admin
    if success and user_data.get("user_id") in config.get("admin.admin_user_ids", []):
        # Get user repository
        user_repo = db.get_repository('user')
        return user_repo.get_user_by_id(user_data.get("user_id"))
    
    return None

def create_access_token(data, expires_delta=None):
    """
    Create a JWT access token.
    
    Args:
        data: Data to include in token (dictionary with 'sub' key for user email)
        expires_delta: Token expiration time in seconds
        
    Returns:
        JWT token string
    """
    from database.db import DatabaseManager
    from config.app_config import AppConfig
    
    # Get database and config instances
    db = DatabaseManager.get_instance()
    config = AppConfig.get_instance()
    
    # Create auth instance
    auth = Auth(db, config.get("security.jwt_secret"))
    
    # Get user ID from email
    user_repo = db.get_repository('user')
    user = user_repo.get_user_by_email(data.get("sub"))
    
    if user:
        # Generate token with user_id
        return auth.generate_token(user.id)
    
    return ""

# Create an alias for backward compatibility
AuthenticationService = Auth