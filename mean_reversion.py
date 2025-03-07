# strategies/mean_reversion.py
import logging
import numpy as np
from typing import Dict, List, Any, Optional

from exchange.abstract_exchange import TradeSignal
from strategies.base_strategy import BaseStrategy
from analysis.technical_indicators import calculate_bollinger_bands, calculate_rsi

logger = logging.getLogger(__name__)

class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion strategy
    
    Uses Bollinger Bands and RSI to identify overbought/oversold conditions
    """
    def __init__(self, exchange, user, risk_manager, config: Dict[str, Any]):
        super().__init__('mean_reversion', exchange, user, risk_manager, config)
        
        # Get parameters
        params = config.get('parameters', {})
        self.bollinger_period = params.get('bollinger_period', 20)
        self.bollinger_std_dev = params.get('bollinger_std_dev', 2.0)
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_overbought = params.get('rsi_overbought', 70)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.take_profit_percent = params.get('take_profit_percent', 2.0)
        self.stop_loss_percent = params.get('stop_loss_percent', 1.0)
        
        # Set update interval
        self.update_interval = 60  # 1 minute
        
    def _update(self) -> None:
        """
        Update strategy
        """
        # Mean reversion strategy doesn't need additional updates beyond the base class
        pass
        
    def _generate_signals(self) -> List[TradeSignal]:
        """
        Generate trading signals based on Bollinger Bands and RSI
        
        Returns:
            List[TradeSignal]: List of trade signals
        """
        signals = []
        
        try:
            # Check each symbol and timeframe
            for symbol in self.symbols:
                for timeframe in self.timeframes:
                    # Get candles
                    candles = self.get_candles(symbol, timeframe)
                    if not candles or len(candles) < self.bollinger_period + 10:
                        continue
                        
                    # Extract close prices
                    closes = [candle['close'] for candle in candles]
                    
                    # Calculate indicators
                    upper, middle, lower = calculate_bollinger_bands(closes, self.bollinger_period, self.bollinger_std_dev)
                    rsi = calculate_rsi(closes, self.rsi_period)
                    
                    # Current price
                    current_price = closes[-1]
                    
                    # Check for buy signal: Price below lower Bollinger Band + RSI oversold
                    if current_price <= lower[-1] and rsi[-1] <= self.rsi_oversold:
                        # Calculate take profit and stop loss
                        take_profit = self.calculate_take_profit_price(current_price, 'buy')
                        stop_loss = self.calculate_stop_loss_price(current_price, 'buy')
                        
                        # Create signal
                        signal = TradeSignal(
                            symbol=symbol,
                            side='buy',
                            price=current_price,
                            take_profit=take_profit,
                            stop_loss=stop_loss,
                            order_type='limit'
                        )
                        
                        signals.append(signal)
                        logger.info(f"Mean Reversion BUY signal for {symbol} on {timeframe} at {current_price}")
                        
                    # Check for sell signal: Price above upper Bollinger Band + RSI overbought
                    elif current_price >= upper[-1] and rsi[-1] >= self.rsi_overbought:
                        # Calculate take profit and stop loss
                        take_profit = self.calculate_take_profit_price(current_price, 'sell')
                        stop_loss = self.calculate_stop_loss_price(current_price, 'sell')
                        
                        # Create signal
                        signal = TradeSignal(
                            symbol=symbol,
                            side='sell',
                            price=current_price,
                            take_profit=take_profit,
                            stop_loss=stop_loss,
                            order_type='limit'
                        )
                        
                        signals.append(signal)
                        logger.info(f"Mean Reversion SELL signal for {symbol} on {timeframe} at {current_price}")
                        
        except Exception as e:
            logger.error(f"Error generating mean reversion signals: {str(e)}")
            
        return signals
