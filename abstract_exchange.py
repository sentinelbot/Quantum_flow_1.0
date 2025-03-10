"""
Abstract Exchange Interface
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class TradeResult:
    """
    Result of a trade execution
    """
    def __init__(self, trade_id: str, symbol: str, side: str, price: float, 
                 quantity: float, timestamp: int, success: bool, message: str = None):
        self.trade_id = trade_id
        self.symbol = symbol
        self.side = side
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp
        self.success = success
        self.message = message

class TradingSignal:
    """
    Trading signal generated by a strategy
    """
    def __init__(self, symbol: str, side: str, quantity: float, price: Optional[float] = None,
                 take_profit: Optional[float] = None, stop_loss: Optional[float] = None,
                 signal_type: str = "market", timeframe: str = "1h"):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.signal_type = signal_type
        self.timeframe = timeframe

class AbstractExchange(ABC):
    """
    Abstract exchange interface that all exchange implementations must follow
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the exchange connection
        
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Close the exchange connection
        """
        pass
    
    @abstractmethod
    def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance
        
        Returns:
            Dict mapping asset symbols to amounts
        """
        pass
    
    @abstractmethod
    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Current price or None if unavailable
        """
        pass
    
    @abstractmethod
    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, List]:
        """
        Get orderbook for a symbol
        
        Args:
            symbol: Trading pair symbol
            limit: Number of price levels to retrieve
            
        Returns:
            Orderbook with bids and asks
        """
        pass
    
    @abstractmethod
    def get_historical_klines(self, symbol: str, interval: str, 
                             start_time: Optional[int] = None, 
                             end_time: Optional[int] = None,
                             limit: int = 500) -> List[Dict]:
        """
        Get historical candlestick data
        
        Args:
            symbol: Trading pair symbol
            interval: Timeframe interval (e.g., '1m', '1h', '1d')
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Maximum number of candles
            
        Returns:
            List of candlestick data
        """
        pass
    
    @abstractmethod
    def execute_trade(self, signal: TradingSignal) -> Optional[TradeResult]:
        """
        Execute a trade based on a trading signal
        
        Args:
            signal: Trading signal
            
        Returns:
            Trade result or None if execution failed
        """
        pass
    
    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an open order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open orders
        
        Args:
            symbol: Trading pair symbol (optional)
            
        Returns:
            List of open orders
        """
        pass
    
    @abstractmethod
    def get_order_status(self, symbol: str, order_id: str) -> Optional[Dict]:
        """
        Get status of a specific order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            Order status or None if not found
        """
        pass
    # At the end of the file or near the class definitions
TradeSignal = TradingSignal