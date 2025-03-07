import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import or_, text, inspect
from datetime import datetime
from database.models.user import User, RiskLevel, TradingMode

logger = logging.getLogger(__name__)

class UserRepository:
    """
    Repository for User model with schema-adaptive querying and robust error handling
    """
    def __init__(self, db_manager=None):
        """
        Initialize UserRepository with optional database manager

        Args:
            db_manager: Database manager instance (optional)
        """
        self.db = db_manager
        self._column_cache = {}
        
        if not self.db:
            logger.warning("UserRepository initialized without a database manager")
        else:
            # Check schema on initialization
            self._validate_schema()
        
    def _validate_schema(self):
        """
        Validate database schema against model and cache column existence
        """
        try:
            if not self.db or not self.db.engine:
                return
                
            inspector = inspect(self.db.engine)
            if not inspector.has_table("users"):
                logger.warning("Users table does not exist in database")
                return
                
            # Get actual columns in the database
            columns = {col['name'] for col in inspector.get_columns("users")}
            
            # Cache column existence for future queries
            for col_name in ["is_admin", "is_active", "is_paused", "kyc_verified", 
                            "trading_mode", "risk_level"]:
                self._column_cache[col_name] = col_name in columns
                
                if col_name not in columns:
                    logger.warning(f"Column '{col_name}' missing from users table in database")
                    
        except Exception as e:
            logger.error(f"Error validating schema: {str(e)}")
    
    def _has_column(self, column_name):
        """
        Check if a column exists in the users table
        
        Args:
            column_name: Name of the column to check
            
        Returns:
            bool: True if column exists, False otherwise
        """
        # Return cached result if available
        if column_name in self._column_cache:
            return self._column_cache[column_name]
            
        # Check database schema if not cached
        try:
            if not self.db or not self.db.engine:
                return False
                
            inspector = inspect(self.db.engine)
            columns = {col['name'] for col in inspector.get_columns("users")}
            exists = column_name in columns
            
            # Cache result
            self._column_cache[column_name] = exists
            return exists
            
        except Exception as e:
            logger.error(f"Error checking column existence: {str(e)}")
            return False
    
    def create_user(self, telegram_id: str, email: str, **kwargs) -> User:
        """
        Create a new user with comprehensive error handling
        """
        if not self.db:
            logger.error("Cannot create user: Database manager not initialized")
            raise RuntimeError("Database manager not initialized")
        
        session = self.db.get_session()
        try:
            # Check if user already exists
            existing_user = session.query(User).filter(
                or_(User.telegram_id == telegram_id, User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.telegram_id == telegram_id:
                    logger.warning(f"User with Telegram ID {telegram_id} already exists")
                else:
                    logger.warning(f"User with email {email} already exists")
                session.close()
                return existing_user
                
            # Create new user
            user = User(
                telegram_id=telegram_id,
                email=email,
                **kwargs
            )
            
            # Set default notification settings
            if 'notification_settings' not in kwargs:
                user.notification_settings = {
                    "trade_execution": True,
                    "take_profit_hit": True,
                    "stop_loss_hit": True,
                    "position_adjustment": True,
                    "daily_summary": True,
                    "system_alerts": True
                }
                
            session.add(user)
            session.commit()
            logger.info(f"Created new user with ID {user.id}")
            return user
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID with improved error handling
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return None
        
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            return user
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_all_users(self) -> List[User]:
        """
        Get all users with comprehensive error handling
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
        
        session = self.db.get_session()
        try:
            users = session.query(User).all()
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """
        Update user properties with robust validation
        """
        if not self.db:
            logger.error("Cannot update user: Database manager not initialized")
            return False
        
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User with ID {user_id} not found")
                return False
                
            # Update user properties
            for key, value in kwargs.items():
                if hasattr(user, key):
                    # Skip updating columns that don't exist in database
                    if key not in ["is_admin", "is_active", "is_paused"] or self._has_column(key):
                        setattr(user, key, value)
                    
            session.commit()
            logger.info(f"Updated user with ID {user_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating user {user_id}: {str(e)}")
            return False
        finally:
            session.close()
    
    def count_users(self) -> int:
        """
        Count total number of users with error handling
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return 0
        
        session = self.db.get_session()
        try:
            return session.query(User).count()
        except Exception as e:
            logger.error(f"Error counting users: {str(e)}")
            return 0
        finally:
            session.close()
    
    def count_active_users(self) -> int:
        """
        Count number of active users with schema-adaptive approach
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return 0
        
        session = self.db.get_session()
        try:
            # Check if is_active column exists
            if self._has_column("is_active"):
                return session.query(User).filter(User.is_active == True).count()
            else:
                # Fallback to count all users if is_active doesn't exist
                logger.warning("is_active column not found, counting all users")
                return session.query(User).count()
        except Exception as e:
            logger.error(f"Error counting active users: {str(e)}")
            return 0
        finally:
            session.close()
    
    def get_users_by_kyc_status(self, status: str) -> List[User]:
        """
        Get users by KYC status with error handling
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
        
        session = self.db.get_session()
        try:
            if self._has_column("kyc_status"):
                return session.query(User).filter(User.kyc_status == status).all()
            else:
                logger.warning("kyc_status column not found, returning empty list")
                return []
        except Exception as e:
            logger.error(f"Error getting users by KYC status: {str(e)}")
            return []
        finally:
            session.close()
    
    def verify_kyc(self, user_id: int) -> bool:
        """
        Mark user KYC as verified
        """
        return self.update_user(
            user_id, 
            kyc_verified=True,
            kyc_verified_at=datetime.utcnow()
        )
    
    def get_active_users(self) -> List[User]:
        """
        Get all active users with schema-adaptive implementation
        
        Returns:
            List of User objects with is_active=True
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
        
        session = self.db.get_session()
        try:
            # Schema-adaptive approach
            if self._has_column("is_active"):
                # Standard approach with is_active column
                try:
                    users = session.query(User).filter(User.is_active == True).all()
                    return users
                except Exception as e:
                    if "column users.is_admin does not exist" in str(e):
                        # Fall back to raw SQL if ORM fails due to missing is_admin column
                        logger.warning("Using raw SQL to get active users due to schema issue")
                        result = session.execute(text("SELECT * FROM users WHERE is_active = true"))
                        users = []
                        for row in result:
                            # Convert row to dict
                            user_dict = {column: value for column, value in zip(result.keys(), row)}
                            # Set default is_admin value
                            if "is_admin" not in user_dict:
                                user_dict["is_admin"] = False
                            # Create user object
                            user = User(**user_dict)
                            users.append(user)
                        return users
                    else:
                        raise
            else:
                # If is_active doesn't exist, return all users
                logger.warning("is_active column not found, returning all users")
                return session.query(User).all()
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            # Return empty list on error
            return []
        finally:
            session.close()
    
    def get_admin_users(self) -> List[User]:
        """
        Get all admin users with schema-adaptive implementation
        
        Returns:
            List of User objects with is_admin=True
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
        
        session = self.db.get_session()
        try:
            # Check if is_admin column exists
            if self._has_column("is_admin"):
                try:
                    users = session.query(User).filter(User.is_admin == True).all()
                    return users
                except Exception as e:
                    if "column users.is_admin does not exist" in str(e):
                        # Fall back to all users if query fails
                        logger.warning("is_admin column query failed, returning empty list")
                        return []
                    else:
                        raise
            else:
                # If is_admin doesn't exist in database, return empty list
                logger.warning("is_admin column not found, returning empty list")
                return []
        except Exception as e:
            logger.error(f"Error getting admin users: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_user_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        """
        Get user by Telegram ID
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            User object or None if not found
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return None
        
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            
            # Set default is_admin if needed
            if user and not self._has_column("is_admin") and not hasattr(user, "is_admin"):
                setattr(user, "is_admin", False)
                
            return user
        except Exception as e:
            logger.error(f"Error getting user by Telegram ID {telegram_id}: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_users_by_trading_mode(self, mode: TradingMode) -> List[User]:
        """
        Get users by trading mode with schema-adaptive implementation
        
        Args:
            mode: TradingMode enum value
            
        Returns:
            List of User objects with the specified trading mode
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
        
        session = self.db.get_session()
        try:
            # Check if trading_mode column exists
            if self._has_column("trading_mode"):
                users = session.query(User).filter(User.trading_mode == mode).all()
                return users
            else:
                logger.warning("trading_mode column not found, returning empty list")
                return []
        except Exception as e:
            logger.error(f"Error getting users by trading mode {mode}: {str(e)}")
            return []
        finally:
            session.close()
    
    def get_users_by_risk_level(self, risk_level: RiskLevel) -> List[User]:
        """
        Get users by risk level with schema-adaptive implementation
        
        Args:
            risk_level: RiskLevel enum value
            
        Returns:
            List of User objects with the specified risk level
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
        
        session = self.db.get_session()
        try:
            # Check if risk_level column exists
            if self._has_column("risk_level"):
                users = session.query(User).filter(User.risk_level == risk_level).all()
                return users
            else:
                logger.warning("risk_level column not found, returning empty list")
                return []
        except Exception as e:
            logger.error(f"Error getting users by risk level {risk_level}: {str(e)}")
            return []
        finally:
            session.close()
            
    def get_strategy_config(self, user_id: int) -> Dict[str, int]:
        """
        Get user's strategy configuration
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with strategy allocations or None if not found
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return None
            
        session = self.db.get_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None
                
            return user.strategy_config or {}
        except Exception as e:
            logger.error(f"Error getting strategy config for user {user_id}: {str(e)}")
            return None
        finally:
            session.close()
            
    def get_user_with_trading_settings(self, user_id: int) -> Optional[User]:
        """
        Get user with trading settings
        
        Args:
            user_id: User ID
            
        Returns:
            User object with trading settings or None if not found
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return None
            
        session = self.db.get_session()
        try:
            # Check if user_trading_settings table exists
            inspector = inspect(self.db.engine)
            has_trading_settings_table = inspector.has_table("user_trading_settings")
            
            if has_trading_settings_table:
                # Use raw SQL for maximum flexibility with different schema versions
                query = text("""
                    SELECT u.*, 
                           ts.trading_mode, 
                           ts.risk_level, 
                           ts.is_paused, 
                           ts.max_open_positions, 
                           ts.max_position_size
                    FROM users u
                    LEFT JOIN user_trading_settings ts ON u.id = ts.user_id
                    WHERE u.id = :user_id
                """)
                
                result = session.execute(query, {"user_id": user_id}).fetchone()
                
                if not result:
                    return None
                    
                # Convert result to dictionary
                column_names = result.keys()
                user_data = {col: result[col] for col in column_names if col not in [
                    'trading_mode', 'risk_level', 'is_paused', 
                    'max_open_positions', 'max_position_size'
                ]}
                
                # Create user object
                user = User(**user_data)
                
                # Add trading settings if available
                if result['trading_mode'] is not None:
                    user.trading_settings = {
                        'trading_mode': result['trading_mode'],
                        'risk_level': result['risk_level'],
                        'is_paused': result['is_paused'],
                        'max_open_positions': result['max_open_positions'],
                        'max_position_size': result['max_position_size']
                    }
                else:
                    user.trading_settings = None
                    
                return user
            else:
                # If trading settings table doesn't exist, just return user
                logger.warning("user_trading_settings table not found, returning user without trading settings")
                return self.get_user_by_id(user_id)
                
        except Exception as e:
            logger.error(f"Error getting user with trading settings: {str(e)}")
            return None
        finally:
            session.close()
            
    def update_trading_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """
        Update user's trading settings
        
        Args:
            user_id: User ID
            settings: Dictionary with trading settings
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return False
            
        session = self.db.get_session()
        try:
            # Check if user_trading_settings table exists
            inspector = inspect(self.db.engine)
            has_trading_settings_table = inspector.has_table("user_trading_settings")
            
            if not has_trading_settings_table:
                logger.warning("user_trading_settings table not found, cannot update trading settings")
                return False
                
            # Check if user exists
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User with ID {user_id} not found")
                return False
                
            # Check if user already has trading settings
            query = text("""
                SELECT 1 FROM user_trading_settings WHERE user_id = :user_id
            """)
            
            exists = session.execute(query, {"user_id": user_id}).scalar() is not None
            
            if exists:
                # Update existing settings
                update_query = text("""
                    UPDATE user_trading_settings
                    SET trading_mode = :trading_mode,
                        risk_level = :risk_level,
                        is_paused = :is_paused,
                        max_open_positions = :max_open_positions,
                        max_position_size = :max_position_size,
                        updated_at = NOW()
                    WHERE user_id = :user_id
                """)
                
                session.execute(update_query, {
                    "user_id": user_id,
                    "trading_mode": settings.get('trading_mode'),
                    "risk_level": settings.get('risk_level'),
                    "is_paused": settings.get('is_paused', False),
                    "max_open_positions": settings.get('max_open_positions'),
                    "max_position_size": settings.get('max_position_size')
                })
            else:
                # Insert new settings
                insert_query = text("""
                    INSERT INTO user_trading_settings (
                        user_id, trading_mode, risk_level, is_paused,
                        max_open_positions, max_position_size, created_at, updated_at
                    ) VALUES (
                        :user_id, :trading_mode, :risk_level, :is_paused,
                        :max_open_positions, :max_position_size, NOW(), NOW()
                    )
                """)
                
                session.execute(insert_query, {
                    "user_id": user_id,
                    "trading_mode": settings.get('trading_mode'),
                    "risk_level": settings.get('risk_level'),
                    "is_paused": settings.get('is_paused', False),
                    "max_open_positions": settings.get('max_open_positions'),
                    "max_position_size": settings.get('max_position_size')
                })
                
            session.commit()
            logger.info(f"Updated trading settings for user {user_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating trading settings for user {user_id}: {str(e)}")
            return False
        finally:
            session.close()
            
    def get_users_with_trading_settings(self) -> List[User]:
        """
        Get all users with their trading settings
        
        Returns:
            List of User objects with trading settings
        """
        if not self.db:
            logger.error("Database manager not initialized")
            return []
            
        session = self.db.get_session()
        try:
            # Check if user_trading_settings table exists
            inspector = inspect(self.db.engine)
            has_trading_settings_table = inspector.has_table("user_trading_settings")
            
            if has_trading_settings_table:
                # Use raw SQL to join users with trading settings
                query = text("""
                    SELECT u.*, 
                           ts.trading_mode, 
                           ts.risk_level, 
                           ts.is_paused, 
                           ts.max_open_positions, 
                           ts.max_position_size
                    FROM users u
                    LEFT JOIN user_trading_settings ts ON u.id = ts.user_id
                """)
                
                results = session.execute(query).fetchall()
                
                users = []
                for result in results:
                    # Convert result to dictionary
                    column_names = result.keys()
                    user_data = {col: result[col] for col in column_names if col not in [
                        'trading_mode', 'risk_level', 'is_paused', 
                        'max_open_positions', 'max_position_size'
                    ]}
                    
                    # Create user object
                    user = User(**user_data)
                    
                    # Add trading settings if available
                    if result['trading_mode'] is not None:
                        user.trading_settings = {
                            'trading_mode': result['trading_mode'],
                            'risk_level': result['risk_level'],
                            'is_paused': result['is_paused'],
                            'max_open_positions': result['max_open_positions'],
                            'max_position_size': result['max_position_size']
                        }
                    else:
                        user.trading_settings = None
                        
                    users.append(user)
                    
                return users
            else:
                # If trading settings table doesn't exist, just return all users
                logger.warning("user_trading_settings table not found, returning users without trading settings")
                return self.get_all_users()
                
        except Exception as e:
            logger.error(f"Error getting users with trading settings: {str(e)}")
            return []
        finally:
            session.close()