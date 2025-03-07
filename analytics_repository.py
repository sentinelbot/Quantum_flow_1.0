# database/repository/analytics_repository.py
import logging
from typing import Dict, Any, List
from datetime import datetime
from database.models.analytics import Analytics

logger = logging.getLogger(__name__)

class AnalyticsRepository:
    """
    Repository for Analytics model
    """
    def __init__(self, db):
        self.db = db
        
    def add_performance_record(self, win_rate: float, total_profit: float, total_trades: int, timestamp: int = None) -> Analytics:
        """
        Add a performance record
        """
        session = self.db.get_session()
        try:
            # Create analytics record
            record = Analytics(
                record_type="performance",
                win_rate=win_rate,
                total_profit=total_profit,
                total_trades=total_trades,
                timestamp=datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()
            )
            
            session.add(record)
            session.commit()
            logger.info(f"Added performance record with ID {record.id}")
            return record
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding performance record: {str(e)}")
            return None
        finally:
            session.close()
            
    def add_strategy_performance(self, strategy_performance: Dict[str, Dict[str, Any]], timestamp: int = None) -> Analytics:
        """
        Add a strategy performance record
        """
        session = self.db.get_session()
        try:
            # Create analytics record
            record = Analytics(
                record_type="strategy_performance",
                strategy_performance=strategy_performance,
                timestamp=datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()
            )
            
            session.add(record)
            session.commit()
            logger.info(f"Added strategy performance record with ID {record.id}")
            return record
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding strategy performance record: {str(e)}")
            return None
        finally:
            session.close()
            
    def add_system_health_record(self, system_health: Dict[str, Any], api_response_times: Dict[str, float], 
                               error_counts: Dict[str, int], timestamp: int = None) -> Analytics:
        """
        Add a system health record
        """
        session = self.db.get_session()
        try:
            # Create analytics record
            record = Analytics(
                record_type="system_health",
                system_health=system_health,
                api_response_times=api_response_times,
                error_counts=error_counts,
                timestamp=datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()
            )
            
            session.add(record)
            session.commit()
            logger.info(f"Added system health record with ID {record.id}")
            return record
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding system health record: {str(e)}")
            return None
        finally:
            session.close()
            
    def add_market_conditions_record(self, market_conditions: Dict[str, Any], timestamp: int = None) -> Analytics:
        """
        Add a market conditions record
        """
        session = self.db.get_session()
        try:
            # Create analytics record
            record = Analytics(
                record_type="market_conditions",
                market_conditions=str(market_conditions),  # Convert to string for Text column
                timestamp=datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()
            )
            
            session.add(record)
            session.commit()
            logger.info(f"Added market conditions record with ID {record.id}")
            return record
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding market conditions record: {str(e)}")
            return None
        finally:
            session.close()
            
    def add_user_stats_record(self, user_count: int, active_user_count: int, timestamp: int = None) -> Analytics:
        """
        Add a user statistics record
        """
        session = self.db.get_session()
        try:
            # Create analytics record
            record = Analytics(
                record_type="user_stats",
                user_count=user_count,
                active_user_count=active_user_count,
                timestamp=datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()
            )
            
            session.add(record)
            session.commit()
            logger.info(f"Added user stats record with ID {record.id}")
            return record
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding user stats record: {str(e)}")
            return None
        finally:
            session.close()
            
    def get_recent_performance(self, limit: int = 30) -> List[Analytics]:
        """
        Get recent performance records
        """
        session = self.db.get_session()
        try:
            records = session.query(Analytics).filter(
                Analytics.record_type == "performance"
            ).order_by(
                Analytics.timestamp.desc()
            ).limit(limit).all()
            return records
        except Exception as e:
            logger.error(f"Error getting recent performance: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_recent_strategy_performance(self, limit: int = 30) -> List[Analytics]:
        """
        Get recent strategy performance records
        """
        session = self.db.get_session()
        try:
            records = session.query(Analytics).filter(
                Analytics.record_type == "strategy_performance"
            ).order_by(
                Analytics.timestamp.desc()
            ).limit(limit).all()
            return records
        except Exception as e:
            logger.error(f"Error getting recent strategy performance: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_recent_system_health(self, limit: int = 30) -> List[Analytics]:
        """
        Get recent system health records
        """
        session = self.db.get_session()
        try:
            records = session.query(Analytics).filter(
                Analytics.record_type == "system_health"
            ).order_by(
                Analytics.timestamp.desc()
            ).limit(limit).all()
            return records
        except Exception as e:
            logger.error(f"Error getting recent system health: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_performance_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Analytics]:
        """
        Get performance records within a date range
        """
        session = self.db.get_session()
        try:
            records = session.query(Analytics).filter(
                Analytics.record_type == "performance",
                Analytics.timestamp >= start_date,
                Analytics.timestamp <= end_date
            ).order_by(
                Analytics.timestamp
            ).all()
            return records
        except Exception as e:
            logger.error(f"Error getting performance by date range: {str(e)}")
            return []
        finally:
            session.close()