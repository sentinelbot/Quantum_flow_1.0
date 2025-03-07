# database/repository/position_repository.py
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta
from database.models.position import Position, PositionStatus, PositionSide

logger = logging.getLogger(__name__)

class PositionRepository:
    """
    Repository for Position model
    """
    def __init__(self, db):
        self.db = db
        
    def create_position(self, user_id: int, symbol: str, side: str, strategy: str,
                      entry_price: float, quantity: float, stop_loss: float = None,
                      take_profit: float = None) -> Position:
        """
        Create a new position
        """
        session = self.db.get_session()
        try:
            # Convert side string to enum
            try:
                position_side = PositionSide(side.lower())
            except ValueError:
                logger.error(f"Invalid position side: {side}")
                return None
                
            # Create position
            position = Position(
                user_id=user_id,
                symbol=symbol,
                side=position_side,
                strategy=strategy,
                initial_entry_price=entry_price,
                average_entry_price=entry_price,
                initial_quantity=quantity,
                current_quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            session.add(position)
            session.commit()
            logger.info(f"Created new position with ID {position.id} for user {user_id}")
            return position
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating position: {str(e)}")
            return None
        finally:
            session.close()
            
    def get_position_by_id(self, position_id: int) -> Optional[Position]:
        """
        Get position by ID
        """
        session = self.db.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id).first()
            return position
        except Exception as e:
            logger.error(f"Error getting position by ID {position_id}: {str(e)}")
            return None
        finally:
            session.close()
            
    def get_positions_by_user(self, user_id: int, status: str = None) -> List[Position]:
        """
        Get positions by user ID, optionally filtered by status
        """
        session = self.db.get_session()
        try:
            query = session.query(Position).filter(Position.user_id == user_id)
            
            if status:
                try:
                    position_status = PositionStatus(status.lower())
                    query = query.filter(Position.status == position_status)
                except ValueError:
                    logger.error(f"Invalid position status: {status}")
                    
            positions = query.order_by(desc(Position.created_at)).all()
            return positions
        except Exception as e:
            logger.error(f"Error getting positions for user {user_id}: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_open_positions_by_user(self, user_id: int) -> List[Position]:
        """
        Get open positions by user ID
        """
        return self.get_positions_by_user(user_id, "open")
        
    def get_open_position_by_symbol(self, user_id: int, symbol: str, side: str = None) -> Optional[Position]:
        """
        Get open position by symbol and optionally side
        """
        session = self.db.get_session()
        try:
            query = session.query(Position).filter(
                Position.user_id == user_id,
                Position.symbol == symbol,
                Position.status == PositionStatus.OPEN
            )
            
            if side:
                try:
                    position_side = PositionSide(side.lower())
                    query = query.filter(Position.side == position_side)
                except ValueError:
                    logger.error(f"Invalid position side: {side}")
                    
            position = query.first()
            return position
        except Exception as e:
            logger.error(f"Error getting open position for user {user_id}, symbol {symbol}: {str(e)}")
            return None
        finally:
            session.close()
            
    def update_position(self, position_id: int, **kwargs) -> bool:
        """
        Update position properties
        """
        session = self.db.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id).first()
            if not position:
                logger.warning(f"Position with ID {position_id} not found")
                return False
                
            # Update position properties
            for key, value in kwargs.items():
                if hasattr(position, key):
                    setattr(position, key, value)
                    
            session.commit()
            logger.info(f"Updated position with ID {position_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating position {position_id}: {str(e)}")
            return False
        finally:
            session.close()
            
    def update_position_size(self, position_id: int, additional_quantity: float, new_price: float) -> bool:
        """
        Update position size and recalculate average entry price
        """
        session = self.db.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id).first()
            if not position:
                logger.warning(f"Position with ID {position_id} not found")
                return False
                
            # Calculate new average entry price
            total_value = (position.average_entry_price * position.current_quantity) + (new_price * additional_quantity)
            new_quantity = position.current_quantity + additional_quantity
            new_avg_price = total_value / new_quantity if new_quantity > 0 else new_price
            
            # Update position
            position.average_entry_price = new_avg_price
            position.current_quantity = new_quantity
            
            session.commit()
            logger.info(f"Updated position size for ID {position_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating position size {position_id}: {str(e)}")
            return False
        finally:
            session.close()
            
    def close_position(self, position_id: int, close_price: float, profit: float, profit_percentage: float) -> bool:
        """
        Close a position
        """
        from datetime import datetime
        return self.update_position(
            position_id,
            status=PositionStatus.CLOSED,
            close_price=close_price,
            profit=profit,
            profit_percentage=profit_percentage,
            closed_at=datetime.utcnow()
        )
        
    def update_stop_loss(self, position_id: int, new_stop_loss: float) -> bool:
        """
        Update position stop loss
        """
        return self.update_position(position_id, stop_loss=new_stop_loss)
        
    def update_take_profit(self, position_id: int, new_take_profit: float) -> bool:
        """
        Update position take profit
        """
        return self.update_position(position_id, take_profit=new_take_profit)
        
    def enable_trailing_stop(self, position_id: int, distance: float) -> bool:
        """
        Enable trailing stop for a position
        """
        return self.update_position(
            position_id,
            trailing_stop=True,
            trailing_stop_distance=distance
        )
        
    def enable_break_even(self, position_id: int, break_even_price: float) -> bool:
        """
        Enable break even for a position
        """
        return self.update_position(
            position_id,
            break_even_activated=True,
            break_even_price=break_even_price
        )
        
    # Added missing methods that were causing errors in the logs
    
    def get_all_active_positions(self) -> List[Position]:
        """
        Get all active positions across all users
        
        Returns:
            List of Position objects with status=OPEN
        """
        session = self.db.get_session()
        try:
            positions = session.query(Position).filter(
                Position.status == PositionStatus.OPEN
            ).order_by(desc(Position.created_at)).all()
            return positions
        except Exception as e:
            logger.error(f"Error getting all active positions: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_positions_by_symbol(self, symbol: str, status: str = None) -> List[Position]:
        """
        Get positions by symbol, optionally filtered by status
        
        Args:
            symbol: Trading symbol (e.g., BTC/USDT)
            status: Position status (optional)
            
        Returns:
            List of Position objects for the specified symbol
        """
        session = self.db.get_session()
        try:
            query = session.query(Position).filter(Position.symbol == symbol)
            
            if status:
                try:
                    position_status = PositionStatus(status.lower())
                    query = query.filter(Position.status == position_status)
                except ValueError:
                    logger.error(f"Invalid position status: {status}")
                    
            positions = query.order_by(desc(Position.created_at)).all()
            return positions
        except Exception as e:
            logger.error(f"Error getting positions for symbol {symbol}: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_active_positions_count(self) -> int:
        """
        Get count of all active positions
        
        Returns:
            Number of open positions
        """
        session = self.db.get_session()
        try:
            count = session.query(Position).filter(
                Position.status == PositionStatus.OPEN
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error counting active positions: {str(e)}")
            return 0
        finally:
            session.close()
    
    def get_active_positions_by_strategy(self, strategy: str) -> List[Position]:
        """
        Get active positions using a specific strategy
        
        Args:
            strategy: Strategy name
            
        Returns:
            List of Position objects using the specified strategy
        """
        session = self.db.get_session()
        try:
            positions = session.query(Position).filter(
                Position.status == PositionStatus.OPEN,
                Position.strategy == strategy
            ).order_by(desc(Position.created_at)).all()
            return positions
        except Exception as e:
            logger.error(f"Error getting active positions by strategy {strategy}: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_positions_at_risk(self, threshold_percentage: float = 5.0) -> List[Position]:
        """
        Get active positions that are near their stop loss (at risk)
        
        Args:
            threshold_percentage: Percentage threshold to consider a position at risk
            
        Returns:
            List of Position objects that are close to hitting stop loss
        """
        session = self.db.get_session()
        try:
            at_risk_positions = []
            active_positions = session.query(Position).filter(
                Position.status == PositionStatus.OPEN,
                Position.stop_loss.isnot(None)
            ).all()
            
            for position in active_positions:
                if position.stop_loss and position.current_price:
                    if position.side == PositionSide.LONG:
                        # For long positions, at risk if price is close to stop loss
                        distance_to_stop = ((position.current_price - position.stop_loss) / position.current_price) * 100
                        if distance_to_stop <= threshold_percentage:
                            at_risk_positions.append(position)
                    else:
                        # For short positions, at risk if price is close to stop loss
                        distance_to_stop = ((position.stop_loss - position.current_price) / position.current_price) * 100
                        if distance_to_stop <= threshold_percentage:
                            at_risk_positions.append(position)
            
            return at_risk_positions
        except Exception as e:
            logger.error(f"Error getting positions at risk: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_user_active_symbols(self, user_id: int) -> List[str]:
        """
        Get list of symbols with active positions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of symbols with active positions
        """
        session = self.db.get_session()
        try:
            symbols = session.query(Position.symbol).filter(
                Position.user_id == user_id,
                Position.status == PositionStatus.OPEN
            ).distinct().all()
            return [symbol[0] for symbol in symbols]
        except Exception as e:
            logger.error(f"Error getting active symbols for user {user_id}: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_all_active_symbols(self) -> List[str]:
        """
        Get list of all symbols with active positions across all users
        
        Returns:
            List of symbols with active positions
        """
        session = self.db.get_session()
        try:
            symbols = session.query(Position.symbol).filter(
                Position.status == PositionStatus.OPEN
            ).distinct().all()
            return [symbol[0] for symbol in symbols]
        except Exception as e:
            logger.error(f"Error getting all active symbols: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_positions_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about positions
        
        Returns:
            Dictionary with position statistics
        """
        session = self.db.get_session()
        try:
            total_positions = session.query(Position).count()
            active_positions = session.query(Position).filter(
                Position.status == PositionStatus.OPEN
            ).count()
            closed_positions = session.query(Position).filter(
                Position.status == PositionStatus.CLOSED
            ).count()
            
            # Calculate profit statistics for closed positions
            profit_positions = session.query(Position).filter(
                Position.status == PositionStatus.CLOSED,
                Position.profit > 0
            ).count()
            
            loss_positions = session.query(Position).filter(
                Position.status == PositionStatus.CLOSED,
                Position.profit < 0
            ).count()
            
            # Calculate win rate
            win_rate = (profit_positions / closed_positions * 100) if closed_positions > 0 else 0
            
            # Get total profit
            total_profit_result = session.query(
                Position.profit.label('total_profit')
            ).filter(
                Position.status == PositionStatus.CLOSED
            ).all()
            
            total_profit = sum([result[0] for result in total_profit_result if result[0] is not None])
            
            return {
                "total_positions": total_positions,
                "active_positions": active_positions,
                "closed_positions": closed_positions,
                "profitable_positions": profit_positions,
                "loss_positions": loss_positions,
                "win_rate": win_rate,
                "total_profit": total_profit
            }
        except Exception as e:
            logger.error(f"Error getting position statistics: {str(e)}")
            return {
                "total_positions": 0,
                "active_positions": 0,
                "closed_positions": 0,
                "profitable_positions": 0,
                "loss_positions": 0,
                "win_rate": 0,
                "total_profit": 0
            }
        finally:
            session.close()
    
    def get_positions_by_date_range(self, start_date: datetime, end_date: datetime, 
                                   status: str = None) -> List[Position]:
        """
        Get positions created within a specific date range
        
        Args:
            start_date: Start datetime
            end_date: End datetime
            status: Position status filter (optional)
            
        Returns:
            List of Position objects created within the date range
        """
        session = self.db.get_session()
        try:
            query = session.query(Position).filter(
                Position.created_at >= start_date,
                Position.created_at <= end_date
            )
            
            if status:
                try:
                    position_status = PositionStatus(status.lower())
                    query = query.filter(Position.status == position_status)
                except ValueError:
                    logger.error(f"Invalid position status: {status}")
                    
            positions = query.order_by(desc(Position.created_at)).all()
            return positions
        except Exception as e:
            logger.error(f"Error getting positions by date range: {str(e)}")
            return []
        finally:
            session.close()