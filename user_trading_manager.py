# services/user_trading_manager.py
import logging
from typing import Dict, Any, Optional

class UserTradingManager:
    """Manages user trading settings including mode switching"""
    
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    def set_trading_mode(self, user_id, mode):
        """Set user's trading mode"""
        try:
            if mode not in ['paper', 'live']:
                self.logger.error(f"Invalid trading mode: {mode}")
                return False
                
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if settings already exist for this user
            cursor.execute(
                "SELECT 1 FROM user_trading_settings WHERE user_id = %s",
                (user_id,)
            )
            
            if cursor.fetchone():
                # Update existing record
                cursor.execute("""
                    UPDATE user_trading_settings
                    SET trading_mode = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    RETURNING id
                """, (mode, user_id))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO user_trading_settings
                    (user_id, trading_mode)
                    VALUES (%s, %s)
                    RETURNING id
                """, (user_id, mode))
                
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                self.logger.info(f"Set trading mode to {mode} for user {user_id}")
                return True
            else:
                self.logger.warning(f"Failed to set trading mode for user {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting trading mode: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()
            return False
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                self.db.release_connection(conn)
    
    def set_risk_level(self, user_id, risk_level):
        """Set user's risk level"""
        try:
            if risk_level not in ['low', 'medium', 'high']:
                self.logger.error(f"Invalid risk level: {risk_level}")
                return False
                
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if settings already exist for this user
            cursor.execute(
                "SELECT 1 FROM user_trading_settings WHERE user_id = %s",
                (user_id,)
            )
            
            if cursor.fetchone():
                # Update existing record
                cursor.execute("""
                    UPDATE user_trading_settings
                    SET risk_level = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    RETURNING id
                """, (risk_level, user_id))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO user_trading_settings
                    (user_id, risk_level)
                    VALUES (%s, %s)
                    RETURNING id
                """, (user_id, risk_level))
                
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                self.logger.info(f"Set risk level to {risk_level} for user {user_id}")
                return True
            else:
                self.logger.warning(f"Failed to set risk level for user {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting risk level: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()
            return False
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                self.db.release_connection(conn)
    
    def set_paused_state(self, user_id, is_paused):
        """Pause or resume trading for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if settings already exist for this user
            cursor.execute(
                "SELECT 1 FROM user_trading_settings WHERE user_id = %s",
                (user_id,)
            )
            
            if cursor.fetchone():
                # Update existing record
                cursor.execute("""
                    UPDATE user_trading_settings
                    SET is_paused = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    RETURNING id
                """, (is_paused, user_id))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO user_trading_settings
                    (user_id, is_paused)
                    VALUES (%s, %s)
                    RETURNING id
                """, (user_id, is_paused))
                
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                status = "paused" if is_paused else "resumed"
                self.logger.info(f"Trading {status} for user {user_id}")
                return True
            else:
                status = "pause" if is_paused else "resume"
                self.logger.warning(f"Failed to {status} trading for user {user_id}")
                return False
                
        except Exception as e:
            status = "pausing" if is_paused else "resuming"
            self.logger.error(f"Error {status} trading: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()
            return False
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                self.db.release_connection(conn)
    
    def get_trading_settings(self, user_id):
        """Get user's trading settings"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT trading_mode, risk_level, is_paused, max_open_positions, max_position_size
                FROM user_trading_settings
                WHERE user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'trading_mode': result[0],
                    'risk_level': result[1],
                    'is_paused': result[2],
                    'max_open_positions': result[3],
                    'max_position_size': result[4]
                }
            else:
                # Return default settings if no record exists
                return {
                    'trading_mode': 'paper',
                    'risk_level': 'medium',
                    'is_paused': False,
                    'max_open_positions': 5,
                    'max_position_size': 0.1
                }
                
        except Exception as e:
            self.logger.error(f"Error getting trading settings: {e}")
            return None
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                self.db.release_connection(conn)
    
    def update_position_limits(self, user_id, max_positions=None, max_size=None):
        """Update position limits for a user"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Check if settings already exist for this user
            cursor.execute(
                "SELECT 1 FROM user_trading_settings WHERE user_id = %s",
                (user_id,)
            )
            
            settings_exist = cursor.fetchone() is not None
            
            if settings_exist:
                # Build update query dynamically based on provided parameters
                update_parts = []
                params = []
                
                if max_positions is not None:
                    update_parts.append("max_open_positions = %s")
                    params.append(max_positions)
                    
                if max_size is not None:
                    update_parts.append("max_position_size = %s")
                    params.append(max_size)
                    
                if not update_parts:
                    # Nothing to update
                    return True
                    
                update_parts.append("updated_at = CURRENT_TIMESTAMP")
                
                query = f"""
                    UPDATE user_trading_settings
                    SET {', '.join(update_parts)}
                    WHERE user_id = %s
                    RETURNING id
                """
                params.append(user_id)
                
                cursor.execute(query, tuple(params))
            else:
                # Insert new record with default values for missing parameters
                insert_columns = ["user_id"]
                insert_values = ["%s"]
                params = [user_id]
                
                if max_positions is not None:
                    insert_columns.append("max_open_positions")
                    insert_values.append("%s")
                    params.append(max_positions)
                    
                if max_size is not None:
                    insert_columns.append("max_position_size")
                    insert_values.append("%s")
                    params.append(max_size)
                    
                query = f"""
                    INSERT INTO user_trading_settings
                    ({', '.join(insert_columns)})
                    VALUES ({', '.join(insert_values)})
                    RETURNING id
                """
                
                cursor.execute(query, tuple(params))
                
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                self.logger.info(f"Updated position limits for user {user_id}")
                return True
            else:
                self.logger.warning(f"Failed to update position limits for user {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating position limits: {e}")
            if 'conn' in locals() and conn:
                conn.rollback()
            return False
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                self.db.release_connection(conn)