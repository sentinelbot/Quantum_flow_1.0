"""
Advanced Self-Healing System for Automated System Recovery and Resilience Management

This module provides a sophisticated self-healing mechanism to monitor, 
diagnose, and automatically recover critical system components.
"""

import logging
import threading
import time
import os
import psutil
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class SelfHealingSystem:
    """
    Comprehensive Self-Healing and System Recovery Management System

    Provides an advanced, configurable approach to system monitoring, 
    fault detection, and automated recovery strategies.
    """

    def __init__(
        self, 
        app=None, 
        config=None, 
        trading_engine=None, 
        system_monitor=None,
        notification_manager=None
    ):
        """
        Initialize the Self-Healing System with configurable dependencies.

        Args:
            app: Main application context
            config (dict): System configuration settings
            trading_engine: Core trading engine component
            system_monitor: System performance monitoring component
            notification_manager: Notification dispatch system
        """
        # Core system dependencies
        self.app = app
        self.config = config or {}
        self.trading_engine = trading_engine
        self.system_monitor = system_monitor
        self.notification_manager = notification_manager

        # Logging setup
        self.logger = logging.getLogger(__name__)

        # Self-healing configuration
        self.healing_interval = self.config.get('self_healing.interval', 10)
        self.max_recovery_attempts = self.config.get('self_healing.max_attempts', 5)
        self.error_cooldown = 1800  # 30 minutes in seconds

        # Monitoring state
        self.healing_thread: Optional[threading.Thread] = None
        self.running = False
        self.last_errors = {}
        self.recovery_attempts = {}

        # Component existence flags
        self.has_trading_engine = self.trading_engine is not None
        self.has_system_monitor = self.system_monitor is not None
        self.has_notification_manager = self.notification_manager is not None

        # Initialize healing strategies
        self.healing_strategies = self._configure_healing_strategies()

        logger.info("Self-Healing System initialized successfully")

    def _configure_healing_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        Configure comprehensive healing strategies for critical system components.

        Returns:
            Dict of configurable healing strategies with check and recovery methods
        """
        strategies = {
            "database_connection": {
                "check": self._check_database_connection,
                "heal": self._heal_database_connection,
                "severity": "critical",
                "attempts": 0,
                "max_attempts": 5,
                "backoff_factor": 2.0,
                "initial_delay": 5.0
            },
            "api_connections": {
                "check": self._check_api_connections,
                "heal": self._heal_api_connections,
                "severity": "critical",
                "attempts": 0,
                "max_attempts": 5,
                "backoff_factor": 2.0,
                "initial_delay": 5.0
            },
            "system_health": {
                "check": self._check_system_health,
                "heal": self._reduce_system_load,
                "severity": "warning",
                "attempts": 0,
                "max_attempts": 3,
                "backoff_factor": 2.0,
                "initial_delay": 5.0
            }
        }
        
        # Only add trading_engine strategy if the engine exists
        if self.has_trading_engine:
            strategies["trading_engine"] = {
                "check": self._check_trading_engine,
                "heal": self._heal_trading_engine,
                "severity": "critical",
                "attempts": 0,
                "max_attempts": 3,
                "backoff_factor": 2.0,
                "initial_delay": 10.0
            }
            
        return strategies

    def start(self) -> None:
        """
        Activate the self-healing monitoring process.
        """
        if self.running:
            self.logger.warning("Self-Healing System is already operational")
            return
            
        self.logger.info("Initiating Self-Healing System")
        self.running = True
        self.healing_thread = threading.Thread(target=self._healing_loop, name="self_healing_thread")
        self.healing_thread.daemon = True
        self.healing_thread.start()
        
        self.logger.info("Self-Healing System activated successfully")
    
    def stop(self) -> None:
        """
        Terminate the self-healing monitoring process.
        """
        if not self.running:
            self.logger.warning("Self-Healing System is already inactive")
            return
            
        self.logger.info("Stopping Self-Healing System")
        self.running = False
        
        if self.healing_thread:
            self.healing_thread.join(timeout=5)
            
        self.logger.info("Self-Healing System deactivated successfully")
    
    def _healing_loop(self) -> None:
        """
        Continuous monitoring and recovery loop.
        """
        while self.running:
            try:
                self._run_healing_cycle()
                time.sleep(self.healing_interval)
            except Exception as e:
                self.logger.error(f"Critical error in healing cycle: {str(e)}")
                time.sleep(30)  # Longer sleep on error to prevent rapid failure loops
    
    def _run_healing_cycle(self) -> None:
        """
        Execute a comprehensive system health check and recovery cycle.
        """
        for name, strategy in self.healing_strategies.items():
            try:
                # Skip checking components that don't exist or are optional
                if name == "trading_engine" and not self.has_trading_engine:
                    continue
                    
                # Perform health check
                is_healthy = strategy["check"]()
                
                if is_healthy:
                    # Reset recovery tracking on successful check
                    self._reset_strategy_tracking(strategy)
                else:
                    # Attempt recovery
                    self._attempt_component_recovery(name, strategy)
                    
            except Exception as e:
                self.logger.error(f"Error processing healing strategy for {name}: {str(e)}")

    def _attempt_component_recovery(self, name: str, strategy: Dict[str, Any]) -> None:
        """
        Attempt to recover a specific system component.
        """
        strategy["attempts"] += 1
        
        # Calculate recovery delay with exponential backoff
        delay = strategy["initial_delay"] * (strategy["backoff_factor"] ** (strategy["attempts"] - 1))
        time.sleep(delay)
        
        # Attempt healing
        if strategy["attempts"] <= strategy["max_attempts"]:
            healed = strategy["heal"]()
            
            if healed:
                self.logger.info(f"Successfully recovered {name}")
                strategy["attempts"] = max(0, strategy["attempts"] - 1)
            else:
                self._handle_recovery_failure(name, strategy)
        else:
            self._handle_persistent_failure(name, strategy)

    def _handle_recovery_failure(self, name: str, strategy: Dict[str, Any]) -> None:
        """
        Process individual component recovery failure.
        """
        self.logger.error(f"Failed to heal {name}")
        
        if strategy["severity"] == "critical" and strategy["attempts"] == strategy["max_attempts"]:
            self._send_critical_alert(name, strategy)

    def _handle_persistent_failure(self, name: str, strategy: Dict[str, Any]) -> None:
        """
        Manage components that fail recovery multiple times.
        """
        self.logger.critical(f"{name} has failed recovery attempts, manual intervention required")
        self._send_critical_alert(name, strategy, manual_intervention=True)

    def _send_critical_alert(
        self, 
        component_name: str, 
        strategy: Dict[str, Any], 
        manual_intervention: bool = False
    ) -> None:
        """
        Send critical alerts for system failures.
        """
        if self.notification_manager:
            message = (
                f"{component_name} has {'exceeded' if manual_intervention else 'failed'} "
                f"recovery attempts. {'Immediate manual intervention required.' if manual_intervention else ''}"
            )
            
            try:
                self.notification_manager.send_admin_alert(
                    subject=f"Critical System Failure: {component_name}",
                    message=message
                )
            except Exception as e:
                self.logger.error(f"Failed to send critical alert: {str(e)}")

    def _reset_strategy_tracking(self, strategy: Dict[str, Any]) -> None:
        """
        Reset recovery tracking for a successful component.
        """
        strategy["attempts"] = 0

    def _check_system_health(self) -> bool:
        """
        Check overall system health metrics.
        """
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                self.logger.warning(f"High CPU usage detected: {cpu_percent}%")
                return False
                
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.logger.warning(f"High memory usage detected: {memory.percent}%")
                return False
                
            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                self.logger.warning(f"High disk usage detected: {disk.percent}%")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error checking system health: {str(e)}")
            return False

    def _reduce_system_load(self) -> bool:
        """
        Reduce system load when resources are constrained.
        """
        try:
            # Reduce CPU load
            if hasattr(self.app, 'scheduler'):
                self.app.scheduler.pause_non_critical_tasks()
            
            # Clear caches
            if hasattr(self.app, 'cache_manager'):
                self.app.cache_manager.clear_all_caches()
            
            # Force garbage collection
            import gc
            collected = gc.collect()
            self.logger.info(f"Garbage collection: collected {collected} objects")
            
            # Clean up log files
            self._cleanup_log_files()
            
            return True
        except Exception as e:
            self.logger.error(f"Error reducing system load: {str(e)}")
            return False

    def _cleanup_log_files(self) -> None:
        """
        Clean up old log files to reduce disk usage.
        """
        try:
            log_dir = os.path.join(os.path.dirname(__file__), '../logs')
            files_deleted = 0
            
            if os.path.exists(log_dir):
                for file in os.listdir(log_dir):
                    if file.endswith('.log'):
                        file_path = os.path.join(log_dir, file)
                        file_age = time.time() - os.path.getmtime(file_path)
                        
                        # Delete logs older than 7 days
                        if file_age > (7 * 24 * 60 * 60):
                            os.remove(file_path)
                            files_deleted += 1
                            
            self.logger.info(f"Disk cleanup: deleted {files_deleted} old log files")
        except Exception as e:
            self.logger.error(f"Error cleaning up log files: {str(e)}")

    def _check_database_connection(self) -> bool:
        """
        Verify database connection health.
        """
        try:
            if not self.app or not hasattr(self.app, 'db'):
                return True
                
            # Test database connection
            conn = None
            try:
                conn = self.app.db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if not result or result[0] != 1:
                    raise Exception("Database query returned unexpected result")
                    
                cursor.close()
            except Exception as e:
                self.logger.error(f"Database connection test failed: {e}")
                return False
            finally:
                if conn:
                    self.app.db.release_connection(conn)
                    
            return True
        except Exception as e:
            self.logger.error(f"Error checking database connection: {e}")
            return False

    def _heal_database_connection(self) -> bool:
        """
        Attempt to recover database connection.
        """
        try:
            if not self.app or not hasattr(self.app, 'db'):
                return False
                
            # Close all existing connections
            self.app.db.close_all_connections()
            
            # Reinitialize database connection
            result = self.app.db.init_database()
            
            return result
        except Exception as e:
            self.logger.error(f"Error restoring database connection: {e}")
            return False

    def _check_api_connections(self) -> bool:
        """
        Verify API connection health.
        """
        try:
            # Check Binance API
            if hasattr(self.app, 'exchange_factory'):
                try:
                    # Create a public client (no authentication required)
                    exchange = self.app.exchange_factory.create_public_client('binance')
                    
                    # Test API with a simple ping or server time request
                    result = exchange.ping()
                    
                    if not result:
                        raise Exception("Binance API ping failed")
                        
                except Exception as e:
                    self.logger.error(f"Binance API connection test failed: {e}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error checking API connections: {e}")
            return False
        
        return True

    def _heal_api_connections(self) -> bool:
        """
        Attempt to recover API connections.
        """
        try:
            if hasattr(self.app, 'exchange_factory'):
                self.app.exchange_factory.reset_clients()
                
            return True
        except Exception as e:
            self.logger.error(f"Error restoring API connection: {e}")
            return False

    def _check_trading_engine(self) -> bool:
        """
        Verify trading engine operational status.
        """
        try:
            if not hasattr(self.app, 'trading_engine'):
                return False
                
            trading_engine = self.app.trading_engine
            
            # Check if engine is responsive
            last_activity = getattr(trading_engine, 'last_activity_time', None)
            
            if last_activity:
                now = datetime.now()
                elapsed = (now - last_activity).total_seconds()
                
                # If no activity for more than 10 minutes
                if elapsed > 600:
                    self.logger.warning(f"Trading engine appears unresponsive (last activity: {elapsed:.0f} seconds ago)")
                    return False
                    
            return True
        except Exception as e:
            self.logger.error(f"Error checking trading engine: {e}")
            return False

    def _heal_trading_engine(self) -> bool:
        """
        Restart the trading engine.
        """
        try:
            if not hasattr(self.app, 'trading_engine'):
                return False
                
            trading_engine = self.app.trading_engine
            
            # Stop the current engine
            if hasattr(trading_engine, 'stop'):
                trading_engine.stop()
                
            # Reinitialize trading engine
            from core.engine import TradingEngine
            self.app.trading_engine = TradingEngine(self.app.db)
            
            # Start the engine
            if hasattr(self.app.trading_engine, 'start'):
                self.app.trading_engine.start()
                
            return True
        except Exception as e:
            self.logger.error(f"Error restarting trading engine: {e}")
            return False

    def update_component(self, name: str, component: Any) -> bool:
        """
        Update a component reference that may have been reinitialized elsewhere.
        
        Args:
            name (str): Component name (e.g., 'trading_engine')
            component (Any): New component instance
            
        Returns:
            bool: Success status
        """
        try:
            # Update the component reference
            if name == 'trading_engine':
                self.trading_engine = component
                self.has_trading_engine = component is not None
                
                # Update healing strategies if necessary
                if component is not None and 'trading_engine' not in self.healing_strategies:
                    self.healing_strategies["trading_engine"] = {
                        "check": self._check_trading_engine,
                        "heal": self._heal_trading_engine,
                        "severity": "critical",
                        "attempts": 0,
                        "max_attempts": 3,
                        "backoff_factor": 2.0,
                        "initial_delay": 10.0
                    }
                elif component is None and 'trading_engine' in self.healing_strategies:
                    del self.healing_strategies['trading_engine']
                    
            elif name == 'system_monitor':
                self.system_monitor = component
                self.has_system_monitor = component is not None
                
            elif name == 'notification_manager':
                self.notification_manager = component
                self.has_notification_manager = component is not None
                
            else:
                self.logger.warning(f"Unknown component type: {name}")
                return False
                
            self.logger.info(f"Component {name} reference updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating component {name}: {str(e)}")
            return False

    def get_system_diagnostics(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive system diagnostics.
        
        Returns:
            Dict containing system health metrics and recovery statistics
        """
        diagnostics = {
            "system_health": {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            },
            "recovery_stats": {},
            "component_status": {
                "trading_engine": self.has_trading_engine,
                "system_monitor": self.has_system_monitor,
                "notification_manager": self.has_notification_manager
            }
        }
        
        # Add recovery history for each strategy
        for name, strategy in self.healing_strategies.items():
            diagnostics["recovery_stats"][name] = {
                "attempts": strategy.get("attempts", 0),
                "max_attempts": strategy.get("max_attempts", 0),
                "severity": strategy.get("severity", "unknown")
            }
        
        return diagnostics

    def manual_component_recovery(self, name: str) -> bool:
        """
        Manually trigger recovery for a specific component.
        
        Args:
            name (str): Name of the component to recover
            
        Returns:
            bool: Success status of manual recovery attempt
        """
        try:
            if name not in self.healing_strategies:
                self.logger.warning(f"No recovery strategy found for component: {name}")
                return False
            
            strategy = self.healing_strategies[name]
            
            # Force reset of attempts to allow immediate recovery
            strategy["attempts"] = 0
            
            # Attempt recovery
            self.logger.info(f"Manually initiating recovery for {name}")
            recovery_result = strategy["heal"]()
            
            if recovery_result:
                self.logger.info(f"Manual recovery of {name} successful")
            else:
                self.logger.error(f"Manual recovery of {name} failed")
            
            return recovery_result
        
        except Exception as e:
            self.logger.error(f"Error during manual component recovery for {name}: {str(e)}")
            return False

# Maintain backward compatibility
SelfHealing = SelfHealingSystem