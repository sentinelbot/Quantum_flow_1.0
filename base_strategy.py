# strategies/base_strategy.py
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

from exchange.abstract_exchange import AbstractExchange, TradeSignal

class BaseStrategy(ABC):
    """
    Base Strategy Class for Trading Systems

    Provides a comprehensive framework for developing and managing 
    trading strategies with robust configuration, market data handling, 
    and signal generation capabilities.
    """

    def __init__(
        self, 
        name: str, 
        exchange: AbstractExchange, 
        user: Any, 
        risk_manager: Any, 
        config: Dict[str, Any]
    ):
        """
        Initialize the base trading strategy.

        Args:
            name (str): Unique identifier for the strategy
            exchange (AbstractExchange): Trading exchange interface
            user (Any): User context for the strategy
            risk_manager (Any): Risk management module
            config (Dict[str, Any]): Configuration parameters for the strategy
        """
        # Core strategy configuration
        self.name = name
        self.exchange = exchange
        self.user = user
        self.risk_manager = risk_manager
        self.config = config or {}
        
        # Logging setup
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Strategy state management
        self.enabled = True
        self.last_update_time = 0
        
        # Strategy parameters
        self.update_interval = self.config.get('update_interval', 60)  # seconds
        self.timeframes = self.config.get('timeframes', [])
        self.symbols = self.config.get('symbols', [])
        self.allocation_percent = self.config.get('allocation_percent', 10.0)
        
        # Strategy parameters from configuration
        self.parameters = self.config.get('parameters', {})
        
        # Market data cache
        self.market_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        
    def is_enabled(self) -> bool:
        """
        Check if the strategy is currently enabled.

        Returns:
            bool: Strategy enabled status
        """
        return self.enabled
        
    def enable(self) -> None:
        """
        Enable the trading strategy.
        """
        self.enabled = True
        self.logger.info(f"Strategy {self.name} enabled")
        
    def disable(self) -> None:
        """
        Disable the trading strategy.
        """
        self.enabled = False
        self.logger.info(f"Strategy {self.name} disabled")
        
    def set_exchange(self, exchange: AbstractExchange) -> None:
        """
        Set the exchange for this strategy.

        Args:
            exchange (AbstractExchange): Trading exchange interface
        """
        self.exchange = exchange
        
    def set_user(self, user: Any) -> None:
        """
        Set the user context for this strategy.

        Args:
            user (Any): User context
        """
        self.user = user
        
    def set_risk_manager(self, risk_manager: Any) -> None:
        """
        Set the risk manager for this strategy.

        Args:
            risk_manager (Any): Risk management module
        """
        self.risk_manager = risk_manager
        
    def update(self) -> None:
        """
        Update strategy with latest market data.
        Manages cache and triggers strategy-specific update logic.
        """
        current_time = time.time()
        
        # Check if update is needed based on interval
        if current_time - self.last_update_time < self.update_interval:
            return
            
        try:
            # Update market data for all symbols and timeframes
            for symbol in self.symbols:
                self.market_data[symbol] = {}
                
                for timeframe in self.timeframes:
                    candles = self.exchange.get_historical_data(symbol, timeframe, limit=100)
                    self.market_data[symbol][timeframe] = candles
                    
            # Invoke strategy-specific update logic
            self._update()
            
            # Update last update timestamp
            self.last_update_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error updating strategy {self.name}: {str(e)}")
        
    def get_position_size(self, symbol: str, price: float) -> float:
        """
        Calculate position size based on strategy allocation and account balance.

        Args:
            symbol (str): Trading symbol
            price (float): Current market price

        Returns:
            float: Calculated position size
        """
        try:
            if not self.exchange:
                self.logger.warning("Exchange not set, cannot calculate position size")
                return 0
                
            # Get account balance
            account_balance = self.exchange.get_account_balance()
            
            if account_balance <= 0:
                self.logger.warning("Account balance is zero or negative")
                return 0
                
            # Calculate allocation amount
            allocation_amount = account_balance * (self.allocation_percent / 100)
            
            # Calculate quantity based on current price
            if price <= 0:
                self.logger.warning(f"Invalid price for {symbol}: {price}")
                return 0
                
            quantity = allocation_amount / price
            
            # Apply position size constraints
            min_quantity = self.parameters.get('min_position_size', 0)
            max_quantity = self.parameters.get('max_position_size', float('inf'))
            
            quantity = max(min_quantity, min(quantity, max_quantity))
            
            # Round to appropriate precision
            decimals = self._get_quantity_precision(symbol)
            quantity = round(quantity, decimals)
            
            return quantity
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0
        
    def _get_quantity_precision(self, symbol: str) -> int:
        """
        Determine decimal precision for position quantity.

        Args:
            symbol (str): Trading symbol

        Returns:
            int: Number of decimal places for quantity
        """
        # Ideally, this would retrieve precision from exchange
        return 6
        
    def create_signal(
        self, 
        symbol: str, 
        side: str, 
        price: float, 
        quantity: Optional[float] = None, 
        stop_loss: Optional[float] = None, 
        take_profit: Optional[float] = None
    ) -> Optional[TradeSignal]:
        """
        Create a trading signal with optional parameters.

        Args:
            symbol (str): Trading symbol
            side (str): Trade side (buy/sell)
            price (float): Entry price
            quantity (float, optional): Trade quantity
            stop_loss (float, optional): Stop loss price
            take_profit (float, optional): Take profit price

        Returns:
            Optional[TradeSignal]: Generated trade signal
        """
        try:
            # Calculate quantity if not provided
            if quantity is None:
                quantity = self.get_position_size(symbol, price)
                
            if quantity <= 0:
                self.logger.warning(f"Cannot create signal with zero quantity for {symbol}")
                return None
            
            # Construct trade signal
            signal = TradeSignal(
                symbol=symbol,
                side=side,
                price=price,
                quantity=quantity,
                strategy=self.name,
                timestamp=int(time.time() * 1000)
            )
            
            # Set optional parameters
            if stop_loss:
                signal.stop_loss = stop_loss
                
            if take_profit:
                signal.take_profit = take_profit
                
            return signal
            
        except Exception as e:
            self.logger.error(f"Error creating signal: {e}")
            return None
        
    def get_candles(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Retrieve cached market candles for a specific symbol and timeframe.

        Args:
            symbol (str): Trading symbol
            timeframe (str): Market data timeframe

        Returns:
            List[Dict[str, Any]]: Cached market candles
        """
        return self.market_data.get(symbol, {}).get(timeframe, [])
        
    def calculate_take_profit_price(self, entry_price: float, side: str) -> float:
        """
        Calculate take profit price based on strategy configuration.

        Args:
            entry_price (float): Trade entry price
            side (str): Trade side (buy/sell)

        Returns:
            float: Calculated take profit price
        """
        take_profit_percent = self.parameters.get('take_profit_percent', 1.0)
        
        return (
            entry_price * (1 + take_profit_percent / 100) if side.lower() == 'buy'
            else entry_price * (1 - take_profit_percent / 100)
        )
        
    def calculate_stop_loss_price(self, entry_price: float, side: str) -> float:
        """
        Calculate stop loss price based on strategy configuration.

        Args:
            entry_price (float): Trade entry price
            side (str): Trade side (buy/sell)

        Returns:
            float: Calculated stop loss price
        """
        stop_loss_percent = self.parameters.get('stop_loss_percent', 0.5)
        
        return (
            entry_price * (1 - stop_loss_percent / 100) if side.lower() == 'buy'
            else entry_price * (1 + stop_loss_percent / 100)
        )
    
    @abstractmethod
    def _update(self) -> None:
        """
        Strategy-specific update logic.
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def generate_signals(self) -> List[TradeSignal]:
        """
        Generate trading signals based on strategy logic.
        
        Returns:
            List[TradeSignal]: List of generated trade signals
        """
        pass