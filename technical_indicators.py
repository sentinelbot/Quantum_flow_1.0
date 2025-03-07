# analysis/technical_indicators.py
"""
Technical Indicators Module for QuantumFlow Trading Bot

Provides a comprehensive set of technical analysis functions and 
methods for advanced financial market analysis and trading strategy development.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Core Technical Indicator Calculation Functions
def calculate_sma(data: List[float], period: int) -> List[float]:
    """
    Calculate Simple Moving Average (SMA)
    
    Args:
        data: List of price values
        period: SMA calculation period
        
    Returns:
        List of SMA values
    """
    try:
        data_array = np.array(data)
        weights = np.ones(period) / period
        sma = np.convolve(data_array, weights, mode='valid')
        
        # Pad with NaN values to match input length
        padding = np.full(period - 1, np.nan)
        sma_padded = np.append(padding, sma)
        
        return sma_padded.tolist()
    except Exception as e:
        logger.error(f"Error calculating SMA: {str(e)}")
        return [np.nan] * len(data)

def calculate_ema(data: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average (EMA)
    
    Args:
        data: List of price values
        period: EMA calculation period
        
    Returns:
        List of EMA values
    """
    try:
        data_array = np.array(data)
        ema = np.full_like(data_array, np.nan)
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Initial SMA
        ema[period-1] = np.mean(data_array[:period])
        
        # Calculate EMA
        for i in range(period, len(data_array)):
            ema[i] = (data_array[i] * multiplier) + (ema[i-1] * (1 - multiplier))
            
        return ema.tolist()
    except Exception as e:
        logger.error(f"Error calculating EMA: {str(e)}")
        return [np.nan] * len(data)

def calculate_rsi(data: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        data: List of price values
        period: RSI calculation period
        
    Returns:
        List of RSI values
    """
    try:
        data_array = np.array(data)
        rsi = np.full_like(data_array, np.nan)
        
        # Calculate price changes
        deltas = np.diff(data_array)
        seed = deltas[:period+1]
        
        # Calculate initial average gains and losses
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        if down == 0:
            # Avoid division by zero
            rsi[period] = 100
        else:
            rs = up / down
            rsi[period] = 100 - (100 / (1 + rs))
            
        # Calculate RSI values
        for i in range(period + 1, len(data_array)):
            delta = deltas[i - 1]
            
            if delta > 0:
                upval = delta
                downval = 0
            else:
                upval = 0
                downval = -delta
                
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            
            if down == 0:
                # Avoid division by zero
                rsi[i] = 100
            else:
                rs = up / down
                rsi[i] = 100 - (100 / (1 + rs))
                
        return rsi.tolist()
    except Exception as e:
        logger.error(f"Error calculating RSI: {str(e)}")
        return [np.nan] * len(data)

def calculate_macd(data: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate Moving Average Convergence Divergence (MACD)
    
    Args:
        data: List of price values
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Tuple of MACD line, Signal line, and Histogram
    """
    try:
        # Calculate fast and slow EMAs
        fast_ema = calculate_ema(data, fast_period)
        slow_ema = calculate_ema(data, slow_period)
        
        # Calculate MACD line
        macd_line = np.array(fast_ema) - np.array(slow_ema)
        
        # Calculate signal line (EMA of MACD line)
        signal_line = np.array(calculate_ema(macd_line.tolist(), signal_period))
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line.tolist(), signal_line.tolist(), histogram.tolist()
    except Exception as e:
        logger.error(f"Error calculating MACD: {str(e)}")
        zero_list = [np.nan] * len(data)
        return zero_list, zero_list, zero_list

def calculate_bollinger_bands(data: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate Bollinger Bands
    
    Args:
        data: List of price values
        period: SMA period
        std_dev: Standard deviation multiplier
        
    Returns:
        Tuple of upper band, middle band, and lower band
    """
    try:
        data_array = np.array(data)
        middle_band = np.array(calculate_sma(data, period))
        
        # Calculate rolling standard deviation
        rolling_std = np.full_like(data_array, np.nan)
        
        for i in range(period - 1, len(data_array)):
            rolling_std[i] = np.std(data_array[i - (period - 1):i + 1])
            
        # Calculate bands
        upper_band = middle_band + (rolling_std * std_dev)
        lower_band = middle_band - (rolling_std * std_dev)
        
        return upper_band.tolist(), middle_band.tolist(), lower_band.tolist()
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {str(e)}")
        return [np.nan] * len(data), [np.nan] * len(data), [np.nan] * len(data)

def calculate_atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
    """
    Calculate Average True Range (ATR)
    
    Args:
        high: List of high prices
        low: List of low prices
        close: List of close prices
        period: ATR calculation period
        
    Returns:
        List of ATR values
    """
    try:
        high_array = np.array(high)
        low_array = np.array(low)
        close_array = np.array(close)
        
        # Calculate true range
        tr = np.zeros(len(high_array))
        
        for i in range(1, len(tr)):
            tr[i] = max(
                high_array[i] - low_array[i],
                abs(high_array[i] - close_array[i-1]),
                abs(low_array[i] - close_array[i-1])
            )
            
        # First value uses high - low
        tr[0] = high_array[0] - low_array[0]
        
        # Calculate ATR using EMA
        atr = np.full_like(tr, np.nan)
        
        # Initial ATR (simple average of first period true ranges)
        atr[period-1] = np.mean(tr[:period])
        
        # Calculate ATR using smoothing formula
        for i in range(period, len(tr)):
            atr[i] = ((period - 1) * atr[i-1] + tr[i]) / period
            
        return atr.tolist()
    except Exception as e:
        logger.error(f"Error calculating ATR: {str(e)}")
        return [np.nan] * len(high)

def calculate_stochastic(high: List[float], low: List[float], close: List[float], k_period: int = 14, d_period: int = 3) -> Tuple[List[float], List[float]]:
    """
    Calculate Stochastic Oscillator (%K and %D)
    
    Args:
        high: List of high prices
        low: List of low prices
        close: List of close prices
        k_period: Period for %K calculation
        d_period: Period for %D calculation (SMA of %K)
        
    Returns:
        Tuple of %K and %D values
    """
    try:
        high_array = np.array(high)
        low_array = np.array(low)
        close_array = np.array(close)
        
        # Calculate %K
        k_values = np.full_like(close_array, np.nan)
        
        for i in range(k_period - 1, len(close_array)):
            highest_high = np.max(high_array[i - (k_period - 1):i + 1])
            lowest_low = np.min(low_array[i - (k_period - 1):i + 1])
            
            if highest_high - lowest_low == 0:
                # Avoid division by zero
                k_values[i] = 50.0  # Middle value when there's no range
            else:
                k_values[i] = ((close_array[i] - lowest_low) / (highest_high - lowest_low)) * 100
        
        # Calculate %D (SMA of %K)
        d_values = np.array(calculate_sma(k_values.tolist(), d_period))
        
        return k_values.tolist(), d_values.tolist()
    except Exception as e:
        logger.error(f"Error calculating Stochastic Oscillator: {str(e)}")
        return [np.nan] * len(close), [np.nan] * len(close)

def detect_support_resistance(prices: List[float], window_size: int = 10, threshold_percent: float = 0.02, max_levels: int = 5) -> Tuple[List[float], List[float]]:
    """
    Detect support and resistance levels from price data
    
    Args:
        prices: List of price values
        window_size: Size of the window to find local minima and maxima
        threshold_percent: Minimum percentage distance between levels
        max_levels: Maximum number of levels to return for each type
        
    Returns:
        Tuple of support levels and resistance levels
    """
    try:
        prices_array = np.array(prices)
        
        # Find local minima for support levels
        support_indices = []
        for i in range(window_size, len(prices_array) - window_size):
            is_min = True
            for j in range(-window_size, window_size + 1):
                if j == 0:
                    continue
                if prices_array[i] > prices_array[i + j]:
                    is_min = False
                    break
            if is_min:
                support_indices.append(i)
        
        # Find local maxima for resistance levels
        resistance_indices = []
        for i in range(window_size, len(prices_array) - window_size):
            is_max = True
            for j in range(-window_size, window_size + 1):
                if j == 0:
                    continue
                if prices_array[i] < prices_array[i + j]:
                    is_max = False
                    break
            if is_max:
                resistance_indices.append(i)
        
        # Extract price levels
        support_levels = [prices_array[i] for i in support_indices]
        resistance_levels = [prices_array[i] for i in resistance_indices]
        
        # Group nearby levels
        def group_levels(levels, threshold):
            if not levels:
                return []
                
            # Sort levels
            sorted_levels = sorted(levels)
            
            # Group levels that are within threshold % of each other
            grouped_levels = []
            current_group = [sorted_levels[0]]
            
            for level in sorted_levels[1:]:
                if (level - current_group[0]) / current_group[0] <= threshold:
                    current_group.append(level)
                else:
                    # Add average of current group to results
                    grouped_levels.append(sum(current_group) / len(current_group))
                    current_group = [level]
            
            # Add the last group
            if current_group:
                grouped_levels.append(sum(current_group) / len(current_group))
                
            return grouped_levels
        
        # Group and limit the number of levels
        support_levels = group_levels(support_levels, threshold_percent)
        resistance_levels = group_levels(resistance_levels, threshold_percent)
        
        # Sort and limit to max_levels
        support_levels = sorted(support_levels, reverse=True)[:max_levels]
        resistance_levels = sorted(resistance_levels)[:max_levels]
        
        return support_levels, resistance_levels
    except Exception as e:
        logger.error(f"Error detecting support and resistance levels: {str(e)}")
        return [], []

# Continue adding other calculation functions as needed...

class TechnicalIndicators:
    """
    Technical Indicators Computation Class
    
    Provides methods for calculating various technical indicators
    using the underlying calculation functions.
    """
    
    def __init__(self):
        """Initialize the TechnicalIndicators class"""
        pass

    def sma(self, data: List[float], period: int) -> List[float]:
        """
        Calculate Simple Moving Average using functional implementation
        
        Args:
            data: List of price values
            period: SMA calculation period
        
        Returns:
            List of SMA values
        """
        return calculate_sma(data, period)

    def ema(self, data: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average using functional implementation
        
        Args:
            data: List of price values
            period: EMA calculation period
        
        Returns:
            List of EMA values
        """
        return calculate_ema(data, period)

    def rsi(self, data: List[float], period: int = 14) -> List[float]:
        """
        Calculate Relative Strength Index using functional implementation
        
        Args:
            data: List of price values
            period: RSI calculation period
        
        Returns:
            List of RSI values
        """
        return calculate_rsi(data, period)

    def macd(self, data: List[float], fast_period: int = 12, 
             slow_period: int = 26, signal_period: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """
        Calculate MACD using functional implementation
        
        Args:
            data: List of price values
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
        
        Returns:
            Tuple of MACD line, Signal line, and Histogram
        """
        return calculate_macd(data, fast_period, slow_period, signal_period)

    def bollinger_bands(self, data: List[float], period: int = 20, 
                        std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
        """
        Calculate Bollinger Bands using functional implementation
        
        Args:
            data: List of price values
            period: SMA period
            std_dev: Standard deviation multiplier
        
        Returns:
            Tuple of upper band, middle band, and lower band
        """
        return calculate_bollinger_bands(data, period, std_dev)

    def atr(self, high: List[float], low: List[float], close: List[float], 
            period: int = 14) -> List[float]:
        """
        Calculate Average True Range using functional implementation
        
        Args:
            high: List of high prices
            low: List of low prices
            close: List of close prices
            period: ATR calculation period
        
        Returns:
            List of ATR values
        """
        return calculate_atr(high, low, close, period)
        
    def stochastic(self, high: List[float], low: List[float], close: List[float],
                  k_period: int = 14, d_period: int = 3) -> Tuple[List[float], List[float]]:
        """
        Calculate Stochastic Oscillator using functional implementation
        
        Args:
            high: List of high prices
            low: List of low prices
            close: List of close prices
            k_period: Period for %K calculation
            d_period: Period for %D calculation
        
        Returns:
            Tuple of %K and %D values
        """
        return calculate_stochastic(high, low, close, k_period, d_period)
        
    def support_resistance(self, prices: List[float], window_size: int = 10, 
                          threshold_percent: float = 0.02, max_levels: int = 5) -> Tuple[List[float], List[float]]:
        """
        Detect support and resistance levels using functional implementation
        
        Args:
            prices: List of price values
            window_size: Size of the window to find local minima and maxima
            threshold_percent: Minimum percentage distance between levels
            max_levels: Maximum number of levels to return for each type
        
        Returns:
            Tuple of support levels and resistance levels
        """
        return detect_support_resistance(prices, window_size, threshold_percent, max_levels)