"""
Notification system for user and admin alerts
"""

import logging
import threading
import time
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Manages all notifications in the system
    """
    def __init__(self, config):
        self.config = config
        self.notification_thread = None
        self.running = False
        self.notification_queue = []
        self.queue_lock = threading.Lock()
        self.logger = logger
        
    def start(self):
        """
        Start the notification manager
        """
        if self.running:
            logger.warning("Notification manager already running")
            return
            
        logger.info("Starting notification manager")
        self.running = True
        self.notification_thread = threading.Thread(target=self._notification_loop)
        self.notification_thread.daemon = True
        self.notification_thread.start()
        
        logger.info("Notification manager started")
    
    def stop(self):
        """
        Stop the notification manager
        """
        if not self.running:
            logger.warning("Notification manager already stopped")
            return
            
        logger.info("Stopping notification manager")
        self.running = False
        
        if self.notification_thread:
            self.notification_thread.join(timeout=5)
            
        logger.info("Notification manager stopped")
    
    def _notification_loop(self):
        """
        Main notification processing loop
        """
        while self.running:
            try:
                notifications_to_process = []
                
                # Get notifications from queue
                with self.queue_lock:
                    if self.notification_queue:
                        notifications_to_process = self.notification_queue.copy()
                        self.notification_queue = []
                
                # Process notifications
                for notification in notifications_to_process:
                    self._process_notification(notification)
                    
                # Sleep if no notifications
                if not notifications_to_process:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in notification loop: {str(e)}")
                time.sleep(5)
    
    def _process_notification(self, notification):
        """
        Process a single notification
        
        Args:
            notification: Notification data
        """
        try:
            notification_type = notification.get("type", "general")
            
            if notification_type == "admin_alert":
                self._send_admin_notification(notification)
            elif notification_type == "user_notification":
                self._send_user_notification(notification)
            elif notification_type == "trade_notification":
                self._send_trade_notification_internal(notification)
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                
        except Exception as e:
            logger.error(f"Error processing notification: {str(e)}")
    
    def _send_admin_notification(self, notification):
        """
        Send notification to admin
        
        Args:
            notification: Notification data
        """
        try:
            subject = notification.get("subject", "Admin Alert")
            message = notification.get("message", "")
            
            # Log notification
            logger.info(f"Admin Alert: {subject}")
            
            # In a real system, you would send email/SMS/etc.
            # For this example, we'll just log it
            logger.info(f"ADMIN NOTIFICATION: {subject} - {message}")
            
        except Exception as e:
            logger.error(f"Error sending admin notification: {str(e)}")
    
    def _send_user_notification(self, notification):
        """
        Send notification to user
        
        Args:
            notification: Notification data
        """
        try:
            user_id = notification.get("user_id")
            message = notification.get("message", "")
            notification_type = notification.get("notification_type", "general")
            
            if not user_id:
                logger.error("User notification missing user_id")
                return
                
            # Log notification
            logger.info(f"User Notification: {user_id} - {notification_type}")
            
            # In a real system, you would send Telegram message, email, etc.
            # For this example, we'll just log it
            logger.info(f"USER NOTIFICATION [{user_id}]: {message}")
            
        except Exception as e:
            logger.error(f"Error sending user notification: {str(e)}")
    
    def _send_trade_notification_internal(self, notification):
        """
        Send trade notification via appropriate channel
        
        Args:
            notification: Trade notification data
        """
        try:
            user = notification.get("user")
            message = notification.get("message", "")
            
            if not user or not hasattr(user, "telegram_id") or not user.telegram_id:
                logger.warning(f"Cannot send notification: No telegram ID for user {user.id if user else 'unknown'}")
                return
            
            # Send via Telegram
            from notification.telegram_bot import TelegramBot
            telegram_bot = TelegramBot()
            telegram_bot.send_message(user.telegram_id, message)
            
            logger.info(f"Trade notification sent to user {user.id}")
            
        except Exception as e:
            logger.error(f"Error sending trade notification: {str(e)}")
    
    def send_notification(self, user_id, message, notification_type="general"):
        """
        Queue a notification to a user
        
        Args:
            user_id: User ID
            message: Notification message
            notification_type: Type of notification
        """
        with self.queue_lock:
            self.notification_queue.append({
                "type": "user_notification",
                "user_id": user_id,
                "message": message,
                "notification_type": notification_type,
                "timestamp": time.time()
            })
    
    def send_admin_alert(self, subject, message):
        """
        Queue an alert for admin
        
        Args:
            subject: Alert subject
            message: Alert message
        """
        with self.queue_lock:
            self.notification_queue.append({
                "type": "admin_alert",
                "subject": subject,
                "message": message,
                "timestamp": time.time()
            })
    
    def send_broadcast(self, message, user_ids=None):
        """
        Send message to multiple users
        
        Args:
            message: Message to send
            user_ids: List of user IDs (None for all users)
        """
        try:
            if user_ids is None:
                # In a real system, you would get all active users from database
                logger.info(f"Broadcasting message to all users: {message}")
            else:
                # Queue notification for each user
                for user_id in user_ids:
                    self.send_notification(user_id, message, "broadcast")
                    
                logger.info(f"Broadcasting message to {len(user_ids)} users")
                
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
            
    def send_trade_notification(self, user, strategy, signal, trade_result):
        """
        Send trade notification to user
        
        Args:
            user: User object
            strategy: Strategy object
            signal: Signal object
            trade_result: Trade result object
        """
        try:
            # Check if we have a telegram ID for the user
            if not user or not hasattr(user, 'telegram_id') or not user.telegram_id:
                self.logger.warning(f"Cannot send notification: No telegram ID for user {user.id if user else 'unknown'}")
                return False
                
            # Format notification message based on trade type
            is_entry = not hasattr(trade_result, 'exit_price') or trade_result.exit_price is None
            
            if is_entry:
                # Entry notification
                message = f"🔔 *New Trade Opened*\n\n"
                message += f"*Symbol:* {signal.symbol}\n"
                message += f"*Side:* {'BUY' if signal.side.lower() == 'buy' else 'SELL'}\n"
                message += f"*Strategy:* {strategy.name}\n"
                message += f"*Entry Price:* {trade_result.entry_price:.8f}\n"
                message += f"*Quantity:* {signal.quantity}\n"
                
                # Add stop loss if available
                if hasattr(signal, 'stop_loss') and signal.stop_loss:
                    message += f"*Stop Loss:* {signal.stop_loss:.8f}\n"
                    
                # Add take profit if available
                if hasattr(signal, 'take_profit') and signal.take_profit:
                    message += f"*Take Profit:* {signal.take_profit:.8f}\n"
            else:
                # Exit notification
                profit = trade_result.profit if hasattr(trade_result, 'profit') else 0
                profit_percent = (profit / (signal.quantity * trade_result.entry_price)) * 100 if trade_result.entry_price > 0 else 0
                
                emoji = "✅" if profit > 0 else "❌"
                
                message = f"{emoji} *Trade Closed*\n\n"
                message += f"*Symbol:* {signal.symbol}\n"
                message += f"*Side:* {'BUY' if signal.side.lower() == 'buy' else 'SELL'}\n"
                message += f"*Strategy:* {strategy.name}\n"
                message += f"*Entry Price:* {trade_result.entry_price:.8f}\n"
                message += f"*Exit Price:* {trade_result.exit_price:.8f}\n"
                message += f"*Quantity:* {signal.quantity}\n"
                message += f"*Profit/Loss:* {profit:.8f} ({profit_percent:.2f}%)\n"
                
                # Add fee information if available
                if hasattr(trade_result, 'fee') and trade_result.fee:
                    message += f"*Fee:* {trade_result.fee:.8f}\n"
                    message += f"*Net Profit/Loss:* {profit - trade_result.fee:.8f}\n"
            
            # Queue notification for processing
            with self.queue_lock:
                self.notification_queue.append({
                    "type": "trade_notification",
                    "user": user,
                    "message": message,
                    "timestamp": time.time()
                })
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending trade notification: {e}")
            return False