# database/models/user.py
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from database.db import Base

class RiskLevel(enum.Enum):
    """
    Risk level enumeration
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
   
class TradingMode(enum.Enum):
    """
    Trading mode enumeration
    """
    PAPER = "paper"
    LIVE = "live"
   
class User(Base):
    """
    User model
    """
    __tablename__ = "users"
   
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(20), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    username = Column(String(50), nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
   
    # KYC/AML verification
    kyc_verified = Column(Boolean, default=False)
    kyc_submitted_at = Column(DateTime, nullable=True)
    kyc_verified_at = Column(DateTime, nullable=True)
    kyc_documents = Column(JSON, nullable=True)
   
    # API configuration
    preferred_exchange = Column(String(50), default="binance")
    api_key_id = Column(String(36), nullable=True)  # UUID reference to encrypted API keys
   
    # Trading configuration
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM)
    trading_mode = Column(Enum(TradingMode), default=TradingMode.PAPER)
    is_active = Column(Boolean, default=True)
    is_paused = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)  # Added admin flag
    trading_pairs = Column(JSON, nullable=True)  # List of enabled trading pairs
    strategy_config = Column(JSON, nullable=True)  # Strategy allocation configuration
   
    # Performance metrics
    balance = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
   
    # Notification preferences
    notification_settings = Column(JSON, nullable=True)
   
    # Referral data
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referral_code = Column(String(20), unique=True, nullable=True)
   
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
   
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, risk_level={self.risk_level.value})>"