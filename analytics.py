# database/models/analytics.py
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.sql import func
from database.db import Base

class Analytics(Base):
    """
    Analytics model for storing system performance metrics
    """
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True)
    record_type = Column(String(50), nullable=False)
    
    # Overall system performance
    user_count = Column(Integer, nullable=True)
    active_user_count = Column(Integer, nullable=True)
    total_traded_volume = Column(Float, nullable=True)
    total_profit = Column(Float, nullable=True)
    total_fees_collected = Column(Float, nullable=True)
    
    # Trading performance
    total_trades = Column(Integer, nullable=True)
    win_count = Column(Integer, nullable=True)
    loss_count = Column(Integer, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    average_win = Column(Float, nullable=True)
    average_loss = Column(Float, nullable=True)
    largest_win = Column(Float, nullable=True)
    largest_loss = Column(Float, nullable=True)
    
    # Risk metrics
    max_drawdown = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    
    # Strategy performance
    strategy_performance = Column(JSON, nullable=True)
    
    # Market conditions
    market_conditions = Column(Text, nullable=True)  # JSON string with market conditions
    
    # System metrics
    system_health = Column(JSON, nullable=True)
    api_response_times = Column(JSON, nullable=True)
    error_counts = Column(JSON, nullable=True)
    
    # Raw data (for various record types)
    data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    timestamp = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f"<Analytics(id={self.id}, record_type={self.record_type}, timestamp={self.timestamp})>"
