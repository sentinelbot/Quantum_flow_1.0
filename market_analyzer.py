
# analysis/market_analyzer.py
import logging
import numpy as np
import time
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

from exchange.abstract_exchange import AbstractExchange
from analysis.technical_indicators import (
    calculate_sma, calculate_ema, calculate_rsi,
    calculate_macd, calculate_bollinger_bands,
    calculate_atr, calculate_stochastic,
    detect_support_resistance
)

logger = logging.getLogger(__name__)

class MarketState:
    """
    Market state enumeration
    """
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

class MarketAnalyzer:
    """
    Market analysis system
    """
    def __init__(self, exchange: AbstractExchange):
        self.exchange = exchange
        
        # Cache for market data
        self.data_cache = {}
        self.indicators_cache = {}
        self.last_update = {}
        
        # Cache expiry in seconds
        self.cache_expiry = {
            '1m': 30,     # 30 seconds
            '5m': 60,     # 1 minute
            '15m': 180,   # 3 minutes
            '1h': 600,    # 10 minutes
            '4h': 1800,   # 30 minutes
            '1d': 3600    # 1 hour
        }
        
        logger.info("Market analyzer initialized")
        
    def analyze_market(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """
        Perform complete market analysis for a symbol
        
        Args:
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Get market data
            data = self.get_market_data(symbol, timeframe)
            
            if not data or len(data) < 50:
                logger.warning(f"Insufficient data for market analysis: {symbol} {timeframe}")
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'state': MarketState.UNKNOWN,
                    'timestamp': int(time.time())
                }
                
            # Extract OHLCV data
            timestamps = [candle['timestamp'] for candle in data]
            opens = [candle['open'] for candle in data]
            highs = [candle['high'] for candle in data]
            lows = [candle['low'] for candle in data]
            closes = [candle['close'] for candle in data]
            volumes = [candle['volume'] for candle in data]
            
            # Calculate indicators
            indicators = self.calculate_indicators(closes, highs, lows, volumes)
            
            # Determine market state
            market_state = self.determine_market_state(indicators)
            
            # Calculate support and resistance levels
            support_resistance = detect_support_resistance(closes)
            
            # Calculate price statistics
            price_stats = {
                'current_price': closes[-1],
                'price_change_24h': self._calculate_price_change(closes, timeframe),
                'volume_change_24h': self._calculate_volume_change(volumes, timeframe),
                'volatility': self._calculate_volatility(closes)
            }
            
            # Generate complete analysis
            analysis = {
                'symbol': symbol,
                'timeframe': timeframe,
                'state': market_state,
                'indicators': indicators,
                'support_resistance': support_resistance,
                'price_stats': price_stats,
                'timestamp': int(time.time())
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market for {symbol} {timeframe}: {str(e)}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'state': MarketState.UNKNOWN,
                'timestamp': int(time.time())
            }
            
    def get_market_data(self, symbol: str, timeframe: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get market data from cache or exchange
        
        Args:
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            force_refresh: Force data refresh
            
        Returns:
            List[Dict[str, Any]]: Market data
        """
        cache_key = f"{symbol}_{timeframe}"
        
        # Check if cache is valid
        current_time = time.time()
        cache_valid = (
            cache_key in self.data_cache and
            cache_key in self.last_update and
            current_time - self.last_update[cache_key] < self.cache_expiry.get(timeframe, 300)
        )
        
        if not cache_valid or force_refresh:
            try:
                # Fetch data from exchange
                candles = self.exchange.get_historical_data(symbol, timeframe, limit=200)
                
                if candles:
                    # Update cache
                    self.data_cache[cache_key] = candles
                    self.last_update[cache_key] = current_time
                    
                return candles
            except Exception as e:
                logger.error(f"Error fetching market data for {symbol} {timeframe}: {str(e)}")
                
                # Return cached data if available
                if cache_key in self.data_cache:
                    return self.data_cache[cache_key]
                return []
        else:
            return self.data_cache[cache_key]
            
    def calculate_indicators(self, closes: List[float], highs: List[float], lows: List[float], volumes: List[float]) -> Dict[str, Any]:
        """
        Calculate technical indicators
        
        Args:
            closes: List of close prices
            highs: List of high prices
            lows: List of low prices
            volumes: List of volumes
            
        Returns:
            Dict[str, Any]: Technical indicators
        """
        try:
            # Calculate various indicators
            sma_20 = calculate_sma(closes, 20)
            sma_50 = calculate_sma(closes, 50)
            sma_200 = calculate_sma(closes, 200)
            
            ema_9 = calculate_ema(closes, 9)
            ema_20 = calculate_ema(closes, 20)
            ema_50 = calculate_ema(closes, 50)
            
            rsi = calculate_rsi(closes, 14)
            
            macd_line, signal_line, histogram = calculate_macd(closes)
            
            upper_band, middle_band, lower_band = calculate_bollinger_bands(closes)
            
            atr = calculate_atr(highs, lows, closes)
            
            stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
            
            # Create indicators dictionary
            indicators = {
                'sma': {
                    '20': sma_20[-1],
                    '50': sma_50[-1],
                    '200': sma_200[-1]
                },
                'ema': {
                    '9': ema_9[-1],
                    '20': ema_20[-1],
                    '50': ema_50[-1]
                },
                'rsi': rsi[-1],
                'macd': {
                    'line': macd_line[-1],
                    'signal': signal_line[-1],
                    'histogram': histogram[-1]
                },
                'bollinger_bands': {
                    'upper': upper_band[-1],
                    'middle': middle_band[-1],
                    'lower': lower_band[-1]
                },
                'atr': atr[-1],
                'stochastic': {
                    'k': stoch_k[-1],
                    'd': stoch_d[-1]
                }
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return {}
            
    def determine_market_state(self, indicators: Dict[str, Any]) -> str:
        """
        Determine current market state based on indicators
        
        Args:
            indicators: Technical indicators
            
        Returns:
            str: Market state
        """
        try:
            if not indicators:
                return MarketState.UNKNOWN
                
            # Extract indicator values
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', {})
            macd_histogram = macd.get('histogram', 0)
            macd_line = macd.get('line', 0)
            bb = indicators.get('bollinger_bands', {})
            bb_width = 0
            
            if bb and 'upper' in bb and 'lower' in bb and 'middle' in bb and bb['middle'] > 0:
                bb_width = (bb['upper'] - bb['lower']) / bb['middle']
                
            # Determine market state
            if rsi > 60 and macd_histogram > 0 and macd_line > 0:
                return MarketState.TRENDING_UP
            elif rsi < 40 and macd_histogram < 0 and macd_line < 0:
                return MarketState.TRENDING_DOWN
            elif 40 <= rsi <= 60 and abs(macd_histogram) < 0.5 and bb_width < 0.05:
                return MarketState.RANGING
            elif bb_width > 0.1:
                return MarketState.VOLATILE
            else:
                return MarketState.RANGING
                
        except Exception as e:
            logger.error(f"Error determining market state: {str(e)}")
            return MarketState.UNKNOWN
            
    def _calculate_price_change(self, closes: List[float], timeframe: str) -> float:
        """
        Calculate price change over approximately 24 hours
        
        Args:
            closes: List of close prices
            timeframe: Chart timeframe
            
        Returns:
            float: Price change percentage
        """
        try:
            # Determine number of periods for 24 hours
            periods = {
                '1m': 1440,
                '5m': 288,
                '15m': 96,
                '1h': 24,
                '4h': 6,
                '1d': 1
            }
            
            periods_24h = periods.get(timeframe, 24)
            periods_24h = min(periods_24h, len(closes) - 1)
            
            # Calculate percentage change
            price_change = (closes[-1] - closes[-periods_24h-1]) / closes[-periods_24h-1] * 100
            
            return price_change
            
        except Exception as e:
            logger.error(f"Error calculating price change: {str(e)}")
            return 0
            
    def _calculate_volume_change(self, volumes: List[float], timeframe: str) -> float:
        """
        Calculate volume change over approximately 24 hours
        
        Args:
            volumes: List of volumes
            timeframe: Chart timeframe
            
        Returns:
            float: Volume change percentage
        """
        try:
            # Determine number of periods for 24 hours
            periods = {
                '1m': 1440,
                '5m': 288,
                '15m': 96,
                '1h': 24,
                '4h': 6,
                '1d': 1
            }
            
            periods_24h = periods.get(timeframe, 24)
            periods_24h = min(periods_24h, len(volumes) - 1)
            
            # Calculate average volume for previous and current 24 hours
            prev_24h_avg = np.mean(volumes[-2 * periods_24h:-periods_24h])
            curr_24h_avg = np.mean(volumes[-periods_24h:])
            
            if prev_24h_avg > 0:
                volume_change = (curr_24h_avg - prev_24h_avg) / prev_24h_avg * 100
            else:
                volume_change = 0
                
            return volume_change
            
        except Exception as e:
            logger.error(f"Error calculating volume change: {str(e)}")
            return 0
            
    def _calculate_volatility(self, closes: List[float]) -> float:
        """
        Calculate price volatility (standard deviation of returns)
        
        Args:
            closes: List of close prices
            
        Returns:
            float: Volatility
        """
        try:
            # Calculate returns
            returns = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
            
            # Calculate standard deviation
            volatility = np.std(returns) * 100
            
            return volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {str(e)}")
            return 0
            
    def get_multi_timeframe_analysis(self, symbol: str, timeframes: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Perform market analysis across multiple timeframes
        
        Args:
            symbol: Trading pair symbol
            timeframes: List of timeframes to analyze
            
        Returns:
            Dict[str, Dict[str, Any]]: Analysis results by timeframe
        """
        if timeframes is None:
            timeframes = ['15m', '1h', '4h', '1d']
            
        results = {}
        
        for timeframe in timeframes:
            results[timeframe] = self.analyze_market(symbol, timeframe)
            
        return results
        
    def get_market_summary(self, symbol: str) -> Dict[str, Any]:
        """
        Get concise market summary for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict[str, Any]: Market summary
        """
        try:
            # Get analysis for multiple timeframes
            timeframes = ['15m', '1h', '4h', '1d']
            analyses = self.get_multi_timeframe_analysis(symbol, timeframes)
            
            # Get current price
            current_price = 0
            for tf in timeframes:
                if tf in analyses and 'price_stats' in analyses[tf]:
                    current_price = analyses[tf]['price_stats'].get('current_price', 0)
                    if current_price > 0:
                        break
                        
            # Determine overall trend
            trend_votes = {
                MarketState.TRENDING_UP: 0,
                MarketState.TRENDING_DOWN: 0,
                MarketState.RANGING: 0,
                MarketState.VOLATILE: 0
            }
            
            for tf in timeframes:
                if tf in analyses:
                    state = analyses[tf].get('state', MarketState.UNKNOWN)
                    if state in trend_votes:
                        trend_votes[state] += 1
                        
            # Overall trend is the one with the most votes
            overall_trend = max(trend_votes.items(), key=lambda x: x[1])[0]
            
            # Get indicator signals
            bullish_signals = 0
            bearish_signals = 0
            
            for tf in timeframes:
                if tf in analyses and 'indicators' in analyses[tf]:
                    indicators = analyses[tf]['indicators']
                    
                    # RSI
                    rsi = indicators.get('rsi', 50)
                    if rsi > 60:
                        bullish_signals += 1
                    elif rsi < 40:
                        bearish_signals += 1
                        
                    # MACD
                    macd = indicators.get('macd', {})
                    histogram = macd.get('histogram', 0)
                    if histogram > 0:
                        bullish_signals += 1
                    elif histogram < 0:
                        bearish_signals += 1
                        
                    # Bollinger Bands
                    bb = indicators.get('bollinger_bands', {})
                    if 'lower' in bb and 'upper' in bb and current_price > 0:
                        if current_price <= bb['lower']:
                            bullish_signals += 1
                        elif current_price >= bb['upper']:
                            bearish_signals += 1
                            
            # Create summary
            summary = {
                'symbol': symbol,
                'current_price': current_price,
                'overall_trend': overall_trend,
                'signal_strength': {
                    'bullish': bullish_signals,
                    'bearish': bearish_signals,
                    'total': len(timeframes) * 3,  # 3 indicators per timeframe
                    'net': bullish_signals - bearish_signals
                },
                'timestamp': int(time.time())
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting market summary for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'current_price': 0,
                'overall_trend': MarketState.UNKNOWN,
                'signal_strength': {
                    'bullish': 0,
                    'bearish': 0,
                    'total': 0,
                    'net': 0
                },
                'timestamp': int(time.time())
            }
