# market_data/market_analysis.py
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple

class MarketAnalysis:
    """Market analysis utilities for trading decisions"""
    
    def __init__(self, db=None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    def get_current_volatility(self, symbol):
        """Calculate current volatility for a symbol"""
        try:
            # Get price history
            from market_data.price_service import PriceService
            price_service = PriceService(self.db)
            
            # Get hourly candles for the last 24 hours
            candles = price_service.get_price_history(symbol, timeframe='1h', limit=24)
            
            if not candles or len(candles) < 2:
                return 0
                
            # Extract close prices
            close_prices = [candle['close'] for candle in candles]
            
            # Calculate returns
            returns = np.diff(close_prices) / close_prices[:-1]
            
            # Calculate annualized volatility
            volatility = np.std(returns) * np.sqrt(24 * 365) * 100  # Annualized and in percentage
            
            return volatility
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 0
            
    def get_current_liquidity(self, symbol):
        """Estimate current liquidity for a symbol based on order book"""
        try:
            # This would typically use your exchange client to get order book data
            from exchange.exchange_factory import ExchangeFactory
            exchange_factory = ExchangeFactory()
            exchange = exchange_factory.create_public_client('binance')
            
            # Get order book
            order_book = exchange.get_order_book(symbol, limit=20)
            
            if not order_book or 'bids' not in order_book or 'asks' not in order_book:
                return 0
                
            # Calculate liquidity as sum of bid/ask volume within 1% of mid price
            bids = order_book['bids']
            asks = order_book['asks']
            
            if not bids or not asks:
                return 0
                
            mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2
            
            # Calculate 1% range
            lower_bound = mid_price * 0.99
            upper_bound = mid_price * 1.01
            
            # Sum volumes within range
            bid_volume = sum(float(bid[1]) for bid in bids if float(bid[0]) >= lower_bound)
            ask_volume = sum(float(ask[1]) for ask in asks if float(ask[0]) <= upper_bound)
            
            # Total liquidity in base currency units
            liquidity = bid_volume + ask_volume
            
            return liquidity
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidity for {symbol}: {e}")
            return 0
            
    def analyze_market_sentiment(self, symbol):
        """Analyze market sentiment for a symbol"""
        try:
            # Placeholder for actual sentiment analysis
            # This would typically involve more complex logic with:
            # - Technical indicators
            # - Social media sentiment
            # - News analysis
            # - On-chain metrics (for cryptocurrencies)
            
            # For simplicity, using a basic moving average crossover as sentiment indicator
            from market_data.price_service import PriceService
            price_service = PriceService(self.db)
            
            # Get price history
            candles = price_service.get_price_history(symbol, timeframe='1h', limit=50)
            
            if not candles or len(candles) < 50:
                return "neutral"
                
            # Extract close prices
            close_prices = np.array([candle['close'] for candle in candles])
            
            # Calculate moving averages
            ma20 = np.mean(close_prices[-20:])
            ma50 = np.mean(close_prices[-50:])
            
            # Determine sentiment
            if ma20 > ma50:
                return "bullish"
            elif ma20 < ma50:
                return "bearish"
            else:
                return "neutral"
                
        except Exception as e:
            self.logger.error(f"Error analyzing market sentiment for {symbol}: {e}")
            return "neutral"
            
    def get_support_resistance_levels(self, symbol, timeframe='1d', periods=90):
        """Calculate support and resistance levels for a symbol"""
        try:
            from market_data.price_service import PriceService
            price_service = PriceService(self.db)
            
            # Get price history
            candles = price_service.get_price_history(symbol, timeframe=timeframe, limit=periods)
            
            if not candles or len(candles) < 30:
                return {"support": [], "resistance": []}
                
            # Extract price data
            highs = np.array([candle['high'] for candle in candles])
            lows = np.array([candle['low'] for candle in candles])
            
            # Calculate recent min/max points
            support_levels = self._find_pivot_points(lows, is_support=True)
            resistance_levels = self._find_pivot_points(highs, is_support=False)
            
            return {
                "support": support_levels,
                "resistance": resistance_levels
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating support/resistance for {symbol}: {e}")
            return {"support": [], "resistance": []}
            
    def _find_pivot_points(self, price_array, is_support=True, window=5):
        """Find pivot points in price array"""
        pivots = []
        
        for i in range(window, len(price_array) - window):
            if is_support:
                # Find local minimums
                if all(price_array[i] <= price_array[i-j] for j in range(1, window+1)) and \
                   all(price_array[i] <= price_array[i+j] for j in range(1, window+1)):
                    pivots.append(price_array[i])
            else:
                # Find local maximums
                if all(price_array[i] >= price_array[i-j] for j in range(1, window+1)) and \
                   all(price_array[i] >= price_array[i+j] for j in range(1, window+1)):
                    pivots.append(price_array[i])
        
        # Return the most significant points (limiting to top 5)
        return sorted(pivots)[:5] if is_support else sorted(pivots, reverse=True)[:5]