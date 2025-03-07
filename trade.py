
# database/models/trade.py
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database.db import Base

class TradeType(enum.Enum):
    """
    Trade type enumeration
    """
    SPOT = "spot"
    MARGIN = "margin"
    FUTURES = "futures"
    
class TradeSide(enum.Enum):
    """
    Trade side enumeration
    """
    BUY = "buy"
    SELL = "sell"
    
class TradeStatus(enum.Enum):
    """
    Trade status enumeration
    """
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"
    
class Trade(Base):
    """
    Trade model
    """
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=True)
    
    # Exchange information
    exchange = Column(String(50), default="binance")
    exchange_trade_id = Column(String(100), nullable=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False)
    trade_type = Column(Enum(TradeType), default=TradeType.SPOT)
    side = Column(Enum(TradeSide), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)  # price * quantity
    fee = Column(Float, default=0.0)
    fee_currency = Column(String(10), nullable=True)
    
    # Strategy information
    strategy = Column(String(50), nullable=False)
    timeframe = Column(String(10), nullable=True)
    signal_score = Column(Float, nullable=True)  # Confidence score of the signal
    
    # Trade management
    entry_balance = Column(Float, nullable=True)  # Balance before trade
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    trailing_stop = Column(Boolean, default=False)
    trailing_stop_value = Column(Float, nullable=True)
    
    # Trade result
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN)
    close_price = Column(Float, nullable=True)
    close_quantity = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    profit_percentage = Column(Float, nullable=True)
    exit_balance = Column(Float, nullable=True)  # Balance after trade
    
    # Fee collection
    fee_collected = Column(Boolean, default=False)
    fee_amount = Column(Float, nullable=True)
    referral_fee_amount = Column(Float, nullable=True)
    
    # Analysis data
    market_conditions = Column(Text, nullable=True)  # JSON string with market conditions
    trade_analysis = Column(Text, nullable=True)  # JSON string with trade analysis
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Trade(id={self.id}, user_id={self.user_id}, symbol={self.symbol}, side={self.side.value}, status={self.status.value})>"
