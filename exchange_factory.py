"""
Factory for creating exchange API instances
"""

import logging
from typing import Dict, Optional

from exchange.abstract_exchange import AbstractExchange
from exchange.binance.client import BinanceExchange

logger = logging.getLogger(__name__)

class ExchangeFactory:
    """
    Factory for creating exchange instances
    """
    def __init__(self):
        self.exchanges = {
            'binance': BinanceExchange
        }
    
    def create_exchange(self, exchange_name: str, api_key: str, api_secret: str) -> Optional[AbstractExchange]:
        """
        Create an instance of the specified exchange
        
        Args:
            exchange_name: Name of the exchange (e.g., 'binance')
            api_key: API key
            api_secret: API secret
            
        Returns:
            Exchange instance or None if exchange is not supported
        """
        exchange_name = exchange_name.lower()
        
        if exchange_name not in self.exchanges:
            logger.error(f"Unsupported exchange: {exchange_name}")
            return None
            
        try:
            exchange_class = self.exchanges[exchange_name]
            return exchange_class(api_key, api_secret)
        except Exception as e:
            logger.error(f"Failed to create exchange instance for {exchange_name}: {str(e)}")
            return None
    
    def register_exchange(self, name: str, exchange_class: type) -> None:
        """
        Register a new exchange type
        
        Args:
            name: Exchange name
            exchange_class: Exchange class
        """
        self.exchanges[name.lower()] = exchange_class
        logger.info(f"Registered exchange: {name}")
    
    def get_supported_exchanges(self) -> list:
        """
        Get list of supported exchanges
        
        Returns:
            List of exchange names
        """
        return list(self.exchanges.keys())