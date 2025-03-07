# database/models/position.py
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database.db import Base

class PositionStatus(enum.Enum):
    """
    Position status enumeration
    """
    OPEN = "open"
    CLOSED = "closed"
    
class PositionSide(enum.Enum):
    """
    Position side enumeration
    """
    LONG = "long"
    SHORT = "short"
    
class Position(Base):
    """
    Position model (groups multiple trades)
    """
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Position details
    symbol = Column(String(20), nullable=False)
    side = Column(Enum(PositionSide), nullable=False)
    strategy = Column(String(50), nullable=False)
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN)
    
    # Position size
    initial_entry_price = Column(Float, nullable=False)
    average_entry_price = Column(Float, nullable=False)
    initial_quantity = Column(Float, nullable=False)
    current_quantity = Column(Float, nullable=False)
    
    # Risk management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    trailing_stop = Column(Boolean, default=False)
    trailing_stop_distance = Column(Float, nullable=True)
    break_even_activated = Column(Boolean, default=False)
    break_even_price = Column(Float, nullable=True)
    
    # Position result
    close_price = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    profit_percentage = Column(Float, nullable=True)
    
    # Analysis data
    position_analysis = Column(Text, nullable=True)  # JSON string with position analysis
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Position(id={self.id}, user_id={self.user_id}, symbol={self.symbol}, side={self.side.value}, status={self.status.value})>"
