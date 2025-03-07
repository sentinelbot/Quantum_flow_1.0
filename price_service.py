# market_data/price_service.py
import logging
import time
from typing import Dict, Optional, List

class PriceService:
    """Service for fetching and managing price data"""
    
    def __init__(self, db=None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.price_cache = {}
        self.last_update = {}
        self.cache_ttl = 60  # Cache TTL in seconds
        
    def get_current_price(self, symbol):
        """Get current price for a symbol"""
        try:
            # Check cache first
            if symbol in self.price_cache and time.time() - self.last_update.get(symbol, 0) < self.cache_ttl:
                return self.price_cache[symbol]
                
            # If not in cache or expired, fetch from exchange
            price = self._fetch_price_from_exchange(symbol)
            
            if price:
                # Update cache
                self.price_cache[symbol] = price
                self.last_update[symbol] = time.time()
                
            return price
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
            
    def _fetch_price_from_exchange(self, symbol):
        """Fetch price from exchange API"""
        try:
            # This would typically use your exchange client
            # This is a simplified implementation
            
            # Placeholder for exchange API call
            from exchange.exchange_factory import ExchangeFactory
            exchange_factory = ExchangeFactory()
            exchange = exchange_factory.create_public_client('binance')
            
            price = exchange.get_ticker_price(symbol)
            return price
            
        except Exception as e:
            self.logger.error(f"Error fetching price from exchange for {symbol}: {e}")
            return None
            
    def get_price_history(self, symbol, timeframe='1h', limit=100):
        """Get price history for a symbol"""
        try:
            # Fetch candle data from exchange
            from exchange.exchange_factory import ExchangeFactory
            exchange_factory = ExchangeFactory()
            exchange = exchange_factory.create_public_client('binance')
            
            candles = exchange.get_candles(symbol, timeframe, limit)
            return candles
            
        except Exception as e:
            self.logger.error(f"Error getting price history for {symbol}: {e}")
            return []
            
    def get_multiple_prices(self, symbols):
        """Get current prices for multiple symbols"""
        try:
            result = {}
            
            for symbol in symbols:
                price = self.get_current_price(symbol)
                if price:
                    result[symbol] = price
                    
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting multiple prices: {e}")
            return {}