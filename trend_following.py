# strategies/trend_following.py
import logging
import numpy as np
from typing import Dict, List, Any, Optional

from exchange.abstract_exchange import TradeSignal
from strategies.base_strategy import BaseStrategy
from analysis.technical_indicators import calculate_ema, calculate_macd

logger = logging.getLogger(__name__)

class TrendFollowingStrategy(BaseStrategy):
    """
    Trend following strategy
    
    Uses EMA crossovers and MACD to identify and follow trends
    """
    def __init__(self, exchange, user, risk_manager, config: Dict[str, Any]):
        super().__init__('trend_following', exchange, user, risk_manager, config)
        
        # Get parameters
        params = config.get('parameters', {})
        self.ema_short_period = params.get('ema_short_period', 20)
        self.ema_long_period = params.get('ema_long_period', 50)
        self.macd_fast_period = params.get('macd_fast_period', 12)
        self.macd_slow_period = params.get('macd_slow_period', 26)
        self.macd_signal_period = params.get('macd_signal_period', 9)
        self.take_profit_percent = params.get('take_profit_percent', 5.0)
        self.stop_loss_percent = params.get('stop_loss_percent', 2.0)
        self.trailing_stop_percent = params.get('trailing_stop_percent', 1.0)
        
        # Set update interval
        self.update_interval = 60  # 1 minute
        
    def _update(self) -> None:
        """
        Update strategy
        """
        # Trend following strategy doesn't need additional updates beyond the base class
        pass
        
    def _generate_signals(self) -> List[TradeSignal]:
        """
        Generate trading signals based on EMA crossovers and MACD
        
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
                    if not candles or len(candles) < self.ema_long_period + 10:
                        continue
                        
                    # Extract close prices
                    closes = [candle['close'] for candle in candles]
                    
                    # Calculate indicators
                    ema_short = calculate_ema(closes, self.ema_short_period)
                    ema_long = calculate_ema(closes, self.ema_long_period)
                    macd, signal, histogram = calculate_macd(
                        closes, 
                        self.macd_fast_period, 
                        self.macd_slow_period, 
                        self.macd_signal_period
                    )
                    
                    # Check for buy signal: EMA short crosses above EMA long + MACD histogram positive
                    if (ema_short[-2] <= ema_long[-2] and ema_short[-1] > ema_long[-1] and 
                        histogram[-1] > 0):
                        
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
                            trailing_stop=True,
                            trailing_stop_percent=self.trailing_stop_percent,
                            order_type='limit'
                        )
                        
                        signals.append(signal)
                        logger.info(f"Trend Following BUY signal for {symbol} on {timeframe} at {current_price}")
                        
                    # Check for sell signal: EMA short crosses below EMA long + MACD histogram negative
                    elif (ema_short[-2] >= ema_long[-2] and ema_short[-1] < ema_long[-1] and 
                        histogram[-1] < 0):
                        
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
                            trailing_stop=True,
                            trailing_stop_percent=self.trailing_stop_percent,
                            order_type='limit'
                        )
                        
                        signals.append(signal)
                        logger.info(f"Trend Following SELL signal for {symbol} on {timeframe} at {current_price}")
                        
        except Exception as e:
            logger.error(f"Error generating trend following signals: {str(e)}")
            
        return signals
