# database/models/transaction.py
import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.sql import func
from database.db import Base

class TransactionType(enum.Enum):
    """
    Transaction type enumeration
    """
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE_FEE = "trade_fee"
    REFERRAL_COMMISSION = "referral_commission"
    
class TransactionStatus(enum.Enum):
    """
    Transaction status enumeration
    """
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    
class Transaction(Base):
    """
    Transaction model
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    trade_id = Column(Integer, ForeignKey('trades.id'), nullable=True)
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Fee details
    fee_percentage = Column(Float, nullable=True)
    fee_calculation = Column(String(255), nullable=True)  # Description of fee calculation
    
    # Blockchain details (for fee collection)
    wallet_address = Column(String(100), nullable=True)
    transaction_hash = Column(String(100), nullable=True)
    block_confirmation = Column(Integer, nullable=True)
    
    # Referral details
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, type={self.transaction_type.value}, amount={self.amount}, status={self.status.value})>"
