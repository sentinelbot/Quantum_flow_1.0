# risk/drawdown_protector.py
import logging
import time
from typing import Dict, Any, List, Optional
from enum import Enum

from config.app_config import AppConfig
from database.db import Database
from notification.notification_manager import NotificationManager

logger = logging.getLogger(__name__)

class DrawdownStage(Enum):
    """
    Drawdown stage enumeration
    """
    NORMAL = 0
    STAGE_1 = 1  # 5% drawdown: Reduce position sizing by 25%
    STAGE_2 = 2  # 10% drawdown: Pause new entries, manage existing only
    STAGE_3 = 3  # 15% drawdown: Begin strategic position reduction
    STAGE_4 = 4  # 20% drawdown: Complete trading halt, notify admin
    
class RecoveryMode(Enum):
    """
    Recovery mode enumeration
    """
    DISABLED = 0
    ENABLED = 1
    

class DrawdownProtector:
    """
    Drawdown protection system
    """
    def __init__(self, config: AppConfig, db: Database, notification_manager: NotificationManager):
        self.config = config
        self.db = db
        self.notification_manager = notification_manager
        
        # Get drawdown thresholds from config
        self.drawdown_thresholds = {
            DrawdownStage.STAGE_1: self.config.get('risk.drawdown_protection.stage1_threshold', 5.0),
            DrawdownStage.STAGE_2: self.config.get('risk.drawdown_protection.stage2_threshold', 10.0),
            DrawdownStage.STAGE_3: self.config.get('risk.drawdown_protection.stage3_threshold', 15.0),
            DrawdownStage.STAGE_4: self.config.get('risk.drawdown_protection.stage4_threshold', 20.0)
        }
        
        # User drawdown state
        self.user_drawdown_state = {}
        
        # Recovery mode settings
        self.recovery_reduction = 0.5  # 50% position size reduction in recovery mode
        self.recovery_profit_target = 5.0  # 5% profit target to exit recovery mode
        
        logger.info("Drawdown protector initialized")
        
    def check_drawdown(self, user_id: int, current_equity: float, max_equity: float = None) -> DrawdownStage:
        """
        Check drawdown for a user and return the drawdown stage
        
        Args:
            user_id: User ID
            current_equity: Current equity
            max_equity: Maximum equity (if None, will use cached or get from DB)
            
        Returns:
            DrawdownStage: Current drawdown stage
        """
        try:
            # Initialize user state if needed
            if user_id not in self.user_drawdown_state:
                self.user_drawdown_state[user_id] = {
                    'max_equity': max_equity or current_equity,
                    'current_equity': current_equity,
                    'drawdown_stage': DrawdownStage.NORMAL,
                    'recovery_mode': RecoveryMode.DISABLED,
                    'last_updated': time.time()
                }
                
            # Get user state
            user_state = self.user_drawdown_state[user_id]
            
            # Update equity values
            user_state['current_equity'] = current_equity
            
            if max_equity:
                user_state['max_equity'] = max_equity
            elif current_equity > user_state['max_equity']:
                user_state['max_equity'] = current_equity
                
            # Calculate drawdown percentage
            max_equity = user_state['max_equity']
            
            if max_equity <= 0:
                return DrawdownStage.NORMAL
                
            drawdown_percent = (max_equity - current_equity) / max_equity * 100
            
            # Determine drawdown stage
            previous_stage = user_state['drawdown_stage']
            
            if drawdown_percent >= self.drawdown_thresholds[DrawdownStage.STAGE_4]:
                user_state['drawdown_stage'] = DrawdownStage.STAGE_4
            elif drawdown_percent >= self.drawdown_thresholds[DrawdownStage.STAGE_3]:
                user_state['drawdown_stage'] = DrawdownStage.STAGE_3
            elif drawdown_percent >= self.drawdown_thresholds[DrawdownStage.STAGE_2]:
                user_state['drawdown_stage'] = DrawdownStage.STAGE_2
            elif drawdown_percent >= self.drawdown_thresholds[DrawdownStage.STAGE_1]:
                user_state['drawdown_stage'] = DrawdownStage.STAGE_1
            else:
                user_state['drawdown_stage'] = DrawdownStage.NORMAL
                
            # Send notification if stage changed
            if previous_stage != user_state['drawdown_stage']:
                self._notify_drawdown_stage_change(user_id, previous_stage, user_state['drawdown_stage'], drawdown_percent)
                
            # Check if recovery mode should be activated
            if previous_stage >= DrawdownStage.STAGE_3 and user_state['drawdown_stage'] < DrawdownStage.STAGE_3:
                self._activate_recovery_mode(user_id)
                
            # Update timestamp
            user_state['last_updated'] = time.time()
            
            return user_state['drawdown_stage']
            
        except Exception as e:
            logger.error(f"Error checking drawdown for user {user_id}: {str(e)}")
            return DrawdownStage.NORMAL
            
    def get_drawdown_stage(self, user_id: int) -> DrawdownStage:
        """
        Get current drawdown stage for a user
        
        Args:
            user_id: User ID
            
        Returns:
            DrawdownStage: Current drawdown stage
        """
        if user_id in self.user_drawdown_state:
            return self.user_drawdown_state[user_id]['drawdown_stage']
        else:
            # Get user equity from database
            user_repo = self.db.get_repository('user')
            user = user_repo.get_user_by_id(user_id)
            
            if user:
                return self.check_drawdown(user_id, user.equity)
            else:
                return DrawdownStage.NORMAL
                
    def is_recovery_mode_active(self, user_id: int) -> bool:
        """
        Check if recovery mode is active for a user
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if recovery mode is active, False otherwise
        """
        if user_id in self.user_drawdown_state:
            return self.user_drawdown_state[user_id]['recovery_mode'] == RecoveryMode.ENABLED
        else:
            return False
            
    def _activate_recovery_mode(self, user_id: int) -> None:
        """
        Activate recovery mode for a user
        
        Args:
            user_id: User ID
        """
        try:
            if user_id in self.user_drawdown_state:
                user_state = self.user_drawdown_state[user_id]
                user_state['recovery_mode'] = RecoveryMode.ENABLED
                
                # Send notification
                self._notify_recovery_mode_activated(user_id)
                
                logger.info(f"Recovery mode activated for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error activating recovery mode for user {user_id}: {str(e)}")
            
    def deactivate_recovery_mode(self, user_id: int) -> None:
        """
        Deactivate recovery mode for a user
        
        Args:
            user_id: User ID
        """
        try:
            if user_id in self.user_drawdown_state:
                user_state = self.user_drawdown_state[user_id]
                
                if user_state['recovery_mode'] == RecoveryMode.ENABLED:
                    user_state['recovery_mode'] = RecoveryMode.DISABLED
                    
                    # Send notification
                    self._notify_recovery_mode_deactivated(user_id)
                    
                    logger.info(f"Recovery mode deactivated for user {user_id}")
                    
        except Exception as e:
            logger.error(f"Error deactivating recovery mode for user {user_id}: {str(e)}")
            
    def check_recovery_progress(self, user_id: int, current_equity: float) -> None:
        """
        Check recovery progress and deactivate recovery mode if target reached
        
        Args:
            user_id: User ID
            current_equity: Current equity
        """
        try:
            if user_id not in self.user_drawdown_state:
                return
                
            user_state = self.user_drawdown_state[user_id]
            
            if user_state['recovery_mode'] != RecoveryMode.ENABLED:
                return
                
            # Update equity
            user_state['current_equity'] = current_equity
            
            # Check if recovery target reached
            equity_at_recovery_start = user_state.get('equity_at_recovery_start', user_state['current_equity'])
            profit_percent = (current_equity - equity_at_recovery_start) / equity_at_recovery_start * 100
            
            if profit_percent >= self.recovery_profit_target:
                self.deactivate_recovery_mode(user_id)
                
        except Exception as e:
            logger.error(f"Error checking recovery progress for user {user_id}: {str(e)}")
            
    def get_position_size_multiplier(self, user_id: int) -> float:
        """
        Get position size multiplier based on drawdown stage and recovery mode
        
        Args:
            user_id: User ID
            
        Returns:
            float: Position size multiplier (0.0-1.0)
        """
        try:
            if user_id not in self.user_drawdown_state:
                return 1.0
                
            user_state = self.user_drawdown_state[user_id]
            drawdown_stage = user_state['drawdown_stage']
            recovery_mode = user_state['recovery_mode']
            
            # Apply drawdown stage reduction
            if drawdown_stage == DrawdownStage.STAGE_1:
                # Stage 1: Reduce position sizing by 25%
                multiplier = 0.75
            elif drawdown_stage == DrawdownStage.STAGE_2:
                # Stage 2: Reduce position sizing by 50%
                multiplier = 0.5
            elif drawdown_stage == DrawdownStage.STAGE_3:
                # Stage 3: Reduce position sizing by 75%
                multiplier = 0.25
            elif drawdown_stage == DrawdownStage.STAGE_4:
                # Stage 4: No new positions
                multiplier = 0.0
            else:
                multiplier = 1.0
                
            # Apply recovery mode reduction
            if recovery_mode == RecoveryMode.ENABLED:
                multiplier *= self.recovery_reduction
                
            return multiplier
            
        except Exception as e:
            logger.error(f"Error getting position size multiplier for user {user_id}: {str(e)}")
            return 1.0
            
    def should_reduce_positions(self, user_id: int) -> bool:
        """
        Check if positions should be reduced (Stage 3+)
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if positions should be reduced, False otherwise
        """
        try:
            stage = self.get_drawdown_stage(user_id)
            return stage >= DrawdownStage.STAGE_3
            
        except Exception as e:
            logger.error(f"Error checking if positions should be reduced for user {user_id}: {str(e)}")
            return False
            
    def should_halt_trading(self, user_id: int) -> bool:
        """
        Check if trading should be halted (Stage 4)
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if trading should be halted, False otherwise
        """
        try:
            stage = self.get_drawdown_stage(user_id)
            return stage >= DrawdownStage.STAGE_4
            
        except Exception as e:
            logger.error(f"Error checking if trading should be halted for user {user_id}: {str(e)}")
            return False
            
    def _notify_drawdown_stage_change(self, user_id: int, previous_stage: DrawdownStage, 
                                    current_stage: DrawdownStage, drawdown_percent: float) -> None:
        """
        Send notification about drawdown stage change
        
        Args:
            user_id: User ID
            previous_stage: Previous drawdown stage
            current_stage: Current drawdown stage
            drawdown_percent: Current drawdown percentage
        """
        try:
            # Skip if no change or normal stage
            if previous_stage == current_stage or current_stage == DrawdownStage.NORMAL:
                return
                
            # Prepare message
            message = f"⚠️ Drawdown Protection Activated: Stage {current_stage.value}\n"
            message += f"Current drawdown: {drawdown_percent:.2f}%\n\n"
            
            if current_stage == DrawdownStage.STAGE_1:
                message += "Position sizing reduced by 25%. Please monitor your portfolio."
            elif current_stage == DrawdownStage.STAGE_2:
                message += "New trade entries paused. Only managing existing positions."
            elif current_stage == DrawdownStage.STAGE_3:
                message += "Strategic position reduction initiated. High-risk positions will be closed."
            elif current_stage == DrawdownStage.STAGE_4:
                message += "TRADING HALTED. All positions will be monitored for exit opportunities."
                
            # Send notification
            self.notification_manager.send_notification(
                user_id=user_id,
                message=message,
                notification_type="risk_alert",
                priority="high"
            )
            
            # Notify admin if Stage 3 or 4
            if current_stage >= DrawdownStage.STAGE_3:
                admin_message = f"🚨 ADMIN ALERT: User {user_id} reached drawdown Stage {current_stage.value}\n"
                admin_message += f"Drawdown: {drawdown_percent:.2f}%"
                
                self.notification_manager.send_admin_notification(
                    message=admin_message,
                    notification_type="risk_alert",
                    priority="high"
                )
                
        except Exception as e:
            logger.error(f"Error sending drawdown notification for user {user_id}: {str(e)}")
            
    def _notify_recovery_mode_activated(self, user_id: int) -> None:
        """
        Send notification about recovery mode activation
        
        Args:
            user_id: User ID
        """
        try:
            message = "🔄 Recovery Mode Activated\n\n"
            message += "Trading will continue with reduced position sizes and higher quality setups "
            message += "until the portfolio recovers."
            
            self.notification_manager.send_notification(
                user_id=user_id,
                message=message,
                notification_type="risk_alert"
            )
            
        except Exception as e:
            logger.error(f"Error sending recovery mode activation notification for user {user_id}: {str(e)}")
            
    def _notify_recovery_mode_deactivated(self, user_id: int) -> None:
        """
        Send notification about recovery mode deactivation
        
        Args:
            user_id: User ID
        """
        try:
            message = "✅ Recovery Mode Deactivated\n\n"
            message += "Your account has recovered successfully. "
            message += "Normal trading parameters have been restored."
            
            self.notification_manager.send_notification(
                user_id=user_id,
                message=message,
                notification_type="risk_alert"
            )
            
        except Exception as e:
            logger.error(f"Error sending recovery mode deactivation notification for user {user_id}: {str(e)}")