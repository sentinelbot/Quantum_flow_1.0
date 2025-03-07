# database/repository/trade_repository.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from database.models.trade import Trade, TradeStatus, TradeSide

logger = logging.getLogger(__name__)

class TradeRepository:
    """
    Repository for Trade model
    """
    def __init__(self, db):
        self.db = db
        
    def add_trade(self, user_id: int, strategy_name: str, symbol: str, side: str, 
                 entry_price: float, quantity: float, take_profit: float = None, 
                 stop_loss: float = None, trade_id: str = None, timestamp: int = None) -> Trade:
        """
        Add a new trade
        """
        session = self.db.get_session()
        try:
            # Convert side string to enum
            try:
                trade_side = TradeSide(side.lower())
            except ValueError:
                logger.error(f"Invalid trade side: {side}")
                return None
                
            # Calculate amount
            amount = entry_price * quantity
            
            # Create trade
            trade = Trade(
                user_id=user_id,
                strategy=strategy_name,
                symbol=symbol,
                side=trade_side,
                price=entry_price,
                quantity=quantity,
                amount=amount,
                stop_loss=stop_loss,
                take_profit=take_profit,
                exchange_trade_id=trade_id,
                created_at=datetime.fromtimestamp(timestamp) if timestamp else func.now()
            )
            
            session.add(trade)
            session.commit()
            logger.info(f"Added new trade with ID {trade.id} for user {user_id}")
            return trade
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding trade: {str(e)}")
            return None
        finally:
            session.close()
            
    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        """
        Get trade by ID
        """
        session = self.db.get_session()
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            return trade
        except Exception as e:
            logger.error(f"Error getting trade by ID {trade_id}: {str(e)}")
            return None
        finally:
            session.close()
            
    def get_trades_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Trade]:
        """
        Get trades by user ID
        """
        session = self.db.get_session()
        try:
            trades = session.query(Trade).filter(
                Trade.user_id == user_id
            ).order_by(
                desc(Trade.created_at)
            ).offset(offset).limit(limit).all()
            return trades
        except Exception as e:
            logger.error(f"Error getting trades for user {user_id}: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_open_trades_by_user(self, user_id: int) -> List[Trade]:
        """
        Get open trades by user ID
        """
        session = self.db.get_session()
        try:
            trades = session.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == TradeStatus.OPEN
            ).order_by(
                desc(Trade.created_at)
            ).all()
            return trades
        except Exception as e:
            logger.error(f"Error getting open trades for user {user_id}: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_all_trades(self, limit: int = 1000, offset: int = 0) -> List[Trade]:
        """
        Get all trades
        """
        session = self.db.get_session()
        try:
            trades = session.query(Trade).order_by(
                desc(Trade.created_at)
            ).offset(offset).limit(limit).all()
            return trades
        except Exception as e:
            logger.error(f"Error getting all trades: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_recent_trades(self, hours: int = 24) -> List[Trade]:
        """
        Get trades from the last N hours
        """
        session = self.db.get_session()
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            trades = session.query(Trade).filter(
                Trade.created_at >= since
            ).order_by(
                desc(Trade.created_at)
            ).all()
            return trades
        except Exception as e:
            logger.error(f"Error getting recent trades: {str(e)}")
            return []
        finally:
            session.close()
            
    def update_trade(self, trade_id: int, **kwargs) -> bool:
        """
        Update trade properties
        """
        session = self.db.get_session()
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                logger.warning(f"Trade with ID {trade_id} not found")
                return False
                
            # Update trade properties
            for key, value in kwargs.items():
                if hasattr(trade, key):
                    setattr(trade, key, value)
                    
            session.commit()
            logger.info(f"Updated trade with ID {trade_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating trade {trade_id}: {str(e)}")
            return False
        finally:
            session.close()
            
    def close_trade(self, trade_id: int, close_price: float, profit: float, profit_percentage: float) -> bool:
        """
        Close a trade
        """
        return self.update_trade(
            trade_id,
            status=TradeStatus.CLOSED,
            close_price=close_price,
            profit=profit,
            profit_percentage=profit_percentage,
            closed_at=datetime.utcnow()
        )
        
    def get_trades_by_symbol(self, symbol: str, limit: int = 100) -> List[Trade]:
        """
        Get trades by symbol
        """
        session = self.db.get_session()
        try:
            trades = session.query(Trade).filter(
                Trade.symbol == symbol
            ).order_by(
                desc(Trade.created_at)
            ).limit(limit).all()
            return trades
        except Exception as e:
            logger.error(f"Error getting trades for symbol {symbol}: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_trades_by_strategy(self, strategy: str, limit: int = 100) -> List[Trade]:
        """
        Get trades by strategy
        """
        session = self.db.get_session()
        try:
            trades = session.query(Trade).filter(
                Trade.strategy == strategy
            ).order_by(
                desc(Trade.created_at)
            ).limit(limit).all()
            return trades
        except Exception as e:
            logger.error(f"Error getting trades for strategy {strategy}: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_user_performance(self, user_id: int) -> Dict[str, Any]:
        """
        Get performance metrics for a user
        """
        session = self.db.get_session()
        try:
            # Get total trades
            total_trades = session.query(func.count(Trade.id)).filter(
                Trade.user_id == user_id,
                Trade.status == TradeStatus.CLOSED
            ).scalar() or 0
            
            # Get winning trades
            win_trades = session.query(func.count(Trade.id)).filter(
                Trade.user_id == user_id,
                Trade.status == TradeStatus.CLOSED,
                Trade.profit > 0
            ).scalar() or 0
            
            # Get losing trades
            lose_trades = session.query(func.count(Trade.id)).filter(
                Trade.user_id == user_id,
                Trade.status == TradeStatus.CLOSED,
                Trade.profit <= 0
            ).scalar() or 0
            
            # Calculate win rate
            win_rate = win_trades / total_trades if total_trades > 0 else 0
            
            # Get total profit
            total_profit = session.query(func.sum(Trade.profit)).filter(
                Trade.user_id == user_id,
                Trade.status == TradeStatus.CLOSED
            ).scalar() or 0
            
            # Get average win
            avg_win = session.query(func.avg(Trade.profit)).filter(
                Trade.user_id == user_id,
                Trade.status == TradeStatus.CLOSED,
                Trade.profit > 0
            ).scalar() or 0
            
            # Get average loss
            avg_loss = session.query(func.avg(Trade.profit)).filter(
                Trade.user_id == user_id,
                Trade.status == TradeStatus.CLOSED,
                Trade.profit <= 0
            ).scalar() or 0
            
            return {
                "total_trades": total_trades,
                "win_trades": win_trades,
                "lose_trades": lose_trades,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "avg_win": avg_win,
                "avg_loss": avg_loss
            }
            
        except Exception as e:
            logger.error(f"Error getting performance for user {user_id}: {str(e)}")
            return {}
        finally:
            session.close()
            
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics by strategy
        """
        session = self.db.get_session()
        try:
            # Get all strategies
            strategies = session.query(Trade.strategy).distinct().all()
            
            result = {}
            for (strategy,) in strategies:
                # Get total trades
                total_trades = session.query(func.count(Trade.id)).filter(
                    Trade.strategy == strategy,
                    Trade.status == TradeStatus.CLOSED
                ).scalar() or 0
                
                # Get winning trades
                win_trades = session.query(func.count(Trade.id)).filter(
                    Trade.strategy == strategy,
                    Trade.status == TradeStatus.CLOSED,
                    Trade.profit > 0
                ).scalar() or 0
                
                # Calculate win rate
                win_rate = win_trades / total_trades if total_trades > 0 else 0
                
                # Get total profit
                total_profit = session.query(func.sum(Trade.profit)).filter(
                    Trade.strategy == strategy,
                    Trade.status == TradeStatus.CLOSED
                ).scalar() or 0
                
                result[strategy] = {
                    "total_trades": total_trades,
                    "win_trades": win_trades,
                    "win_rate": win_rate,
                    "total_profit": total_profit
                }
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting strategy performance: {str(e)}")
            return {}
        finally:
            session.close()
            
    def mark_fee_collected(self, trade_id: int, fee_amount: float, referral_fee_amount: float = 0) -> bool:
        """
        Mark trade fee as collected
        """
        return self.update_trade(
            trade_id,
            fee_collected=True,
            fee_amount=fee_amount,
            referral_fee_amount=referral_fee_amount
        )
