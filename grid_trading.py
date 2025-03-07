# strategies/grid_trading.py
import logging
import numpy as np
from typing import Dict, List, Any, Optional

from exchange.abstract_exchange import TradeSignal
from strategies.base_strategy import BaseStrategy
from analysis.technical_indicators import calculate_bollinger_bands, calculate_atr

logger = logging.getLogger(__name__)

class GridTradingStrategy(BaseStrategy):
    """
    Grid trading strategy
    
    Creates a grid of buy and sell orders within a price range
    """
    def __init__(self, exchange, user, risk_manager, config: Dict[str, Any]):
        super().__init__('grid_trading', exchange, user, risk_manager, config)
        
        # Get parameters
        params = config.get('parameters', {})
        self.grid_levels = params.get('grid_levels', 10)
        self.grid_spacing_percent = params.get('grid_spacing_percent', 1.0)
        self.total_investment_percent = params.get('total_investment_percent', 20.0)
        self.dynamic_boundaries = params.get('dynamic_boundaries', True)
        self.volatility_factor = params.get('volatility_factor', 1.5)
        
        # Grid state
        self.active_grids = {}  # Symbol -> Grid info
        
        # Set update interval to 5 minutes for grid trading
        self.update_interval = 300
        
    def _update(self) -> None:
        """
        Update grid boundaries based on current market conditions
        """
        try:
            for symbol in self.symbols:
                # Get 1h candles for grid boundaries
                candles = self.get_candles(symbol, '1h')
                if not candles or len(candles) < 20:
                    continue
                    
                # Extract close prices
                closes = [candle['close'] for candle in candles]
                
                if self.dynamic_boundaries:
                    # Calculate Bollinger Bands for dynamic grid boundaries
                    upper, middle, lower = calculate_bollinger_bands(closes, 20, 2)
                    
                    # Calculate ATR for grid spacing
                    highs = [candle['high'] for candle in candles]
                    lows = [candle['low'] for candle in candles]
                    atr = calculate_atr(highs, lows, closes, 14)
                    
                    # Set grid boundaries
                    current_price = closes[-1]
                    price_range = self.volatility_factor * atr[-1]
                    
                    upper_boundary = current_price + price_range
                    lower_boundary = current_price - price_range
                    
                    # Save grid info
                    if symbol not in self.active_grids:
                        self.active_grids[symbol] = {}
                        
                    self.active_grids[symbol]['upper_boundary'] = upper_boundary
                    self.active_grids[symbol]['lower_boundary'] = lower_boundary
                    self.active_grids[symbol]['current_price'] = current_price
                    self.active_grids[symbol]['grid_spacing'] = (upper_boundary - lower_boundary) / self.grid_levels
                    
                    logger.info(f"Updated grid for {symbol}: {lower_boundary:.2f} - {upper_boundary:.2f}, spacing: {self.active_grids[symbol]['grid_spacing']:.2f}")
                    
        except Exception as e:
            logger.error(f"Error updating grid boundaries: {str(e)}")
            
    def _generate_signals(self) -> List[TradeSignal]:
        """
        Generate trading signals based on grid levels
        
        Returns:
            List[TradeSignal]: List of trade signals
        """
        signals = []
        
        try:
            for symbol in self.symbols:
                # Skip if no grid info
                if symbol not in self.active_grids:
                    continue
                    
                grid_info = self.active_grids[symbol]
                current_price = grid_info['current_price']
                upper_boundary = grid_info['upper_boundary']
                lower_boundary = grid_info['lower_boundary']
                grid_spacing = grid_info['grid_spacing']
                
                # Get current ticker
                ticker = self.exchange.get_ticker(symbol)
                if not ticker or 'price' not in ticker:
                    continue
                    
                # Update current price
                latest_price = ticker['price']
                
                # Check if price has moved enough to trigger a grid level
                for i in range(self.grid_levels + 1):
                    grid_price = lower_boundary + i * grid_spacing
                    
                    # Buy signal if price crosses below a grid level
                    if current_price > grid_price and latest_price <= grid_price:
                        # Calculate position size
                        investment_per_grid = self.total_investment_percent / self.grid_levels
                        
                        # Create buy signal
                        signal = TradeSignal(
                            symbol=symbol,
                            side='buy',
                            price=grid_price,
                            take_profit=grid_price * (1 + self.grid_spacing_percent / 100),
                            stop_loss=None,  # Grid trading typically doesn't use stop loss
                            order_type='limit'
                        )
                        
                        signals.append(signal)
                        logger.info(f"Grid BUY signal for {symbol} at {grid_price:.2f}")
                        
                    # Sell signal if price crosses above a grid level
                    elif current_price < grid_price and latest_price >= grid_price:
                        # Create sell signal
                        signal = TradeSignal(
                            symbol=symbol,
                            side='sell',
                            price=grid_price,
                            take_profit=grid_price * (1 - self.grid_spacing_percent / 100),
                            stop_loss=None,  # Grid trading typically doesn't use stop loss
                            order_type='limit'
                        )
                        
                        signals.append(signal)
                        logger.info(f"Grid SELL signal for {symbol} at {grid_price:.2f}")
                        
                # Update current price in grid info
                self.active_grids[symbol]['current_price'] = latest_price
                
        except Exception as e:
            logger.error(f"Error generating grid trading signals: {str(e)}")
            
        return signals
