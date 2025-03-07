"""
Application configuration
"""

import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class AppConfig:
    """
    Application configuration
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Get singleton instance
        
        Returns:
            AppConfig: Singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, config_file=None):
        self.config = {}
        self.config_file = config_file
        
        # Load configuration
        self._load_config()
        
        # Database URL
        self.db_url = self._get_db_url()
    
    def _load_config(self):
        """
        Load configuration from file and environment
        """
        # Default configuration
        self.config = {
            "app": {
                "name": "QuantumFlow Trading Bot",
                "version": "1.0.0",
                "environment": "development"
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "quantumflow",
                "user": "quantumuser",
                "password": "your_password"
            },
            "telegram": {
                "bot_token": "",
                "admin_bot_token": ""
            },
            "admin": {
                "admin_user_ids": []
            },
            "trading": {
                "default_risk_level": "medium",
                "paper_trading_balance": 10000.0,
                "exchange": "binance"
            },
            "logging": {
                "level": "INFO",
                "file": "logs/quantumflow.log"
            },
            "security": {
                "jwt_secret": "your_jwt_secret_key",
                "encryption_key": "your_encryption_key"
            },
            "profit": {
                "fees": {
                    "admin_wallet": "YOUR_WALLET_ADDRESS_HERE",
                    "fee_percentage": 0.1
                }
            }
        }
        
        # Load from config file if provided
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self._merge_config(self.config, file_config)
                logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading configuration file: {str(e)}")
        
        # Override with environment variables
        self._load_from_env()
        
        # Validate admin wallet configuration
        self._validate_admin_wallet()
    
    def _validate_admin_wallet(self):
        """
        Validate that admin wallet address is configured
        """
        admin_wallet = self.get('profit.fees.admin_wallet')
        if not admin_wallet or admin_wallet == "YOUR_WALLET_ADDRESS_HERE":
            logger.warning("Admin wallet address is missing or using default placeholder value")
            
            # Check for environment variable
            if os.environ.get('ADMIN_WALLET_ADDRESS'):
                self._set_config_value('profit.fees.admin_wallet', os.environ.get('ADMIN_WALLET_ADDRESS'))
                logger.info("Admin wallet address set from environment variable")
    
    def _set_config_value(self, path, value):
        """
        Set a configuration value at the specified path
        
        Args:
            path: Configuration key (dot notation)
            value: Value to set
        """
        parts = path.split('.')
        config = self.config
        
        # Navigate to the correct location in the config dictionary
        for i, part in enumerate(parts[:-1]):
            if part not in config:
                config[part] = {}
            config = config[part]
            
        # Set the value
        config[parts[-1]] = value
    
    def _merge_config(self, target, source):
        """
        Recursively merge dictionaries
        
        Args:
            target: Target dictionary
            source: Source dictionary
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
    
    def _load_from_env(self):
        """
        Load configuration from environment variables
        """
        # Database configuration
        if os.environ.get('DB_HOST'):
            self.config['database']['host'] = os.environ.get('DB_HOST')
            
        if os.environ.get('DB_PORT'):
            self.config['database']['port'] = int(os.environ.get('DB_PORT'))
            
        if os.environ.get('DB_NAME'):
            self.config['database']['database'] = os.environ.get('DB_NAME')
            
        if os.environ.get('DB_USER'):
            self.config['database']['user'] = os.environ.get('DB_USER')
            
        if os.environ.get('DB_PASSWORD'):
            self.config['database']['password'] = os.environ.get('DB_PASSWORD')
            
        # Telegram configuration
        if os.environ.get('TELEGRAM_BOT_TOKEN'):
            self.config['telegram']['bot_token'] = os.environ.get('TELEGRAM_BOT_TOKEN')
            
        if os.environ.get('ADMIN_BOT_TOKEN'):
            self.config['telegram']['admin_bot_token'] = os.environ.get('ADMIN_BOT_TOKEN')
            
        # Admin configuration
        if os.environ.get('ADMIN_USER_IDS'):
            admin_ids = os.environ.get('ADMIN_USER_IDS').split(',')
            self.config['admin']['admin_user_ids'] = [id.strip() for id in admin_ids]
            
        # App environment
        if os.environ.get('ENVIRONMENT'):
            self.config['app']['environment'] = os.environ.get('ENVIRONMENT')
            
        # Logging configuration
        if os.environ.get('LOG_LEVEL'):
            self.config['logging']['level'] = os.environ.get('LOG_LEVEL')
            
        # Security configuration
        if os.environ.get('JWT_SECRET'):
            self.config['security']['jwt_secret'] = os.environ.get('JWT_SECRET')
            
        if os.environ.get('ENCRYPTION_KEY'):
            self.config['security']['encryption_key'] = os.environ.get('ENCRYPTION_KEY')
            
        # Admin wallet configuration
        if os.environ.get('ADMIN_WALLET_ADDRESS'):
            self._set_config_value('profit.fees.admin_wallet', os.environ.get('ADMIN_WALLET_ADDRESS'))
    
    def _get_db_url(self):
        """
        Get database URL
        
        Returns:
            Database connection URL
        """
        db_config = self.config['database']
        return f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    
    def get(self, key, default=None):
        """
        Get configuration value
        
        Args:
            key: Configuration key (dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def get_all(self):
        """
        Get all configuration settings
        
        Returns:
            Dict: All configuration settings
        """
        return self.config