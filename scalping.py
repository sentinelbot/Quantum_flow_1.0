# strategies/scalping.py
import logging
import numpy as np
from typing import Dict, List, Any, Optional

from exchange.abstract_exchange import TradeSignal
from strategies.base_strategy import BaseStrategy
from analysis.technical_indicators import calculate_rsi, calculate_ema

logger = logging.getLogger(__name__)

class ScalpingStrategy(BaseStrategy):
    """
    Scalping strategy for short-term trades
    
    Uses RSI and EMA crossovers on short timeframes to identify entry points
    """
    def __init__(self, exchange, user, risk_manager, config: Dict[str, Any]):
        super().__init__('scalping', exchange, user, risk_manager, config)
        
        # Get parameters
        params = config.get('parameters', {})
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_overbought = params.get('rsi_overbought', 70)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.ema_fast_period = params.get('ema_fast_period', 9)
        self.ema_slow_period = params.get('ema_slow_period', 21)
        self.take_profit_percent = params.get('take_profit_percent', 1.0)
        self.stop_loss_percent = params.get('stop_loss_percent', 0.5)
        
        # Set update interval to 10 seconds for scalping
        self.update_interval = 10
        
    def _update(self) -> None:
        """
        Update strategy
        """
        # Scalping strategy doesn't need additional updates beyond the base class
        pass
        
    def _generate_signals(self) -> List[TradeSignal]:
        """
        Generate trading signals based on RSI and EMA crossovers
        
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
                    if not candles or len(candles) < self.ema_slow_period + 10:
                        continue
                        
                    # Extract close prices
                    closes = [candle['close'] for candle in candles]
                    
                    # Calculate indicators
                    rsi = calculate_rsi(closes, self.rsi_period)
                    ema_fast = calculate_ema(closes, self.ema_fast_period)
                    ema_slow = calculate_ema(closes, self.ema_slow_period)
                    
                    # Check for buy signal: RSI oversold + EMA fast crosses above EMA slow
                    if (rsi[-2] <= self.rsi_oversold and rsi[-1] > self.rsi_oversold and
                        ema_fast[-2] <= ema_slow[-2] and ema_fast[-1] > ema_slow[-1]):
                        
                        # Get current price
                        current_price = closes[-1]
                        
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
                        logger.info(f"Scalping BUY signal for {symbol} on {timeframe} at {current_price}")
                        
                    # Check for sell signal: RSI overbought + EMA fast crosses below EMA slow
                    elif (rsi[-2] >= self.rsi_overbought and rsi[-1] < self.rsi_overbought and
                        ema_fast[-2] >= ema_slow[-2] and ema_fast[-1] < ema_slow[-1]):
                        
                        # Get current price
                        current_price = closes[-1]
                        
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
                        logger.info(f"Scalping SELL signal for {symbol} on {timeframe} at {current_price}")
                        
        except Exception as e:
            logger.error(f"Error generating scalping signals: {str(e)}")
            
        return signals