import logging
import signal
import sys
import time
from threading import Event, Thread
from typing import Optional, Dict, Any, List, Tuple, Callable
import datetime

from config.app_config import AppConfig
from core.engine import TradingEngine
from core.scheduler import Scheduler
from database.db import DatabaseManager
from database.repository.user_repository import UserRepository
from exchange.exchange_factory import ExchangeFactory
from notification.notification_manager import NotificationManager
from security.api_key_manager import APIKeyManager
from maintenance.self_healing import SelfHealingSystem
from maintenance.system_monitor import SystemMonitor
from risk_management.risk_manager import RiskManager
from strategies.strategy_manager import StrategyManager

logger = logging.getLogger(__name__)

class QuantumFlow:
    """
    Main application class for QuantumFlow Trading Bot
    """
    def __init__(self, config: AppConfig):
        """
        Initialize the QuantumFlow application with configuration.
        All components are initialized in the correct dependency order.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.app_name = "QuantumFlow Trading Bot"
        
        # Component containers - all initialized to None initially
        self.db_manager = None
        self.user_repository = None
        self.api_key_manager = None
        self.exchange_factory = None
        self.risk_manager = None
        self.strategy_manager = None
        self.notification_manager = None
        self.trading_engine = None
        self.scheduler = None
        self.system_monitor = None
        self.self_healing = None
        
        # Optional bot components (placeholder for future implementation)
        self.admin_bot = None
        self.telegram_bot = None
        
        # Initialize shutdown event
        self.shutdown_event = Event()
        self.start_time = None
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        # Initialize all components in proper order
        try:
            self._init_components()
            self.logger.info("QuantumFlow application initialized successfully")
        except Exception as e:
            self.logger.critical(f"Failed to initialize QuantumFlow: {str(e)}")
            sys.exit(1)
        
    def _init_components(self):
        """
        Initialize components in the correct order with dependency checks
        """
        components_to_init: List[Tuple[str, Callable[[], bool]]] = [
            ("database", self._init_database),
            ("repositories", self._init_repositories),
            ("security", self._init_security),
            ("exchanges", self._init_exchanges),
            ("risk_management", self._init_risk_management),
            ("strategies", self._init_strategies),
            ("notification", self._init_notification),
            ("trading_engine", self._init_trading_engine),
            ("scheduler", self._init_scheduler),
            ("monitoring", self._init_monitoring)
        ]
        
        for name, init_func in components_to_init:
            try:
                self.logger.info(f"Initializing {name} components...")
                if not init_func():
                    self.logger.error(f"Failed to initialize {name} components")
                    raise RuntimeError(f"Failed to initialize {name} components")
            except Exception as e:
                self.logger.error(f"Error initializing {name} components: {str(e)}")
                raise RuntimeError(f"Error initializing {name} components: {str(e)}")
    
    def _init_database(self) -> bool:
        """Initialize database connection and manager"""
        try:
            self.db_manager = DatabaseManager(
                connection_string=self.config.database.connection_string,
                pool_size=self.config.database.pool_size,
                max_overflow=self.config.database.max_overflow,
                timeout=self.config.database.timeout
            )
            self.db_manager.initialize()
            return True
        except Exception as e:
            self.logger.error(f"Database initialization error: {str(e)}")
            return False
    
    def _init_repositories(self) -> bool:
        """Initialize all data repositories"""
        if not self.db_manager:
            self.logger.error("Cannot initialize repositories: Database manager not initialized")
            return False
        
        try:
            self.user_repository = UserRepository(self.db_manager)
            # Add other repositories here as needed
            return True
        except Exception as e:
            self.logger.error(f"Repository initialization error: {str(e)}")
            return False
    
    def _init_security(self) -> bool:
        """Initialize security components"""
        try:
            self.api_key_manager = APIKeyManager(
                key_storage_path=self.config.security.key_storage_path,
                encryption_key=self.config.security.encryption_key
            )
            return True
        except Exception as e:
            self.logger.error(f"Security initialization error: {str(e)}")
            return False
    
    def _init_exchanges(self) -> bool:
        """Initialize exchange connections"""
        if not self.api_key_manager:
            self.logger.error("Cannot initialize exchanges: API key manager not initialized")
            return False
        
        try:
            self.exchange_factory = ExchangeFactory(
                api_key_manager=self.api_key_manager,
                config=self.config.exchanges
            )
            return True
        except Exception as e:
            self.logger.error(f"Exchange initialization error: {str(e)}")
            return False
    
    def _init_risk_management(self) -> bool:
        """Initialize risk management components"""
        try:
            self.risk_manager = RiskManager(
                config=self.config.risk_management,
                user_repository=self.user_repository
            )
            return True
        except Exception as e:
            self.logger.error(f"Risk management initialization error: {str(e)}")
            return False
    
    def _init_strategies(self) -> bool:
        """Initialize trading strategies"""
        if not self.exchange_factory or not self.risk_manager:
            self.logger.error("Cannot initialize strategies: Dependencies not initialized")
            return False
        
        try:
            self.strategy_manager = StrategyManager(
                config=self.config.strategies,
                exchange_factory=self.exchange_factory,
                risk_manager=self.risk_manager
            )
            return True
        except Exception as e:
            self.logger.error(f"Strategy initialization error: {str(e)}")
            return False
    
    def _init_notification(self) -> bool:
        """Initialize notification systems"""
        try:
            self.notification_manager = NotificationManager(
                config=self.config.notifications,
                user_repository=self.user_repository
            )
            return True
        except Exception as e:
            self.logger.error(f"Notification initialization error: {str(e)}")
            return False
    
    def _init_trading_engine(self) -> bool:
        """Initialize the core trading engine"""
        if not self.strategy_manager or not self.exchange_factory or not self.risk_manager:
            self.logger.error("Cannot initialize trading engine: Dependencies not initialized")
            return False
        
        try:
            self.trading_engine = TradingEngine(
                strategy_manager=self.strategy_manager,
                exchange_factory=self.exchange_factory,
                risk_manager=self.risk_manager,
                notification_manager=self.notification_manager,
                config=self.config.trading
            )
            return True
        except Exception as e:
            self.logger.error(f"Trading engine initialization error: {str(e)}")
            return False
    
    def _init_scheduler(self) -> bool:
        """Initialize the task scheduler"""
        try:
            self.scheduler = Scheduler(
                config=self.config.scheduler,
                shutdown_event=self.shutdown_event
            )
            # Add standard scheduled tasks
            self._add_scheduled_tasks()
            return True
        except Exception as e:
            self.logger.error(f"Scheduler initialization error: {str(e)}")
            return False
    
    def _init_monitoring(self) -> bool:
        """Initialize monitoring and self-healing systems"""
        try:
            self.system_monitor = SystemMonitor(
                components={
                    "database": self.db_manager,
                    "trading_engine": self.trading_engine,
                    "notification": self.notification_manager
                },
                config=self.config.monitoring
            )
            
            self.self_healing = SelfHealingSystem(
                system_monitor=self.system_monitor,
                notification_manager=self.notification_manager,
                config=self.config.self_healing
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Monitoring initialization error: {str(e)}")
            return False
    
    def _add_scheduled_tasks(self):
        """Add standard scheduled tasks to the scheduler"""
        if not self.scheduler:
            return
        
        # Add system health check task
        self.scheduler.add_task(
            name="system_health_check",
            func=self.system_monitor.run_health_check,
            interval_seconds=self.config.monitoring.health_check_interval,
            run_immediately=True
        )
        
        # Add database maintenance task
        self.scheduler.add_task(
            name="database_maintenance",
            func=self.db_manager.run_maintenance,
            interval_seconds=self.config.database.maintenance_interval,
            run_immediately=False
        )
        
        # Add any other scheduled tasks here
    
    def start(self):
        """
        Start the QuantumFlow trading bot
        """
        try:
            self.logger.info(f"Starting {self.app_name}")
            
            # Ensure components are initialized
            if not self._init_components():
                raise RuntimeError("Failed to initialize components")
            
            # Set start time
            self.start_time = datetime.datetime.now()
            
            # Start self-healing system
            self.self_healing = SelfHealingSystem(
                system_monitor=self.system_monitor,
                notification_manager=self.notification_manager,
                config=self.config.self_healing
            )
            self.self_healing.start_monitoring()
            
            # Start scheduler
            if hasattr(self, 'scheduler'):
                self.scheduler.start()
            
            # Start trading engine
            if hasattr(self, 'trading_engine'):
                self.trading_engine.start()
            
            # Start admin bot (placeholder, implement when admin bot is developed)
            if hasattr(self, 'admin_bot'):
                admin_thread = Thread(target=self.admin_bot.start)
                admin_thread.daemon = True
                admin_thread.start()
            
            # Start telegram bot (placeholder, implement when telegram bot is developed)
            if hasattr(self, 'telegram_bot'):
                telegram_thread = Thread(target=self.telegram_bot.start)
                telegram_thread.daemon = True
                telegram_thread.start()
            
            # Notify startup
            self.notify_startup()
            
            self.logger.info(f"{self.app_name} started successfully")
            
            # Keep main thread alive until shutdown
            while not self.shutdown_event.is_set():
                time.sleep(1)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            self.handle_shutdown(None, None)
            return False
        
        except KeyboardInterrupt:
            self.handle_shutdown(None, None)
            return False
    
    def handle_shutdown(self, sig, frame):
        """
        Handle graceful shutdown of the application
        """
        if self.shutdown_event.is_set():
            self.logger.warning("Forced shutdown initiated")
            sys.exit(1)
            
        self.logger.info("Graceful shutdown initiated")
        self.shutdown_event.set()
        
        # Stop all components in reverse order
        components_to_stop = [
            (self.scheduler, "Scheduler"),
            (self.trading_engine, "Trading Engine"),
            (self.notification_manager, "Notification Manager"),
            (self.self_healing, "Self Healing System"),
            (self.system_monitor, "System Monitor")
        ]
        
        for component, name in components_to_stop:
            if component:
                try:
                    self.logger.info(f"Stopping {name}...")
                    component.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping {name}: {str(e)}")
        
        self.logger.info("QuantumFlow Trading Bot shutdown complete")
    
    def get_uptime(self) -> int:
        """
        Get the application uptime in seconds
        
        Returns:
            int: Uptime in seconds, or 0 if not started
        """
        if not self.start_time:
            return 0
            
        delta = datetime.datetime.now() - self.start_time
        return int(delta.total_seconds())
        
    def notify_startup(self):
        """
        Send startup notification to administrators
        """
        try:
            if not self.user_repository or not self.notification_manager:
                self.logger.error("Cannot send startup notification: Dependencies not initialized")
                return
                
            admin_users = self.user_repository.get_admin_users()
            
            startup_message = (
                f"QuantumFlow Trading Bot started successfully at "
                f"{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            for admin in admin_users:
                self.notification_manager.send_notification(
                    user_id=admin.id,
                    message=startup_message,
                    notification_type="system_status"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to send startup notification: {str(e)}")