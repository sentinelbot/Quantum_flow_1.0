"""
Encryption utilities for sensitive data
"""
import logging
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt

logger = logging.getLogger(__name__)

class Encryption:
    """
    Encryption and decryption utilities
    """
    def __init__(self, key: Optional[str] = None):
        # Use provided key or get from environment
        self.key = key or os.environ.get('ENCRYPTION_KEY')
        
        # If key not provided, generate one
        if not self.key:
            self.key = Fernet.generate_key().decode()
            logger.warning("No encryption key provided, generated new key")
            logger.warning(f"ENCRYPTION_KEY={self.key}")
            
        # Initialize Fernet cipher
        self.cipher = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string
        
        Args:
            data: String to encrypt
            
        Returns:
            Encrypted string (base64)
        """
        if not data:
            return ""
            
        try:
            # Convert to bytes and encrypt
            data_bytes = data.encode('utf-8')
            encrypted = self.cipher.encrypt(data_bytes)
            
            # Return as base64 string
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            encrypted_data: Encrypted string (base64)
            
        Returns:
            Decrypted string
        """
        if not encrypted_data:
            return ""
            
        try:
            # Decode base64 and decrypt
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted = self.cipher.decrypt(encrypted_bytes)
            
            # Return as string
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key
        
        Returns:
            Base64 encoded key
        """
        key = Fernet.generate_key()
        return key.decode('utf-8')
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple:
        """
        Derive encryption key from password
        
        Args:
            password: Password string
            salt: Salt bytes (optional)
            
        Returns:
            Tuple of (key, salt)
        """
        # Generate salt if not provided
        if salt is None:
            salt = os.urandom(16)
            
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def hash_password(self, password: str) -> tuple:
        """
        Hash a password with a random salt
        
        Args:
            password: Password to hash
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        # Generate a random salt
        salt = os.urandom(16)
        
        # Hash the password with the salt
        key, salt = self.derive_key_from_password(password, salt)
        
        # Return the hashed password and salt
        return key.decode('utf-8'), salt
    
    def verify_password(self, password: str, stored_hash: str, salt: bytes) -> bool:
        """
        Verify a password against a stored hash
        
        Args:
            password: Password to verify
            stored_hash: Stored password hash
            salt: Salt used for hashing
            
        Returns:
            True if password matches, False otherwise
        """
        # Hash the provided password with the same salt
        key, _ = self.derive_key_from_password(password, salt)
        
        # Compare the hashes
        return key.decode('utf-8') == stored_hash
    
    def generate_token(self, payload: dict, secret: str, expires_in: int = 86400) -> str:
        """
        Generate a JWT token
        
        Args:
            payload: Data to include in token
            secret: Secret key for signing
            expires_in: Expiration time in seconds (default: 24 hours)
            
        Returns:
            JWT token
        """
        import time
        
        # Add expiration time to payload
        payload['exp'] = int(time.time()) + expires_in
        
        # Generate the token
        token = jwt.encode(payload, secret, algorithm='HS256')
        
        # Return as string
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token
    
    def verify_token(self, token: str, secret: str) -> dict:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token
            secret: Secret used for signing
            
        Returns:
            Decoded payload or None if invalid
        """
        try:
            # Decode and verify the token
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None


# Create an alias for backward compatibility
EncryptionService = Encryption