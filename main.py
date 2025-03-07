"""
QuantumFlow Trading Bot - Main Application

This is the central integration point for the QuantumFlow trading bot system,
coordinating all components and providing the primary entry point for the application.
"""

import logging
import time
import signal
import threading
import traceback
from typing import Dict, List, Any, Optional

# Core components
from core.app import QuantumFlow as Application
from core.engine import TradingEngine
from core.scheduler import Scheduler as TaskScheduler

# Configuration
from config.app_config import AppConfig
from config.logging_config import configure_logging
from config.trading_config import TradingConfig

# Database
from database.db import DatabaseManager
from database.repository.user_repository import UserRepository
from database.repository.trade_repository import TradeRepository
from database.repository.position_repository import PositionRepository
from database.repository.analytics_repository import AnalyticsRepository
from database.repository.api_key_repository import ApiKeyRepository
from database.models.api_key import ApiKey

# Exchange
from exchange.exchange_factory import ExchangeFactory
from exchange.exchange_helper import ExchangeHelper

# Strategies
from strategies.strategy_factory import StrategyFactory

# Risk management
from risk.risk_manager import RiskManager
from risk.position_sizer import PositionSizer
from risk.drawdown_protector import DrawdownProtector

# Analysis
from analysis.market_analyzer import MarketAnalyzer
from analysis.technical_indicators import TechnicalIndicators
from analysis.sentiment_analyzer import SentimentAnalyzer

# Machine Learning
from ml.data_processor import DataProcessor
from ml.model_trainer import ModelTrainer
from ml.models.price_predictor import PricePredictor
from ml.models.pattern_recognition import PatternRecognition
from ml.models.regime_classifier import RegimeClassifier

# Notification
from notification.telegram_bot import TelegramBot
from notification.email_notifier import EmailNotifier
from notification.notification_manager import NotificationManager

# Admin
from admin.admin_bot import AdminBot
from admin.dashboard_api import DashboardAPI
from admin.monitoring import SystemMonitoring

# Security
from security.encryption import EncryptionService
from security.api_key_manager import APIKeyManager
from security.auth import AuthenticationService

# Compliance
from compliance.kyc import KYCProcessor
from compliance.aml import AMLChecker
from compliance.reporting import ComplianceReporter

# Profit
from profit.fee_calculator import FeeCalculator
from profit.profit_tracker import ProfitTracker

# Maintenance
from maintenance.self_healing import SelfHealingSystem
from maintenance.system_monitor import SystemMonitor

# New Services
from services.user_trading_manager import UserTradingManager
from services.pairs_manager import PairsManager
from services.strategy_manager import StrategyManager
from market_data.price_service import PriceService
from market_data.market_analysis import MarketAnalysis
from profit.stats_service import StatsService
from reporting.report_generator import ReportGenerator

# Utils
from utils.helpers import generate_unique_id
from utils.validators import validate_config
from utils.decorators import log_execution, retry


class QuantumFlowBot:
    """
    Main QuantumFlow Trading Bot class that integrates all system components
    and manages their lifecycle.
    """
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize the QuantumFlow Trading Bot with all its components.
        
        Args:
            config_path: Path to the configuration file
        """
        # Configure logging first
        configure_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing QuantumFlow Trading Bot...")
        
        # Load configuration
        self.app_config = AppConfig(config_path)
        self.trading_config = TradingConfig(config_path)
        
        # Validate configuration
        validation_result = validate_config(self.app_config.get_all())
        if isinstance(validation_result, tuple):
            is_valid, error_message = validation_result
            if not is_valid:
                raise ValueError(f"Invalid configuration detected: {error_message}")
        elif not validation_result:
            raise ValueError("Invalid configuration detected")
        
        # System state
        self.running = False
        self.initialized = False
        self.threads = []
        self.components = {}
        self.system_status = "initializing"
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self.handle_shutdown_signal)
        
        # Initialize but don't start components yet
        self._init_components()
    
    @log_execution
    def _init_components(self):
        """Initialize all system components without starting them."""
        try:
            self.logger.info("Initializing system components...")
            
            # Initialize core database
            try:
                db_url = f"postgresql://{self.app_config.get('database.username')}:{self.app_config.get('database.password')}@{self.app_config.get('database.host')}:{self.app_config.get('database.port')}/{self.app_config.get('database.name')}"
                self.db_manager = DatabaseManager(db_url)
                # Make sure database is properly initialized and schema is validated
                if not self.db_manager.initialize():
                    raise RuntimeError("Database initialization failed")
                
                # Verify the schema immediately after initialization
                # This will add missing columns and avoid errors later
                self._verify_database_schema()
                
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {str(e)}")
                raise RuntimeError("Database initialization failed") from e
            
            # Initialize repositories - use enhanced versions with schema adaptation
            self.user_repo = UserRepository(self.db_manager)
            self.trade_repo = TradeRepository(self.db_manager)
            self.position_repo = PositionRepository(self.db_manager)
            self.analytics_repo = AnalyticsRepository(self.db_manager)
            
            # Initialize security services
            jwt_secret = self.app_config.get("security.jwt_secret")
            if not jwt_secret:
                raise ValueError("JWT secret is required but not found in configuration")
                
            self.encryption_service = EncryptionService(
                key=self.app_config.get("security.encryption_key")
            )
            self.auth_service = AuthenticationService(
                db=self.db_manager,
                jwt_secret=self.app_config.get("security.jwt_secret")
            )
            self.api_key_manager = APIKeyManager(
                db=self.db_manager,
            )
            
            # Initialize API key repository
            self.api_key_repository = ApiKeyRepository(
                db_manager=self.db_manager,
                encryption_service=self.encryption_service
            )
            
            # Initialize exchange components
            self.exchange_factory = ExchangeFactory()
            # Get a default exchange instance for analysis
            default_exchange = self.exchange_factory.create_exchange(
                exchange_name=self.app_config.get("exchange.default", "binance"),
                api_key=self.app_config.get("exchange.api_key", ""),
                api_secret=self.app_config.get("exchange.api_secret", "")
            )
            
            # Initialize notification components first (since other components depend on them)
            self.email_notifier = EmailNotifier(
                enabled=self.app_config.get("notification.email.enabled", False),
                smtp_server=self.app_config.get("notification.email.smtp_server", ""),
                smtp_port=self.app_config.get("notification.email.smtp_port", 587),
                smtp_username=self.app_config.get("notification.email.smtp_username", ""),
                smtp_password=self.app_config.get("notification.email.smtp_password", ""),
                from_email=self.app_config.get("notification.email.from_email", "")
            )
            self.notification_manager = NotificationManager(
                config=self.app_config.get("notification.general")
            )
            
            # Initialize risk management components
            self.position_sizer = PositionSizer(config=self.app_config)
            self.drawdown_protector = DrawdownProtector(
                config=self.app_config,
                db=self.db_manager,
                notification_manager=self.notification_manager
            )
            self.risk_manager = RiskManager(
                config=self.app_config,
                db=self.db_manager
            )
            
            # Initialize strategy factory with required parameters
            self.strategy_factory = StrategyFactory(
                config=self.app_config,  # Pass AppConfig instance
                risk_manager=self.risk_manager  # Pass RiskManager instance
            )
            
            # Initialize analysis tools
            self.technical_indicators = TechnicalIndicators()
            self.sentiment_analyzer = SentimentAnalyzer()
            # Market analyzer requires an exchange instance
            self.market_analyzer = MarketAnalyzer(
                exchange=default_exchange
            )
            
            # Initialize ML components
            # DataProcessor initialization
            data_processing_config = self.app_config.get("ml.data_processing", {})
            cache_dir = data_processing_config.get("cache_dir", "cache") if isinstance(data_processing_config, dict) else "cache"
            self.data_processor = DataProcessor(
                cache_dir=cache_dir
            )
            
            # PricePredictor initialization
            price_predictor_config = self.app_config.get("ml.models.price_predictor", {})
            price_model_dir = price_predictor_config.get("model_dir", "models") if isinstance(price_predictor_config, dict) else "models"
            self.price_predictor = PricePredictor(
                model_dir=price_model_dir
            )
            
            # PatternRecognition initialization
            pattern_recognition_config = self.app_config.get("ml.models.pattern_recognition", {})
            pattern_model_dir = pattern_recognition_config.get("model_dir", "models") if isinstance(pattern_recognition_config, dict) else "models"
            self.pattern_recognition = PatternRecognition(
                model_dir=pattern_model_dir
            )
            
            # RegimeClassifier initialization
            regime_classifier_config = self.app_config.get("ml.models.regime_classifier", {})
            regime_model_dir = regime_classifier_config.get("model_dir", "models") if isinstance(regime_classifier_config, dict) else "models"
            self.regime_classifier = RegimeClassifier(
                model_dir=regime_model_dir
            )
            # Initialize ML model trainer
            training_config = self.app_config.get("ml.training", {})
            model_dir = training_config.get("model_dir", "models") if isinstance(training_config, dict) else "models"
            data_dir = training_config.get("data_dir", "data") if isinstance(training_config, dict) else "data"
            
            self.model_trainer = ModelTrainer(
                model_dir=model_dir,
                data_dir=data_dir
            )
            
            # NEW SERVICES INITIALIZATION
            self.user_trading_manager = UserTradingManager(
                db=self.db_manager
            )

            self.pairs_manager = PairsManager(
                db=self.db_manager
            )

            self.strategy_manager = StrategyManager(
                db=self.db_manager
            )

            self.price_service = PriceService(
                db=self.db_manager
            )

            self.market_analysis = MarketAnalysis(
                db=self.db_manager
            )

            self.stats_service = StatsService(
                db=self.db_manager
            )

            self.report_generator = ReportGenerator(
                db=self.db_manager
            )
            
            # Initialize telegram bot 
            telegram_token = self.app_config.get("notification.telegram.token", "")
            admin_chat_ids = self.app_config.get("admin.admin_user_ids", [])
            
            self.telegram_bot = TelegramBot(
                token=telegram_token,
                admin_chat_ids=admin_chat_ids,
                api_key_repository=self.api_key_repository,
                db=self.db_manager,
                user_trading_manager=self.user_trading_manager,
                pairs_manager=self.pairs_manager,
                strategy_manager=self.strategy_manager,
                price_service=self.price_service,
                market_analysis=self.market_analysis,
                stats_service=self.stats_service,
                report_generator=self.report_generator
            )

            # Initialize Exchange Helper
            self.exchange_helper = ExchangeHelper(
                exchange_factory=self.exchange_factory,
                api_key_repository=self.api_key_repository,
                user_repository=self.user_repo
            )
            
            # Initialize admin components
            self.system_monitoring = SystemMonitoring(
                notification_manager=self.notification_manager
            )
            self.admin_bot = AdminBot(
                token=self.app_config.get("admin.telegram.token"),
                admin_ids=self.app_config.get("admin.admin_user_ids"),
                user_repository=self.user_repo,
                trade_repository=self.trade_repo,
                system_monitoring=self.system_monitoring
            )
            self.dashboard_api = DashboardAPI(
                auth_service=self.auth_service,
                user_repository=self.user_repo,
                trade_repository=self.trade_repo,
                analytics_repository=self.analytics_repo,
                system_monitoring=self.system_monitoring,
                host=self.app_config.get("admin.dashboard.host"),
                port=self.app_config.get("admin.dashboard.port")
            )
            
            # Initialize compliance components
            self.kyc_processor = KYCProcessor(
                user_repository=self.user_repo,
                notification_manager=self.notification_manager,
                config=self.app_config.get("compliance.kyc")
            )
            self.aml_checker = AMLChecker(
                user_repository=self.user_repo,
                trade_repository=self.trade_repo,
                notification_manager=self.notification_manager,
                config=self.app_config.get("compliance.aml")
            )
            self.compliance_reporter = ComplianceReporter(
                user_repository=self.user_repo,
                trade_repository=self.trade_repo,
                config=self.app_config.get("compliance.reporting")
            )
            
            # Initialize profit tracking
            self.fee_calculator = FeeCalculator(
                config=self.app_config.get("profit.fees")
            )
            self.profit_tracker = ProfitTracker(
                fee_calculator=self.fee_calculator,
                trade_repository=self.trade_repo,
                user_repository=self.user_repo,
                config=self.app_config.get("profit.tracking")
            )
            
            # Initialize system monitor first (needed for self-healing)
            self.system_monitor = SystemMonitor(
                notification_manager=self.notification_manager
            )
            
            # Initialize scheduler (needed for many components)
            self.scheduler = TaskScheduler()
            
            # Initialize trading engine (depends on many components)
            self.trading_engine = TradingEngine(
                config=self.app_config,
                trading_config=self.trading_config,
                db=self.db_manager,
                exchange_factory=self.exchange_factory,
                strategy_factory=self.strategy_factory,
                api_key_manager=self.api_key_manager,
                risk_manager=self.risk_manager,
                notification_manager=self.notification_manager,
                market_analyzer=self.market_analyzer,
                price_predictor=self.price_predictor,
                pattern_recognition=self.pattern_recognition,
                regime_classifier=self.regime_classifier,
                position_repository=self.position_repo,
                trade_repository=self.trade_repo,
                user_repository=self.user_repo,
                profit_tracker=self.profit_tracker,
                user_trading_manager=self.user_trading_manager,
                pairs_manager=self.pairs_manager,
                strategy_manager=self.strategy_manager,
                price_service=self.price_service,
                market_analysis=self.market_analysis
            )
            
            # Initialize self-healing AFTER trading engine
            # This ensures it has a valid reference
            self.self_healing = SelfHealingSystem(
                config=self.app_config,
                trading_engine=self.trading_engine,
                system_monitor=self.system_monitor,
                notification_manager=self.notification_manager
            )
            
            # Initialize core application (coordinates all components)
            self.app = Application(
                trading_engine=self.trading_engine,
                notification_manager=self.notification_manager,
                scheduler=self.scheduler,
                user_repository=self.user_repo,
                config=self.app_config
            )
            
            # Track components for status reporting and management
            self.components = {
                "database": self.db_manager,
                "trading_engine": self.trading_engine,
                "telegram_bot": self.telegram_bot,
                "admin_bot": self.admin_bot,
                "dashboard_api": self.dashboard_api,
                "notification_manager": self.notification_manager,
                "system_monitor": self.system_monitor,
                "self_healing": self.self_healing,
                "scheduler": self.scheduler,
                "app": self.app,
                "user_trading_manager": self.user_trading_manager,
                "pairs_manager": self.pairs_manager,
                "strategy_manager": self.strategy_manager,
                "price_service": self.price_service,
                "market_analysis": self.market_analysis,
                "stats_service": self.stats_service,
                "report_generator": self.report_generator
            }
            
            self.initialized = True
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize components: {str(e)}", exc_info=True)
            self.system_status = "initialization_error"
            raise

    def _verify_database_schema(self):
        """Verify and fix database schema issues."""
        try:
            self.logger.info("Verifying database schema...")
            
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check user_trading_settings table existence
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_trading_settings'
                );
            """)

            if not cursor.fetchone()[0]:
                self.logger.warning("user_trading_settings table doesn't exist, creating it now")
                cursor.execute("""
                    CREATE TABLE user_trading_settings (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) UNIQUE,
                        trading_mode VARCHAR(10) NOT NULL DEFAULT 'paper', 
                        risk_level VARCHAR(10) NOT NULL DEFAULT 'medium',
                        is_paused BOOLEAN DEFAULT false,
                        max_open_positions INTEGER DEFAULT 5,
                        max_position_size DECIMAL(10,5) DEFAULT 0.1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

            # Check fee_transactions table existence
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'fee_transactions'
                );
            """)

            if not cursor.fetchone()[0]:
                self.logger.warning("fee_transactions table doesn't exist, creating it now")
                cursor.execute("""
                    CREATE TABLE fee_transactions (
                        id SERIAL PRIMARY KEY,
                        trade_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        referrer_id INTEGER,
                        profit_amount DECIMAL(20,10) NOT NULL,
                        fee_amount DECIMAL(20,10) NOT NULL,
                        fee_rate DECIMAL(10,5) NOT NULL,
                        referral_amount DECIMAL(20,10) NOT NULL DEFAULT 0,
                        admin_amount DECIMAL(20,10) NOT NULL,
                        admin_wallet VARCHAR(255),
                        transaction_status VARCHAR(20) DEFAULT 'pending',
                        transaction_hash VARCHAR(255),
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

            # Check user_trading_pairs table existence
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_trading_pairs'
                );
            """)

            if not cursor.fetchone()[0]:
                self.logger.warning("user_trading_pairs table doesn't exist, creating it now")
                cursor.execute("""
                    CREATE TABLE user_trading_pairs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        trading_pair VARCHAR(20) NOT NULL,
                        is_enabled BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT unique_user_pair UNIQUE (user_id, trading_pair)
                    );
                """)

            # Check user_strategies table existence
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_strategies'
                );
            """)

            if not cursor.fetchone()[0]:
                self.logger.warning("user_strategies table doesn't exist, creating it now")
                cursor.execute("""
                    CREATE TABLE user_strategies (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        strategy_name VARCHAR(50) NOT NULL,
                        allocation_percent DECIMAL(5,2) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT unique_user_strategy UNIQUE (user_id, strategy_name)
                    );
                """)

            conn.commit()
            self.logger.info("Database schema verification completed")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database schema verification failed: {str(e)}")
        finally:
            cursor.close()
            self.db_manager.release_connection(conn)

    def _register_scheduled_tasks(self):
        """Register all scheduled tasks with the scheduler."""
        self.logger.info("Registering scheduled tasks...")
        
        # Register model training tasks
        self.scheduler.schedule(
            func=self.model_trainer.train_price_predictor,
            interval_seconds=86400,  # Daily
            task_id="train_price_predictor"
        )
        
        self.scheduler.schedule(
            func=self.model_trainer.train_pattern_recognition,
            interval_seconds=86400 * 3,  # Every 3 days
            task_id="train_pattern_recognition"
        )
        
        self.scheduler.schedule(
            func=self.model_trainer.train_regime_classifier,
            interval_seconds=86400 * 7,  # Weekly
            task_id="train_regime_classifier"
        )
        
        # Register risk management tasks
        self.scheduler.schedule(
            func=self.risk_manager.update_user_risk_metrics,
            interval_seconds=3600,  # Hourly
            task_id="update_risk_metrics"
        )
        
        self.scheduler.schedule(
            func=self.drawdown_protector.check_drawdowns,
            interval_seconds=600,  # Every 10 minutes
            task_id="check_drawdowns"
        )
        
        # Register market analysis tasks
        self.scheduler.schedule(
            func=self.market_analyzer.update_analysis,
            interval_seconds=1800,  # Every 30 minutes
            task_id="update_market_analysis"
        )
        
        # Register maintenance tasks
        self.scheduler.schedule(
            func=self.system_monitor.check_system_health,
            interval_seconds=300,  # Every 5 minutes
            task_id="check_system_health"
        )
        
        self.scheduler.schedule(
            func=self.self_healing.check_and_heal,
            interval_seconds=3600,  # Hourly
            task_id="self_healing"
        )
        
        # Register compliance tasks
        self.scheduler.schedule(
            func=self.aml_checker.run_scheduled_checks,
            interval_seconds=86400,  # Daily
            task_id="aml_checks"
        )
        
        self.scheduler.schedule(
            func=self.compliance_reporter.generate_daily_report,
            interval_seconds=86400,  # Daily
            task_id="compliance_report",
            run_at_time="23:00:00"  # Run at 11 PM
        )
        
        # New scheduled tasks for new services
        self.scheduler.schedule(
            func=self.user_trading_manager.check_paused_accounts,
            interval_seconds=3600,  # Hourly
            task_id="check_paused_accounts"
        )

        self.scheduler.schedule(
            func=self.market_analysis.update_market_analysis,
            interval_seconds=1800,  # 30 minutes
            task_id="update_market_analysis"
        )

        self.scheduler.schedule(
            func=self.stats_service.generate_daily_statistics,
            interval_seconds=86400,  # Daily
            task_id="generate_daily_statistics",
            run_at_time="00:15:00"  # Run at 15 minutes past midnight
        )
        
        self.logger.info("Successfully registered all scheduled tasks")

    def _start_components(self):
        """Start all system components."""
        try:
            if not self.initialized:
                raise RuntimeError("Cannot start components before initialization")
            
            self.logger.info("Starting system components...")
            
            # Start core components first
            self.system_monitor.start()
            self.scheduler.start()
            
            # Start notification components
            if hasattr(self.notification_manager, 'start'):
                self.notification_manager.start()
            
            # Start telegram bot in a separate thread
            telegram_thread = threading.Thread(
                target=self.telegram_bot.start_polling,
                name="TelegramBot"
            )
            telegram_thread.daemon = True
            telegram_thread.start()
            self.threads.append(telegram_thread)
            
            # Start admin components
            admin_bot_thread = threading.Thread(
                target=self.admin_bot.start_polling,
                name="AdminBot"
            )
            admin_bot_thread.daemon = True
            admin_bot_thread.start()
            self.threads.append(admin_bot_thread)
            
            dashboard_thread = threading.Thread(
                target=self.dashboard_api.start,
                name="DashboardAPI"
            )
            dashboard_thread.daemon = True
            dashboard_thread.start()
            self.threads.append(dashboard_thread)
            
            # Start trading engine
            trading_thread = threading.Thread(
                target=self.trading_engine.start,
                name="TradingEngine"
            )
            trading_thread.daemon = True
            trading_thread.start()
            self.threads.append(trading_thread)
            
            # Register all scheduled tasks
            self._register_scheduled_tasks()
            
            # Finally, start the application coordinator
            app_thread = threading.Thread(
                target=self.app.run,
                name="ApplicationCoordinator"
            )
            app_thread.daemon = True
            app_thread.start()
            self.threads.append(app_thread)
            
            self.running = True
            self.system_status = "running"
            self.logger.info("All components started successfully")
            
        except Exception as e:
            self.logger.critical(f"Failed to start components: {str(e)}", exc_info=True)
            self.system_status = "startup_error"
            # Try to perform emergency shutdown
            self._emergency_shutdown()
            raise

    @retry(max_attempts=3, delay_seconds=2)
    def _stop_components(self):
        """Stop all system components gracefully."""
        if not self.running:
            self.logger.info("Components are not running, nothing to stop")
            return
        
        self.logger.info("Stopping system components...")
        self.system_status = "shutting_down"
        
        # Stop in reverse order of startup
        try:
            # First stop the application coordinator
            if hasattr(self.app, 'stop'):
                self.app.stop()
            
            # Stop trading engine
            if hasattr(self.trading_engine, 'stop'):
                self.trading_engine.stop()
            
            # Stop admin components
            if hasattr(self.dashboard_api, 'stop'):
                self.dashboard_api.stop()
            
            if hasattr(self.admin_bot, 'stop'):
                self.admin_bot.stop()
            
            # Stop telegram bot
            if hasattr(self.telegram_bot, 'stop'):
                self.telegram_bot.stop()
            
            # Stop notification components
            if hasattr(self.notification_manager, 'stop'):
                self.notification_manager.stop()
            
            # Stop scheduler last to allow scheduled stop tasks to complete
            if hasattr(self.scheduler, 'stop'):
                self.scheduler.stop()
            
            # Stop system monitor last
            if hasattr(self.system_monitor, 'stop'):
                self.system_monitor.stop()
            
            # Wait for all threads to finish
            for thread in self.threads:
                if thread.is_alive():
                    thread.join(timeout=5.0)  # 5 second timeout
            
            self.running = False
            self.system_status = "stopped"
            self.logger.info("All components stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during component shutdown: {str(e)}")
            self.system_status = "shutdown_error"
            raise

    def _emergency_shutdown(self):
        """Perform emergency shutdown when critical errors occur."""
        self.logger.critical("Performing emergency shutdown")
        
        # First, set the system status
        self.system_status = "emergency_shutdown"
        
        # Force stop critical components in a specific order
        try:
            # Stop trading engine first (to prevent new trades)
            if hasattr(self.trading_engine, 'emergency_stop'):
                self.trading_engine.emergency_stop()
            elif hasattr(self.trading_engine, 'stop'):
                self.trading_engine.stop()
            
            # Stop other components that might be processing trades
            components_to_stop = [
                self.app,
                self.dashboard_api,
                self.admin_bot,
                self.telegram_bot,
                self.notification_manager,
                self.scheduler
            ]
            
            for component in components_to_stop:
                if hasattr(component, 'emergency_stop'):
                    component.emergency_stop()
                elif hasattr(component, 'stop'):
                    component.stop()
                    
            # Terminate threads if necessary after timeout
            for thread in self.threads:
                if thread.is_alive():
                    thread.join(timeout=2.0)  # 2 second timeout
            
            self.running = False
            self.logger.warning("Emergency shutdown completed")
            
        except Exception as e:
            self.logger.critical(f"Error during emergency shutdown: {str(e)}")

    def handle_shutdown_signal(self, signum, frame):
        """Handle system shutdown signals (SIGINT, SIGTERM)."""
        signal_names = {
            signal.SIGINT: "SIGINT",
           signal.SIGTERM: "SIGTERM"
       }
        signal_name = signal_names.get(signum, f"signal {signum}")
       
        self.logger.info(f"Received {signal_name}, initiating shutdown...")
        self.stop()

    def start(self):
       """Start the QuantumFlow Bot."""
       if self.running:
           self.logger.warning("QuantumFlow Bot is already running")
           return
       
       self.logger.info("Starting QuantumFlow Bot...")
       
       # Start all components
       self._start_components()
       
       self.logger.info("QuantumFlow Bot started successfully")

    def stop(self):
       """Stop the QuantumFlow Bot gracefully."""
       if not self.running:
           self.logger.warning("QuantumFlow Bot is not running")
           return
       
       self.logger.info("Stopping QuantumFlow Bot...")
       
       # Stop all components
       self._stop_components()
       
       self.logger.info("QuantumFlow Bot stopped successfully")

    def restart(self):
       """Restart the QuantumFlow Bot."""
       self.logger.info("Restarting QuantumFlow Bot...")
       
       # Stop and start
       if self.running:
           self.stop()
       
       # Small delay to ensure clean shutdown
       time.sleep(2)
       
       self.start()
       
       self.logger.info("QuantumFlow Bot restarted successfully")

    def run_forever(self):
       """Run the QuantumFlow Bot continuously."""
       self.logger.info("Running QuantumFlow Bot in continuous mode...")
       
       try:
           # Start the bot
           self.start()
           
           # Keep the main thread alive to allow SIGINT/SIGTERM to work
           while self.running:
               time.sleep(1)
               
       except KeyboardInterrupt:
           self.logger.info("KeyboardInterrupt received, stopping...")
       except Exception as e:
           self.logger.critical(f"Unhandled exception in main loop: {str(e)}", exc_info=True)
           self._emergency_shutdown()
       finally:
           # Ensure clean shutdown
           if self.running:
               self.stop()

    def get_system_status(self) -> Dict[str, Any]:
       """Get the current system status and component health."""
       status = {
           "system_status": self.system_status,
           "running": self.running,
           "initialized": self.initialized,
           "uptime_seconds": 0,  # Will be calculated if running
           "components": {}
       }
       
       # Add component status
       for name, component in self.components.items():
           if hasattr(component, 'get_status'):
               status["components"][name] = component.get_status()
           else:
               status["components"][name] = "unknown"
       
       return status

# Entry point for the application
if __name__ == "__main__":
   try:
       bot = QuantumFlowBot("config/settings.json")  # Explicitly specify the config path
       bot.run_forever()
   except FileNotFoundError as e:
       logging.critical(f"Configuration file not found: {str(e)}")
       exit(1)
   except ValueError as e:
       logging.critical(f"Invalid configuration: {str(e)}")
       exit(1)
   except Exception as e:
       logging.critical(f"Unhandled exception: {str(e)}", exc_info=True)
       exit(1)